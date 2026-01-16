"""
IMDRF Prefix Insights Analysis Module

This module provides functionality to analyze IMDRF codes at the prefix level,
comparing manufacturers against universal and prefix-specific baselines.

This is a read-only analysis module that does not modify the original data.
"""

import re
from datetime import datetime
import pandas as pd
import numpy as np


def parse_ddmmyyyy_to_date(s):
    """
    Parse DD-MM-YYYY date string to pandas Timestamp.

    Args:
        s: Date string in DD-MM-YYYY format

    Returns:
        pandas.Timestamp or pd.NaT if invalid
    """
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip()
    if not s or s.lower() in ["nan", "nat", "none", ""]:
        return pd.NaT
    try:
        return pd.to_datetime(s, format="%d-%m-%Y", errors="coerce")
    except Exception:
        return pd.NaT


def extract_imdrf_prefixes(imdrf_code_str):
    """
    Extract IMDRF prefixes from a code string.

    Rules:
    - Split on "|" (pipe)
    - For each token, extract first 3 alphanumeric characters
    - Uppercase the result
    - Skip if fewer than 3 alphanumeric characters

    Args:
        imdrf_code_str: String containing IMDRF codes (may be pipe-separated)

    Returns:
        list of prefixes (e.g., ["A05", "A07"])
    """
    if pd.isna(imdrf_code_str):
        return []

    s = str(imdrf_code_str).strip()
    if not s or s.lower() in ["nan", "nat", "none", ""]:
        return []

    tokens = s.split("|")
    prefixes = []

    for token in tokens:
        token = token.strip()
        # Extract only alphanumeric characters
        alphanumeric = re.sub(r'[^A-Za-z0-9]', '', token)

        # Take first 3 characters and uppercase
        if len(alphanumeric) >= 3:
            prefix = alphanumeric[:3].upper()
            prefixes.append(prefix)

    return prefixes


def explode_imdrf_prefixes(df, imdrf_col, date_col):
    """
    Explode rows so each IMDRF prefix gets its own row.

    Args:
        df: DataFrame with IMDRF codes
        imdrf_col: Name of the IMDRF Code column
        date_col: Name of the date column to parse

    Returns:
        DataFrame with additional columns: 'imdrf_prefix', 'parsed_date'
        Only includes rows with valid IMDRF prefixes
    """
    df = df.copy()
    df['_prefixes'] = df[imdrf_col].apply(extract_imdrf_prefixes)

    # Filter to rows with at least one prefix
    df_with_prefixes = df[df['_prefixes'].apply(len) > 0].copy()

    if df_with_prefixes.empty:
        return pd.DataFrame()

    # Explode so each prefix gets its own row
    df_exploded = df_with_prefixes.explode('_prefixes')
    df_exploded = df_exploded.rename(columns={'_prefixes': 'imdrf_prefix'})

    # Parse dates
    df_exploded['parsed_date'] = df_exploded[date_col].apply(parse_ddmmyyyy_to_date)

    return df_exploded


def aggregate_by_grain(df, date_col, grain='W'):
    """
    Aggregate counts by date grain.

    Args:
        df: DataFrame with parsed dates
        date_col: Name of the parsed date column
        grain: 'D' (daily), 'W' (weekly), 'M' (monthly)

    Returns:
        Series with date index and counts
    """
    df = df[df[date_col].notna()].copy()

    if df.empty:
        return pd.Series(dtype=int)

    # Group by the specified grain
    counts = df.set_index(date_col).resample(grain).size()

    return counts


def find_date_column(df):
    """Find the appropriate date column (prefer Event Date, fallback to Date Received)."""
    for col in df.columns:
        if col.strip().lower() == "event date":
            return col

    for col in df.columns:
        if col.strip().lower() == "date received":
            return col

    return None


def find_column(df, target):
    """Find a column by normalized name."""
    target_lower = target.strip().lower()
    for col in df.columns:
        if col.strip().lower() == target_lower:
            return col
    return None


def analyze_imdrf_insights(df, selected_prefix, selected_manufacturers, grain='W', threshold_k=2.0):
    """
    Perform IMDRF prefix insights analysis.

    Args:
        df: DataFrame with exploded IMDRF prefixes and parsed dates
        selected_prefix: IMDRF prefix to analyze (e.g., "A05")
        selected_manufacturers: List of manufacturer names to compare
        grain: Date aggregation grain ('D', 'W', 'M')
        threshold_k: Standard deviation multiplier for thresholds

    Returns:
        dict with analysis results including:
        - universal_mean: Mean across all IMDRF events
        - prefix_mean: Mean for selected prefix
        - manufacturer_series: Dict of time-series per manufacturer
        - date_range: Complete date range for plotting
        - statistics: Summary statistics per manufacturer
    """
    mfr_col = None
    for col in df.columns:
        if col.strip().lower() in ["manufacturer", "manufacturer name"]:
            mfr_col = col
            break

    if mfr_col is None:
        raise ValueError("Manufacturer column not found")

    # Filter to rows with valid dates
    df_with_dates = df[df['parsed_date'].notna()].copy()

    if df_with_dates.empty:
        raise ValueError("No valid dates found in dataset")

    # A) Universal mean baseline (all IMDRF-coded events, all prefixes)
    universal_counts = aggregate_by_grain(df_with_dates, 'parsed_date', grain)
    universal_mean = float(universal_counts.mean()) if len(universal_counts) > 0 else 0.0

    # Filter to selected prefix
    df_prefix = df_with_dates[df_with_dates['imdrf_prefix'] == selected_prefix].copy()

    if df_prefix.empty:
        raise ValueError(f"No data found for prefix '{selected_prefix}'")

    # B) Prefix-specific mean baseline (selected prefix, all manufacturers)
    prefix_counts = aggregate_by_grain(df_prefix, 'parsed_date', grain)
    prefix_mean = float(prefix_counts.mean()) if len(prefix_counts) > 0 else 0.0
    prefix_std = float(prefix_counts.std()) if len(prefix_counts) > 0 else 0.0

    # Calculate thresholds
    upper_threshold = prefix_mean + threshold_k * prefix_std
    lower_threshold = max(0.0, prefix_mean - threshold_k * prefix_std)

    # Filter to selected manufacturers
    df_selected = df_prefix[df_prefix[mfr_col].isin(selected_manufacturers)].copy()

    if df_selected.empty:
        raise ValueError(f"No data found for selected manufacturers with prefix '{selected_prefix}'")

    # Create time-series for each manufacturer
    manufacturer_series = {}
    all_dates = set()

    for mfr in selected_manufacturers:
        df_mfr = df_selected[df_selected[mfr_col] == mfr]
        mfr_counts = aggregate_by_grain(df_mfr, 'parsed_date', grain)
        manufacturer_series[mfr] = mfr_counts
        if len(mfr_counts) > 0:
            all_dates.update(mfr_counts.index)

    # Create a complete date range
    if all_dates:
        date_range = pd.date_range(
            start=min(all_dates),
            end=max(all_dates),
            freq=grain
        )

        # Reindex each manufacturer series to fill gaps with 0
        for mfr in manufacturer_series:
            manufacturer_series[mfr] = manufacturer_series[mfr].reindex(date_range, fill_value=0)
    else:
        date_range = pd.DatetimeIndex([])

    # Calculate summary statistics per manufacturer
    statistics = []
    for mfr, series in manufacturer_series.items():
        total_events = int(series.sum())
        mean_per_period = float(series.mean())
        max_per_period = int(series.max())
        periods_with_events = int((series > 0).sum())

        statistics.append({
            "manufacturer": mfr,
            "total_events": total_events,
            "mean_per_period": round(mean_per_period, 2),
            "max_per_period": max_per_period,
            "periods_with_events": periods_with_events
        })

    return {
        "universal_mean": round(universal_mean, 2),
        "prefix_mean": round(prefix_mean, 2),
        "prefix_std": round(prefix_std, 2),
        "upper_threshold": round(upper_threshold, 2),
        "lower_threshold": round(lower_threshold, 2),
        "manufacturer_series": manufacturer_series,
        "date_range": date_range,
        "statistics": statistics,
        "grain": grain,
        "selected_prefix": selected_prefix
    }


def prepare_data_for_insights(file_path):
    """
    Read and prepare data for IMDRF insights analysis.

    Args:
        file_path: Path to cleaned CSV or Excel file

    Returns:
        dict with:
        - df_exploded: DataFrame with exploded IMDRF prefixes
        - all_prefixes: List of all available prefixes
        - all_manufacturers: List of all manufacturers
        - date_col: Name of the date column used
    """
    # Read file (CSV or Excel)
    import os
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path, dtype=str)
    elif file_ext == '.csv':
        df = pd.read_csv(file_path, dtype=str, encoding="utf-8", on_bad_lines="skip")
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Please upload CSV, XLS, or XLSX file.")

    # Clean up string columns
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": "", "NaN": "", "None": ""})

    # Find required columns
    imdrf_col = find_column(df, "IMDRF Code")
    if imdrf_col is None:
        raise ValueError("Missing required column: 'IMDRF Code'")

    mfr_col = find_column(df, "Manufacturer")
    if mfr_col is None:
        mfr_col = find_column(df, "Manufacturer Name")
    if mfr_col is None:
        raise ValueError("Missing required column: 'Manufacturer' or 'Manufacturer Name'")

    date_col = find_date_column(df)
    if date_col is None:
        raise ValueError("Missing required date column: 'Event Date' or 'Date Received'")

    # Explode IMDRF prefixes
    df_exploded = explode_imdrf_prefixes(df, imdrf_col, date_col)

    if df_exploded.empty:
        raise ValueError("No valid IMDRF codes found in the dataset")

    # Filter to rows with valid dates
    df_with_dates = df_exploded[df_exploded['parsed_date'].notna()].copy()

    if df_with_dates.empty:
        raise ValueError(f"No parsable dates found in '{date_col}' column. Expected format: DD-MM-YYYY")

    # Get unique prefixes and manufacturers
    all_prefixes = sorted(df_with_dates['imdrf_prefix'].unique())
    all_manufacturers = sorted([m for m in df_with_dates[mfr_col].unique() if m.strip()])

    return {
        "df_exploded": df_with_dates,
        "all_prefixes": all_prefixes,
        "all_manufacturers": all_manufacturers,
        "date_col": date_col,
        "mfr_col": mfr_col,
        "total_rows": len(df),
        "rows_with_imdrf": len(df_exploded),
        "rows_with_dates": len(df_with_dates)
    }


def get_top_manufacturers_for_prefix(df_exploded, prefix, mfr_col, top_n=5):
    """
    Get top N manufacturers by volume for a specific IMDRF prefix.

    Args:
        df_exploded: DataFrame with exploded IMDRF prefixes
        prefix: IMDRF prefix to filter by
        mfr_col: Name of manufacturer column
        top_n: Number of top manufacturers to return

    Returns:
        list of top manufacturer names
    """
    df_prefix = df_exploded[df_exploded['imdrf_prefix'] == prefix]
    mfr_counts = df_prefix[mfr_col].value_counts()
    return mfr_counts.head(top_n).index.tolist()
