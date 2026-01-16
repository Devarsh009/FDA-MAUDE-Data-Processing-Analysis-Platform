# Deployment Guide

## Vercel Deployment (Optimized)

### ✅ What Works on Vercel
- Main MAUDE data processing (file upload, cleaning, IMDRF mapping)
- User authentication (login, register, password reset)
- File download of cleaned data

### ⚠️ Limitations on Vercel
- **IMDRF Insights feature**: May have limited functionality due to:
  - Serverless function size constraints (250MB limit)
  - Ephemeral file system (uploaded files don't persist)
  - Stateless functions (session storage limitations)

### 📦 Dependency Management

We maintain multiple requirement files for different scenarios:

1. **`requirements.txt`** (Production - Vercel)
   - Optimized for Vercel deployment
   - Uses older, smaller versions of pandas (2.0.3) and numpy (1.24.3)
   - Excludes Streamlit, plotly, and other heavy dependencies
   - Total size: < 250MB unzipped

2. **`requirements-dev.txt`** (Local Development - Full Features)
   - All dependencies included
   - Latest versions of all libraries
   - IMDRF Insights fully functional
   - Streamlit dashboard included

3. **`requirements-minimal.txt`** (Absolute Minimum)
   - Core Flask functionality only
   - Smallest possible deployment

4. **`requirements-vercel.txt`** (Alternative Vercel Config)
   - Another optimization strategy
   - Can be used instead of requirements.txt

### 🚀 How to Deploy to Vercel

1. **Connect GitHub Repository**
   ```
   https://vercel.com/new
   ```

2. **Vercel Configuration**
   - Framework: Other
   - Build Command: (leave default)
   - Output Directory: (leave default)
   - Install Command: pip install -r requirements.txt

3. **Environment Variables**
   Set these in Vercel dashboard:
   ```
   SECRET_KEY=your-secret-key-here
   GROQ_API_KEY=your-groq-key (optional)
   MAIL_USERNAME=your-email@domain.com
   MAIL_PASSWORD=your-email-password
   TEST_ACCOUNTS_ENABLED=False (for production)
   ```

4. **Deploy**
   - Push to main branch triggers automatic deployment
   - Check build logs for any errors

### 🔧 Vercel Configuration Files

**`vercel.json`**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb"
      }
    }
  ],
  "functions": {
    "api/index.py": {
      "memory": 3008,
      "maxDuration": 60
    }
  }
}
```

**`.vercelignore`**
- Excludes unnecessary files (tests, cache, Streamlit pages, docs)
- Reduces deployment size

### 💻 Local Development (Full Features)

For full functionality including IMDRF Insights:

```bash
# Install full dependencies
pip install -r requirements-dev.txt

# Run Flask app
python app.py

# Or run Streamlit dashboard
streamlit run streamlit_app.py
```

Access at:
- Flask: http://localhost:5000
- Streamlit: http://localhost:8501

### 🐳 Alternative: Docker Deployment

For production with all features, consider Docker:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY . .
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

### ☁️ Alternative Hosting Platforms

If you need IMDRF Insights on production:

1. **Heroku** (better for larger apps)
   - Supports larger slug sizes
   - Persistent file system with add-ons
   - Better session management

2. **AWS Lambda** (with layers)
   - Use Lambda Layers for heavy dependencies
   - S3 for file storage
   - DynamoDB for session storage

3. **Google Cloud Run**
   - Container-based deployment
   - No size restrictions
   - Full Flask app support

4. **Railway / Render**
   - Similar to Heroku
   - Easy deployment
   - Better for monolithic apps

### 📊 Performance Notes

**Vercel (Serverless)**
- Cold start: 2-5 seconds
- Function timeout: 60 seconds
- Memory: 3008 MB (configured)
- Best for: Low-traffic, occasional processing

**Self-Hosted (Docker/VM)**
- Always warm (no cold starts)
- No timeout limits
- Custom memory allocation
- Best for: High-traffic, heavy processing

### 🔍 Troubleshooting Vercel Deployment

**Error: "Serverless Function size exceeds 250MB"**
- Ensure you're using `requirements.txt` (not requirements-dev.txt)
- Check `.vercelignore` is properly excluding files
- Verify pandas and numpy versions are downgraded

**Error: "No module named 'pandas'"**
- Check that requirements.txt is being used
- Verify build logs show successful pip install
- May need to clear Vercel cache

**IMDRF Insights not working**
- Expected on Vercel due to session/file storage limitations
- Use local deployment for full insights functionality
- Consider alternative hosting for production insights

### ✅ Recommended Setup

**For MVP / Demo**: Vercel (current setup)
- Free tier available
- Easy deployment
- Core features work

**For Production**: Self-hosted or Heroku
- All features functional
- Better performance
- No size limitations

### 📝 Summary

| Feature | Vercel | Local | Docker/Heroku |
|---------|--------|-------|---------------|
| MAUDE Processing | ✅ | ✅ | ✅ |
| Authentication | ✅ | ✅ | ✅ |
| File Download | ✅ | ✅ | ✅ |
| IMDRF Insights | ⚠️ | ✅ | ✅ |
| Streamlit Dashboard | ❌ | ✅ | ✅ |
| Cost | Free | Free | $7-15/mo |
| Setup Difficulty | Easy | Easy | Medium |

---

**Current Status**: Optimized for Vercel deployment with core features functional.

For questions or issues, check build logs at: https://vercel.com/dashboard
