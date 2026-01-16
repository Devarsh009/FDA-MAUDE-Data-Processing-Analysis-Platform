# Free Deployment Guide - No Credit Card Required

## 🎯 Best Option: Render.com (FREE)

Render offers the best free tier for Flask apps with pandas/numpy.

### Why Render?
- ✅ **Completely FREE** - No credit card required
- ✅ **750 hours/month** - Enough for 24/7 operation
- ✅ **No size limits** - pandas & numpy work perfectly
- ✅ **Automatic deployments** - Push to GitHub = auto deploy
- ✅ **HTTPS included** - Free SSL certificates
- ✅ **All features work** - IMDRF Insights fully functional
- ⚠️ **Only downside**: Spins down after 15 minutes of inactivity (30-60 second cold start)

---

## 📋 Step-by-Step Deployment to Render

### Step 1: Sign Up (30 seconds)

1. Go to [render.com](https://render.com)
2. Click **"Get Started"**
3. Sign up with your **GitHub account** (easiest)
4. No credit card required!

### Step 2: Create Web Service (2 minutes)

1. Click **"New +"** → **"Web Service"**
2. Click **"Connect a repository"**
3. Authorize Render to access your GitHub
4. Find and select: **FDA-MAUDE-Data-Processing-Analysis-Platform**
5. Click **"Connect"**

### Step 3: Configure Service (2 minutes)

Fill in these settings:

**Basic Settings:**
- **Name**: `maude-processor` (or any name you like)
- **Region**: Choose closest to you (US East, EU, etc.)
- **Branch**: `main`
- **Root Directory**: Leave blank
- **Runtime**: `Python 3`

**Build & Deploy:**
- **Build Command**:
  ```bash
  pip install -r requirements-dev.txt
  ```

- **Start Command**:
  ```bash
  gunicorn -b 0.0.0.0:$PORT app:app --timeout 120 --workers 2
  ```

**Instance Type:**
- Select **"Free"** (at the bottom)

### Step 4: Add Environment Variables (1 minute)

Scroll down to **"Environment Variables"** and add these:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | `maude-secret-key-production-2024` |
| `TEST_ACCOUNTS_ENABLED` | `True` |
| `TEST_USER_EMAIL` | `test@maude.local` |
| `TEST_USER_PASSWORD` | `Test12345` |

*Optional (for email features):*
| Key | Value |
|-----|-------|
| `MAIL_USERNAME` | Your Gmail address |
| `MAIL_PASSWORD` | Your Gmail app password |
| `GROQ_API_KEY` | Your Groq API key (if you have one) |

### Step 5: Deploy! (5-10 minutes)

1. Click **"Create Web Service"** at the bottom
2. Wait for build to complete (5-10 minutes first time)
3. Watch the logs - you'll see:
   ```
   Installing dependencies...
   Building...
   Starting server...
   Your service is live at https://maude-processor.onrender.com
   ```

4. **Done!** Your app is now live! 🎉

---

## 🌐 Accessing Your App

Once deployed, you'll get a URL like:
```
https://maude-processor.onrender.com
```

**Login with:**
- Email: `test@maude.local`
- Password: `Test12345`

**Features Available:**
- ✅ MAUDE file upload and processing
- ✅ IMDRF code mapping
- ✅ IMDRF Prefix Insights (fully functional!)
- ✅ User authentication
- ✅ All local features work

---

## ⚠️ Important: Free Tier Limitations

### Inactivity Spin-Down
- App **sleeps after 15 minutes** of no activity
- First visit after sleep takes **30-60 seconds** to wake up
- Subsequent visits are instant

**Solutions:**
1. **Accept it** - 750 hours/month is enough for normal use
2. **Use UptimeRobot** - Free service to ping your app every 5 minutes (keeps it awake)
   - Sign up at [uptimerobot.com](https://uptimerobot.com)
   - Add monitor with your Render URL
   - Ping interval: 5 minutes

### Storage
- **512MB disk space** (plenty for this app)
- Uploaded files are **ephemeral** (cleared on redeploy)
- For permanent storage, consider adding a free database

---

## 🔄 Auto-Deployment from GitHub

Every time you push to GitHub, Render automatically:
1. Detects the push
2. Builds your app
3. Deploys the new version
4. No manual steps needed!

**To disable auto-deploy:**
- Go to service settings → Disable "Auto-Deploy"

---

## 🐛 Troubleshooting

### Build Fails
**Check logs** in Render dashboard for errors.

Common issues:
- **Missing requirements**: Add to `requirements-dev.txt`
- **Python version**: Render uses Python 3.7 by default
  - Add `runtime.txt` with: `python-3.11.0`

### App Won't Start
- Check **"Logs"** tab in Render dashboard
- Ensure gunicorn is installed
- Verify start command is correct

### 502 Bad Gateway
- App is still starting (wait 1-2 minutes)
- Or app crashed - check logs

### Environment Variables Not Working
- Redeploy after adding env vars
- Click **"Manual Deploy"** → **"Clear build cache & deploy"**

---

## 💾 Adding Database (Optional, FREE)

Render offers **free PostgreSQL** database:

### Add PostgreSQL (500MB free)
1. In dashboard, click **"New +"** → **"PostgreSQL"**
2. Name: `maude-db`
3. Select **"Free"** plan
4. Click **"Create Database"**
5. Copy the **Internal Database URL**
6. Add to your web service as `DATABASE_URL` environment variable

### Use in Your App
```python
# In config.py
DATABASE_URL = os.getenv("DATABASE_URL")

# For persistent file storage, upload metadata to DB
# For persistent files, use S3-compatible storage
```

---

## 📊 Other Free Options Comparison

### Railway.app
- **Free tier**: $5 credit/month
- **Pros**: Faster cold starts, better UX
- **Cons**: Limited hours, credit expires

**Best for**: Testing and development

### Fly.io
- **Free tier**: 3 VMs, 160GB bandwidth
- **Pros**: Global edge deployment, fast
- **Cons**: Requires credit card (not charged)

**Best for**: Global apps, lower latency

### Koyeb
- **Free tier**: 1 web service, 2GB RAM
- **Pros**: Simple, generous free tier
- **Cons**: Newer platform, less mature

**Best for**: Simple apps

---

## 🎯 Recommended Setup

**For Your Use Case** (MAUDE processor with IMDRF Insights):

✅ **Use Render.com** because:
- All pandas/numpy features work
- No size restrictions
- Generous free tier
- Simple deployment
- All your features are functional

**Optional enhancements:**
1. Add **UptimeRobot** to prevent sleep (keeps app warm)
2. Add **PostgreSQL** database for persistent storage
3. Use **Cloudinary** or **Imgbb** for file storage (both have free tiers)

---

## 📝 Summary

| Step | Time | Difficulty |
|------|------|------------|
| Sign up | 30 sec | Easy |
| Connect GitHub | 1 min | Easy |
| Configure | 2 min | Easy |
| Deploy | 5-10 min | Automatic |
| **Total** | **~10 min** | **Very Easy** |

**Cost**: $0.00 💰

**Result**: Fully functional MAUDE processor with IMDRF Insights, accessible worldwide! 🌎

---

## 🚀 Quick Start Command

If you prefer using `render.yaml` (included in repo):

```bash
# Push to GitHub
git push origin main

# Render will auto-detect render.yaml and use those settings
# Just click "Apply" in the dashboard
```

---

## ✅ Next Steps After Deployment

1. **Test your app**: Visit the Render URL
2. **Login**: Use test credentials
3. **Upload a file**: Test MAUDE processing
4. **Try IMDRF Insights**: Upload cleaned file
5. **Share the URL**: Your app is now public!

---

## 🆘 Need Help?

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Community Forum**: [community.render.com](https://community.render.com)
- **Check logs**: Dashboard → Your Service → Logs tab

---

**Your app is now ready for free deployment!** 🎉

No credit card, no charges, all features work. Enjoy! 🚀
