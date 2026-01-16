# IMDRF Prefix Insights - Implementation Guide

## Overview
The IMDRF Prefix Insights feature has been successfully integrated into your Flask web application. This feature allows users to analyze IMDRF codes at the prefix level, comparing manufacturers against universal and prefix-specific baselines.

## What Was Changed

### ✅ Files Created/Modified

1. **NEW: `backend/imdrf_insights.py`** (Backend Module)
   - Contains all data processing logic for IMDRF prefix analysis
   - Functions for extracting prefixes, exploding data, aggregating by time grain
   - Calculation of universal and prefix-specific baselines
   - Read-only operations - no data mutation

2. **NEW: `templates/imdrf_insights.html`** (Frontend Template)
   - Beautiful, responsive HTML page with Plotly visualizations
   - File upload interface for cleaned CSV files
   - Interactive controls for prefix selection, date aggregation, manufacturer selection
   - Real-time chart rendering with baseline overlays
   - Summary statistics table

3. **MODIFIED: `app.py`** (Flask Routes)
   - Added import for IMDRF insights module
   - Added route `/imdrf-insights` for the main page
   - Added API endpoint `/api/imdrf-insights/prepare` for file upload
   - Added API endpoint `/api/imdrf-insights/top-manufacturers` for manufacturer selection
   - Added API endpoint `/api/imdrf-insights/analyze` for analysis execution

4. **MODIFIED: `templates/index.html`** (Navigation)
   - Added navigation button to access IMDRF Insights page

5. **NO CHANGE: `requirements.txt`**
   - All required libraries (pandas, numpy, plotly) were already present

### ✅ Streamlit Files Removed
- Deleted: `pages/2_IMDRF_Prefix_Insights.py` (Streamlit version)
- Deleted: Previous `IMDRF_INSIGHTS_GUIDE.md`

## Features Implemented

### Core Functionality

#### 1. IMDRF Prefix Extraction
- Splits multi-code entries (e.g., "A050114 | A0703xx")
- Extracts first 3 alphanumeric characters
- Uppercases prefixes (A05, A07, etc.)
- Skips invalid/short codes

#### 2. Two Baseline Calculations
- **Universal Mean**: Average across ALL IMDRF-coded events (all prefixes)
- **Prefix-Specific Mean**: Average for selected prefix only
- Both displayed as horizontal reference lines

#### 3. User Controls
- CSV file uploader (cleaned data only)
- IMDRF prefix selector (auto-populated from data)
- Date aggregation: Daily / Weekly / Monthly
- Manufacturer multi-select (defaults to top 5 by volume)
- Threshold sensitivity slider (k = 0.5 to 5.0, default 2.0)

#### 4. Visualization
- Interactive Plotly line chart with:
  - One line per selected manufacturer
  - Universal mean baseline (gray dashed line)
  - Prefix mean baseline (red dotted line)
  - Upper/lower threshold bands (mean ± k×std)
  - Hover tooltips with unified x-axis

#### 5. Summary Statistics
- Table showing per-manufacturer metrics:
  - Total events
  - Mean per period
  - Max per period
  - Count of periods with events

### Edge Cases Handled
✅ Missing IMDRF Code column → Clear error message
✅ No parsable dates → Error with format hint
✅ Blank/NaN IMDRF codes → Skipped gracefully
✅ Invalid date formats → Excluded from time-series
✅ Selected prefix with no data → Warning message
✅ Manufacturer gaps in timeline → Filled with zeros
✅ Session management → Files stored per user session

## How to Use

### Starting the Application

```bash
# 1. Activate virtual environment (if using one)
source .venv/Scripts/activate  # Git Bash on Windows
# or
.venv\Scripts\activate  # CMD on Windows

# 2. Start Flask application
python app.py
```

### Accessing IMDRF Insights

1. **Open your browser** and navigate to: [http://localhost:5000](http://localhost:5000)
2. **Log in** with your credentials (test account: test@maude.local / Test12345)
3. **Click "IMDRF Insights"** button in the top navigation
4. **Upload a cleaned CSV** file (must have been processed by the MAUDE pipeline)
5. **Select an IMDRF prefix** from the dropdown
6. **Choose manufacturers** to compare (top 5 are pre-selected)
7. **Adjust settings** (date grain, threshold)
8. **Click "Analyze Trends"** to generate the visualization

### Required CSV Format

Your uploaded CSV must contain:
- **IMDRF Code** column (may contain pipe-separated multiple codes)
- **Manufacturer** or **Manufacturer Name** column
- **Event Date** (preferred) or **Date Received** column in DD-MM-YYYY format

## Technical Details

### Data Flow

```
1. User uploads cleaned CSV
   ↓
2. Backend extracts IMDRF prefixes and validates data
   ↓
3. User selects prefix and manufacturers
   ↓
4. Backend performs analysis:
   - Calculates universal mean (all events)
   - Calculates prefix mean (selected prefix)
   - Aggregates time-series per manufacturer
   - Computes threshold bands
   ↓
5. Frontend renders Plotly chart with baselines
   ↓
6. Display summary statistics table
```

### API Endpoints

#### POST `/api/imdrf-insights/prepare`
Uploads and prepares CSV for analysis
- **Input**: FormData with CSV file
- **Output**: JSON with file_id, prefixes list, manufacturers list, row counts

#### GET `/api/imdrf-insights/top-manufacturers`
Gets top 5 manufacturers for a specific prefix
- **Input**: Query params (prefix, file_id)
- **Output**: JSON with top_manufacturers list

#### POST `/api/imdrf-insights/analyze`
Performs full IMDRF insights analysis
- **Input**: JSON with file_id, prefix, manufacturers, grain, threshold_k
- **Output**: JSON with means, thresholds, time-series data, statistics

### Security Features
- **Login required**: All endpoints require authentication
- **Session-based file storage**: Files are isolated per user
- **Secure filename handling**: Uses werkzeug's secure_filename
- **No data mutation**: Analysis is completely read-only

## File Structure

```
Maude/
├── app.py                           # Flask app (modified - added routes)
├── backend/
│   ├── imdrf_insights.py           # NEW: IMDRF analysis logic
│   ├── processor.py                # Existing: MAUDE data processor
│   └── ...
├── templates/
│   ├── imdrf_insights.html         # NEW: Insights page UI
│   ├── index.html                  # Modified: Added navigation link
│   └── ...
├── requirements.txt                 # No changes needed
└── ...
```

## Key Implementation Highlights

### 1. Production-Safe Design
- Robust error handling at every step
- Clear error messages for missing data
- No crashes on edge cases

### 2. Efficient Processing
- Pandas-based data transformations
- Vectorized operations for speed
- Minimal memory footprint

### 3. User-Friendly Interface
- Intuitive step-by-step workflow
- Real-time feedback messages
- Responsive design for mobile

### 4. Clean Code
- Well-documented functions
- Separation of concerns (backend/frontend)
- RESTful API design

## Comparison: Flask vs Streamlit Implementation

You requested that the functionality be moved from Streamlit to Flask. Here's what changed:

| Aspect | Streamlit (Removed) | Flask (Implemented) |
|--------|---------------------|---------------------|
| **File** | `pages/2_IMDRF_Prefix_Insights.py` | `templates/imdrf_insights.html` + routes in `app.py` |
| **Navigation** | Sidebar automatic | Button in main page |
| **State Management** | Streamlit session state | Flask session + file IDs |
| **Charts** | Plotly via st.plotly_chart | Plotly.js CDN (client-side) |
| **Deployment** | Separate Streamlit process | Integrated in Flask app |
| **Authentication** | No auth | Flask-Login protected |
| **URL** | Separate Streamlit port | `/imdrf-insights` route |

## Troubleshooting

### "File not found. Please upload again."
→ Session expired or file was cleaned up. Re-upload the CSV file.

### "Missing required column: 'IMDRF Code'"
→ Ensure your CSV was processed by the MAUDE cleaning pipeline first.

### "No parsable dates found"
→ Check that dates are in DD-MM-YYYY format (not MM-DD-YYYY or YYYY-MM-DD).

### "No valid IMDRF codes found"
→ Verify that the IMDRF Code column contains data (not all blanks).

### Chart shows no data
→ Try selecting different manufacturers or a different prefix.

### Flask app won't start
→ Check if port 5000 is already in use: `netstat -ano | findstr :5000` (Windows)

## Next Steps

### Recommended Enhancements (Optional)
1. **Export functionality**: Add CSV/Excel export of filtered results
2. **Date range filter**: Allow users to zoom into specific time periods
3. **Multiple prefix comparison**: Compare multiple prefixes simultaneously
4. **Save/load analysis**: Save analysis configurations for later reuse
5. **Email reports**: Send analysis results via email

### Deployment Considerations
1. **Production WSGI server**: Use Gunicorn or Waitress instead of Flask dev server
2. **File cleanup**: Implement periodic cleanup of old uploaded files
3. **Caching**: Cache prepared data to avoid re-processing
4. **Database storage**: Store analysis results in database for history

## Summary

✅ **Streamlit files removed** - No more Streamlit dependency for this feature
✅ **Flask integration complete** - Fully integrated into existing web app
✅ **All functionality preserved** - Same analysis capabilities
✅ **Better UX** - More polished interface with authentication
✅ **Production-ready** - Robust error handling and security

The IMDRF Prefix Insights feature is now fully operational in your Flask web application at:
**http://localhost:5000/imdrf-insights**

All core requirements have been met:
- Read-only analysis (no data mutation)
- Two baseline calculations (universal and prefix-specific)
- Manufacturer comparison time-series
- Interactive Plotly visualization
- Configurable date aggregation
- Threshold bands
- Summary statistics

Enjoy analyzing your IMDRF data! 🎉
