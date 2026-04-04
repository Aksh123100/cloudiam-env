# HuggingFace Deployment Guide - CloudIAMEnv

## ✅ Method 1: Web UI Upload (RECOMMENDED - Easiest!)

### Step 1: Create a Space
1. Go to https://huggingface.co/new-space
2. Fill in:
   - **Owner:** Your username
   - **Space name:** `cloudiam-env` (or any name)
   - **License:** MIT
   - **Select the Space SDK:** Docker
   - **Space hardware:** Free CPU basic (sufficient)
   - **Visibility:** Public

3. Click **Create Space**

### Step 2: Upload Files via Web Interface
1. Your Space will open with an "Upload files" button
2. Click "Upload files"
3. Drag and drop ALL files from CloudIAMEnv folder:
   - `env.py`
   - `tasks.py`
   - `baseline.py`
   - `main.py`
   - `inference.py`
   - `requirements.txt`
   - `Dockerfile`
   - `openenv.yaml`
   - `README.md`

4. Add commit message: "Initial CloudIAMEnv deployment"
5. Click "Commit to main"

### Step 3: Wait for Build
- HuggingFace will automatically:
  1. Build your Docker container (takes 2-5 minutes)
  2. Start your server
  3. Show "Running" status when ready

### Step 4: Test Your Space
Once "Running", test these URLs:
- `https://huggingface.co/spaces/YOUR_USERNAME/cloudiam-env` (Web UI)
- `https://YOUR_USERNAME-cloudiam-env.hf.space/health` (API)
- `https://YOUR_USERNAME-cloudiam-env.hf.space/docs` (Swagger docs)

---

## ✅ Method 2: Git with Access Token (If you prefer Git)

### Step 1: Create Access Token
1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name: `cloudiam-deployment`
4. Role: **Write**
5. Copy the token (starts with `hf_...`)

### Step 2: Clone and Push
```powershell
# Navigate to parent folder
cd C:\Users\akshs

# Clone the Space repository (replace YOUR_USERNAME)
git clone https://huggingface.co/spaces/YOUR_USERNAME/cloudiam-env
cd cloudiam-env

# Copy your files
Copy-Item ..\CloudIAMEnv\* . -Force

# Configure git
git config user.email "akshsinghal00@gmail.com"
git config user.name "Aksh Singhal"

# Add files
git add .
git commit -m "Initial CloudIAMEnv deployment"

# Push (use token as password when prompted)
git push
```

When prompted for password, paste your `hf_...` token.

---

## ✅ Method 3: Using openenv CLI (Most Professional)

### Step 1: Install OpenEnv CLI
```powershell
pip install openenv-core
```

### Step 2: Login to HuggingFace
```powershell
# Set your HF token
$env:HF_TOKEN = "hf_YOUR_TOKEN_HERE"

# Or use huggingface-cli
pip install huggingface-hub
huggingface-cli login
```

### Step 3: Push Your Environment
```powershell
cd C:\Users\akshs\CloudIAMEnv

# Push to HuggingFace Spaces
openenv push --repo-id YOUR_USERNAME/cloudiam-env
```

---

## 🐛 Troubleshooting

### Issue: "Git authentication failed"
**Solution:** Use Method 1 (Web UI) - no authentication needed!

### Issue: "Docker build failed"
**Check these:**
1. All files uploaded?
2. `Dockerfile` has correct content?
3. Check Build logs in Space settings

### Issue: "Space stuck on 'Building'"
**Wait:** Docker builds take 2-5 minutes. Check "Settings" → "Logs" for progress.

### Issue: "Runtime error after deployment"
**Check:**
1. Visit `https://YOUR_USERNAME-cloudiam-env.hf.space/health`
2. Check Space logs for Python errors
3. Ensure all dependencies in `requirements.txt`

---

## 📋 Pre-Flight Checklist

Before deploying, verify:
- [ ] All 9 files exist in CloudIAMEnv folder
- [ ] `baseline.py` runs successfully (`python baseline.py` → 1.0/1.0)
- [ ] `main.py` starts without errors (`python main.py`)
- [ ] `Dockerfile` has correct content
- [ ] `requirements.txt` has all dependencies

---

## 🎯 After Deployment

### 1. Test your endpoints:
```powershell
# Replace YOUR_USERNAME with your HF username
$BASE_URL = "https://YOUR_USERNAME-cloudiam-env.hf.space"

# Test health
curl "$BASE_URL/health"

# Test reset
curl -X POST "$BASE_URL/reset"

# Test tasks endpoint (hackathon requirement)
curl "$BASE_URL/tasks"

# Test baseline endpoint (hackathon requirement)
curl "$BASE_URL/baseline"
```

### 2. Submit to Hackathon
1. Copy your Space URL: `https://YOUR_USERNAME-cloudiam-env.hf.space`
2. Go to hackathon portal
3. Paste URL in submission form
4. Submit before deadline: **April 8, 2026, 11:59 PM IST**

---

## 💡 Tips for Success

1. **Use Method 1** if you're not familiar with Git
2. **Test locally first** before deploying
3. **Check Space logs** if something goes wrong
4. **Free CPU is enough** - this environment is lightweight
5. **Make Space Public** - judges need to access it

---

## 🆘 Need Help?

If you encounter issues:
1. Check Space logs: Space Settings → Logs
2. Test locally: `python main.py` should work
3. Verify Dockerfile builds: `docker build -t test .`
4. Ask on Discord: OpenEnv Hackathon community

Good luck! 🚀
