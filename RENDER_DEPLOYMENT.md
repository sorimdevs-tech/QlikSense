# Complete Render Deployment Guide

This guide provides step-by-step instructions to deploy the Qlik Sense Accelerator to Render.

---

## Prerequisites

Before starting, ensure you have:
1. ✅ GitHub account with repository access
2. ✅ Render.com account (sign up at https://render.com)
3. ✅ Qlik Cloud credentials (Client ID and Client Secret)

---

## Step 1: Push Code to GitHub

Your code is already at: `https://github.com/sorimdevs-tech/qlikscence`

If not, push your code:
```bash
cd your-project-folder
git remote add origin https://github.com/sorimdevs-tech/qlikscence.git
git add -A
git commit -m "Initial deployment commit"
git push -u origin main
```

---

## Step 2: Get Qlik Cloud Credentials

1. Go to your Qlik Cloud tenant: https://c8vlzp3sx6akvnh.in.qlikcloud.com
2. Login and navigate to **Console** → **API Keys**
3. Click **Create new API key**
4. Copy and save:
   - **Client ID**
   - **Client Secret** ⚠️ (save immediately - won't be shown again)
5. Create and save your own **API_KEY** (any random string)

---

## Step 3: Deploy Using Render Blueprint (Recommended)

### Step 3.1: Create Blueprint
1. Go to https://dashboard.render.com
2. Click **New +** → **Blueprint**
3. Connect your GitHub repository
4. Enter repo URL: `https://github.com/sorimdevs-tech/qlikscence`
5. Click **Connect**

### Step 3.2: Configure Blueprint
Render will detect `render.yaml` and show two services:

#### Service 1: qlik-api (Backend)
| Field | Value |
|-------|-------|
| Name | qlik-api |
| Root Directory | `/` |
| Build Command | `pip install -r qlik_app/qlik/qlik-fastapi-backend/requirements.txt --no-cache-dir` |
| Start Command | `uvicorn qlik_app.qlik.qlik-fastapi-backend.main:app --host 0.0.0.0 --port $PORT` |

#### Service 2: qlik-frontend (Frontend)
| Field | Value |
|-------|-------|
| Name | qlik-frontend |
| Root Directory | `/` |
| Build Command | `cd qlik_app/converter/csv && npm install && npm run build` |
| Publish Directory | `qlik_app/converter/csv/dist` |

### Step 3.3: Add Environment Variables

Click **Add Environment Variable Group** and add:

| Key | Value |
|-----|-------|
| `QLIK_CLIENT_ID` | (your Qlik Client ID) |
| `QLIK_CLIENT_SECRET` | (your Qlik Client Secret) |
| `API_KEY` | (your custom API key) |
| `QLIK_TENANT_URL` | `https://c8vlzp3sx6akvnh.in.qlikcloud.com` |
| `QLIK_API_BASE_URL` | `https://c8vlzp3sx6akvnh.in.qlikcloud.com/api/v1` |
| `PYTHON_VERSION` | `3.11` |

### Step 3.4: Deploy
1. Click **Apply**
2. Wait for deployment to complete (5-10 minutes)
3. Check build logs for any errors

---

## Step 4: Manual Deployment (Alternative)

### Step 4.1: Create Backend Service

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `qlik-api` |
| **Repo** | `https://github.com/sorimdevs-tech/qlikscence.git` |
| **Branch** | `main` |
| **Root Directory** | `/` |
| **Build Command** | `pip install -r qlik_app/qlik/qlik-fastapi-backend/requirements.txt --no-cache-dir` |
| **Start Command** | `uvicorn qlik_app.qlik.qlik-fastapi-backend.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | `Free` |

4. Click **Create Web Service**
5. Go to **Environment** tab and add:

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.11` |
| `QLIK_CLIENT_ID` | (your Qlik Client ID) |
| `QLIK_CLIENT_SECRET` | (your Qlik Client Secret) |
| `API_KEY` | (your custom API key) |
| `QLIK_TENANT_URL` | `https://c8vlzp3sx6akvnh.in.qlikcloud.com` |
| `QLIK_API_BASE_URL` | `https://c8vlzp3sx6akvnh.in.qlikcloud.com/api/v1` |

### Step 4.2: Create Frontend Service

1. Go to https://dashboard.render.com
2. Click **New +** → **Static Site**
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `qlik-frontend` |
| **Repo** | `https://github.com/sorimdevs-tech/qlikscence.git` |
| **Branch** | `main` |
| **Root Directory** | `/` |
| **Build Command** | `cd qlik_app/converter/csv && npm install && npm run build` |
| **Publish Directory** | `qlik_app/converter/csv/dist` |
| **Plan** | `Free` |

4. Click **Create Static Site**
5. Go to **Environment** tab and add:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://qlik-api.onrender.com` |

---

## Step 5: Verify Deployment

### Check Backend API
1. Visit: `https://qlik-api.onrender.com/`
2. Should see: `{"message": "Qlik FastAPI Backend...", "status": "running"}`
3. Health check: `https://qlik-api.onrender.com/health`

### Check Frontend
1. Visit: `https://qlik-frontend.onrender.com`
2. Should see your React application

---

## Troubleshooting

### Build Fails - Requirements.txt Not Found
**Error:** `Could not open requirements file: [Errno 2] No such file or directory: 'requirements.txt'`

**Solution:**
- Ensure `rootDirectory` is `/`
- Use full path: `qlik_app/qlik/qlik-fastapi-backend/requirements.txt`

### CORS Errors
**Error:** `Access to fetch at '...' from origin '...' has been blocked by CORS policy`

**Solution:**
- CORS is already configured in `main.py` to allow all origins
- If issues persist, check the frontend URL is correct

### Qlik Connection Failed
**Error:** `Invalid tenant or credentials`

**Solution:**
1. Verify `QLIK_CLIENT_ID` and `QLIK_CLIENT_SECRET` are correct
2. Ensure tenant URL format: `https://your-tenant.qlikcloud.com`
3. Check API key is active in Qlik Cloud Console

### Service Won't Start
**Error:** `Application failed to respond`

**Solution:**
1. Check logs in Render Dashboard
2. Ensure `$PORT` is used in start command
3. Verify all environment variables are set

---

## URLs After Deployment

| Service | URL |
|---------|-----|
| Backend API | `https://qlik-api.onrender.com` |
| Frontend | `https://qlik-frontend.onrender.com` |
| API Health | `https://qlik-api.onrender.com/health` |

---

## Free Tier Limitations

- Services sleep after 15 minutes of inactivity
- First request after sleep may take 30-60 seconds
- Build time limit: 10 minutes
- Memory limit: 512MB

For production, upgrade to paid plan.

---

## Updating Deployment

To deploy new changes:
1. Push changes to GitHub
2. Go to Render Dashboard
3. Click **Manual Deploy** → **Deploy latest commit**
