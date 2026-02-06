# Render Deployment Guide

## Quick Deploy (Using Blueprint)

1. Go to https://dashboard.render.com/blueprints
2. Click "New Blueprint"
3. Connect: `https://github.com/sorimdevs-tech/qlikscence`
4. Review configuration and click "Create Blueprint"

## Manual Deployment

### Backend Service (qlik-api)

| Field | Value |
|-------|-------|
| **Name** | qlik-api |
| **Root Directory** | `/` |
| **Build Command** | `pip install -r qlik_app/qlik/qlik-fastapi-backend/requirements.txt` |
| **Start Command** | `uvicorn qlik_app.qlik.qlik-fastapi-backend.main:app --host 0.0.0.0 --port $PORT` |

**Environment Variables:**
| Key | Value |
|-----|-------|
| PYTHON_VERSION | 3.11 |
| QLIK_TENANT_URL | https://c8vlzp3sx6akvnh.in.qlikcloud.com |
| QLIK_API_BASE_URL | https://c8vlzp3sx6akvnh.in.qlikcloud.com/api/v1 |
| QLIK_CLIENT_ID | (from Qlik Cloud Console) |
| QLIK_CLIENT_SECRET | (from Qlik Cloud Console) |
| API_KEY | (your custom API key) |

### Frontend Service (qlik-frontend)

| Field | Value |
|-------|-------|
| **Name** | qlik-frontend |
| **Root Directory** | `/` |
| **Build Command** | `cd qlik_app/converter/csv && npm install && npm run build` |
| **Publish Directory** | `qlik_app/converter/csv/dist` |

**Environment Variables:**
| Key | Value |
|-----|-------|
| VITE_API_URL | (auto-filled from qlik-api service) |

## Getting Qlik Cloud Credentials

1. Go to https://c8vlzp3sx6akvnh.in.qlikcloud.com/console/api-keys
2. Create new API key
3. Copy Client ID and Client Secret
4. ⚠️ Save Client Secret - it won't be shown again!
