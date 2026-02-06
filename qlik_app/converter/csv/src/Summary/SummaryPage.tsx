

import "./SummaryPage.css";
import { useEffect, useState, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { fetchTables, fetchTableData, fetchVehicleSummary } from "../api/qlikApi";
import Csvicon from "../assets/Csvicon.png";
import { useWizard } from "../context/WizardContext";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";

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
  // Data-table controls
  const [tableQuery, setTableQuery] = useState<string>("");
  const [pageSize, setPageSize] = useState<number>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Derived pagination lists with search + sorting
  const [orderBy, setOrderBy] = useState<string>("");
  const [order, setOrder] = useState<"asc" | "desc">("asc");

  const processedRows = useMemo(() => {
    let out = rows || [];

    // search filter
    if (tableQuery.trim()) {
      const q = tableQuery.toLowerCase();
      out = out.filter((r) =>
        Object.values(r).some((v) =>
          String(v ?? "").toLowerCase().includes(q)
        )
      );
    }

    // sorting
    if (orderBy) {
      out = out.slice().sort((a: any, b: any) => {
        const va = a[orderBy];
        const vb = b[orderBy];
        if (va === vb) return 0;
        if (va == null) return 1;
        if (vb == null) return -1;
        if (typeof va === "number" && typeof vb === "number") {
          return order === "asc" ? va - vb : vb - va;
        }
        const sa = String(va).toLowerCase();
        const sb = String(vb).toLowerCase();
        if (sa < sb) return order === "asc" ? -1 : 1;
        if (sa > sb) return order === "asc" ? 1 : -1;
        return 0;
      });
    }

    return out;
  }, [rows, tableQuery, orderBy, order]);

  const totalEntries = processedRows.length;
  const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
  const current = Math.min(currentPage, totalPages);
  const startIndex = totalEntries ? (current - 1) * pageSize : 0;
  const endIndex = Math.min(startIndex + pageSize, totalEntries);
  const visibleRows = processedRows.slice(startIndex, endIndex);

  const handleRequestSort = (property: string) => {
    if (orderBy === property) {
      setOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setOrderBy(property);
      setOrder("asc");
    }
  };

  const pageNumbers = useMemo<(number | string)[]>(() => {
    const nums: (number | string)[] = [];
    const max = totalPages;
    const cur = current;
    if (max <= 7) {
      for (let i = 1; i <= max; i++) nums.push(i);
    } else {
      nums.push(1);
      if (cur > 3) nums.push("...");
      const start = Math.max(2, cur - 1);
      const end = Math.min(max - 1, cur + 1);
      for (let i = start; i <= end; i++) nums.push(i);
      if (cur < max - 2) nums.push("...");
      nums.push(max);
    }
    return nums;
  }, [totalPages, current]);

  useEffect(() => {
    setCurrentPage(1);
  }, [rows, pageSize, tableQuery]);

  // 1 → GET APP ID FROM NAVIGATION STATE
  useEffect(() => {
    const state = location.state as any;
    const passedAppId = state?.appId || sessionStorage.getItem("appSelected");

    if (!passedAppId) {
      alert("No app selected. Please go back and select an app.");
      navigate("/apps");
      return;
    }

    setAppId(passedAppId);
  }, [location, navigate]);

  // 2 → LOAD TABLE LIST
  const { stopTimer, startTimer, getLastElapsed } = useWizard();

  useEffect(() => {
    if (!appId) return;

    // ensure we have an active timer for /summary (covers direct navigation)
    if (sessionStorage.getItem("lastTimerTarget") !== "/summary") {
      startTimer?.("/summary");
    }
      
    fetchTables(appId)
      .then((data) => {
        // If table objects have `created` or `createdAt`, sort by newest first
        const sorted = (data || []).slice().sort((x: any, y: any) => {
          const xa = typeof x === "string" ? null : x.created || x.createdAt || null;
          const ya = typeof y === "string" ? null : y.created || y.createdAt || null;

          if (xa && ya) return +new Date(ya) - +new Date(xa);
          return 0;
        });

        setTables(sorted);
        setFilteredTables(sorted);
        console.log("All tables fetched:", sorted); // ✅ debug
        
        // AUTO-LOAD FIRST TABLE
        if (sorted && sorted.length > 0) {
          const firstTableName = typeof sorted[0] === "string" ? sorted[0] : sorted[0]?.name;
          if (firstTableName) {
            loadData(firstTableName);
          }
        }
      })
      .catch(() => {})
      .finally(() => {
        setLoading(false);
        // Stop timer started by Apps when navigating to Summary
        // stopTimer?.("/summary");
      });
  }, [appId, stopTimer, startTimer]);



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

      // Persist selection for Export fallback
      try {
        sessionStorage.setItem("selectedTable", tableName);
        sessionStorage.setItem("selectedRows", JSON.stringify(data || []));
      } catch (e) {
        // ignore storage errors
      }

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
          <h3 className="title">Tables {`(${tables.length})`}</h3>
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
              {/* Page-specific analysis time */}
              {getLastElapsed?.("/summary") && (
                <div className="analysis-badge">AnalysisTime - {getLastElapsed!("/summary")}</div>
              )}
            </div>

            <SummaryReport summary={summary} rows={rows} />

            {/* ===== SEPARATE DIV FOR TABLE ===== */}
            <div className="data-section">
              

              {tableLoading && <p>Loading data…</p>}

              {!tableLoading && rows.length > 0 && (
                <>
                  {/* Top controls: page length + search */}
                  <div className="data-controls">
                    <div className="length">
                      <label>
                        <select
                          value={pageSize}
                          onChange={(e) => setPageSize(parseInt(e.target.value, 10))}
                        >
                          <option value={10}>10</option>
                          <option value={25}>25</option>
                          <option value={50}>50</option>
                          <option value={100}>100</option>
                        </select>
                        records per page
                      </label>
                    </div>
                    <div className="searchfilter">
                      <label className="lable-search">
                        Search:
                        <input
                          type="search"
                          value={tableQuery}
                          onChange={(e) => setTableQuery(e.target.value)}
                          placeholder="Search..."
                        />
                      </label>
                      <button
                      className="csv-btn"
                      disabled={!rows.length}
                      onClick={downloadCSV}
                    >
                      <img src={Csvicon} alt="csv " className="btn-icon" /> 
                    </button>
                    </div>
                  </div>

                  <div className="table-wrapper">
                    <TableContainer component={Paper}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            {rows[0] && Object.keys(rows[0]).map((k) => (
                              <TableCell key={k} sortDirection={orderBy === k ? order : false}>
                                <TableSortLabel
                                  active={orderBy === k}
                                  direction={orderBy === k ? order : 'asc'}
                                  onClick={() => handleRequestSort(k)}
                                >
                                  {k}
                                </TableSortLabel>
                              </TableCell>
                            ))}
                          </TableRow>
                        </TableHead>

                        <TableBody>
                          {visibleRows.map((r, i) => (
                            <TableRow key={i} hover>
                              {Object.keys(rows[0]).map((k, j) => (
                                <TableCell key={j}>{String(r[k] ?? "")}</TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>

                    <div className="table-footer">
                      {`Showing ${totalEntries ? startIndex + 1 : 0} to ${endIndex} of ${totalEntries} entries`}
                    </div>
                  </div>

                  {/* Pagination */}
                  <div className="pagination-bar">
                    <button
                      className="page-btn"
                      disabled={current === 1}
                      onClick={() => setCurrentPage(current - 1)}
                    >
                      Previous
                    </button>
                    {pageNumbers.map((p, idx) =>
                      typeof p === "number" ? (
                        <button
                          key={idx}
                          className={`page-btn ${p === current ? "active" : ""}`}
                          onClick={() => setCurrentPage(p)}
                        >
                          {p}
                        </button>
                      ) : (
                        <span key={idx} className="ellipsis">…</span>
                      )
                    )}
                    <button
                      className="page-btn"
                      disabled={current === totalPages}
                      onClick={() => setCurrentPage(current + 1)}
                    >
                      Next
                    </button>
                  </div>

                  {/* BOTTOM RIGHT BUTTON */}
                  <div className="bottom-actions">
                    <button
                      className="export-btn"
                      onClick={() => {
                        stopTimer?.("/summary");
                        // Mark summary completed to enable export step
                        sessionStorage.setItem("summaryComplete", "true");

                        // Start timer for export page load
                        startTimer?.("/export");

                        navigate("/export", {
                          state: {
                            appId,
                            appName: location.state?.appName || sessionStorage.getItem("appName") || appId,
                            selectedTable,
                            rows,
                          },
                        });
                      }}
                      title="Navigate to Export tab"
                    >
                      📤Continue to Export
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

interface SummaryReportProps {
  summary: any;
  rows: Row[];
}

// Pie Chart Component
const PieChart: React.FC<{ data: Record<string, number>; title: string }> = ({ data, title }) => {
  const entries = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);

  const total = entries.reduce((sum, [_, val]) => sum + val, 0);

  const colors = [
    "#FF6B6B",
    "#4ECDC4",
    "#45B7D1",
    "#FFA07A",
    "#98D8C8",
    "#F7DC6F",
    "#BB8FCE",
    "#85C1E2",
  ];

  let currentAngle = 0;
  const slices = entries.map(([label, value], i) => {
    const percentage = (value / total) * 100;
    const sliceAngle = (percentage / 100) * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + sliceAngle;

    // Convert angles to radians
    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);

    // Calculate path points
    const x1 = 100 + 80 * Math.cos(startRad);
    const y1 = 100 + 80 * Math.sin(startRad);
    const x2 = 100 + 80 * Math.cos(endRad);
    const y2 = 100 + 80 * Math.sin(endRad);

    const largeArc = sliceAngle > 180 ? 1 : 0;

    const pathData = [
      `M 100 100`,
      `L ${x1} ${y1}`,
      `A 80 80 0 ${largeArc} 1 ${x2} ${y2}`,
      `Z`,
    ].join(" ");

    // Label position
    const labelAngle = (startAngle + endAngle) / 2;
    const labelRad = (labelAngle - 90) * (Math.PI / 180);
    const labelX = 100 + 50 * Math.cos(labelRad);
    const labelY = 100 + 50 * Math.sin(labelRad);

    currentAngle = endAngle;

    return {
      pathData,
      color: colors[i % colors.length],
      label,
      percentage,
      value,
      labelX,
      labelY,
    };
  });

  return (
    <div className="pie-chart-container">
      <div className="pie-chart-content">
        <div className="pie-chart-left">
          {title && <h4>{title}</h4>}
          <svg viewBox="0 0 200 200" className="pie-svg">
            {slices.map((slice, i) => (
              <g key={i}>
                <path d={slice.pathData} fill={slice.color} stroke="white" strokeWidth="2" />
                {slice.percentage > 8 && (
                  <text
                    x={slice.labelX}
                    y={slice.labelY}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="pie-label"
                  >
                    {slice.percentage.toFixed(0)}%
                  </text>
                )}
              </g>
            ))}
          </svg>
        </div>
        <div className="pie-legend">
          {slices.map((slice, i) => (
            <div key={i} className="legend-item">
              <span className="legend-color" style={{ backgroundColor: slice.color }}></span>
              <span className="legend-text">
                {slice.label.substring(0, 20)}: {slice.percentage.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export const SummaryReport: React.FC<SummaryReportProps> = ({
  summary,
  rows,
}) => {
  if (!summary && rows.length === 0) return null;

  // Combine ALL categorical data into one pie chart
  const allCategoricalCounts: Record<string, number> = {};
  let topCityValue = "";
  let topCityCount = 0;
  const cityCount: Record<string, number> = {};

  rows.forEach((row) => {
    Object.entries(row).forEach(([key, value]) => {
      if (key.toLowerCase().includes('id')) return;

      const num = Number(value);
      if (isNaN(num) || num === null || num === 0) {
        // Categorical data
        const strValue = String(value);
        const label = `${key}: ${strValue}`;
        allCategoricalCounts[label] = (allCategoricalCounts[label] || 0) + 1;
        
        // Track top city
        if (key.toLowerCase().includes('city')) {
          cityCount[strValue] = (cityCount[strValue] || 0) + 1;
          if (cityCount[strValue] > topCityCount) {
            topCityCount = cityCount[strValue];
            topCityValue = strValue;
          }
        }
      }
    });
  });

  // Calculate metrics
  const totalVehicles = rows.length;
  const totalSales = rows.reduce((sum, row) => {
    const salesVal = Object.values(row).find(v => {
      const num = Number(v);
      return !isNaN(num) && num > 100;
    });
    return sum + (Number(salesVal) || 0);
  }, 0);
  const salesM = (totalSales / 1000000).toFixed(2);

  // Generate executive summary text
  const generateExecutiveSummary = () => {
    const topCity = topCityValue || "leading";
    const topEntries = Object.entries(allCategoricalCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3);
    
    const bulletPoints = [];
    
    bulletPoints.push(`Dataset contains ${totalVehicles} vehicles with total sales value of ${salesM}M`);
    bulletPoints.push(`${topCity} is the leading city with ${topCityCount} vehicles`);
    
    if (topEntries.length > 0) {
      const topItem = topEntries[0];
      const percentage = ((topItem[1] / totalVehicles) * 100).toFixed(1);
      bulletPoints.push(`Primary market segment: ${topItem[0].split(': ')[1]} (${percentage}% of dataset)`);
    }
    
    if (topEntries.length > 1) {
      const secondItem = topEntries[1];
      const percentage = ((secondItem[1] / totalVehicles) * 100).toFixed(1);
      bulletPoints.push(`Secondary segment: ${secondItem[0].split(': ')[1]} (${percentage}% of dataset)`);
    }
    
    bulletPoints.push(`Strong market performance with significant concentration in key geographical regions`);
    bulletPoints.push(`Diversified product portfolio across multiple categories`);
    
    return bulletPoints;
  };

  return (
    <div className="summary-report">
      {/* Top Metrics Cards */}
      {/* <div className="metrics-container">
        <div className="metric-card">
          <div className="metric-value">{totalVehicles}</div>
          <div className="metric-label">Total Vehicles</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{salesM}</div>
          <div className="metric-label">Total Sales (M)</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{(totalSales * 0.01).toFixed(1)}</div>
          <div className="metric-label">2025 Sales (M)</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{topCityValue}</div>
          <div className="metric-label">Top City</div>
        </div>
      </div> */}

      {/* Analytics Container - Pie Chart and Summary Side by Side */}
      <div className="analytics-container">
        {/* Left: Chart Section */}
        {Object.keys(allCategoricalCounts).length > 0 && (
          <div className="chart-section">
            <h4>Top Cities by Sales Value</h4>
            <PieChart data={allCategoricalCounts} title="" />
          </div>
        )}
        
        {/* Right: AI Summary Section */}
        <div className="hf-summary-section">
          <h4>Executive Summary</h4>
          <ul className="hf-summary-content">
            {generateExecutiveSummary().map((point, idx) => (
              <li key={idx}>{point}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
