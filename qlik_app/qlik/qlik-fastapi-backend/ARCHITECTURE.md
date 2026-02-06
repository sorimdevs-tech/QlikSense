# Integration Architecture

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND                               │
│          (qlik_app/converter/csv/ - Port 5173)                 │
│                                                                  │
│  User provides table data in CSV/JSON format                   │
│  ↓                                                               │
│  Sends HTTP POST request with table data                       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ POST /summary/table
                        │ POST /summary/batch
                        │ POST /summary/text
                        │ POST /summary/quality
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                  FASTAPI BACKEND                                │
│       (qlik_app/qlik/qlik-fastapi-backend/ - Port 8000)       │
│                                                                  │
│  main.py - 4 Summary Endpoints                                 │
│  ├── /summary/table      → Full summary with metrics           │
│  ├── /summary/batch      → Multiple tables at once             │
│  ├── /summary/text       → Text-only summary                   │
│  └── /summary/quality    → Data quality metrics                │
│                                                                  │
│  ↓                                                               │
│                                                                  │
│  summary_utils.py - Core Functions                             │
│  ├── load_data_from_json()       → Parse JSON to DataFrame     │
│  ├── extract_metrics()           → Generate statistics          │
│  ├── generate_summary()          → Main summary generator       │
│  ├── generate_batch_summary()    → Multi-table processing      │
│  ├── get_data_quality_score()    → Quality assessment          │
│  └── get_data_preview()          → Get sample rows             │
│                                                                  │
│  ↓                                                               │
│                                                                  │
│  Pandas DataFrame Processing                                   │
│  ├── Column type detection                                     │
│  ├── Statistics calculation                                    │
│  ├── Missing value detection                                   │
│  └── Category analysis                                         │
│                                                                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ Returns JSON Response
                        │ with metrics & summary
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND                               │
│                                                                  │
│  Displays:                                                       │
│  ├── 📊 Metrics (totals, averages, ranges)                     │
│  ├── 📈 Top categories analysis                                │
│  ├── ✅ Quality score (0-100%)                                 │
│  ├── 📝 Summary text                                           │
│  └── 🔍 Data preview                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Request/Response Cycle

### Single Table Request
```
REQUEST:
┌─────────────────────────────────────────┐
│ POST /summary/table                     │
├─────────────────────────────────────────┤
│ {                                       │
│   "table_name": "Sales Data",          │
│   "data": [                            │
│     {"product": "A", "sales": 1000},  │
│     {"product": "B", "sales": 2000}   │
│   ]                                     │
│ }                                       │
└─────────────────────────────────────────┘
         ↓ Processing ↓
      Extract Metrics
      Calculate Stats
      Analyze Categories
      Check Quality
         ↓ Response ↓
┌─────────────────────────────────────────┐
│ 200 OK                                  │
├─────────────────────────────────────────┤
│ {                                       │
│   "success": true,                     │
│   "metrics": {                         │
│     "Total Records": 2,                │
│     "Total Value": 3000,               │
│     "Average Value": 1500,             │
│     ...                                │
│   },                                    │
│   "summary_text": "📊 Sales...",      │
│   "data_quality_score": 100.0,        │
│   "data_preview": [...],               │
│   ...                                   │
│ }                                       │
└─────────────────────────────────────────┘
```

---

## Component Interactions

```
┌──────────────────────────────────────────────────────────────┐
│                   FRONTEND COMPONENT                         │
│              (React/TypeScript)                              │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ tableData: Array<object>
                          ↓
┌──────────────────────────────────────────────────────────────┐
│              POST REQUEST HANDLER                            │
│         (Fetch API / Axios)                                 │
│                                                              │
│ fetch('http://localhost:8000/summary/table', {             │
│   method: 'POST',                                           │
│   headers: { 'Content-Type': 'application/json' },         │
│   body: JSON.stringify({                                    │
│     table_name: 'My Table',                                 │
│     data: tableData                                         │
│   })                                                         │
│ })                                                           │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP Request
                          ↓
┌──────────────────────────────────────────────────────────────┐
│            FASTAPI ENDPOINT (@app.post)                     │
│                                                              │
│ async def create_table_summary(                            │
│     request: TableDataRequest                              │
│ )                                                            │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ request.data (List[Dict])
                          │ request.table_name (str)
                          ↓
┌──────────────────────────────────────────────────────────────┐
│           SUMMARY_UTILS FUNCTIONS                           │
│                                                              │
│ generate_summary()                                           │
│   ├── load_data_from_json()                                 │
│   │   └── pd.DataFrame(data)                                │
│   │                                                          │
│   ├── extract_metrics()                                      │
│   │   ├── Select numeric columns                            │
│   │   ├── Select categorical columns                        │
│   │   ├── Calculate sum, mean, min, max                     │
│   │   └── Group by category                                 │
│   │                                                          │
│   └── build_summary_text()                                  │
│       └── Format metrics as readable text                   │
│                                                              │
│ get_data_quality_score()                                     │
│   └── Calculate: (total_cells - missing) / total * 100      │
│                                                              │
│ get_data_preview()                                           │
│   └── df.head(5).to_dict('records')                         │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ Structured Response Dict
                          ↓
┌──────────────────────────────────────────────────────────────┐
│           JSON RESPONSE                                      │
│                                                              │
│ {                                                            │
│   success: boolean,                                          │
│   metrics: {                                                 │
│     "Total Records": number,                                │
│     "Total Value": number,                                  │
│     "Average Value": number,                                │
│     "Min Value": number,                                    │
│     "Max Value": number,                                    │
│     "Top Categories": Dict,                                 │
│     "Column Info": Dict                                     │
│   },                                                         │
│   summary_text: string,                                      │
│   data_quality_score: number,                               │
│   data_preview: Array<object>,                              │
│   ...                                                        │
│ }                                                            │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP 200 + JSON
                          ↓
┌──────────────────────────────────────────────────────────────┐
│              FRONTEND DISPLAY                                │
│                                                              │
│ summary.metrics                → Display in metrics cards   │
│ summary.summary_text           → Show in text section      │
│ summary.data_quality_score     → Display quality badge    │
│ summary.data_preview           → Show table preview       │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Transformation Pipeline

```
Raw JSON Data (Frontend)
        │
        ↓
┌──────────────────────────┐
│ load_data_from_json()    │
├──────────────────────────┤
│ Input: List[Dict]        │
│ Output: pd.DataFrame     │
└──────────────────────────┘
        │
        ↓
┌──────────────────────────┐
│ extract_metrics()        │
├──────────────────────────┤
│ Numeric Cols Analysis    │
│ ├─ Sum                   │
│ ├─ Mean                  │
│ ├─ Min/Max               │
│ └─ Groupby Categories    │
│                          │
│ Categorical Cols Analysis│
│ └─ Type Detection        │
└──────────────────────────┘
        │
        ↓
┌──────────────────────────┐
│ Multiple Functions       │
├──────────────────────────┤
│ build_summary_text()     │
│ get_data_quality_score() │
│ get_data_preview()       │
└──────────────────────────┘
        │
        ↓
JSON Response with All Data
```

---

## File Structure

```
qlik_app/
└── qlik/
    └── qlik-fastapi-backend/
        ├── main.py                      ✅ UPDATED
        │   └── 4 Summary Endpoints
        │
        ├── summary_utils.py             ✅ UPDATED
        │   └── 6 Core Functions
        │
        ├── SUMMARY_ENDPOINTS.md         ✅ NEW
        │   └── Complete API Docs
        │
        ├── SUMMARY_INTEGRATION.md       ✅ NEW
        │   └── Setup & Integration Guide
        │
        ├── QUICK_START.md               ✅ NEW
        │   └── Quick Reference
        │
        ├── INTEGRATION_COMPLETE.md      ✅ NEW
        │   └── Summary of Changes
        │
        └── test_summary_endpoints.py    ✅ NEW
            └── Automated Test Suite
```

---

## Deployment Flow

```
Development Cycle:

1. FRONTEND                    2. BACKEND
   ├── User Input Data            ├── Receives JSON
   ├── Validate Format            ├── Parse Request
   ├── Send via HTTP              ├── Process Data
   └── Await Response             ├── Generate Metrics
                                  ├── Build Summary
                                  └── Return Response

3. DISPLAY                     4. REPEAT
   ├── Parse Response             ├── More Tables?
   ├── Show Metrics               ├── Batch Process?
   ├── Display Summary            ├── Check Quality?
   └── Highlight Quality          └── Generate New?
```

---

## Benefits of This Architecture

✅ **Separation of Concerns**
- Frontend handles UI/UX
- Backend handles data processing
- Clear API contract

✅ **Reusability**
- Functions usable independently
- Can be imported elsewhere
- Type hints for IDE support

✅ **Scalability**
- Batch processing ready
- Can handle multiple tables
- Pandas handles large datasets

✅ **Error Handling**
- Pydantic validation on input
- Try/catch on processing
- Detailed error messages

✅ **Maintainability**
- Clear function names
- Good documentation
- Type annotations
- Test suite included
