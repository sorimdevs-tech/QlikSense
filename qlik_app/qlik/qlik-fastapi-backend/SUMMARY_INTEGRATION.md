# Summary Integration Setup Guide

## Overview

This guide explains how the `summary_utils.py` has been integrated with `main.py` to provide summary generation endpoints for table data.

## What Was Changed

### 1. **Updated `summary_utils.py`**
- Removed commented-out old code
- Created clean, reusable functions:
  - `load_data_from_json()` - Convert JSON to DataFrame
  - `extract_metrics()` - Generate statistics
  - `generate_summary()` - Main summary generation
  - `generate_batch_summary()` - Multiple tables at once
  - `get_data_quality_score()` - Data quality assessment
  - `get_data_preview()` - Get sample rows

### 2. **Added Summary Endpoints to `main.py`**
Four new POST endpoints added:

| Endpoint | Purpose |
|----------|---------|
| `/summary/table` | Generate detailed summary for a single table |
| `/summary/batch` | Generate summaries for multiple tables |
| `/summary/text` | Generate human-readable summary text only |
| `/summary/quality` | Check data quality metrics |

---

## How to Use

### Step 1: Start the FastAPI Server

```bash
cd d:\qliksensecloud\qlikSense-Accellarater\qlik_app\qlik\qlik-fastapi-backend
python -m uvicorn main:app --reload
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Step 2: Send Data from Frontend

From your React frontend, send table data as JSON:

```typescript
// In your React component
const response = await fetch('http://localhost:8000/summary/table', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    table_name: 'My Table',
    data: [
      { product: 'A', sales: 1000 },
      { product: 'B', sales: 2000 }
    ]
  })
});

const summary = await response.json();
console.log(summary.metrics);
console.log(summary.summary_text);
```

### Step 3: Use the Response

The response includes:
- **metrics** - Comprehensive statistics
- **summary_text** - Human-readable summary
- **data_quality_score** - Quality percentage (0-100)
- **data_preview** - First 5 rows of data
- **columns** - List of column names

---

## Example Requests & Responses

### Example 1: Simple Sales Data

**Request:**
```json
{
  "table_name": "Sales",
  "data": [
    {"item": "Laptop", "price": 1000, "qty": 5},
    {"item": "Mouse", "price": 50, "qty": 20},
    {"item": "Monitor", "price": 500, "qty": 10}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "Sales",
  "row_count": 3,
  "column_count": 3,
  "columns": ["item", "price", "qty"],
  "metrics": {
    "Total Records": 3,
    "Total Value": 1550,
    "Average Value": 516.67,
    "Min Value": 50,
    "Max Value": 1000,
    "Top Categories": {
      "Laptop": 5000,
      "Monitor": 5000,
      "Mouse": 1000
    },
    "Column Info": {
      "Numeric Columns": ["price", "qty"],
      "Categorical Columns": ["item"],
      "Total Columns": 3
    }
  },
  "data_quality_score": 100.0,
  "summary_text": "📊 Sales Summary Report\n..."
}
```

### Example 2: Data with Missing Values

**Request:**
```json
{
  "table_name": "Employees",
  "data": [
    {"name": "John", "salary": 5000, "dept": "IT"},
    {"name": "Jane", "salary": null, "dept": "HR"},
    {"name": null, "salary": 6000, "dept": "Finance"}
  ]
}
```

**Response (via /summary/quality):**
```json
{
  "success": true,
  "quality_score": 77.78,
  "missing_values": {
    "name": {"count": 1, "percentage": 33.33},
    "salary": {"count": 1, "percentage": 33.33},
    "dept": {"count": 0, "percentage": 0.0}
  }
}
```

---

## Testing

### Automated Test Script

Run the test suite to verify all endpoints work:

```bash
cd d:\qliksensecloud\qlikSense-Accellarater\qlik_app\qlik\qlik-fastapi-backend

# Make sure server is running in another terminal first
python test_summary_endpoints.py
```

This will test all 4 endpoints with sample data.

### Manual Testing with cURL

```bash
# Test single table summary
curl -X POST "http://localhost:8000/summary/table" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "Test",
    "data": [{"name":"A","value":100},{"name":"B","value":200}]
  }'

# Test data quality
curl -X POST "http://localhost:8000/summary/quality" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "Test",
    "data": [{"name":"A","value":100},{"name":null,"value":null}]
  }'
```

---

## Frontend Integration

### React Example

```typescript
import { useState } from 'react';

export function DataSummary({ tableData }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const generateSummary = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/summary/table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_name: 'Current Data',
          data: tableData
        })
      });

      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Error generating summary:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={generateSummary} disabled={loading}>
        {loading ? 'Generating...' : 'Generate Summary'}
      </button>

      {summary && (
        <div>
          <h3>Summary</h3>
          <pre>{summary.summary_text}</pre>
          <p>Quality Score: {summary.data_quality_score}%</p>
          <details>
            <summary>Metrics</summary>
            <pre>{JSON.stringify(summary.metrics, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
```

---

## API Reference

### POST /summary/table
**Description:** Generate summary for a single table

**Request Body:**
```typescript
{
  table_name: string;        // Name of the table
  data: Array<object>;       // Array of records
}
```

**Response:**
```typescript
{
  success: boolean;
  table_name: string;
  row_count: number;
  column_count: number;
  columns: string[];
  metrics: {
    "Total Records": number;
    "Total Value": number;
    "Average Value": number;
    "Min Value": number;
    "Max Value": number;
    "Top Categories": object;
    "Column Info": object;
  };
  data_quality_score: number;
  data_preview: Array<object>;
  summary_text: string;
}
```

### POST /summary/batch
**Description:** Generate summaries for multiple tables

**Request Body:**
```typescript
{
  tables: {
    [tableName: string]: Array<object>;
  };
}
```

### POST /summary/text
**Description:** Generate only the text summary

**Request Body:**
```typescript
{
  table_name: string;
  data: Array<object>;
}
```

**Response:**
```typescript
{
  success: boolean;
  table_name: string;
  summary: string;  // Plain text summary
}
```

### POST /summary/quality
**Description:** Check data quality

**Request Body:**
```typescript
{
  table_name: string;
  data: Array<object>;
}
```

**Response:**
```typescript
{
  success: boolean;
  table_name: string;
  total_rows: number;
  total_columns: number;
  quality_score: number;
  missing_values: {
    [column: string]: {
      count: number;
      percentage: number;
    };
  };
}
```

---

## Troubleshooting

### Issue: Connection refused
**Solution:** Make sure FastAPI server is running
```bash
python -m uvicorn main:app --reload
```

### Issue: JSON parsing error
**Solution:** Check that your data is valid JSON. Example:
```python
import json
data = json.dumps(your_data)  # Validate serializable
```

### Issue: Empty metrics
**Solution:** Ensure your data has numeric columns. For example:
```json
[
  {"name": "A", "value": 100},  // "value" is numeric
  {"name": "B", "value": 200}
]
```

### Issue: Low quality score
**Solution:** This means there are missing values. Check the `/summary/quality` endpoint for details.

---

## Files Modified/Created

✅ **Modified:**
- `summary_utils.py` - Cleaned up and added new functions
- `main.py` - Added 4 new summary endpoints

✅ **Created:**
- `SUMMARY_ENDPOINTS.md` - Detailed API documentation
- `test_summary_endpoints.py` - Automated test suite
- `SUMMARY_INTEGRATION.md` - This setup guide

---

## Next Steps

1. ✅ Start the FastAPI server
2. ✅ Send table data from frontend
3. ✅ Receive summaries in response
4. ✅ Display metrics and summaries in UI

For detailed endpoint documentation, see [SUMMARY_ENDPOINTS.md](SUMMARY_ENDPOINTS.md)
