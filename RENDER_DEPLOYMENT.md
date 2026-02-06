# Where to Add Start Command and Root Directory in Render

## For Backend (qlik-api) - Web Service

When creating/editing a Web Service in Render, you will see these fields:

### Step-by-step Screenshot Guide:

1. **Go to Render Dashboard**
   - https://dashboard.render.com

2. **Click "New +" → "Web Service"**

3. **Fill in the details on the page:**

   ```
   ┌─────────────────────────────────────────────────────────┐
   │  Name:              qlik-api                           │
   │                                                         │
   │  Repo:              https://github.com/sorimdevs-tech/qlikscence.git
   │                                                         │
   │  Branch:            main                                │
   │                                                         │
   │  Root Directory:    /                                   │
   │                                                         │
   │  Build Command:     pip install -r qlik_app/qlik/       │
   │                      qlik-fastapi-backend/             │
   │                      requirements.txt --no-cache-dir    │
   │                                                         │
   │  Start Command:     uvicorn qlik_app.qlik.             │
   │                      qlik-fastapi-backend.main:app     │
   │                      --host 0.0.0.0 --port $PORT       │
   │                                                         │
   │  Plan:              Free                                │
   └─────────────────────────────────────────────────────────┘
   ```

4. **Scroll down and click "Create Web Service"**

5. **After creation, go to "Environment" tab to add variables**

---

## Field Locations in Render UI:

```
┌────────────────────────────────────────────────────────────────┐
│  CREATE WEB SERVICE                                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Name *                      [____________]                    │
│                                                                │
│  Repository *                 [https://github.com/...] [Change]│
│                                                                │
│  Branch *                     [main_____________] [v]           │
│                                                                │
│  Root Directory (optional)    [/___________]  <-- ENTER "/"   │
│                                                                │
│  Build Command *              [_________________________]      │
│                              pip install -r ...                 │
│                                                                │
│  Start Command *              [_________________________]      │
│                              uvicorn ...                       │
│                                                                │
│  Plan                        [Free_______] [v]                 │
│                                                                │
│  [Create Web Service]                                            │
└────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference:

### Root Directory
- **Where to find:** Third field from top on the service creation page
- **What to enter:** `/`

### Start Command
- **Where to find:** Fifth field from top on the service creation page
- **What to enter:**
  ```
  uvicorn qlik_app.qlik.qlik-fastapi-backend.main:app --host 0.0.0.0 --port $PORT
  ```

---

## After Creating Service:

1. Click on your service name (qlik-api)
2. Go to **"Environment"** tab (top navigation)
3. Click **"Add Environment Variable"**
4. Add all your key-value pairs

---

## For Frontend (qlik-frontend) - Static Site

```
┌─────────────────────────────────────────────────────────┐
│  CREATE STATIC SITE                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Name *                    qlik-frontend                  │
│                                                         │
│  Repository *               https://github.com/...       │
│                                                         │
│  Branch *                  main                          │
│                                                         │
│  Root Directory (optional)  /                            │
│                                                         │
│  Build Command *           cd qlik_app/converter/csv    │
│                             && npm install               │
│                             && npm run build             │
│                                                         │
│  Publish Directory *       qlik_app/converter/csv/dist  │
│                                                         │
│  Plan                      Free                          │
│                                                         │
│  [Create Static Site]                                      │
└─────────────────────────────────────────────────────────┘
```
