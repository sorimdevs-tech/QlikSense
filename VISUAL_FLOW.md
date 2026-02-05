# Visual Flow Diagram - Qlik Cloud Data Explorer

## 🔄 Complete Application Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    QLIK CLOUD DATA EXPLORER                     │
└─────────────────────────────────────────────────────────────────┘

                          ┌──────────────┐
                          │  START HERE  │
                          └──────┬───────┘
                                 │
                    ┌────────────▼────────────┐
                    │   LOGIN PAGE (/)        │
                    │                        │
                    │ Enter Tenant URL:      │
                    │ https://xxx.qlikcloud  │
                    │                        │
                    │ [Continue Button]      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  VALIDATE & SAVE URL   │
                    │  localStorage.setItem  │
                    │  ("tenant_url", url)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   APPS PAGE (/apps)    │
                    │                        │
                    │  ┌──────────────────┐  │
                    │  │  App Card 1      │  │
                    │  │  [Image]         │  │
                    │  │  Name      [5]   │  │
                    │  └──────────────────┘  │
                    │                        │
                    │  ┌──────────────────┐  │
                    │  │  App Card 2      │  │
                    │  │  [Image]         │  │
                    │  │  Name      [3]   │  │
                    │  └──────────────────┘  │
                    │                        │
                    │  [Click App Card]      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────────────────────┐
                    │  SUMMARY PAGE (/summary)               │
                    │                                        │
                    │  ┌──────────────┬──────────────────┐   │
                    │  │ LEFT PANEL   │  RIGHT PANEL     │   │
                    │  │              │                  │   │
                    │  │ ← Back       │  Table Name      │   │
                    │  │ Tables       │  ┌────────────┐  │   │
                    │  │              │  │ Summary    │  │   │
                    │  │ Table 1      │  │ Report     │  │   │
                    │  │ Table 2 ✓    │  └────────────┘  │   │
                    │  │ Table 3      │  ┌────────────┐  │   │
                    │  │ Table 4      │  │ Col1│Col2  │  │   │
                    │  │              │  ├─────┼─────┤  │   │
                    │  │ [Click]      │  │Data │Data │  │   │
                    │  │              │  │Data │Data │  │   │
                    │  │              │  │...  │...  │  │   │
                    │  │              │  └────────────┘  │   │
                    │  │              │  Total 150 rows  │   │
                    │  │              │  [Download CSV]  │   │
                    │  └──────────────┴──────────────────┘   │
                    │                                        │
                    │  [Click Back] ──────────────────────┐  │
                    └────────────────────────────────────┼──┘
                                                         │
                                    ┌────────────────────┘
                                    │
                                    ▼
                    ┌────────────────────────────┐
                    │   BACK TO APPS PAGE        │
                    │   (Can select another app) │
                    └────────────────────────────┘
```

---

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ConnectPage                                               │
│  ├─ Input: Tenant URL                                      │
│  ├─ Save: localStorage.tenant_url                          │
│  └─ Navigate: /apps                                        │
│                                                             │
│  AppsPage                                                  │
│  ├─ Read: localStorage.tenant_url                          │
│  ├─ Call: fetchApps(tenantUrl)                             │
│  ├─ Call: fetchTables(appId) for each app                  │
│  ├─ Display: App cards with table counts                   │
│  └─ Navigate: /summary with appId                          │
│                                                             │
│  SummaryPage                                               │
│  ├─ Receive: appId from navigation state                   │
│  ├─ Call: fetchTables(appId)                               │
│  ├─ Display: Tables in left panel                          │
│  ├─ Call: fetchTableData(appId, tableName)                 │
│  ├─ Call: fetchVehicleSummary(appId, tableName)            │
│  ├─ Display: Data in right panel                           │
│  └─ Export: CSV download                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP Requests
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  GET /applications?tenant_url={url}                        │
│  └─ Returns: [{ id, name }, ...]                           │
│                                                             │
│  GET /applications/{app_id}/tables                         │
│  └─ Returns: [{ name, fields }, ...]                       │
│                                                             │
│  GET /applications/{app_id}/script/table/{table_name}      │
│  └─ Returns: [{ col1, col2, ... }, ...]                    │
│                                                             │
│  GET /vehicle-summary?app_id={id}&table_name={name}        │
│  └─ Returns: { summary_data }                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket/REST
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  QLIK CLOUD API                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ├─ Get Applications                                       │
│  ├─ Get Tables from App                                    │
│  ├─ Get Fields from Table                                  │
│  ├─ Get Data from Table                                    │
│  └─ Get App Script                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Component Hierarchy

```
App
├── Header
├── Stepper
└── AppRoutes
    ├── Route: /
    │   └── ConnectPage
    │       ├── Input: Tenant URL
    │       ├── Checkbox: Connect as user
    │       └── Button: Continue
    │
    ├── Route: /apps
    │   └── AppsPage
    │       ├── State: apps[], tableCount{}
    │       └── UI: App Cards Grid
    │           ├── Card Image
    │           ├── App Name
    │           ├── Table Count Badge
    │           ├── Favorite Star
    │           └── Menu Icon
    │
    └── Route: /summary
        └── SummaryPage
            ├── State: appId, tables[], selectedTable, rows[]
            ├── Left Panel
            │   ├── Back Button
            │   ├── Tables Header
            │   └── Table List
            │       └── Table Items (clickable)
            │
            └── Right Panel
                ├── Table Header
                ├── Summary Report
                ├── Data Table
                │   ├── Sticky Header
                │   ├── Table Rows
                │   └── Row Count Footer
                └── Download CSV Button
```

---

## 🔐 State Management Flow

```
┌──────────────────────────────────────────────────────────┐
│                   localStorage                           │
├──────────────────────────────────────────────────────────┤
│  tenant_url: "https://xxx.qlikcloud.com"                │
└──────────────────────────────────────────────────────────┘
                         │
                         │ Read by AppsPage
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                   AppsPage State                         │
├──────────────────────────────────────────────────────────┤
│  apps: [{ id, name }, ...]                              │
│  tableCount: { appId: count, ... }                       │
│  loading: boolean                                        │
│  favourites: [appId, ...]                               │
└──────────────────────────────────────────────────────────┘
                         │
                         │ Pass appId via navigation
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                 SummaryPage State                        │
├──────────────────────────────────────────────────────────┤
│  appId: string                                           │
│  tables: [{ name, fields }, ...]                        │
│  selectedTable: string                                   │
│  rows: [{ col1, col2, ... }, ...]                       │
│  loading: boolean                                        │
│  tableLoading: boolean                                   │
│  summary: { statistics }                                │
└──────────────────────────────────────────────────────────┘
```

---

## 🔄 User Interaction Flow

```
START
  │
  ├─ User enters tenant URL
  │  └─ Clicks "Continue"
  │     └─ Validates URL format
  │        └─ Saves to localStorage
  │           └─ Navigates to /apps
  │
  ├─ User sees apps list
  │  └─ Clicks app card
  │     └─ Navigates to /summary with appId
  │        └─ Loads tables for app
  │           └─ Displays tables in left panel
  │
  ├─ User clicks table name
  │  └─ Table is highlighted
  │     └─ Loads table data
  │        └─ Displays data in right panel
  │           └─ Shows summary statistics
  │
  ├─ User views data
  │  └─ Can scroll through rows
  │     └─ Can download as CSV
  │        └─ File is saved to Downloads
  │
  ├─ User clicks back button
  │  └─ Returns to /apps
  │     └─ Can select another app
  │        └─ Repeats process
  │
  └─ END
```

---

## 📱 UI Layout Breakdown

### AppsPage Layout
```
┌─────────────────────────────────────────────────────────┐
│  Applications to explore                    View all    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ App 1    │  │ App 2    │  │ App 3    │             │
│  │ [Image]  │  │ [Image]  │  │ [Image]  │             │
│  │ Name [5] │  │ Name [3] │  │ Name [2] │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                         │
│  ┌──────────┐  ┌──────────┐                           │
│  │ App 4    │  │ App 5    │                           │
│  │ [Image]  │  │ [Image]  │                           │
│  │ Name [4] │  │ Name [1] │                           │
│  └──────────┘  └──────────┘                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### SummaryPage Layout
```
┌──────────────┬──────────────────────────────────────┐
│ ← Back       │                                      │
│ Tables       │  Table Name                          │
├──────────────┼──────────────────────────────────────┤
│ Table 1      │  Summary Report                      │
│ Table 2 ✓    │  ┌────────────────────────────────┐  │
│ Table 3      │  │ Category │ Metric │ Value      │  │
│ Table 4      │  ├──────────┼────────┼────────────┤  │
│ Table 5      │  │ Total    │ Count  │ 150        │  │
│              │  �� By Type  │ Cars   │ 100        │  │
│              │  │ By Type  │ Bikes  │ 50         │  │
│              │  └────────────────────────────────┘  │
│              │                                      │
│              │  Data Table                          │
│              │  ┌────────────────────────────────┐  │
│              │  │ Col1 │ Col2 │ Col3 │ Col4     │  │
│              │  ├──────┼──────┼──────┼──────────┤  │
│              │  │ Data │ Data │ Data │ Data     │  │
│              │  │ Data │ Data │ Data │ Data     │  │
│              │  │ Data │ Data │ Data │ Data     │  │
│              │  │ ...  │ ...  │ ...  │ ...      │  │
│              │  └────────────────────────────────┘  │
│              │  Total 150 rows                      │
│              │  [Download CSV]                      │
└──────────────┴──────────────────────────────────────┘
```

---

## 🔗 Navigation Routes

```
/ (ConnectPage)
  ↓ [Continue]
  
/apps (AppsPage)
  ↓ [Click App]
  
/summary (SummaryPage)
  ├─ [Click Table] → Load Data
  └─ [Back Button] → /apps
```

---

## 📡 API Call Sequence

```
1. ConnectPage
   └─ validateLogin(url, true, email, password)

2. AppsPage
   ├─ fetchApps(tenantUrl)
   └─ fetchTables(appId) × N apps

3. SummaryPage
   ├─ fetchTables(appId)
   ├─ fetchTableData(appId, tableName)
   └─ fetchVehicleSummary(appId, tableName)

4. CSV Download
   └─ Generate CSV from rows array
```

---

## ✨ Key Features Visualization

```
┌─────────────────────────────────────────────────────────┐
│                   KEY FEATURES                          │
├───────────────────────────���─────────────────────────────┤
│                                                         │
│  ✅ Secure Login                                        │
│     └─ Tenant URL validation                           │
│        └─ localStorage persistence                     │
│                                                         │
│  ✅ App Discovery                                       │
│     └─ List all apps                                   │
│        └─ Show table counts                            │
│           └─ Favorite toggle                           │
│                                                         │
│  ✅ Table Browsing                                      │
│     └─ List tables in app                              │
│        └─ Highlight selected table                     │
│           └─ Easy navigation                           │
│                                                         │
│  ✅ Data Display                                        │
│     └─ Show all rows                                   │
│        └─ Sticky headers                               │
│           └─ Horizontal scroll                         │
│                                                         │
│  ✅ Data Export                                         │
│     └─ Download as CSV                                 │
│        └─ Proper formatting                            │
│           └─ File naming                               │
│                                                         │
│  ✅ Summary Statistics                                  │
│     └─ Data analysis                                   │
│        └─ Category counts                              │
│           └─ Numeric analysis                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Summary

The Qlik Cloud Data Explorer provides a complete, intuitive flow for:
1. **Authenticating** with Qlik Cloud
2. **Discovering** available apps
3. **Exploring** tables within apps
4. **Viewing** complete table data
5. **Exporting** data for analysis

All with a clean, professional UI and smooth navigation!
