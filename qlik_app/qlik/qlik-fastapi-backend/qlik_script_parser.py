# qlik_script_parser.py - Extract data from Qlik INLINE statements
import re
from typing import Dict, List, Any

class QlikScriptParser:
    """Parse Qlik load scripts to extract table data"""
    
    @staticmethod
    def parse_inline_data(script: str) -> Dict[str, Any]:
        """
        Parse INLINE data from Qlik script
        Returns tables with their data
        """
        tables = {}
        
        # Split script into sections
        sections = script.split('///$tab')
        
        for section in sections:
            if not section.strip():
                continue
            
            # Extract table data from this section
            table_data = QlikScriptParser._parse_section(section)
            if table_data:
                for table_name, data in table_data.items():
                    tables[table_name] = data
        
        return {
            "success": True,
            "tables": tables,
            "table_count": len(tables),
            "table_names": list(tables.keys())
        }
    
    @staticmethod
    def _parse_section(section: str) -> Dict[str, Dict[str, Any]]:
        """Parse a single script section"""
        tables = {}
        
        # Find all LOAD ... INLINE patterns
        # Pattern: TableName: LOAD ... INLINE [ ... ];
        
        # First, find table name (word followed by colon)
        lines = section.split('\n')
        current_table = None
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip comments
            if line_stripped.startswith('//'):
                continue
            
            # Check for table name (ends with colon)
            if ':' in line and not line_stripped.startswith('LOAD'):
                parts = line.split(':')
                if len(parts) >= 2:
                    potential_table = parts[0].strip()
                    # Check if next lines contain LOAD
                    next_lines = '\n'.join(lines[i:i+5])
                    if 'LOAD' in next_lines.upper():
                        current_table = potential_table
            
            # Check for INLINE block
            if current_table and 'INLINE' in line_stripped.upper():
                # Extract the INLINE block
                inline_data = QlikScriptParser._extract_inline_block(
                    '\n'.join(lines[i:]), 
                    current_table
                )
                if inline_data:
                    tables[current_table] = inline_data
                    current_table = None
        
        return tables
    
    @staticmethod
    def _extract_inline_block(text: str, table_name: str) -> Dict[str, Any]:
        """Extract data from INLINE [ ... ] block"""
        try:
            # Find INLINE [ ... ];
            match = re.search(r'INLINE\s*\[(.*?)\];', text, re.DOTALL | re.IGNORECASE)
            
            if not match:
                return None
            
            inline_content = match.group(1).strip()
            
            # Split by newlines
            lines = [line.strip() for line in inline_content.split('\n') if line.strip()]
            
            if len(lines) < 2:
                return None
            
            # First line is headers
            header_line = lines[0]
            # Parse headers (comma-separated)
            headers = [h.strip() for h in header_line.split(',')]
            
            # Rest are data rows
            rows = []
            for line in lines[1:]:
                # Skip empty lines
                if not line:
                    continue
                
                # Parse row data (comma-separated, respecting quotes)
                values = QlikScriptParser._parse_csv_line(line)
                
                if len(values) == len(headers):
                    row_dict = {}
                    for i, header in enumerate(headers):
                        row_dict[header] = values[i]
                    rows.append(row_dict)
            
            return {
                "table_name": table_name,
                "columns": headers,
                "rows": rows,
                "row_count": len(rows),
                "column_count": len(headers)
            }
            
        except Exception as e:
            print(f"Error parsing inline block for {table_name}: {e}")
            return None
    
    @staticmethod
    def _parse_csv_line(line: str) -> List[str]:
        """Parse a CSV line, handling commas inside quotes"""
        values = []
        current_value = ""
        in_quotes = False
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                values.append(current_value.strip())
                current_value = ""
            else:
                current_value += char
        
        # Add last value
        if current_value:
            values.append(current_value.strip())
        
        return values
    
    @staticmethod
    def get_table_preview(script: str, table_name: str, limit: int = 10) -> Dict[str, Any]:
        """Get preview of a specific table from script"""
        result = QlikScriptParser.parse_inline_data(script)
        
        if not result.get("success"):
            return {"success": False, "error": "Failed to parse script"}
        
        tables = result.get("tables", {})
        
        if table_name not in tables:
            return {
                "success": False,
                "error": f"Table '{table_name}' not found in script",
                "available_tables": list(tables.keys())
            }
        
        table_data = tables[table_name]
        rows = table_data.get("rows", [])
        
        return {
            "success": True,
            "table_name": table_name,
            "columns": table_data.get("columns", []),
            "rows": rows[:limit],
            "total_rows": len(rows),
            "showing_rows": min(limit, len(rows)),
            "column_count": table_data.get("column_count", 0)
        }
    
    @staticmethod
    def convert_to_html_table(script: str, table_name: str = None) -> str:
        """Convert script data to HTML table"""
        result = QlikScriptParser.parse_inline_data(script)
        
        if not result.get("success"):
            return "<p>Error parsing script</p>"
        
        tables = result.get("tables", {})
        
        if not tables:
            return "<p>No tables found in script</p>"
        
        html = "<style>"
        html += "table { border-collapse: collapse; width: 100%; margin: 20px 0; }"
        html += "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }"
        html += "th { background-color: #4CAF50; color: white; }"
        html += "tr:nth-child(even) { background-color: #f2f2f2; }"
        html += "h2 { color: #333; }"
        html += ".table-container { margin: 20px 0; }"
        html += "</style>"
        
        # If specific table requested
        if table_name:
            if table_name in tables:
                html += QlikScriptParser._table_to_html(table_name, tables[table_name])
            else:
                html += f"<p>Table '{table_name}' not found</p>"
        else:
            # Show all tables
            for tbl_name, tbl_data in tables.items():
                html += QlikScriptParser._table_to_html(tbl_name, tbl_data)
        
        return html
    
    @staticmethod
    def _table_to_html(table_name: str, table_data: Dict[str, Any]) -> str:
        """Convert a single table to HTML"""
        html = f'<div class="table-container">'
        html += f'<h2>{table_name}</h2>'
        html += f'<p>Rows: {table_data.get("row_count", 0)} | Columns: {table_data.get("column_count", 0)}</p>'
        html += '<table>'
        
        # Headers
        html += '<thead><tr>'
        for col in table_data.get("columns", []):
            html += f'<th>{col}</th>'
        html += '</tr></thead>'
        
        # Rows
        html += '<tbody>'
        for row in table_data.get("rows", []):
            html += '<tr>'
            for col in table_data.get("columns", []):
                value = row.get(col, '')
                html += f'<td>{value}</td>'
            html += '</tr>'
        html += '</tbody>'
        
        html += '</table>'
        html += '</div>'
        
        return html
    
    @staticmethod
    def convert_to_csv(script: str, table_name: str) -> str:
        """Convert script data to CSV"""
        result = QlikScriptParser.parse_inline_data(script)
        
        if not result.get("success"):
            return ""
        
        tables = result.get("tables", {})
        
        if table_name not in tables:
            return ""
        
        table_data = tables[table_name]
        
        # Create CSV
        csv_lines = []
        
        # Headers
        csv_lines.append(','.join(table_data.get("columns", [])))
        
        # Rows
        for row in table_data.get("rows", []):
            values = [str(row.get(col, '')) for col in table_data.get("columns", [])]
            csv_lines.append(','.join(values))
        
        return '\n'.join(csv_lines)