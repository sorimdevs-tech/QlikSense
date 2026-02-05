
import "./SummaryPage.css";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { fetchTables, fetchTableData, fetchVehicleSummary } from "../api/qlikApi";

type TableInfo = string | { name: string; [key: string]: any };
type Row = Record<string, any>;

export default function SummaryPage() {
  const location = useLocation();
  const navigate = useNavigate();
  
  const [appId, setAppId] = useState<string>("");
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [filteredTables, setFilteredTables] = useState<TableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // 1 → GET APP ID FROM NAVIGATION STATE
  useEffect(() => {
    const state = location.state as any;
    const passedAppId = state?.appId;

    if (!passedAppId) {
      alert("No app selected. Please go back and select an app.");
      navigate("/apps");
      return;
    }

    setAppId(passedAppId);
  }, [location, navigate]);

  // 2 → LOAD TABLE LIST
  useEffect(() => {
    if (!appId) return;
      
    fetchTables(appId)
      .then((data) => {
        setTables(data || []);
        setFilteredTables(data || []);
        console.log("All tables fetched:", data); // ✅ debug
        
        // AUTO-LOAD FIRST TABLE
        if (data && data.length > 0) {
          const firstTableName = typeof data[0] === "string" ? data[0] : data[0]?.name;
          if (firstTableName) {
            loadData(firstTableName);
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [appId]);

  // SEARCH FILTER
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    
    if (!query.trim()) {
      setFilteredTables(tables);
    } else {
      const filtered = tables.filter((t) => {
        const tableName = typeof t === "string" ? t : t?.name;
        return tableName?.toLowerCase().includes(query.toLowerCase());
      });
      setFilteredTables(filtered);
    }
  };

  // 3 → LOAD DATA FOR SELECTED TABLE
  const loadData = async (tableName: string) => {
    if (!tableName || tableName === selectedTable) return;

    setSelectedTable(tableName);
    setTableLoading(true);
    setRows([]);
    setSummary(null);

    try {
      const data = await fetchTableData(appId, tableName);
      setRows(data || []);

      // 2️⃣ SUMMARY DATA
      const sum = await fetchVehicleSummary(appId, tableName);
      setSummary(sum);
    } catch (e) {
      console.error(e);
    } finally {
      setTableLoading(false);
    }
  };

  // CSV DOWNLOAD
  const downloadCSV = () => {
    if (!rows.length) {
      alert("No data");
      return;
    }

    const headers = Object.keys(rows[0]);
    const csv = [
      headers.join(","),
      ...rows.map((r) => headers.map((h) => `"${r[h] ?? ""}"`).join(",")),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedTable || "data"}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading) {
    return <div className="wrap">Loading…</div>;
  }

  return (
    <div className="summary-layout">
      {/* LEFT – TABLE NAMES */}
      <div className="left-panel">
        <div className="panel-header">
          <h3 className="title">Tables</h3>
        </div>

        {/* SEARCH BOX */}
        <div className="search-box">
          <input
            type="text"
            placeholder="Search tables..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="search-input"
          />
        </div>

        {tables.length === 0 && (
          <p className="no-tables">No tables found</p>
        )}

        {filteredTables.map((t, i) => {
          const tableName = typeof t === "string" ? t : t?.name;
          if (!tableName) return null;

          return (
            <div
              key={i}
              className={
                tableName === selectedTable
                  ? "table-item active"
                  : "table-item"
              }
              onClick={() => loadData(tableName)}
            >
              {tableName}
            </div>
          );
        })}
      </div>

      {/* RIGHT – SUMMARY + DATA */}
      <div className="right-panel">
        {!selectedTable && (
          <div className="empty">
            <p>👈 Select a table on the left to view its data</p>
          </div>
        )}

        {selectedTable && (
          <>

            {/* HEADER ONLY TITLE */}
            <div className="header">
              <h2>{selectedTable}</h2>
            </div>

            <SummaryReport summary={summary} />

            {/* ===== SEPARATE DIV FOR TABLE ===== */}
            <div className="data-section">

              {tableLoading && <p>Loading data…</p>}

              {!tableLoading && rows.length > 0 && (
                <>
                  <div className="table-wrapper">
                    <table className="data-table">
                      <thead>
                        <tr>
                          {Object.keys(rows[0]).map((k) => (
                            <th key={k}>{k}</th>
                          ))}
                        </tr>
                      </thead>

                      <tbody>
                         {/* ✅ Show all rows, removed slice */}
            {rows.map((r, i) => (
              <tr key={i}>
                {Object.keys(rows[0]).map((k, j) => (
                  <td key={j}>{String(r[k] ?? "")}</td>
                ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    <div className="table-footer">
                      Total {rows.length} rows
                    </div>
                  </div>

                  {/* BOTTOM RIGHT BUTTON */}
                  <div className="bottom-actions">
                    <button
                      className="export-btn"
                      onClick={() => navigate("/export", { state: { appId, selectedTable, rows } })}
                      title="Navigate to Export tab"
                    >
                      📤 Export
                    </button>
                    <button
                      className="csv-btn"
                      disabled={!rows.length}
                      onClick={downloadCSV}
                    >
                      Download CSV
                    </button>
                  </div>
                </>
              )}

            </div>

          </>
        )}
      </div>
    </div>
  );
}

// ================= SUMMARY REPORT COMPONENT =================
import React from "react";
import { data } from "react-router-dom";

interface SummaryReportProps {
  summary: any;
  onDownload?: () => void;
}

export const SummaryReport: React.FC<SummaryReportProps> = ({
  summary,
  onDownload,
}) => {
  if (!summary) return null;

  const rows = [
    {
      category: "Total Vehicles",
      metric: "Count",
      value: summary["Total Rows"],
      notes: "Full dataset size",
    },
    {
      category: "By Type",
      metric: "Cars",
      value: summary["Category Counts"]?.VehicleType?.Car || 0,
      notes: `${Math.round(
        ((summary["Category Counts"]?.VehicleType?.Car || 0) /
          summary["Total Rows"]) *
          100
      )}% of dataset`,
    },
    {
      category: "By Type",
      metric: "Bikes",
      value: summary["Category Counts"]?.VehicleType?.Bike || 0,
      notes: `${Math.round(
        ((summary["Category Counts"]?.VehicleType?.Bike || 0) /
          summary["Total Rows"]) *
          100
      )}% of dataset`,
    },
    {
      category: "Fuel Type",
      metric: "Petrol",
      value: summary["Category Counts"]?.FuelType?.Petrol || 0,
      notes: "Dominant fuel",
    },
    {
      category: "Fuel Type",
      metric: "Diesel",
      value: summary["Category Counts"]?.FuelType?.Diesel || 0,
      notes: "Only in cars",
    },
    {
      category: "Fuel Type",
      metric: "Electric",
      value: summary["Category Counts"]?.FuelType?.Electric || 0,
      notes: "Tata Nexon",
    },
    {
      category: "Price (₹)",
      metric: "Highest",
      value: summary["Numeric Analysis"]?.Price?.max || "-",
      notes: "Hyundai Creta",
    },
    {
      category: "Price (₹)",
      metric: "Lowest",
      value: summary["Numeric Analysis"]?.Price?.min || "-",
      notes: "Hero SplendorPlus",
    },
    {
      category: "Price (₹)",
      metric: "Avg – Cars",
      value: summary["Numeric Analysis"]?.Price?.avg || "-",
      notes: "Premium segment",
    },
    {
      category: "Price (₹)",
      metric: "Avg – Bikes",
      value: summary["Numeric Analysis"]?.Price?.avg || "-",
      notes: "Economy segment",
    },
    {
      category: "Mileage",
      metric: "Best",
      value: summary["Numeric Analysis"]?.Mileage?.max || "-",
      notes: "Hero Splendor",
    },
    {
      category: "Mileage",
      metric: "Worst",
      value: summary["Numeric Analysis"]?.Mileage?.min || "-",
      notes: "Electric vehicle",
    },
    {
      category: "Mileage",
      metric: "Avg – Cars",
      value: summary["Numeric Analysis"]?.Mileage?.avg || "-",
      notes: "Excluding EV",
    },
    {
      category: "Mileage",
      metric: "Avg – Bikes",
      value: summary["Numeric Analysis"]?.Mileage?.avg || "-",
      notes: "Very efficient",
    },
    {
      category: "City Spread",
      metric: "Unique Cities",
      value: Object.keys(summary["Category Counts"]?.City || {}).length,
      notes: "Good coverage",
    },
    {
      category: "City Spread",
      metric: "Top Cities",
      value: Object.keys(summary["Category Counts"]?.City || {})
        .slice(0, 2)
        .join(", "),
      notes: "2 vehicles each",
    },
    {
      category: "Year Trend",
      metric: "2023 Models",
      value: 4,
      notes: "Most recent",
    },
    {
      category: "Year Trend",
      metric: "2022 Models",
      value: 4,
      notes: "Stable demand",
    },
    {
      category: "Year Trend",
      metric: "2021 & 2020",
      value: 2,
      notes: "Older stock",
    },
  ];




  return (
    <div className="summary-report">
      <h3>📌Summary Table</h3>
      {/* <table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Metric</th>
            <th>Value</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td >{r.category}</td>
              <td>{r.metric}</td>
              <td className="value">{r.value}</td>
              <td>{r.notes}</td>
            </tr>
          ))}
        </tbody>
      </table> */}
    </div>
  );
};
