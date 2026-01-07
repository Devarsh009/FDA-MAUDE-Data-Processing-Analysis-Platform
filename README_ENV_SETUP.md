# Environment Variable Setup

## GROQ_API_KEY Setup

The application requires a Groq API key for AI-assisted features (column identification, IMDRF mapping fallback, manufacturer normalization).

### Quick Setup (Current Session Only)

**Option 1: Using PowerShell Script**
```powershell
.\set_groq_key.ps1
```

**Option 2: Manual PowerShell Command**
```powershell
$env:GROQ_API_KEY = "your-api-key-here"
```

### Permanent Setup

**Option 1: PowerShell (Run as Administrator)**
```powershell
[System.Environment]::SetEnvironmentVariable("GROQ_API_KEY", "your-api-key-here", "User")
```

**Option 2: Windows GUI**
1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Go to **Advanced** tab → **Environment Variables**
3. Under **User variables**, click **New**
4. Variable name: `GROQ_API_KEY`
5. Variable value: (your API key)
6. Click **OK** on all dialogs
7. **Restart your terminal/IDE** for changes to take effect

### Get Your Groq API Key

1. Visit https://console.groq.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (you won't be able to see it again)

### Verify Setup

After setting the environment variable, verify it's set:
```powershell
echo $env:GROQ_API_KEY
```

Or in Python:
```python
import os
print(os.getenv('GROQ_API_KEY'))
```

### Note

- The API key is used for AI-assisted features only
- Core processing (deterministic mapping, date formatting, etc.) works without it
- However, some features like column identification fallback and manufacturer M&A verification require it
