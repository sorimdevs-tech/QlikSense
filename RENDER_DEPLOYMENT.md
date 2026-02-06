# Deploying to Render

This guide explains how to deploy the Qlik Sense Accelerator to Render.com.

## Prerequisites

1. **GitHub Account** with the repository pushed
2. **Render.com Account** (free tier works)
3. **Qlik Cloud Credentials** (Client ID and Client Secret)

## Deployment Steps

### Option 1: Using Render Blueprint (Recommended)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" and select "Blueprint"
3. Connect your GitHub repository
4. Render should detect the `render.yaml` file
5. Review the configuration and click "Apply"
6. Add your environment variables:
   - `QLIK_CLIENT_ID`: Your Qlik Cloud client ID
   - `QLIK_CLIENT_SECRET`: Your Qlik Cloud client secret
7. Wait for deployment to complete

### Option 2: Manual Deployment

#### 1. Deploy Backend (Web Service)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `qlik-api`
   - **Root Directory**: `qlik_app/qlik/qlik-fastapi-backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. Add Environment Variables:
   - `QLIK_CLIENT_ID`: Your Qlik Cloud client ID
   - `QLIK_CLIENT_SECRET`: Your Qlik Cloud client secret
   - `PYTHON_VERSION`: `3.11`
6. Click "Create Web Service"

#### 2. Deploy Frontend (Static Site)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" and select "Static Site"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `qlik-frontend`
   - **Root Directory**: `qlik_app/converter/csv`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
5. Add Environment Variables:
   - `VITE_API_URL`: Your backend URL (e.g., `https://qlik-api.onrender.com`)
6. Click "Create Static Site"

## Getting Qlik Cloud Credentials

1. Log in to your Qlik Cloud tenant
2. Go to https://your-tenant.qlikcloud.com/console/api-keys
3. Click "Create new API key"
4. Copy the **Client ID** and **Client Secret**
5. ⚠️ **Important**: Save the client secret immediately - it won't be shown again!

## Testing the Deployment

1. Backend API: `https://your-backend.onrender.com`
   - Visit `https://your-backend.onrender.com/` to see API info
   - Visit `https://your-backend.onrender.com/health` for health check

2. Frontend: `https://your-frontend.onrender.com`
   - Should load the React application

## Troubleshooting

### CORS Errors
- Make sure CORS is configured to allow your frontend domain
- Update `allow_origins` in `main.py` if needed

### Large Files Error
- If you see "File exceeds 100MB" error:
- Remove large files from the repository
- Use `.gitignore` for build artifacts
- Consider using a requirements.txt instead of committing venv

### Build Fails
- Check that Python version is set to 3.11
- Verify all dependencies are in requirements.txt
- Check Render build logs for specific errors

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `QLIK_CLIENT_ID` | Yes | Qlik Cloud API Client ID |
| `QLIK_CLIENT_SECRET` | Yes | Qlik Cloud API Client Secret |
| `PYTHON_VERSION` | No | Python version (default: 3.11) |
| `VITE_API_URL` | Frontend only | Backend API URL |

## Free Tier Limitations

- Services sleep after 15 minutes of inactivity
- Build time limits apply
- Limited compute resources

For production, consider upgrading to a paid plan.
