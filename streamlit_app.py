"""
MAUDE Signal Dashboard (Streamlit)

Usage:
  pip install -r requirements.txt
  streamlit run streamlit_app.py

This app reads a cleaned MAUDE file (.xlsx/.xls/.csv) and provides
filters (Event Type, Manufacturer, IMDRF Code) and visualizations:
- 3D Plotly chart: X=date index, Y=rolling mean, Z=daily count + threshold planes
- 2D Plotly chart: daily counts, rolling mean, thresholds, spike/dip markers

Important: This file is independent of Flask app and does not call any LLMs.
"""

import os
import re
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# -----------------------------
# Helpers
# -----------------------------
DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")


def parse_ddmmyyyy_to_date(s: str):
    """Parse DD-MM-YYYY to pandas.Timestamp; return NaT if invalid."""
    if s is None:
        return pd.NaT
    s = str(s).strip()
    if not s or s.lower() == "nan":
        return pd.NaT
    if not DATE_RE.match(s):
        return pd.NaT
    try:
        return pd.to_datetime(s, format="%d-%m-%Y", errors="coerce")
    except Exception:
        return pd.NaT


def normalize_text_cell(x) -> str:
    """Safe text normalization for filters only (does not modify stored file)."""
    if x is None:
        return ""
    s = str(x).strip()
    if s.lower() == "nan":
        return ""
    return s


def safe_read_dataset(uploaded_file_or_path: str) -> pd.DataFrame:
    """
    Read Excel or CSV reliably.
    You can pass an uploaded file object from Streamlit or a filesystem path.
    """
    # Streamlit uploaded file has .name and .read()
    name = getattr(uploaded_file_or_path, "name", None)
    if name is None and isinstance(uploaded_file_or_path, str):
        name = uploaded_file_or_path

    ext = os.path.splitext(str(name).lower())[1]

    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(uploaded_file_or_path, dtype=str)
    elif ext == ".csv":
        df = pd.read_csv(uploaded_file_or_path, dtype=str, encoding="utf-8", on_bad_lines="skip")
    else:
        raise ValueError("Unsupported file type. Upload .xlsx, .xls, or .csv")

    # Keep original columns, but ensure strings and strip whitespace
    for c in df.columns:
        df[c] = df[c].astype(str).replace({"nan": ""}).map(lambda v: v.strip())

    return df


def find_col(df: pd.DataFrame, target: str) -> str | None:
    """Find a column by normalized header, without renaming the dataframe."""
    t = target.strip().lower()
    for c in df.columns:
        if str(c).strip().lower() == t:
            return c
    return None


def series_daily_counts(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """
    Build daily count series. Drops NaT dates.
    Returns dataframe with ['date', 'count'].
    """
    d = df.copy()
    d["_date"] = d[date_col].apply(parse_ddmmyyyy_to_date)
    d = d.dropna(subset=["_date"])
    if d.empty:
        return pd.DataFrame(columns=["date", "count"]) 

    g = d.groupby(d["_date"].dt.date).size().reset_index(name="count")
    g = g.rename(columns={"_date": "date"})
    g["date"] = pd.to_datetime(g["date"])
    g = g.sort_values("date").reset_index(drop=True)
    return g


def make_3d_figure(ts: pd.DataFrame, roll_window: int, k_sigma: float):
    """
    3D chart:
      X = date index
      Y = rolling mean
      Z = count
    plus threshold plane at upper/lower thresholds.
    """
    if ts.empty:
        return None

    counts = ts["count"].astype(float).to_numpy()
    mean = float(np.mean(counts))
    std = float(np.std(counts, ddof=0))
    upper = mean + k_sigma * std
    lower = max(0.0, mean - k_sigma * std)

    ts = ts.copy()
    ts["roll_mean"] = ts["count"].rolling(window=roll_window, min_periods=1).mean()
    ts["x"] = np.arange(len(ts), dtype=float)  # numeric x for 3D stability

    # Main 3D trajectory
    fig = go.Figure()

    fig.add_trace(
        go.Scatter3d(
            x=ts["x"],
            y=ts["roll_mean"],
            z=ts["count"],
            mode="lines+markers",
            name="Daily count trajectory",
        )
    )

    # Threshold planes: create a rectangular surface across x and y ranges
    x_min, x_max = float(ts["x"].min()), float(ts["x"].max())
    y_min, y_max = float(ts["roll_mean"].min()), float(ts["roll_mean"].max())

    X = np.array([[x_min, x_max], [x_min, x_max]])
    Y = np.array([[y_min, y_min], [y_max, y_max]])

    Z_upper = np.array([[upper, upper], [upper, upper]])
    Z_lower = np.array([[lower, lower], [lower, lower]])

    fig.add_trace(
        go.Surface(
            x=X,
            y=Y,
            z=Z_upper,
            name="Upper threshold",
            showscale=False,
            opacity=0.25,
        )
    )

    fig.add_trace(
        go.Surface(
            x=X,
            y=Y,
            z=Z_lower,
            name="Lower threshold",
            showscale=False,
            opacity=0.25,
        )
    )

    # Axis ticks: map x back to date labels
    tickvals = ts["x"].iloc[:: max(1, len(ts) // 8)].tolist()
    ticktext = ts["date"].dt.strftime("%d-%m-%Y").iloc[:: max(1, len(ts) // 8)].tolist()

    fig.update_layout(
        height=650,
        scene=dict(
            xaxis=dict(title="Date", tickvals=tickvals, ticktext=ticktext),
            yaxis=dict(title=f"Rolling mean (window={roll_window})"),
            zaxis=dict(title="Daily count"),
        ),
        margin=dict(l=0, r=0, t=35, b=0),
        title="3D view: Date vs Rolling Mean vs Daily Count",
        legend=dict(orientation="h"),
    )

    return fig, mean, lower, upper


def make_2d_figure(ts: pd.DataFrame, roll_window: int, k_sigma: float):
    """
    2D chart for readability:
      - daily count
      - rolling mean
      - upper/lower thresholds
      - spike/dip markers
    """
    if ts.empty:
        return None

    counts = ts["count"].astype(float).to_numpy()
    mean = float(np.mean(counts))
    std = float(np.std(counts, ddof=0))
    upper = mean + k_sigma * std
    lower = max(0.0, mean - k_sigma * std)

    ts = ts.copy()
    ts["roll_mean"] = ts["count"].rolling(window=roll_window, min_periods=1).mean()
    ts["spike"] = ts["count"] > upper
    ts["dip"] = ts["count"] < lower

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=ts["date"], y=ts["count"], mode="lines+markers", name="Daily count"))
    fig.add_trace(go.Scatter(x=ts["date"], y=ts["roll_mean"], mode="lines", name="Rolling mean"))
    fig.add_trace(go.Scatter(x=ts["date"], y=[upper] * len(ts), mode="lines", name="Upper threshold"))
    fig.add_trace(go.Scatter(x=ts["date"], y=[lower] * len(ts), mode="lines", name="Lower threshold"))

    # Spike markers
    if ts["spike"].any():
        fig.add_trace(
            go.Scatter(
                x=ts.loc[ts["spike"], "date"],
                y=ts.loc[ts["spike"], "count"],
                mode="markers",
                name="Spikes",
            )
        )

    # Dip markers
    if ts["dip"].any():
        fig.add_trace(
            go.Scatter(
                x=ts.loc[ts["dip"], "date"],
                y=ts.loc[ts["dip"], "count"],
                mode="markers",
                name="Dips",
            )
        )

    fig.update_layout(
        height=450,
        title="2D view: Daily counts with mean thresholds and spike/dip markers",
        xaxis_title="Date",
        yaxis_title="Count",
        margin=dict(l=0, r=0, t=35, b=0),
        legend=dict(orientation="h"),
    )

    return fig, mean, lower, upper


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="MAUDE Signal Dashboard", layout="wide")
st.title("MAUDE Signal Dashboard: Event Type + Manufacturer + IMDRF Code")
st.caption("Filters drive daily counts; dashboard shows mean baseline, threshold band, and spikes/dips.")

with st.sidebar:
    st.header("Data input")
    uploaded = st.file_uploader("Upload cleaned MAUDE file (.xlsx/.xls/.csv)", type=["xlsx", "xls", "csv"])
    st.divider()
    st.header("Signal settings")
    roll_window = st.number_input("Rolling mean window (days)", min_value=1, max_value=90, value=7, step=1)
    k_sigma = st.number_input("Threshold multiplier (k × std dev)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
    date_basis = st.selectbox("Date basis", ["Event Date", "Date Received"], index=0)

if not uploaded:
    st.info("Upload a cleaned MAUDE file to begin.")
    st.stop()

try:
    df = safe_read_dataset(uploaded)
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

# Find required columns without renaming
event_type_col = find_col(df, "Event Type")
mfr_col = find_col(df, "Manufacturer")
dp_col = None
for c in df.columns:
    if str(c).strip().lower() == "device problem":
        dp_col = c
        break
imdrf_col = find_col(df, "IMDRF Code")
event_text_col = find_col(df, "Event Text")

date_col = find_col(df, date_basis)

missing = []
if event_type_col is None:
    missing.append("Event Type")
if mfr_col is None:
    missing.append("Manufacturer")
if dp_col is None:
    missing.append("Device Problem")
if imdrf_col is None:
    missing.append("IMDRF Code")
if date_col is None:
    missing.append(date_basis)

if missing:
    st.error(f"Missing required columns: {', '.join(missing)}")
    st.stop()

# Prepare filter values
df[event_type_col] = df[event_type_col].map(normalize_text_cell)
df[mfr_col] = df[mfr_col].map(normalize_text_cell)
df[imdrf_col] = df[imdrf_col].map(normalize_text_cell)

event_types = sorted([x for x in df[event_type_col].unique() if x])
manufacturers = sorted([x for x in df[mfr_col].unique() if x])
imdrf_codes = sorted([x for x in df[imdrf_col].unique() if x])

c1, c2, c3 = st.columns(3)
with c1:
    sel_event_type = st.selectbox("Event Type", ["(Any)"] + event_types, index=0)
with c2:
    sel_mfr = st.selectbox("Manufacturer", ["(Any)"] + manufacturers, index=0)
with c3:
    sel_imdrf = st.selectbox("IMDRF Code", ["(Any)"] + imdrf_codes, index=0)

filtered = df.copy()
if sel_event_type != "(Any)":
    filtered = filtered[filtered[event_type_col] == sel_event_type]
if sel_mfr != "(Any)":
    filtered = filtered[filtered[mfr_col] == sel_mfr]
if sel_imdrf != "(Any)":
    filtered = filtered[filtered[imdrf_col] == sel_imdrf]

ts = series_daily_counts(filtered, date_col=date_col)

left, right = st.columns([2, 1])
with right:
    st.subheader("Summary")
    st.metric("Filtered rows", int(len(filtered)))
    st.metric("Days with events", int(len(ts)))
    if len(ts) > 0:
        counts = ts["count"].astype(float).to_numpy()
        st.metric("Mean daily count", float(np.mean(counts)))
        st.metric("Min daily count", float(np.min(counts)))
        st.metric("Max daily count", float(np.max(counts)))

st.divider()

if ts.empty:
    st.warning("No dated records after filtering (or selected date column has no parsable dates).")
    st.stop()

fig3d, mean3d, low3d, up3d = make_3d_figure(ts, roll_window=int(roll_window), k_sigma=float(k_sigma))
fig2d, mean2d, low2d, up2d = make_2d_figure(ts, roll_window=int(roll_window), k_sigma=float(k_sigma))

st.subheader("3D chart")
if fig3d is not None:
    st.plotly_chart(fig3d, use_container_width=True)
else:
    st.info("Insufficient data for 3D chart.")

st.subheader("2D chart (readable spike and dip view)")
if fig2d is not None:
    st.plotly_chart(fig2d, use_container_width=True)
else:
    st.info("Insufficient data for 2D chart.")

st.caption(
    f"Thresholds computed as mean ± k·std dev on daily counts; mean={mean2d:.3f}, lower={low2d:.3f}, upper={up2d:.3f}."
)
