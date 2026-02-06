# Quick Start - Summary Endpoints

## TL;DR

Your table data comes as JSON from the frontend. Send it to the backend to get summaries.

## 3 Steps to Get a Summary

### 1. Get your table data
```javascript
// From your table/data in the frontend
const tableData = [
  { product: 'A', sales: 1000, region: 'North' },
  { product: 'B', sales: 2000, region: 'South' }
];
```

### 2. Send to backend
```javascript
const response = await fetch('http://localhost:8000/summary/table', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    table_name: 'My Table',
    data: tableData
  })
});

const summary = await response.json();
```

### 3. Use the response
```javascript
console.log(summary.metrics);           // Statistics
console.log(summary.summary_text);      // Human-readable text
console.log(summary.data_quality_score); // Quality: 0-100%
console.log(summary.data_preview);       // First 5 rows
```

---

## What You Get Back

```json
{
  "success": true,
  "metrics": {
    "Total Records": 2,
    "Total Value": 3000,
    "Average Value": 1500,
    "Top Categories": { "A": 1000, "B": 2000 }
  },
  "summary_text": "📊 Summary...",
  "data_quality_score": 100.0
}
```

---

## 4 Endpoints

| Endpoint | Use Case |
|----------|----------|
| `/summary/table` | Full summary with metrics |
| `/summary/batch` | Multiple tables at once |
| `/summary/text` | Just the text summary |
| `/summary/quality` | Check data quality |

---

## Complete React Example

```typescript
import { useState } from 'react';

export function TableSummary({ data }) {
  const [summary, setSummary] = useState(null);

  const handleGenerateSummary = async () => {
    const response = await fetch('http://localhost:8000/summary/table', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        table_name: 'My Data',
        data: data
      })
    });
    const result = await response.json();
    setSummary(result);
  };

  return (
    <div>
      <button onClick={handleGenerateSummary}>Generate Summary</button>
      
      {summary && (
        <>
          <h3>Summary</h3>
          <p>{summary.summary_text}</p>
          <p>Quality: {summary.data_quality_score}%</p>
          <pre>{JSON.stringify(summary.metrics, null, 2)}</pre>
        </>
      )}
    </div>
  );
}
```

---

## Data Format

Your data must be an array of objects:
```javascript
[
  { column1: value, column2: value, ... },
  { column1: value, column2: value, ... }
]
```

**Supports:**
- ✅ Numbers (1, 100, 50.5)
- ✅ Strings ("text", "category")
- ✅ Missing values (null, undefined)
- ✅ Mixed types

---

## Errors & Fixes

| Error | Fix |
|-------|-----|
| Connection refused | Start server: `python -m uvicorn main:app --reload` |
| 400 Bad Request | Check JSON format with `JSON.stringify()` |
| CORS error | Server already has CORS enabled for `http://localhost:5173` |

---

## Server Setup

```bash
cd qlik_app/qlik/qlik-fastapi-backend
python -m uvicorn main:app --reload
```

Open: http://localhost:8000/docs (for interactive API)

---

See [SUMMARY_ENDPOINTS.md](SUMMARY_ENDPOINTS.md) for full API details.
