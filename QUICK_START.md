# Quick Start Guide - Qlik Cloud Data Explorer

## Prerequisites
- Node.js installed
- Python 3.8+ installed
- Qlik Cloud tenant with apps containing data

## Setup & Run

### 1. Start Backend (FastAPI)
```bash
cd d:\commonQlikApp\qlik_app\qlik\qlik-fastapi-backend

# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```
Backend will start on `http://localhost:8000`

### 2. Start Frontend (React + Vite)
```bash
cd d:\commonQlikApp\qlik_app\converter\csv

# Install dependencies
npm install

# Run dev server
npm run dev
```
Frontend will start on `http://localhost:5173`

### 3. Open in Browser
```
http://localhost:5173
```

---

## Complete User Flow

### 1️⃣ Login Page
```
Enter Tenant URL: https://your-tenant.in.qlikcloud.com
Click "Connect"
```

### 2️⃣ Apps Page
```
See all your Qlik Cloud apps
Click on any app card to explore
```

### 3️⃣ Tables Page (Left Panel)
```
See all tables in the selected app
Click on a table name to view its data
```

### 4️⃣ Data Display (Right Panel)
```
See all rows from the selected table
Click "Download CSV" to export
```

---

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Login | `src/pages/Connect/ConnectPage.tsx` | Tenant URL entry |
| Apps List | `src/Apps/AppsPage.tsx` | Browse apps |
| Tables & Data | `src/Summary/SummaryPage.tsx` | View tables & data |
| API | `src/api/qlikApi.ts` | Backend communication |
| Router | `src/router/AppRouter.tsx` | Navigation |

---

## API Endpoints

### Apps
- `GET /applications` - List all apps

### Tables
- `GET /applications/{app_id}/tables` - Get tables in app

### Data
- `GET /applications/{app_id}/script/table/{table_name}` - Get table data

### Summary
- `GET /vehicle-summary` - Get data statistics

---

## Features Implemented

✅ Login with Qlik Cloud tenant URL
✅ Browse all available apps
✅ View tables in each app
✅ Display complete table data
✅ Download table data as CSV
✅ View data summary statistics
✅ Easy navigation with back button
✅ Responsive UI layout

---

## Troubleshooting

### Backend not connecting
```
Error: "Backend not connected"
Solution: 
1. Check backend is running on http://localhost:8000
2. Check CORS settings in main.py
3. Verify tenant URL is correct
```

### Tables not loading
```
Error: "No tables found"
Solution:
1. Verify app has data (last reload time)
2. Check app permissions
3. Check backend logs for errors
```

### Data not displaying
```
Error: Empty table
Solution:
1. Verify table has data
2. Check browser console for errors
3. Verify API response in Network tab
```

---

## File Structure

```
d:\commonQlikApp\
├── qlik_app\
│   ├── converter\csv\
│   │   ├── src\
│   │   │   ├── api\qlikApi.ts
│   │   │   ├── Apps\AppsPage.tsx
│   │   │   ├── Summary\SummaryPage.tsx
│   │   │   ├── pages\Connect\ConnectPage.tsx
│   │   │   ├── router\AppRouter.tsx
│   │   │   └── App.tsx
│   │   └── package.json
│   └── qlik\qlik-fastapi-backend\
│       ├── main.py
│       ├── qlik_client.py
│       ├── qlik_websocket_client.py
│       └── requirements.txt
└── FEATURE_FLOW.md
```

---

## Next Steps

1. ✅ Complete: Login to Qlik Cloud
2. ✅ Complete: Load apps from Qlik Cloud
3. ✅ Complete: Click app to list tables
4. ✅ Complete: Click table to show data
5. 🔄 Optional: Add search/filter
6. 🔄 Optional: Add data visualization
7. 🔄 Optional: Add Power BI export

---

## Support

For issues or questions:
1. Check browser console (F12)
2. Check backend logs
3. Verify API responses in Network tab
4. Check CORS settings
5. Verify tenant URL format
