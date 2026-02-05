# Qlik Cloud Data Explorer - Complete Feature Flow

## Overview
This application allows you to:
1. **Login** to Qlik Cloud with your tenant URL
2. **Browse Apps** from your Qlik Cloud instance
3. **Select an App** to explore its tables
4. **View Tables** within the selected app
5. **Click a Table** to display all its data
6. **Download Data** as CSV

---

## Step-by-Step Flow

### Step 1: Login (ConnectPage)
**File:** `src/pages/Connect/ConnectPage.tsx`

- User enters their Qlik Cloud tenant URL (e.g., `https://c8vlzp3sx6akvnh.in.qlikcloud.com`)
- Tenant URL is saved to `localStorage` as `tenant_url`
- User is redirected to `/apps` page

**Key Functions:**
- `testBrowserLogin(tenantUrl)` - Validates tenant and initiates login

---

### Step 2: Browse Apps (AppsPage)
**File:** `src/Apps/AppsPage.tsx`

- Retrieves the tenant URL from `localStorage`
- Fetches all available apps from Qlik Cloud
- Displays apps as cards with:
  - App name
  - Number of tables (badge)
  - Favorite toggle (star icon)
  - Menu options

**Key Functions:**
- `fetchApps(tenantUrl)` - Gets list of apps from backend
- `fetchTables(appId)` - Gets table count for each app

**User Action:** Click on an app card → Navigates to `/summary` with `appId` in state

---

### Step 3: View Tables (SummaryPage - Left Panel)
**File:** `src/Summary/SummaryPage.tsx`

When you click an app:
- App ID is passed via React Router state
- Left panel displays all tables in the selected app
- Tables are clickable items

**Key Functions:**
- `fetchTables(appId)` - Retrieves list of tables from the app

**User Action:** Click on a table name → Loads table data

---

### Step 4: Display Table Data (SummaryPage - Right Panel)
**File:** `src/Summary/SummaryPage.tsx`

When you click a table:
- Table name is highlighted in the left panel
- Right panel shows:
  - Table title
  - Summary report (if available)
  - Full data table with all rows
  - Row count at the bottom
  - Download CSV button

**Key Functions:**
- `fetchTableData(appId, tableName)` - Gets all rows from the table
- `fetchVehicleSummary(appId, tableName)` - Gets summary statistics

**User Action:** Click "Download CSV" → Downloads table data as CSV file

---

## API Endpoints Used

### Backend (FastAPI)
- `GET /applications` - List all apps
- `GET /applications/{app_id}/tables` - Get tables in an app
- `GET /applications/{app_id}/script/table/{table_name}` - Get table data
- `GET /vehicle-summary` - Get summary statistics

### Frontend API Functions
**File:** `src/api/qlikApi.ts`

```typescript
// Login
testBrowserLogin(tenantUrl: string)

// Apps
fetchApps(tenantUrl: string)

// Tables
fetchTables(appId: string, tenantUrl?: string)

// Data
fetchTableData(appId: string, tableName: string)
fetchVehicleSummary(appId: string, tableName: string)
```

---

## Component Structure

```
App
├── Header
├── Stepper
└── AppRoutes
    ├── / (ConnectPage) - Login
    ├── /apps (AppsPage) - Browse apps
    └── /summary (SummaryPage) - View tables & data
        ├── Left Panel - Table list
        └── Right Panel - Table data
```

---

## State Management

### localStorage
- `tenant_url` - Qlik Cloud tenant URL (saved during login)

### Component State (SummaryPage)
- `appId` - Currently selected app ID
- `tables` - List of tables in the app
- `selectedTable` - Currently selected table name
- `rows` - Table data rows
- `loading` - Initial load state
- `tableLoading` - Table data load state
- `summary` - Summary statistics

---

## UI Layout

### AppsPage
```
┌─────────────────────────────────────┐
│  Applications to explore    View all │
├─────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐         │
│  │ App Card │  │ App Card │  ...    │
│  │ [Image]  │  │ [Image]  │         │
│  │ Name  [5]│  │ Name  [3]│         │
│  └──────────┘  └──────────┘         │
└─────────────────────────────────────┘
```

### SummaryPage
```
┌──────────────┬──────────────────────────────┐
│ ← Back       │                              │
│ Tables       │  Table Name                  │
├──────────────┤──────────────────────────────┤
│ Table 1      │  Summary Report              │
│ Table 2 ✓    │  ┌────────────────────────┐  │
│ Table 3      │  │ Col1 │ Col2 │ Col3     │  │
│ Table 4      │  ├──────┼──────┼──────────┤  │
│              │  │ Data │ Data │ Data     │  │
│              │  │ Data │ Data │ Data     │  │
│              │  │ ...  │ ...  │ ...      │  │
│              │  └────────────────────────┘  │
│              │  Total 150 rows              │
│              │  [Download CSV]              │
└──────────────┴──────────────────────────────┘
```

---

## Key Features

✅ **Login with Tenant URL** - Secure connection to Qlik Cloud
✅ **App Discovery** - Browse all available apps
✅ **Table Listing** - See all tables in an app
✅ **Data Preview** - View complete table data
✅ **CSV Export** - Download table data as CSV
✅ **Summary Statistics** - View data analysis
✅ **Navigation** - Easy back button to return to apps
✅ **Responsive Design** - Works on different screen sizes

---

## How to Use

1. **Start the application**
   ```bash
   npm run dev
   ```

2. **Login**
   - Enter your Qlik Cloud tenant URL
   - Click "Connect"

3. **Browse Apps**
   - See all your Qlik Cloud apps
   - Click on any app card

4. **Explore Tables**
   - Left panel shows all tables
   - Click on a table to view its data

5. **Download Data**
   - Click "Download CSV" to export table data

---

## Files Modified/Created

- ✅ `src/Apps/AppsPage.tsx` - App listing with tenant URL support
- ✅ `src/Summary/SummaryPage.tsx` - Table listing and data display
- ✅ `src/Summary/SummaryPage.css` - Layout and styling
- ✅ `src/api/qlikApi.ts` - API functions with tenant URL support
- ✅ `src/router/AppRouter.tsx` - Routing configuration

---

## Testing the Flow

### Test Scenario 1: Complete Flow
1. Login with valid tenant URL
2. See apps list
3. Click an app
4. See tables in left panel
5. Click a table
6. See data in right panel
7. Download CSV

### Test Scenario 2: Navigation
1. Login → Apps → App → Tables
2. Click back button → Returns to Apps
3. Click another app → Shows different tables

### Test Scenario 3: Data Display
1. Select table with many rows
2. Verify all rows are displayed
3. Verify CSV download works
4. Verify row count is accurate

---

## Troubleshooting

### Issue: "No app selected" error
- **Cause:** Navigating directly to `/summary` without selecting an app
- **Solution:** Go back to `/apps` and select an app

### Issue: Tables not loading
- **Cause:** Backend not running or tenant URL invalid
- **Solution:** Check backend is running on `http://localhost:8000`

### Issue: Table data not showing
- **Cause:** Table has no data or API error
- **Solution:** Check browser console for error messages

---

## Next Steps

Potential enhancements:
- Add search/filter for apps and tables
- Add pagination for large datasets
- Add data visualization (charts)
- Add field-level filtering
- Add data export to Power BI
- Add data transformation options
