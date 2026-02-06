# Summary Generation Endpoints

These endpoints integrate with `summary_utils.py` to generate summaries from table data in JSON format.

## Overview

The summary endpoints accept table data in JSON format and generate:
- Comprehensive metrics (totals, averages, ranges)
- Top categories analysis
- Data quality scores
- Professional summary text

## Endpoints

### 1. **POST /summary/table**
Generate a detailed summary from table data

**Request:**
```json
{
  "table_name": "Sales Data",
  "data": [
    {"product": "Product A", "sales": 1000, "region": "North"},
    {"product": "Product B", "sales": 2000, "region": "South"},
    {"product": "Product A", "sales": 1500, "region": "East"}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "Sales Data",
  "row_count": 3,
  "column_count": 3,
  "columns": ["product", "sales", "region"],
  "metrics": {
    "Total Records": 3,
    "Total Value": 4500,
    "Average Value": 1500,
    "Min Value": 1000,
    "Max Value": 2000,
    "Top Categories": {
      "Product A": 2500,
      "Product B": 2000
    },
    "Column Info": {
      "Numeric Columns": ["sales"],
      "Categorical Columns": ["product", "region"],
      "Total Columns": 3
    }
  },
  "data_quality_score": 100.0,
  "data_preview": [
    {"product": "Product A", "sales": 1000, "region": "North"},
    {"product": "Product B", "sales": 2000, "region": "South"},
    {"product": "Product A", "sales": 1500, "region": "East"}
  ],
  "summary_text": "📊 Sales Data Summary Report\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nTotal Records: 3\nTotal Value: 4500\nAverage Value: 1500\nRange: 1000 - 2000\n\nTop Categories:\n  • Product A: 2500\n  • Product B: 2000"
}
```

---

### 2. **POST /summary/batch**
Generate summaries for multiple tables at once

**Request:**
```json
{
  "tables": {
    "Sales": [
      {"product": "A", "amount": 100},
      {"product": "B", "amount": 200}
    ],
    "Inventory": [
      {"item": "A", "stock": 50},
      {"item": "B", "stock": 100}
    ]
  }
}
```

**Response:**
```json
{
  "success": true,
  "total_tables": 2,
  "summaries": {
    "Sales": { /* summary data */ },
    "Inventory": { /* summary data */ }
  }
}
```

---

### 3. **POST /summary/text**
Generate a human-readable summary text (no metrics)

**Request:**
```json
{
  "table_name": "Sales Data",
  "data": [
    {"product": "A", "sales": 1000},
    {"product": "B", "sales": 2000}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "Sales Data",
  "summary": "📊 Sales Data Summary Report\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nTotal Records: 2\nTotal Value: 3000\nAverage Value: 1500\nRange: 1000 - 2000"
}
```

---

### 4. **POST /summary/quality**
Check data quality metrics for a table

**Request:**
```json
{
  "table_name": "Sales Data",
  "data": [
    {"product": "A", "sales": 1000, "region": "North"},
    {"product": "B", "sales": null, "region": "South"},
    {"product": null, "sales": 1500, "region": "East"}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "Sales Data",
  "total_rows": 3,
  "total_columns": 3,
  "quality_score": 88.89,
  "missing_values": {
    "product": {
      "count": 1,
      "percentage": 33.33
    },
    "sales": {
      "count": 1,
      "percentage": 33.33
    },
    "region": {
      "count": 0,
      "percentage": 0.0
    }
  }
}
```

---

## Usage Examples

### cURL Examples

**Generate Table Summary:**
```bash
curl -X POST "http://localhost:8000/summary/table" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "Orders",
    "data": [
      {"item": "Laptop", "price": 1000, "quantity": 5},
      {"item": "Mouse", "price": 25, "quantity": 50}
    ]
  }'
```

**Batch Summary:**
```bash
curl -X POST "http://localhost:8000/summary/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "tables": {
      "Orders": [...],
      "Products": [...]
    }
  }'
```

### Python Example

```python
import requests

# Generate summary for a single table
response = requests.post(
    "http://localhost:8000/summary/table",
    json={
        "table_name": "Sales Data",
        "data": [
            {"product": "A", "sales": 1000},
            {"product": "B", "sales": 2000}
        ]
    }
)

summary = response.json()
print(summary["metrics"])
print(summary["summary_text"])
```

---

## Features

✅ **Automatic Metrics Generation**
- Total records count
- Sum, average, min, max for numeric columns
- Top categories analysis
- Column type detection

✅ **Data Quality Assessment**
- Quality score (0-100%)
- Missing value detection
- Column-wise missing data percentage

✅ **Flexible Input**
- Accepts raw JSON arrays
- Supports nested structures
- Automatic dataframe conversion

✅ **Professional Summaries**
- Human-readable text format
- Statistical metrics
- Category analysis

---

## Integration with Frontend

From your React frontend in `/qlik_app/converter/csv/`, you can call these endpoints after fetching table data:

```typescript
// In your React component
const generateSummary = async (tableData: any[]) => {
  const response = await fetch('http://localhost:8000/summary/table', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      table_name: 'Current Table',
      data: tableData
    })
  });
  
  const summary = await response.json();
  return summary;
};
```

---

## Notes

- Data quality score is calculated as: `(total_cells - missing_cells) / total_cells * 100`
- Top categories shows the top 5 categories by numeric value
- All numeric values are rounded to 2 decimal places for clarity
- Missing/null values in numeric columns are handled gracefully
