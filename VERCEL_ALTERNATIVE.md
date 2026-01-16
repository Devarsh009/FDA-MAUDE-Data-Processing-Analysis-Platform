# Vercel Deployment Alternative Solutions

## The Problem

Vercel has a 250MB unzipped serverless function size limit. With pandas + numpy, even the smallest versions exceed this limit:

- pandas 1.3.5 + numpy 1.21.6 ≈ 180-200MB
- Flask + dependencies ≈ 30MB
- Application code ≈ 10-20MB
- **Total: ~220-250MB** (cutting it very close)

## Solution 1: Split Architecture (Recommended for Vercel)

### Frontend (Vercel)
Deploy a lightweight Flask app that serves the UI only:
- Authentication pages
- File upload interface
- Results display

### Backend (External Service)
Deploy the heavy processing on a different platform:
- Railway / Render / Heroku (handles pandas/numpy)
- AWS Lambda with layers
- Google Cloud Run

**Files needed:**
```
vercel/ (Frontend)
├── app_frontend.py (UI only, no pandas)
├── templates/
└── requirements_frontend.txt (Flask only)

backend-service/ (External)
├── app_backend.py (Processing API)
├── backend/
└── requirements_backend.txt (Full dependencies)
```

## Solution 2: Use Vercel Edge Functions + External Storage

Store uploaded files in:
- AWS S3
- Vercel Blob Storage
- Cloudflare R2

Process files asynchronously:
- Queue jobs to external worker
- Return job ID to user
- Poll for completion

## Solution 3: Use Docker on Alternative Platform

**Recommended platforms that support Docker:**

### Option A: Railway.app
```bash
# Automatic deployment from GitHub
# Supports larger applications
# $5/month for starter plan
```

Advantages:
- No size limits
- Persistent storage
- Better for data processing apps
- One-click GitHub integration

### Option B: Render.com
```bash
# Free tier available
# Docker support
# Good for monolithic apps
```

Advantages:
- Free tier with 750 hours/month
- Automatic deployments
- Better performance for heavy apps

### Option C: Fly.io
```bash
# Modern platform
# Edge deployment
# Good pricing
```

Advantages:
- Global edge deployment
- Better cold start times
- Flexible scaling

## Solution 4: Optimize Current Approach Further

If staying on Vercel is critical:

### A. Remove IMDRF Insights Feature
```python
# In app.py, wrap insights routes in try/except
try:
    from backend.imdrf_insights import ...
    INSIGHTS_ENABLED = True
except ImportError:
    INSIGHTS_ENABLED = False

@app.route('/imdrf-insights')
@login_required
def imdrf_insights_page():
    if not INSIGHTS_ENABLED:
        return "Feature not available on this deployment", 503
    ...
```

### B. Use Polars Instead of Pandas
Polars is lighter and faster:
```txt
# requirements.txt
polars==0.19.0  # ~50MB lighter than pandas
```

Requires rewriting:
- `backend/processor.py`
- `backend/imdrf_insights.py`

### C. Use PyArrow + CSV Only
```txt
pyarrow==10.0.0
```

Remove Excel support, CSV only.

## Solution 5: Serverless Architecture

### Use Vercel for UI Only
```
/api/upload -> Upload to S3, return URL
/api/status -> Check processing status
/api/download -> Get results from S3
```

### Use AWS Lambda for Processing
```
Lambda function with:
- pandas/numpy in Lambda Layer (separate from function)
- Triggered by S3 upload
- Writes results back to S3
```

**Architecture:**
```
User -> Vercel (UI) -> S3 (Storage) -> Lambda (Processing) -> S3 (Results) -> Vercel (Display)
```

## Recommended: Railway Deployment

**Why Railway?**
- ✅ No 250MB limit
- ✅ Supports all dependencies
- ✅ Persistent storage
- ✅ Better for data processing
- ✅ GitHub integration
- ✅ Affordable ($5-10/month)

**Setup:**
1. Sign up at railway.app
2. Connect GitHub repository
3. Set environment variables
4. Deploy automatically

**railway.json:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn -b 0.0.0.0:$PORT app:app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Add to requirements-dev.txt:
```
gunicorn==21.2.0
```

## Current Status

**Latest commit:** `fb1ef7f`
- pandas 1.3.5 (older version)
- numpy 1.21.6 (older version)
- Aggressive .vercelignore

**Expected result:** Might work, but very close to limit (~220-240MB)

**If it still fails:**
1. Remove pandas entirely (disable all processing features)
2. Switch to Railway/Render (recommended)
3. Implement split architecture

## Quick Migration to Railway

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Link to GitHub
railway link

# 5. Add environment variables
railway variables set SECRET_KEY=your-secret-key

# 6. Deploy
git push
```

Railway will automatically:
- Detect Flask app
- Install requirements-dev.txt
- Start with gunicorn
- Provide public URL

**Cost:** ~$5-10/month (much more reliable than Vercel for this use case)

## Summary

| Platform | Size Limit | Cost | Complexity | Recommendation |
|----------|------------|------|------------|----------------|
| Vercel | 250MB | Free | High | ❌ Too small for pandas |
| Railway | None | $5-10/mo | Low | ✅ Best for this app |
| Render | None | Free tier | Low | ✅ Good alternative |
| Heroku | None | $7/mo | Low | ✅ Classic choice |
| AWS Lambda | 250MB* | Variable | High | ⚠️ Needs layers |

*Lambda layers allow 250MB per layer + 50MB function code

**Final Recommendation:** Migrate to Railway or Render for stress-free deployment with full features.
