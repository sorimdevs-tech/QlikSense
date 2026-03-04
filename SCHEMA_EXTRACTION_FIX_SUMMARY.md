# Schema Extraction Fix - Complete Summary

## Problem
Power BI tables were published empty (zero columns) showing only placeholder "Value" column because the `_extract_fields_from_m()` function failed to parse M expressions properly.

## Root Cause
The `_extract_fields_from_m()` function in `powerbi_publisher.py` was looking for schema definitions in the pattern:
```m
type table [col = type text, ...]
```

But `mquery_converter.py` actually generates M queries using:
```m
Table.TransformColumnTypes(PromotedHeaders, {
    {"ColumnName", type text},
    {"AnotherColumn", type number}
})
```

**Result**: Pattern mismatch → zero fields extracted → BIM created with no columns → Power BI received empty schema.

## Solution Applied

### File Modified
- **Path**: `d:\QlikSense\qlik_app\qlik\qlik-fastapi-backend\powerbi_publisher.py`
- **Lines**: 228-280 (function `_extract_fields_from_m()`)

### Key Changes

#### 1. Fixed Regex Pattern (Line 262)
**Before**:
```python
transform_pattern = r'Table\.TransformColumnTypes\s*\(\s*[^,]+?\s*,\s*\[\s*(.+?)\s*\]\s*\)'
                    # ↑ Looked for square brackets [ ]
```

**After**:
```python
transform_pattern = r'Table\.TransformColumnTypes\s*\(\s*[^,]+?\s*,\s*\{\s*(.+?)\s*\}\s*\)'
                    # ↑ Correctly matches curly braces { }
```

#### 2. Fixed Column Parsing Pattern (Line 267)
**Before**:
```python
col_pattern = r'\[\s*"([^"]+)"\s*,\s*(type\s+\w+|Int64\.Type)\s*\]'
             # ↑ Looked for ["name", type] format
```

**After**:
```python
col_pattern = r'\{\s*"([^"]+)"\s*,\s*(Int64\.Type|type\s+\w+)\s*\}'
             # ↑ Matches {"name", type} format
```

#### 3. Enhanced Type Support
- `Int64.Type` → `"integer"`
- `type text` → `"string"` + name-based inference
- `type number` → `"number"`
- `type datetime` → `"datetime"`
- Plus 8+ other patterns

#### 4. Improved Logging
- Log level messages at `[Extract]` prefix for debugging
- Tracks successful pattern matches
- Logs extracted field count and names

## Test Verification

The fix was tested with a sample M expression:
```m
let
    PromotedHeaders = ...,
    TypedTable = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"VIN", type text},
            {"ModelName", type text},
            {"ManufactureYear", Int64.Type},
            {"Price", type number},
            {"CreatedDate", type datetime}
        }
    )
in TypedTable
```

**Result: ALL 5 FIELDS SUCCESSFULLY EXTRACTED**
```
VIN                  -> string
ModelName            -> string
ManufactureYear      -> integer
Price                -> number
CreatedDate          -> datetime
```

## Data Flow Impact

The fix enables proper end-to-end data flow:

```
mquery_converter.py
  ↓ Generates M with Table.TransformColumnTypes
  ├─ Creates fields list in output dict
  │
migration_api.py (line 844)
  ↓ Passes "fields": t.get("fields", [])
  │
powerbi_publisher.py _build_bim()
  ↓ Line 427: Gets fields from tables_m
  ├─ Line 430: Falls back to _extract_fields_from_m() if empty
  ├─ NOW FIXED: Correctly extracts columns from M expressions
  │
  ↓ Line 433-438: Creates columns in BIM
  │
Fabric Items API (/v1/workspaces/{id}/semanticModels)
  ↓ Receives TMSL with explicit column definitions
  │
Power BI
  └─ Shows full table schema with actual columns
```

## Expected Behavior After Fix

When publishing a mquery to Power BI:

1. ✅ mquery converted to M expression with column type specifications
2. ✅ Field extraction now successfully parses column list
3. ✅ BIM builder receives 5-50+ actual columns (not placeholder)
4. ✅ Fabric API receives complete schema definition
5. ✅ Power BI creates semantic model with all columns
6. ✅ Data refreshes and becomes visible

## Testing Checklist

- [ ] Publish test dataset (Vehicle_Fact_MASTER recommended)
- [ ] Verify columns appear in Power BI Fabric model
- [ ] Check that column count matches source table
- [ ] Verify data types are correctly mapped
- [ ] Test refresh to ensure data loads
- [ ] Validate in Power BI UI - should NOT show just "Value" column

## Rollback Plan (If Needed)

The old extraction function is commented out in lines 213-227 if reverting becomes necessary.

## Files Affected
- `d:\QlikSense\qlik_app\qlik\qlik-fastapi-backend\powerbi_publisher.py` - Lines 228-280 FIXED

---

**Status**: Core fix complete and tested
**Next Step**: End-to-end integration testing with actual Power BI publication
