

// import "./SummaryPage.css";
// import { useEffect, useState, useMemo, useRef } from "react";
// import { useLocation, useNavigate } from "react-router-dom";
// import { fetchTables, fetchTableData } from "../api/qlikApi";
// import Csvicon from "../assets/Csvicon.png";
// import { useWizard } from "../context/WizardContext";
// import Paper from "@mui/material/Paper";
// import Table from "@mui/material/Table";
// import TableBody from "@mui/material/TableBody";
// import TableCell from "@mui/material/TableCell";
// import TableContainer from "@mui/material/TableContainer";
// import TableHead from "@mui/material/TableHead";
// import TableRow from "@mui/material/TableRow";
// import TableSortLabel from "@mui/material/TableSortLabel";
// import exportImg from "../assets/export2.png";
 
// type TableInfo = string | { name: string; [key: string]: any };
// type Row = Record<string, any>;


 
// export default function SummaryPage() {
//   const location = useLocation();
//   const navigate = useNavigate();
//   const pageStartTimeRef = useRef<number | null>(null);
 
//   const [appId, setAppId] = useState<string>("");
//   const [tables, setTables] = useState<TableInfo[]>([]);
//   const [filteredTables, setFilteredTables] = useState<TableInfo[]>([]);
//   const [selectedTable, setSelectedTable] = useState<string>("");
//   const [rows, setRows] = useState<Row[]>([]);
//   const [loading, setLoading] = useState(true);
//   const [tableLoading, setTableLoading] = useState(false);
//   const [summary, setSummary] = useState<any>(null);
//   const [pageLoadTime, setPageLoadTime] = useState<string | null>(null);

//   // Multi-select removed — clicking a master table will automatically include related tables when exporting
//   // (Manual multi-select UI was removed per UX request)
 
//   // Track page load start time
//   useEffect(() => {
//     pageStartTimeRef.current = Date.now();
//   }, []);
//   // Data-table controls
//   const [tableQuery, setTableQuery] = useState<string>("");
//   const [pageSize, setPageSize] = useState<number>(10);
//   const [currentPage, setCurrentPage] = useState<number>(1);
//   // Search for table list on the left panel
//   const [tableListQuery, setTableListQuery] = useState<string>("");
 
//   // Derived pagination lists with search + sorting
//   const [orderBy, setOrderBy] = useState<string>("");
//   const [order, setOrder] = useState<"asc" | "desc">("asc");
 
//   const processedRows = useMemo(() => {
//     let out = rows || [];
 
//     // search filter
//     if (tableQuery.trim()) {
//       const q = tableQuery.toLowerCase();
//       out = out.filter((r) =>
//         Object.values(r).some((v) =>
//           String(v ?? "").toLowerCase().includes(q)
//         )
//       );
//     }
 
//     // sorting
//     if (orderBy) {
//       out = out.slice().sort((a: any, b: any) => {
//         const va = a[orderBy];
//         const vb = b[orderBy];
//         if (va === vb) return 0;
//         if (va == null) return 1;
//         if (vb == null) return -1;
//         if (typeof va === "number" && typeof vb === "number") {
//           return order === "asc" ? va - vb : vb - va;
//         }
//         const sa = String(va).toLowerCase();
//         const sb = String(vb).toLowerCase();
//         if (sa < sb) return order === "asc" ? -1 : 1;
//         if (sa > sb) return order === "asc" ? 1 : -1;
//         return 0;
//       });
//     }
 
//     return out;
//   }, [rows, tableQuery, orderBy, order]);
 
//   const totalEntries = processedRows.length;
//   const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
//   const current = Math.min(currentPage, totalPages);
//   const startIndex = totalEntries ? (current - 1) * pageSize : 0;
//   const endIndex = Math.min(startIndex + pageSize, totalEntries);
//   const visibleRows = processedRows.slice(startIndex, endIndex);
 
//   const handleRequestSort = (property: string) => {
//     if (orderBy === property) {
//       setOrder((o) => (o === "asc" ? "desc" : "asc"));
//     } else {
//       setOrderBy(property);
//       setOrder("asc");
//     }
//   };
 
//   const pageNumbers = useMemo<(number | string)[]>(() => {
//     const nums: (number | string)[] = [];
//     const max = totalPages;
//     const cur = current;
//     if (max <= 7) {
//       for (let i = 1; i <= max; i++) nums.push(i);
//     } else {
//       nums.push(1);
//       if (cur > 3) nums.push("...");
//       const start = Math.max(2, cur - 1);
//       const end = Math.min(max - 1, cur + 1);
//       for (let i = start; i <= end; i++) nums.push(i);
//       if (cur < max - 2) nums.push("...");
//       nums.push(max);
//     }
//     return nums;
//   }, [totalPages, current]);
 
//   useEffect(() => {
//     setCurrentPage(1);
//   }, [rows, pageSize, tableQuery]);
 
//   // Filter the left-side table list when the user types in the table search box
//   useEffect(() => {
//     if (!tableListQuery) {
//       // Already sorted by recency, no need to reverse
//       setFilteredTables((tables || []).slice());
//       return;
//     }
 
//     const q = tableListQuery.toLowerCase();
//     const filtered = (tables || [])
//       .filter((t) => {
//         const name = typeof t === "string" ? t : t?.name || "";
//         return String(name).toLowerCase().includes(q);
//       })
//       .slice();
//     // Already sorted by recency, no need to reverse
//     setFilteredTables(filtered);
//   }, [tableListQuery, tables]);
 
//   // 1 → GET APP ID FROM NAVIGATION STATE
//   useEffect(() => {
//     const state = location.state as any;
//     const passedAppId = state?.appId || sessionStorage.getItem("appSelected");
 
//     if (!passedAppId) {
//       alert("No app selected. Please go back and select an app.");
//       navigate("/apps");
//       return;
//     }
 
//     setAppId(passedAppId);
//   }, [location, navigate]);
 
//   // 2 → LOAD TABLE LIST
//   const { stopTimer, startTimer, getLastElapsed } = useWizard();
 
//   useEffect(() => {
//     if (!appId) return;
 
//     // ensure we have an active timer for /summary (covers direct navigation)
//     if (sessionStorage.getItem("lastTimerTarget") !== "/summary") {
//       startTimer?.("/summary");
//     }
     
//       fetchTables(appId)
//       .then((data) => {
//         // Remove Qlik Cloud "@syn" system tables from the UI (user requested)
//         const cleaned = (data || []).filter((t: any) => {
//           const name = typeof t === 'string' ? t : t?.name || '';
//           if (!name) return false;
//           return !name.toLowerCase().startsWith('@syn');
//         });

//         // Sort table list by creation/added timestamp (newest first).
//         const getTimestamp = (t: any) => {
//           if (!t || typeof t === 'string') return 0;
//           const candidates = ['added_timestamp','created','createdAt','created_at','createdDate','modifiedDate','lastModifiedDate','lastReloadTime','lastReload'];
//           for (const k of candidates) {
//             const v = t[k];
//             if (v) {
//               const asNum = typeof v === 'number' ? v : Number(v);
//               if (!isNaN(asNum) && asNum > 0) return asNum;
//               const parsed = Date.parse(String(v));
//               if (!isNaN(parsed)) return parsed;
//             }
//           }
//           return 0;
//         };

//         const sorted = (cleaned || []).slice().sort((x: any, y: any) => {
//           const tx = getTimestamp(x);
//           const ty = getTimestamp(y);
//           if (tx !== ty) return ty - tx; // newest first

//           // Prefer explicitly flagged 'is_new' items
//           const xi = (typeof x === 'string') ? false : !!x.is_new;
//           const yi = (typeof y === 'string') ? false : !!y.is_new;
//           if (xi && !yi) return -1;
//           if (!xi && yi) return 1;

//           // fallback to case-insensitive alphabetical order
//           const nx = typeof x === 'string' ? x : x?.name || '';
//           const ny = typeof y === 'string' ? y : y?.name || '';
//           return String(nx).localeCompare(String(ny), undefined, { sensitivity: 'base' });
//         });

//         setTables(sorted);
//         // Display list already sorted by recency, no need to reverse
//         setFilteredTables(sorted);
//         console.log("All tables fetched (sorted by recency, @syn filtered):", sorted);

//         // AUTO-LOAD: prefer a detected *master* table, otherwise fall back to most-recent
//         if (sorted && sorted.length > 0) {
//           // 1) explicit master-like names (priority)
//           const masterLike = sorted.find((t: any) => {
//             const n = typeof t === 'string' ? t : t?.name || '';
//             return /\b(master|fact|main)\b/i.test(n);
//           });

//           // 2) if none, pick table with highest field count in any prefix group (best-effort master)
//           let fieldiest: any = null;
//           if (!masterLike) {
//             for (const t of sorted) {
//               const name = typeof t === 'string' ? t : t?.name || '';
//               const fields = typeof t === 'string' ? 0 : (t?.fields || []).length || 0;
//               if (!fieldiest || fields > (fieldiest.fields || 0)) fieldiest = { name, fields };
//             }
//           }

//           const chosen = masterLike ? (typeof masterLike === 'string' ? masterLike : masterLike?.name) : (fieldiest ? fieldiest.name : (typeof sorted[0] === 'string' ? sorted[0] : sorted[0]?.name));

//           if (chosen) loadData(chosen);
//         }
//       })
//       .catch(() => {})
//       .finally(() => {
//         setLoading(false);
//         // Don't stop timer yet - wait for table data to load
//       });
//   }, [appId, stopTimer, startTimer]);
 
 
 
//   // 3 → LOAD DATA FOR SELECTED TABLE
//   const formatElapsed = (msTotal: number) => {
//     const minutes = Math.floor(msTotal / 60000);
//     const seconds = Math.floor((msTotal % 60000) / 1000);
//     const centis = Math.floor((msTotal % 1000) / 10);
//     const pad = (n: number, width = 2) => String(n).padStart(width, "0");
//     return `${pad(minutes)}m : ${pad(seconds)}s : ${pad(centis)}ms`;
//   };
 
//   const loadData = async (tableName: string) => {
//     if (!tableName || tableName === selectedTable) return;
 
//     setSelectedTable(tableName);
//     setTableLoading(true);
//     setRows([]);
//     setSummary(null);
 
//     // start timing this table's data load
//     startTimer?.(`/summary/data/${tableName}`);
 
//     try {
//       const data = await fetchTableData(appId, tableName);
//       setRows(data || []);
 
//       // Persist selection for Export fallback
//       try {
//         sessionStorage.setItem("selectedTable", tableName);
//         sessionStorage.setItem("selectedRows", JSON.stringify(data || []));
//       } catch (e) {
//         // ignore storage errors
//       }
 
//       // 2️⃣ SUMMARY DATA - Calculate locally from the fetched data
//       // This avoids backend dependency and works with any data format
//       const { generateSummaryFromData } = await import("../api/qlikApi");
//       const summary = generateSummaryFromData(data, tableName);
//       setSummary(summary);
//     } catch (e) {
//       console.error("❌ Error loading table data:", e);
      
//       // Show helpful error message
//       const errorMessage = e instanceof Error ? e.message : String(e);
//       alert(
//         `Failed to load table "${tableName}".\n\n` +
//         `Error: ${errorMessage}\n\n` +
//         `Suggestions:\n` +
//         `1. Verify the table name is correct\n` +
//         `2. Ensure the app has been reloaded with the latest data in QlikCloud\n` +
//         `3. Check the backend is running (http://127.0.0.1:8000)`
//       );
//     } finally {
//       setTableLoading(false);
 
//       // Prefer the specific table/data load elapsed if available
//       const tableElapsed = stopTimer?.(`/summary/data/${tableName}`);
//       if (tableElapsed) {
//         console.debug(`Table ${tableName} load time:`, tableElapsed);
//         setPageLoadTime(tableElapsed);
//       } else {
//         // Fallback: show navigation/load time for the Summary page if available
//         const navElapsed = getLastElapsed?.("/summary");
//         if (navElapsed) {
//           setPageLoadTime(navElapsed);
//         } else if (pageStartTimeRef.current) {
//           // As a last resort, show local elapsed since page mount
//           const totalTime = Date.now() - pageStartTimeRef.current;
//           setPageLoadTime(formatElapsed(totalTime));
//         }
//       }
//     }
//   };

//   // related-table prefetch is handled when exporting a master table (no per-table cache required here) 
 
//   // CSV DOWNLOAD
//   const downloadCSV = () => {
//     if (!rows.length) {
//       alert("No data");
//       return;
//     }
 
//     const headers = Object.keys(rows[0]);
//     const csv = [
//       headers.join(","),
//       ...rows.map((r) => headers.map((h) => `"${r[h] ?? ""}"`).join(",")),
//     ].join("\n");
 
//     const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
//     const url = window.URL.createObjectURL(blob);
 
//     const a = document.createElement("a");
//     a.href = url;
//     a.download = `${selectedTable || "data"}.csv`;
//     a.click();
//     window.URL.revokeObjectURL(url);
//   };
 
//   // Compute master table per-prefix (heuristic: prefer name containing "fact/master/main", else use largest field count)
//   const masterMap = useMemo(() => {
//     const map = new Map<string, string>();
//     const groups: Record<string, any[]> = {};
//     (tables || []).forEach((t) => {
//       const name = typeof t === "string" ? t : t?.name || "";
//       if (!name) return;
//       const prefix = name.includes("_") ? name.split("_")[0] : "__noprefix__";
//       groups[prefix] = groups[prefix] || [];
//       groups[prefix].push(t);
//     });

//     Object.keys(groups).forEach((prefix) => {
//       const group = groups[prefix];
//       if (!group || group.length <= 1) return;

//       const candidates = group.map((g: any) => {
//         const name = typeof g === "string" ? g : g?.name || "";
//         const fields = typeof g === "string" ? 0 : (g?.fields || []).length || 0;
//         return { name, fields };
//       });

//       // explicit override: if a table named exactly 'Ford_Vehicle_Fact' exists use it as the master
//       const fordExplicit = candidates.find((c: any) => c.name.toLowerCase() === 'ford_vehicle_fact');
//       if (fordExplicit) {
//         map.set(prefix, fordExplicit.name);
//         return;
//       }

//       // prefer explicit names (Fact / Master / Main)
//       const explicit = candidates.find((c: any) => /fact|master|main/i.test(c.name));
//       if (explicit) {
//         map.set(prefix, explicit.name);
//         return;
//       }

//       // fallback to table with most fields
//       candidates.sort((a: any, b: any) => (b.fields || 0) - (a.fields || 0));
//       map.set(prefix, candidates[0].name);
//     });

//     return map;
//   }, [tables]);

//   const isMasterTable = (name: string) => {
//     if (!name) return false;
//     const lower = name.toLowerCase();
//     // Explicit override: treat Ford_Vehicle_Fact as master (case-insensitive)
//     if (lower === "ford_vehicle_fact") return true;
//     const prefix = name.includes("_") ? name.split("_")[0] : null;
//     if (!prefix) return false;
//     return masterMap.get(prefix) === name;
//   };

//   const isRelatedTable = (name: string) => {
//     if (!name) return false;
//     const prefix = name.includes("_") ? name.split("_")[0] : null;
//     if (!prefix) return false;
//     const master = masterMap.get(prefix);
//     return Boolean(master && master !== name && (tables || []).some(t => (typeof t === 'string' ? t : t?.name) === master));
//   };

//   const sortedFilteredTables = useMemo(() => {
//     const arr = (filteredTables || []).slice();
//     arr.sort((a, b) => {
//       const an = typeof a === 'string' ? a : a?.name || '';
//       const bn = typeof b === 'string' ? b : b?.name || '';
//       const aMaster = isMasterTable(an);
//       const bMaster = isMasterTable(bn);
//       if (aMaster && !bMaster) return -1;
//       if (!aMaster && bMaster) return 1;
//       return an.localeCompare(bn);
//     });
//     return arr;
//   }, [filteredTables, masterMap]);

//   const isSelectionMaster = !!(selectedTable && isMasterTable(selectedTable));
//   // Export allowed when either master is selected or the selected table has no related tables
//   const exportAllowed = Boolean(selectedTable && (isSelectionMaster || !isRelatedTable(selectedTable)));


//   if (loading) {
//     return <div className="wrap">Loading…</div>;
//   }
 
//   return (
//     <div className="summary-layout">
//       {/* LEFT – TABLE NAMES */}
//       <div className="left-panel">
//         <div className="panel-header">
//           <h3 className="title">Tables {`(${tables.length})`}</h3>

//         </div>
 
//         {/* Table list search (searches the list of table names) */}
//         <div className="table-search">
//           <input
//             type="search"
//             placeholder="Search tables..."
//             value={tableListQuery}
//             onChange={(e) => setTableListQuery(e.target.value)}
//             className="table-search-input"
//           />
//         </div>
 
 
 
//         {tables.length === 0 && (
//           <p className="no-tables">No tables found</p>
//         )}
 
//         {sortedFilteredTables.map((t, i) => {
//           const tableName = typeof t === "string" ? t : t?.name;
//           const isNew = typeof t === "string" ? false : t?.is_new;
//           if (!tableName) return null;

//           const master = isMasterTable(tableName);
//           const related = isRelatedTable(tableName);
//           const cls = `${tableName === selectedTable ? "table-item active" : "table-item"}${master ? " master-row" : ""}`;

//           return (
//             <div
//               key={i}
//               className={cls}
//               onClick={() => loadData(tableName)}
//               title={master ? "Master table — click to export master + its related tables" : related ? "Related table — preview only — export disabled (select master to export)" : "Click to preview table"}
//             >
//               <span style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
//                 <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{tableName}</span>
//               </span>
//               {isNew && <span className="new-badge">NEW</span>}
//             </div>
//           );
//         })}
//       </div>

//       {/* RIGHT – SUMMARY + DATA */}
//       <div className="right-panel">
//         {!selectedTable && (
//           <div className="empty">
//             <p>👈 Select a table on the left to view its data</p>
//           </div>
//         )}
 
//         {selectedTable && (
//           <>
 
//               {/* HEADER ONLY TITLE */}
//             <div className="header">
//               <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",width: "100%" }}>
//                 <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
//                   <span>{selectedTable}</span>
//                   {isSelectionMaster && <span className="master-indicator">master</span>}
//                 </h2>
//                 {pageLoadTime && (
//                   <div className="timer-badge">Analysis Time: {pageLoadTime}</div>
//                 )}
//               </div>
//             </div>
 
//             <SummaryReport summary={summary} rows={rows} />
 
//             {/* ===== SEPARATE DIV FOR TABLE ===== */}
//             <div className="data-section">
             
 
//               {tableLoading && <p>Loading data…</p>}

//               {!tableLoading && (
//                 <>
//                   {rows.length > 0 ? (
//                     <>
//                       {/* Top controls: page length + search */}
//                       <div className="data-controls">
//                         <div className="length">
//                           <label>
//                             <select
//                               value={pageSize}
//                               onChange={(e) => setPageSize(parseInt(e.target.value, 10))}
//                             >
//                               <option value={10}>10</option>
//                               <option value={25}>25</option>
//                               <option value={50}>50</option>
//                               <option value={100}>100</option>
//                             </select>
//                             records per page
//                           </label>
//                         </div>
//                         <div className="searchfilter">
//                           <label className="lable-search">
//                             Search:
//                             <input
//                               type="search"
//                               value={tableQuery}
//                               onChange={(e) => setTableQuery(e.target.value)}
//                               placeholder="Search..."
//                             />
//                           </label>
//                           <button
//                             className="csv-btn"
//                             disabled={!rows.length}
//                             onClick={downloadCSV}
//                           >
//                             <img src={Csvicon} alt="csv " className="btn-icon" />
//                           </button>
//                         </div>
//                       </div>

//                       <div className="table-wrapper">
//                         <TableContainer component={Paper}>
//                           <Table size="small">
//                             <TableHead>
//                               <TableRow>
//                                 {rows[0] && Object.keys(rows[0]).map((k) => (
//                                   <TableCell key={k} sortDirection={orderBy === k ? order : false}>
//                                     <TableSortLabel
//                                       active={orderBy === k}
//                                       direction={orderBy === k ? order : 'asc'}
//                                       onClick={() => handleRequestSort(k)}
//                                     >
//                                       {k}
//                                     </TableSortLabel>
//                                   </TableCell>
//                                 ))}
//                               </TableRow>
//                             </TableHead>

//                             <TableBody>
//                               {visibleRows.map((r, i) => (
//                                 <TableRow key={i} hover>
//                                   {Object.keys(rows[0]).map((k, j) => (
//                                     <TableCell key={j}>{String(r[k] ?? "")}</TableCell>
//                                   ))}
//                                 </TableRow>
//                               ))}
//                             </TableBody>
//                           </Table>
//                         </TableContainer>

//                         <div className="table-footer">
//                           {`Showing ${totalEntries ? startIndex + 1 : 0} to ${endIndex} of ${totalEntries} entries`}
//                         </div>
//                       </div>

//                       {/* Pagination */}
//                       <div className="pagination-bar">
//                         <button
//                           className="page-btn"
//                           disabled={current === 1}
//                           onClick={() => setCurrentPage(current - 1)}
//                         >
//                           Previous
//                         </button>
//                         {pageNumbers.map((p, idx) =>
//                           typeof p === "number" ? (
//                             <button
//                               key={idx}
//                               className={`page-btn ${p === current ? "active" : ""}`}
//                               onClick={() => setCurrentPage(p)}
//                             >
//                               {p}
//                             </button>
//                           ) : (
//                             <span key={idx} className="ellipsis">…</span>
//                           )
//                         )}
//                         <button
//                           className="page-btn"
//                           disabled={current === totalPages}
//                           onClick={() => setCurrentPage(current + 1)}
//                         >
//                           Next
//                         </button>
//                       </div>
//                     </>
//                   ) : (
//                     <div className="no-data-placeholder" style={{ padding: 20 }}>
//                       <p style={{ margin: 0, color: '#444' }}>No rows available for this table — preview not available.</p>
//                       <p style={{ marginTop: 8, color: '#666' }}>You can still export this table; clicking <strong>Continue to Export</strong> will attempt to load the table data.</p>
//                     </div>
//                   )}

//                   {/* BOTTOM RIGHT BUTTON - Export (single table or auto-include related tables for master) */}
//                   <div className="bottom-actions">
//                     <button
//                       className="export-btn"
//                       disabled={!exportAllowed || tableLoading}
//                       title={!exportAllowed ? "Export disabled: select the master table (or a standalone table) to export" : "Continue to export selected table(s)"}
//                       onClick={async () => {
//                         try {
//                           stopTimer?.("/summary");
//                           sessionStorage.setItem("summaryComplete", "true");
//                           startTimer?.("/export");

//                           const sel = selectedTable || sessionStorage.getItem("selectedTable") || "";

//                           // If we don't have rows for the selected table yet, try to fetch them now
//                           let masterRows = rows;
//                           if ((!masterRows || masterRows.length === 0) && sel) {
//                             try {
//                               setTableLoading(true);
//                               const loaded = await fetchTableData(appId, sel);
//                               masterRows = loaded || [];
//                               setRows(masterRows);
//                               // regenerate summary for the newly loaded data
//                               const { generateSummaryFromData } = await import("../api/qlikApi");
//                               setSummary(generateSummaryFromData(masterRows, sel));
//                             } catch (e) {
//                               console.warn("Failed to load selected table prior to export:", e);
//                               alert("Failed to load table data for export. See console for details.");
//                               setTableLoading(false);
//                               return;
//                             } finally {
//                               setTableLoading(false);
//                             }
//                           }

//                           const prefix = sel && sel.includes("_") ? sel.split("_")[0] : null;
//                           const candidateNames = (tables || []).map((t) => (typeof t === "string" ? t : t?.name)).filter(Boolean) as string[];
//                           const related = prefix ? candidateNames.filter(n => n.startsWith(prefix + "_") && n !== sel) : [];

//                           if (!related || related.length === 0) {
//                             // No related tables — continue with single-table export
//                             navigate("/export", {
//                               state: {
//                                 appId,
//                                 appName: location.state?.appName || sessionStorage.getItem("appName") || appId,
//                                 selectedTable: sel,
//                                 rows: masterRows || [],
//                               },
//                             });
//                             return;
//                           }

//                           // Prefetch related tables (master first)
//                           setTableLoading(true);
//                           const selectedData: any[] = [];
//                           selectedData.push({ name: sel, data: { name: sel, rows: masterRows || [], summary } });

//                           for (const relName of related) {
//                             try {
//                               const relRows = await fetchTableData(appId, relName);
//                               const { generateSummaryFromData } = await import("../api/qlikApi");
//                               const relSummary = generateSummaryFromData(relRows, relName);
//                               selectedData.push({ name: relName, data: { name: relName, rows: relRows, summary: relSummary } });
//                             } catch (e) {
//                               console.warn("Failed to load related table:", relName, e);
//                             }
//                           }

//                           setTableLoading(false);

//                           navigate("/export", {
//                             state: {
//                               appId,
//                               appName: location.state?.appName || sessionStorage.getItem("appName") || appId,
//                               selectedTables: selectedData,
//                             },
//                           });
//                         } catch (err) {
//                           setTableLoading(false);
//                           console.error(err);
//                           alert("Failed to prepare related tables for export. See console for details.");
//                         }
//                       }}
//                     >
//                       <img src={exportImg} alt="Export" />Continue to Export
//                     </button>

//                     {/* Hint shown when export is disabled because a related table is selected */}
//                     {!exportAllowed && selectedTable && isRelatedTable(selectedTable) && (
//                       <div className="export-hint">Export disabled for related tables — select the master table to export all related tables together.</div>
//                     )}
//                   </div>
//                 </>
//               )}
 
//             </div>
 
//           </>
//         )}
//       </div>
//     </div>
//   );
// }

// // ================= SUMMARY REPORT COMPONENT =================
// import React from "react";
 
// interface SummaryReportProps {
//   summary: any;
//   rows: Row[];
// }
 
// // Pie Chart Component
// const PieChart: React.FC<{ data: Record<string, number>; title: string }> = ({ data, title }) => {
//   const entries = Object.entries(data)
//     .sort((a, b) => b[1] - a[1])
//     .slice(0, 8);
 
//   const total = entries.reduce((sum, [_, val]) => sum + val, 0);
 
//   const colors = [
//     "#FF6B6B",
//     "#4ECDC4",
//     "#45B7D1",
//     "#FFA07A",
//     "#98D8C8",
//     "#F7DC6F",
//     "#BB8FCE",
//     "#85C1E2",
//   ];
 
//   let currentAngle = 0;
//   const slices = entries.map(([label, value], i) => {
//     const percentage = (value / total) * 100;
//     const sliceAngle = (percentage / 100) * 360;
//     const startAngle = currentAngle;
//     const endAngle = currentAngle + sliceAngle;
 
//     // Convert angles to radians
//     const startRad = (startAngle - 90) * (Math.PI / 180);
//     const endRad = (endAngle - 90) * (Math.PI / 180);
 
//     // Calculate path points
//     const x1 = 100 + 80 * Math.cos(startRad);
//     const y1 = 100 + 80 * Math.sin(startRad);
//     const x2 = 100 + 80 * Math.cos(endRad);
//     const y2 = 100 + 80 * Math.sin(endRad);
 
//     const largeArc = sliceAngle > 180 ? 1 : 0;
 
//     const pathData = [
//       `M 100 100`,
//       `L ${x1} ${y1}`,
//       `A 80 80 0 ${largeArc} 1 ${x2} ${y2}`,
//       `Z`,
//     ].join(" ");
 
//     // Label position
//     const labelAngle = (startAngle + endAngle) / 2;
//     const labelRad = (labelAngle - 90) * (Math.PI / 180);
//     const labelX = 100 + 50 * Math.cos(labelRad);
//     const labelY = 100 + 50 * Math.sin(labelRad);
 
//     currentAngle = endAngle;
 
//     return {
//       pathData,
//       color: colors[i % colors.length],
//       label,
//       percentage,
//       value,
//       labelX,
//       labelY,
//     };
//   });
 
//   return (
//     <div className="pie-chart-container">
//       <div className="pie-chart-content">
//         <div className="pie-chart-left">
//           {title && <h4>{title}</h4>}
//           <svg viewBox="0 0 200 200" className="pie-svg">
//             {slices.map((slice, i) => (
//               <g key={i}>
//                 <path d={slice.pathData} fill={slice.color} stroke="white" strokeWidth="2" />
//                 {slice.percentage > 8 && (
//                   <text
//                     x={slice.labelX}
//                     y={slice.labelY}
//                     textAnchor="middle"
//                     dominantBaseline="middle"
//                     className="pie-label"
//                   >
//                     {slice.percentage.toFixed(0)}%
//                   </text>
//                 )}
//               </g>
//             ))}
//           </svg>
//         </div>
//         <div className="pie-legend">
//           {slices.map((slice, i) => (
//             <div key={i} className="legend-item">
//               <span className="legend-color" style={{ backgroundColor: slice.color }}></span>
//               <span className="legend-text">
//                 {slice.label.substring(0, 20)}: {slice.percentage.toFixed(1)}%
//               </span>
//             </div>
//           ))}
//         </div>
//       </div>
//     </div>
//   );
// };
 
// export const SummaryReport: React.FC<SummaryReportProps> = ({
//   summary,
//   rows,
// }) => {
//   if (!summary && rows.length === 0) return null;
 
//   // Combine ALL categorical data into one pie chart
//   const allCategoricalCounts: Record<string, number> = {};
//   let topCityValue = "";
//   let topCityCount = 0;
//   const cityCount: Record<string, number> = {};
 
//   rows.forEach((row) => {
//     Object.entries(row).forEach(([key, value]) => {
//       if (key.toLowerCase().includes('id')) return;
 
//       const num = Number(value);
//       if (isNaN(num) || num === null || num === 0) {
//         // Categorical data
//         const strValue = String(value);
//         const label = `${key}: ${strValue}`;
//         allCategoricalCounts[label] = (allCategoricalCounts[label] || 0) + 1;
       
//         // Track top city
//         if (key.toLowerCase().includes('city')) {
//           cityCount[strValue] = (cityCount[strValue] || 0) + 1;
//           if (cityCount[strValue] > topCityCount) {
//             topCityCount = cityCount[strValue];
//             topCityValue = strValue;
//           }
//         }
//       }
//     });
//   });
 
//   // Calculate metrics
//   const totalVehicles = rows.length;
//   const totalSales = rows.reduce((sum, row) => {
//     const salesVal = Object.values(row).find(v => {
//       const num = Number(v);
//       return !isNaN(num) && num > 100;
//     });
//     return sum + (Number(salesVal) || 0);
//   }, 0);
//   const salesM = (totalSales / 1000000).toFixed(2);
 
//   // Generate executive summary text
//   const generateExecutiveSummary = () => {
//     const topCity = topCityValue || "leading";
//     const topEntries = Object.entries(allCategoricalCounts)
//       .sort((a, b) => b[1] - a[1])
//       .slice(0, 3);
   
//     const bulletPoints = [];
   
//     bulletPoints.push(`Dataset contains ${totalVehicles} vehicles with total sales value of ${salesM}M`);
//     bulletPoints.push(`${topCity} is the leading city with ${topCityCount} vehicles`);
   
//     if (topEntries.length > 0) {
//       const topItem = topEntries[0];
//       const percentage = ((topItem[1] / totalVehicles) * 100).toFixed(1);
//       bulletPoints.push(`Primary market segment: ${topItem[0].split(': ')[1]} (${percentage}% of dataset)`);
//     }
   
//     if (topEntries.length > 1) {
//       const secondItem = topEntries[1];
//       const percentage = ((secondItem[1] / totalVehicles) * 100).toFixed(1);
//       bulletPoints.push(`Secondary segment: ${secondItem[0].split(': ')[1]} (${percentage}% of dataset)`);
//     }
   
//     bulletPoints.push(`Strong market performance with significant concentration in key geographical regions`);
//     bulletPoints.push(`Diversified product portfolio across multiple categories`);
   
//     return bulletPoints;
//   };
 
//   return (
//     <div className="summary-report">
//       {/* Top Metrics Cards */}
//       {/* <div className="metrics-container">
//         <div className="metric-card">
//           <div className="metric-value">{totalVehicles}</div>
//           <div className="metric-label">Total Vehicles</div>
//         </div>
//         <div className="metric-card">
//           <div className="metric-value">{salesM}</div>
//           <div className="metric-label">Total Sales (M)</div>
//         </div>
//         <div className="metric-card">
//           <div className="metric-value">{(totalSales * 0.01).toFixed(1)}</div>
//           <div className="metric-label">2025 Sales (M)</div>
//         </div>
//         <div className="metric-card">
//           <div className="metric-value">{topCityValue}</div>
//           <div className="metric-label">Top City</div>
//         </div>
//       </div> */}
 
//       {/* Analytics Container - Pie Chart and Summary Side by Side */}
//       <div className="analytics-container">
//         {/* Left: Chart Section */}
//         {Object.keys(allCategoricalCounts).length > 0 && (
//           <div className="chart-section">
//             {/* <h4>Top Cities by Sales Value</h4> */}
//             <PieChart data={allCategoricalCounts} title="" />
//           </div>
//         )}
       
//         {/* Right: AI Summary Section */}
//         <div className="hf-summary-section">
//           <h4>Executive Summary</h4>
//           <ul className="hf-summary-content">
//             {generateExecutiveSummary().map((point, idx) => (
//               <li key={idx}>{point}</li>
//             ))}
//           </ul>
//         </div>
//       </div>
//     </div>
//   );
// };










// // import "./SummaryPage.css";
// // import { useEffect, useState, useMemo } from "react";
// // import { useLocation, useNavigate } from "react-router-dom";
// // import { fetchTables, fetchTableData, fetchVehicleSummary } from "../api/qlikApi";
// // import Csvicon from "../assets/Csvicon.png";
// // import { useWizard } from "../context/WizardContext";
// // import Paper from "@mui/material/Paper";
// // import Table from "@mui/material/Table";
// // import TableBody from "@mui/material/TableBody";
// // import TableCell from "@mui/material/TableCell";
// // import TableContainer from "@mui/material/TableContainer";
// // import TableHead from "@mui/material/TableHead";
// // import TableRow from "@mui/material/TableRow";
// // import TableSortLabel from "@mui/material/TableSortLabel";

// // type TableInfo = string | { name: string; [key: string]: any };
// // type Row = Record<string, any>;

// // export default function SummaryPage() {
// //   const location = useLocation();
// //   const navigate = useNavigate();
  
// //   const [appId, setAppId] = useState<string>("");
// //   const [tables, setTables] = useState<TableInfo[]>([]);
// //   const [filteredTables, setFilteredTables] = useState<TableInfo[]>([]);
// //   const [selectedTable, setSelectedTable] = useState<string>("");
// //   const [rows, setRows] = useState<Row[]>([]);
// //   const [loading, setLoading] = useState(true);
// //   const [tableLoading, setTableLoading] = useState(false);
// //   const [summary, setSummary] = useState<any>(null);
// //   // Data-table controls
// //   const [tableQuery, setTableQuery] = useState<string>("");
// //   const [pageSize, setPageSize] = useState<number>(10);
// //   const [currentPage, setCurrentPage] = useState<number>(1);

// //   // Derived pagination lists with search + sorting
// //   const [orderBy, setOrderBy] = useState<string>("");
// //   const [order, setOrder] = useState<"asc" | "desc">("asc");

// //   const processedRows = useMemo(() => {
// //     let out = rows || [];

// //     // search filter
// //     if (tableQuery.trim()) {
// //       const q = tableQuery.toLowerCase();
// //       out = out.filter((r) =>
// //         Object.values(r).some((v) =>
// //           String(v ?? "").toLowerCase().includes(q)
// //         )
// //       );
// //     }

// //     // sorting
// //     if (orderBy) {
// //       out = out.slice().sort((a: any, b: any) => {
// //         const va = a[orderBy];
// //         const vb = b[orderBy];
// //         if (va === vb) return 0;
// //         if (va == null) return 1;
// //         if (vb == null) return -1;
// //         if (typeof va === "number" && typeof vb === "number") {
// //           return order === "asc" ? va - vb : vb - va;
// //         }
// //         const sa = String(va).toLowerCase();
// //         const sb = String(vb).toLowerCase();
// //         if (sa < sb) return order === "asc" ? -1 : 1;
// //         if (sa > sb) return order === "asc" ? 1 : -1;
// //         return 0;
// //       });
// //     }

// //     return out;
// //   }, [rows, tableQuery, orderBy, order]);

// //   const totalEntries = processedRows.length;
// //   const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
// //   const current = Math.min(currentPage, totalPages);
// //   const startIndex = totalEntries ? (current - 1) * pageSize : 0;
// //   const endIndex = Math.min(startIndex + pageSize, totalEntries);
// //   const visibleRows = processedRows.slice(startIndex, endIndex);

// //   const handleRequestSort = (property: string) => {
// //     if (orderBy === property) {
// //       setOrder((o) => (o === "asc" ? "desc" : "asc"));
// //     } else {
// //       setOrderBy(property);
// //       setOrder("asc");
// //     }
// //   };

// //   const pageNumbers = useMemo<(number | string)[]>(() => {
// //     const nums: (number | string)[] = [];
// //     const max = totalPages;
// //     const cur = current;
// //     if (max <= 7) {
// //       for (let i = 1; i <= max; i++) nums.push(i);
// //     } else {
// //       nums.push(1);
// //       if (cur > 3) nums.push("...");
// //       const start = Math.max(2, cur - 1);
// //       const end = Math.min(max - 1, cur + 1);
// //       for (let i = start; i <= end; i++) nums.push(i);
// //       if (cur < max - 2) nums.push("...");
// //       nums.push(max);
// //     }
// //     return nums;
// //   }, [totalPages, current]);

// //   useEffect(() => {
// //     setCurrentPage(1);
// //   }, [rows, pageSize, tableQuery]);

// //   // 1 → GET APP ID FROM NAVIGATION STATE
// //   useEffect(() => {
// //     const state = location.state as any;
// //     const passedAppId = state?.appId || sessionStorage.getItem("appSelected");

// //     if (!passedAppId) {
// //       alert("No app selected. Please go back and select an app.");
// //       navigate("/apps");
// //       return;
// //     }

// //     setAppId(passedAppId);
// //   }, [location, navigate]);

// //   // 2 → LOAD TABLE LIST
// //   const { stopTimer, startTimer, getLastElapsed } = useWizard();

// //   useEffect(() => {
// //     if (!appId) return;

// //     // ensure we have an active timer for /summary (covers direct navigation)
// //     if (sessionStorage.getItem("lastTimerTarget") !== "/summary") {
// //       startTimer?.("/summary");
// //     }
      
// //     fetchTables(appId)
// //       .then((data) => {
// //         // If table objects have `created` or `createdAt`, sort by newest first
// //         const sorted = (data || []).slice().sort((x: any, y: any) => {
// //           const xa = typeof x === "string" ? null : x.created || x.createdAt || null;
// //           const ya = typeof y === "string" ? null : y.created || y.createdAt || null;

// //           if (xa && ya) return +new Date(ya) - +new Date(xa);
// //           return 0;
// //         });

// //         setTables(sorted);
// //         setFilteredTables(sorted);
// //         console.log("All tables fetched:", sorted); // ✅ debug
        
// //         // AUTO-LOAD FIRST TABLE
// //         if (sorted && sorted.length > 0) {
// //           const firstTableName = typeof sorted[0] === "string" ? sorted[0] : sorted[0]?.name;
// //           if (firstTableName) {
// //             loadData(firstTableName);
// //           }
// //         }
// //       })
// //       .catch(() => {})
// //       .finally(() => {
// //         setLoading(false);
// //         // Stop timer started by Apps when navigating to Summary
// //         // stopTimer?.("/summary");
// //       });
// //   }, [appId, stopTimer, startTimer]);



// //   // 3 → LOAD DATA FOR SELECTED TABLE
// //   const loadData = async (tableName: string) => {
// //     if (!tableName || tableName === selectedTable) return;

// //     setSelectedTable(tableName);
// //     setTableLoading(true);
// //     setRows([]);
// //     setSummary(null);

// //     try {
// //       const data = await fetchTableData(appId, tableName);
// //       setRows(data || []);

// //       // Persist selection for Export fallback
// //       try {
// //         sessionStorage.setItem("selectedTable", tableName);
// //         sessionStorage.setItem("selectedRows", JSON.stringify(data || []));
// //       } catch (e) {
// //         // ignore storage errors
// //       }

// //       // 2️⃣ SUMMARY DATA
// //       const sum = await fetchVehicleSummary(appId, tableName);
// //       setSummary(sum);
// //     } catch (e) {
// //       console.error(e);
// //     } finally {
// //       setTableLoading(false);
// //     }
// //   };

// //   // CSV DOWNLOAD
// //   const downloadCSV = () => {
// //     if (!rows.length) {
// //       alert("No data");
// //       return;
// //     }

// //     const headers = Object.keys(rows[0]);
// //     const csv = [
// //       headers.join(","),
// //       ...rows.map((r) => headers.map((h) => `"${r[h] ?? ""}"`).join(",")),
// //     ].join("\n");

// //     const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
// //     const url = window.URL.createObjectURL(blob);

// //     const a = document.createElement("a");
// //     a.href = url;
// //     a.download = `${selectedTable || "data"}.csv`;
// //     a.click();
// //     window.URL.revokeObjectURL(url);
// //   };

// //   if (loading) {
// //     return <div className="wrap">Loading…</div>;
// //   }

// //   return (
// //     <div className="summary-layout">
// //       {/* LEFT – TABLE NAMES */}
// //       <div className="left-panel">
// //         <div className="panel-header">
// //           <h3 className="title">Tables {`(${tables.length})`}</h3>
// //         </div>



// //         {tables.length === 0 && (
// //           <p className="no-tables">No tables found</p>
// //         )}

// //         {filteredTables.map((t, i) => {
// //           const tableName = typeof t === "string" ? t : t?.name;
// //           if (!tableName) return null;

// //           return (
// //             <div
// //               key={i}
// //               className={
// //                 tableName === selectedTable
// //                   ? "table-item active"
// //                   : "table-item"
// //               }
// //               onClick={() => loadData(tableName)}
// //             >
// //               {tableName}
// //             </div>
// //           );
// //         })}
// //       </div>

// //       {/* RIGHT – SUMMARY + DATA */}
// //       <div className="right-panel">
// //         {!selectedTable && (
// //           <div className="empty">
// //             <p>👈 Select a table on the left to view its data</p>
// //           </div>
// //         )}

// //         {selectedTable && (
// //           <>

// //             {/* HEADER ONLY TITLE */}
// //             <div className="header">
// //               <h2>{selectedTable}</h2>
// //               {/* Page-specific analysis time */}
// //               {getLastElapsed?.("/summary") && (
// //                 <div className="analysis-badge">AnalysisTime - {getLastElapsed!("/summary")}</div>
// //               )}
// //             </div>

// //             <SummaryReport summary={summary} rows={rows} />

// //             {/* ===== SEPARATE DIV FOR TABLE ===== */}
// //             <div className="data-section">
              

// //               {tableLoading && <p>Loading data…</p>}

// //               {!tableLoading && rows.length > 0 && (
// //                 <>
// //                   {/* Top controls: page length + search */}
// //                   <div className="data-controls">
// //                     <div className="length">
// //                       <label>
// //                         <select
// //                           value={pageSize}
// //                           onChange={(e) => setPageSize(parseInt(e.target.value, 10))}
// //                         >
// //                           <option value={10}>10</option>
// //                           <option value={25}>25</option>
// //                           <option value={50}>50</option>
// //                           <option value={100}>100</option>
// //                         </select>
// //                         records per page
// //                       </label>
// //                     </div>
// //                     <div className="searchfilter">
// //                       <label className="lable-search">
// //                         Search:
// //                         <input
// //                           type="search"
// //                           value={tableQuery}
// //                           onChange={(e) => setTableQuery(e.target.value)}
// //                           placeholder="Search..."
// //                         />
// //                       </label>
// //                       <button
// //                       className="csv-btn"
// //                       disabled={!rows.length}
// //                       onClick={downloadCSV}
// //                     >
// //                       <img src={Csvicon} alt="csv " className="btn-icon" /> 
// //                     </button>
// //                     </div>
// //                   </div>

// //                   <div className="table-wrapper">
// //                     <TableContainer component={Paper}>
// //                       <Table size="small">
// //                         <TableHead>
// //                           <TableRow>
// //                             {rows[0] && Object.keys(rows[0]).map((k) => (
// //                               <TableCell key={k} sortDirection={orderBy === k ? order : false}>
// //                                 <TableSortLabel
// //                                   active={orderBy === k}
// //                                   direction={orderBy === k ? order : 'asc'}
// //                                   onClick={() => handleRequestSort(k)}
// //                                 >
// //                                   {k}
// //                                 </TableSortLabel>
// //                               </TableCell>
// //                             ))}
// //                           </TableRow>
// //                         </TableHead>

// //                         <TableBody>
// //                           {visibleRows.map((r, i) => (
// //                             <TableRow key={i} hover>
// //                               {Object.keys(rows[0]).map((k, j) => (
// //                                 <TableCell key={j}>{String(r[k] ?? "")}</TableCell>
// //                               ))}
// //                             </TableRow>
// //                           ))}
// //                         </TableBody>
// //                       </Table>
// //                     </TableContainer>

// //                     <div className="table-footer">
// //                       {`Showing ${totalEntries ? startIndex + 1 : 0} to ${endIndex} of ${totalEntries} entries`}
// //                     </div>
// //                   </div>

// //                   {/* Pagination */}
// //                   <div className="pagination-bar">
// //                     <button
// //                       className="page-btn"
// //                       disabled={current === 1}
// //                       onClick={() => setCurrentPage(current - 1)}
// //                     >
// //                       Previous
// //                     </button>
// //                     {pageNumbers.map((p, idx) =>
// //                       typeof p === "number" ? (
// //                         <button
// //                           key={idx}
// //                           className={`page-btn ${p === current ? "active" : ""}`}
// //                           onClick={() => setCurrentPage(p)}
// //                         >
// //                           {p}
// //                         </button>
// //                       ) : (
// //                         <span key={idx} className="ellipsis">…</span>
// //                       )
// //                     )}
// //                     <button
// //                       className="page-btn"
// //                       disabled={current === totalPages}
// //                       onClick={() => setCurrentPage(current + 1)}
// //                     >
// //                       Next
// //                     </button>
// //                   </div>

// //                   {/* BOTTOM RIGHT BUTTON */}
// //                   <div className="bottom-actions">
// //                     <button
// //                       className="export-btn"
// //                       onClick={() => {
// //                         stopTimer?.("/summary");
// //                         // Mark summary completed to enable export step
// //                         sessionStorage.setItem("summaryComplete", "true");

// //                         // Start timer for export page load
// //                         startTimer?.("/export");

// //                         navigate("/export", {
// //                           state: {
// //                             appId,
// //                             appName: location.state?.appName || sessionStorage.getItem("appName") || appId,
// //                             selectedTable,
// //                             rows,
// //                           },
// //                         });
// //                       }}
// //                       title="Navigate to Export tab"
// //                     >
// //                       📤Continue to Export
// //                     </button>
// //                   </div>
// //                 </>
// //               )}

// //             </div>

// //           </>
// //         )}
// //       </div>
// //     </div>
// //   );
// // }

// // // ================= SUMMARY REPORT COMPONENT =================
// // import React from "react";

// // interface SummaryReportProps {
// //   summary: any;
// //   rows: Row[];
// // }

// // // Pie Chart Component
// // const PieChart: React.FC<{ data: Record<string, number>; title: string }> = ({ data, title }) => {
// //   const entries = Object.entries(data)
// //     .sort((a, b) => b[1] - a[1])
// //     .slice(0, 8);

// //   const total = entries.reduce((sum, [_, val]) => sum + val, 0);

// //   const colors = [
// //     "#FF6B6B",
// //     "#4ECDC4",
// //     "#45B7D1",
// //     "#FFA07A",
// //     "#98D8C8",
// //     "#F7DC6F",
// //     "#BB8FCE",
// //     "#85C1E2",
// //   ];

// //   let currentAngle = 0;
// //   const slices = entries.map(([label, value], i) => {
// //     const percentage = (value / total) * 100;
// //     const sliceAngle = (percentage / 100) * 360;
// //     const startAngle = currentAngle;
// //     const endAngle = currentAngle + sliceAngle;

// //     // Convert angles to radians
// //     const startRad = (startAngle - 90) * (Math.PI / 180);
// //     const endRad = (endAngle - 90) * (Math.PI / 180);

// //     // Calculate path points
// //     const x1 = 100 + 80 * Math.cos(startRad);
// //     const y1 = 100 + 80 * Math.sin(startRad);
// //     const x2 = 100 + 80 * Math.cos(endRad);
// //     const y2 = 100 + 80 * Math.sin(endRad);

// //     const largeArc = sliceAngle > 180 ? 1 : 0;

// //     const pathData = [
// //       `M 100 100`,
// //       `L ${x1} ${y1}`,
// //       `A 80 80 0 ${largeArc} 1 ${x2} ${y2}`,
// //       `Z`,
// //     ].join(" ");

// //     // Label position
// //     const labelAngle = (startAngle + endAngle) / 2;
// //     const labelRad = (labelAngle - 90) * (Math.PI / 180);
// //     const labelX = 100 + 50 * Math.cos(labelRad);
// //     const labelY = 100 + 50 * Math.sin(labelRad);

// //     currentAngle = endAngle;

// //     return {
// //       pathData,
// //       color: colors[i % colors.length],
// //       label,
// //       percentage,
// //       value,
// //       labelX,
// //       labelY,
// //     };
// //   });

// //   return (
// //     <div className="pie-chart-container">
// //       <div className="pie-chart-content">
// //         <div className="pie-chart-left">
// //           {title && <h4>{title}</h4>}
// //           <svg viewBox="0 0 200 200" className="pie-svg">
// //             {slices.map((slice, i) => (
// //               <g key={i}>
// //                 <path d={slice.pathData} fill={slice.color} stroke="white" strokeWidth="2" />
// //                 {slice.percentage > 8 && (
// //                   <text
// //                     x={slice.labelX}
// //                     y={slice.labelY}
// //                     textAnchor="middle"
// //                     dominantBaseline="middle"
// //                     className="pie-label"
// //                   >
// //                     {slice.percentage.toFixed(0)}%
// //                   </text>
// //                 )}
// //               </g>
// //             ))}
// //           </svg>
// //         </div>
// //         <div className="pie-legend">
// //           {slices.map((slice, i) => (
// //             <div key={i} className="legend-item">
// //               <span className="legend-color" style={{ backgroundColor: slice.color }}></span>
// //               <span className="legend-text">
// //                 {slice.label.substring(0, 20)}: {slice.percentage.toFixed(1)}%
// //               </span>
// //             </div>
// //           ))}
// //         </div>
// //       </div>
// //     </div>
// //   );
// // };

// // export const SummaryReport: React.FC<SummaryReportProps> = ({
// //   summary,
// //   rows,
// // }) => {
// //   if (!summary && rows.length === 0) return null;

// //   // Combine ALL categorical data into one pie chart
// //   const allCategoricalCounts: Record<string, number> = {};
// //   let topCityValue = "";
// //   let topCityCount = 0;
// //   const cityCount: Record<string, number> = {};

// //   rows.forEach((row) => {
// //     Object.entries(row).forEach(([key, value]) => {
// //       if (key.toLowerCase().includes('id')) return;

// //       const num = Number(value);
// //       if (isNaN(num) || num === null || num === 0) {
// //         // Categorical data
// //         const strValue = String(value);
// //         const label = `${key}: ${strValue}`;
// //         allCategoricalCounts[label] = (allCategoricalCounts[label] || 0) + 1;
        
// //         // Track top city
// //         if (key.toLowerCase().includes('city')) {
// //           cityCount[strValue] = (cityCount[strValue] || 0) + 1;
// //           if (cityCount[strValue] > topCityCount) {
// //             topCityCount = cityCount[strValue];
// //             topCityValue = strValue;
// //           }
// //         }
// //       }
// //     });
// //   });

// //   // Calculate metrics
// //   const totalVehicles = rows.length;
// //   const totalSales = rows.reduce((sum, row) => {
// //     const salesVal = Object.values(row).find(v => {
// //       const num = Number(v);
// //       return !isNaN(num) && num > 100;
// //     });
// //     return sum + (Number(salesVal) || 0);
// //   }, 0);
// //   const salesM = (totalSales / 1000000).toFixed(2);

// //   // Generate executive summary text
// //   const generateExecutiveSummary = () => {
// //     const topCity = topCityValue || "leading";
// //     const topEntries = Object.entries(allCategoricalCounts)
// //       .sort((a, b) => b[1] - a[1])
// //       .slice(0, 3);
    
// //     const bulletPoints = [];
    
// //     bulletPoints.push(`Dataset contains ${totalVehicles} vehicles with total sales value of ${salesM}M`);
// //     bulletPoints.push(`${topCity} is the leading city with ${topCityCount} vehicles`);
    
// //     if (topEntries.length > 0) {
// //       const topItem = topEntries[0];
// //       const percentage = ((topItem[1] / totalVehicles) * 100).toFixed(1);
// //       bulletPoints.push(`Primary market segment: ${topItem[0].split(': ')[1]} (${percentage}% of dataset)`);
// //     }
    
// //     if (topEntries.length > 1) {
// //       const secondItem = topEntries[1];
// //       const percentage = ((secondItem[1] / totalVehicles) * 100).toFixed(1);
// //       bulletPoints.push(`Secondary segment: ${secondItem[0].split(': ')[1]} (${percentage}% of dataset)`);
// //     }
    
// //     bulletPoints.push(`Strong market performance with significant concentration in key geographical regions`);
// //     bulletPoints.push(`Diversified product portfolio across multiple categories`);
    
// //     return bulletPoints;
// //   };

// //   return (
// //     <div className="summary-report">
// //       {/* Top Metrics Cards */}
// //       {/* <div className="metrics-container">
// //         <div className="metric-card">
// //           <div className="metric-value">{totalVehicles}</div>
// //           <div className="metric-label">Total Vehicles</div>
// //         </div>
// //         <div className="metric-card">
// //           <div className="metric-value">{salesM}</div>
// //           <div className="metric-label">Total Sales (M)</div>
// //         </div>
// //         <div className="metric-card">
// //           <div className="metric-value">{(totalSales * 0.01).toFixed(1)}</div>
// //           <div className="metric-label">2025 Sales (M)</div>
// //         </div>
// //         <div className="metric-card">
// //           <div className="metric-value">{topCityValue}</div>
// //           <div className="metric-label">Top City</div>
// //         </div>
// //       </div> */}

// //       {/* Analytics Container - Pie Chart and Summary Side by Side */}
// //       <div className="analytics-container">
// //         {/* Left: Chart Section */}
// //         {Object.keys(allCategoricalCounts).length > 0 && (
// //           <div className="chart-section">
// //             <h4>Top Cities by Sales Value</h4>
// //             <PieChart data={allCategoricalCounts} title="" />
// //           </div>
// //         )}
        
// //         {/* Right: AI Summary Section */}
// //         <div className="hf-summary-section">
// //           <h4>Executive Summary</h4>
// //           <ul className="hf-summary-content">
// //             {generateExecutiveSummary().map((point, idx) => (
// //               <li key={idx}>{point}</li>
// //             ))}
// //           </ul>
// //         </div>
// //       </div>
// //     </div>
// //   );
// // };




// import "./SummaryPage.css";
// import { useEffect, useState, useMemo, useRef } from "react";
// import { useLocation, useNavigate } from "react-router-dom";
// import { fetchTables, fetchTableData, fetchVehicleSummary } from "../api/qlikApi";
// import Csvicon from "../assets/Csvicon.png";
// import { useWizard } from "../context/WizardContext";
// import Paper from "@mui/material/Paper";
// import Table from "@mui/material/Table";
// import TableBody from "@mui/material/TableBody";
// import TableCell from "@mui/material/TableCell";
// import TableContainer from "@mui/material/TableContainer";
// import TableHead from "@mui/material/TableHead";
// import TableRow from "@mui/material/TableRow";
// import TableSortLabel from "@mui/material/TableSortLabel";
// import exportImg from "../assets/export2.png";

// type TableInfo = string | { name: string; [key: string]: any };
// type Row = Record<string, any>;

// export default function SummaryPage() {
//   const location = useLocation();
//   const navigate = useNavigate();
//   const pageStartTimeRef = useRef<number | null>(null);
  
//   const [appId, setAppId] = useState<string>("");
//   const [tables, setTables] = useState<TableInfo[]>([]);
//   const [filteredTables, setFilteredTables] = useState<TableInfo[]>([]);
//   const [selectedTable, setSelectedTable] = useState<string>("");
//   const [rows, setRows] = useState<Row[]>([]);
//   const [loading, setLoading] = useState(true);
//   const [tableLoading, setTableLoading] = useState(false);
//   const [summary, setSummary] = useState<any>(null);
//   const [pageLoadTime, setPageLoadTime] = useState<string | null>(null);
  
//   // Track page load start time
//   useEffect(() => {
//     pageStartTimeRef.current = Date.now();
//   }, []);
//   // Data-table controls
//   const [tableQuery, setTableQuery] = useState<string>("");
//   const [pageSize, setPageSize] = useState<number>(10);
//   const [currentPage, setCurrentPage] = useState<number>(1);
//   // Search for table list on the left panel
//   const [tableListQuery, setTableListQuery] = useState<string>("");

//   // Derived pagination lists with search + sorting
//   const [orderBy, setOrderBy] = useState<string>("");
//   const [order, setOrder] = useState<"asc" | "desc">("asc");

//   const processedRows = useMemo(() => {
//     let out = rows || [];

//     // search filter
//     if (tableQuery.trim()) {
//       const q = tableQuery.toLowerCase();
//       out = out.filter((r) =>
//         Object.values(r).some((v) =>
//           String(v ?? "").toLowerCase().includes(q)
//         )
//       );
//     }

//     // sorting
//     if (orderBy) {
//       out = out.slice().sort((a: any, b: any) => {
//         const va = a[orderBy];
//         const vb = b[orderBy];
//         if (va === vb) return 0;
//         if (va == null) return 1;
//         if (vb == null) return -1;
//         if (typeof va === "number" && typeof vb === "number") {
//           return order === "asc" ? va - vb : vb - va;
//         }
//         const sa = String(va).toLowerCase();
//         const sb = String(vb).toLowerCase();
//         if (sa < sb) return order === "asc" ? -1 : 1;
//         if (sa > sb) return order === "asc" ? 1 : -1;
//         return 0;
//       });
//     }

//     return out;
//   }, [rows, tableQuery, orderBy, order]);

//   const totalEntries = processedRows.length;
//   const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
//   const current = Math.min(currentPage, totalPages);
//   const startIndex = totalEntries ? (current - 1) * pageSize : 0;
//   const endIndex = Math.min(startIndex + pageSize, totalEntries);
//   const visibleRows = processedRows.slice(startIndex, endIndex);

//   const handleRequestSort = (property: string) => {
//     if (orderBy === property) {
//       setOrder((o) => (o === "asc" ? "desc" : "asc"));
//     } else {
//       setOrderBy(property);
//       setOrder("asc");
//     }
//   };

//   const pageNumbers = useMemo<(number | string)[]>(() => {
//     const nums: (number | string)[] = [];
//     const max = totalPages;
//     const cur = current;
//     if (max <= 7) {
//       for (let i = 1; i <= max; i++) nums.push(i);
//     } else {
//       nums.push(1);
//       if (cur > 3) nums.push("...");
//       const start = Math.max(2, cur - 1);
//       const end = Math.min(max - 1, cur + 1);
//       for (let i = start; i <= end; i++) nums.push(i);
//       if (cur < max - 2) nums.push("...");
//       nums.push(max);
//     }
//     return nums;
//   }, [totalPages, current]);

//   useEffect(() => {
//     setCurrentPage(1);
//   }, [rows, pageSize, tableQuery]);

//   // Filter the left-side table list when the user types in the table search box
//   useEffect(() => {
//     if (!tableListQuery) {
//       setFilteredTables(tables);
//       return;
//     }

//     const q = tableListQuery.toLowerCase();
//     const filtered = (tables || []).filter((t) => {
//       const name = typeof t === "string" ? t : t?.name || "";
//       return String(name).toLowerCase().includes(q);
//     });
//     setFilteredTables(filtered);
//   }, [tableListQuery, tables]);

//   // 1 → GET APP ID FROM NAVIGATION STATE
//   useEffect(() => {
//     const state = location.state as any;
//     const passedAppId = state?.appId || sessionStorage.getItem("appSelected");

//     if (!passedAppId) {
//       alert("No app selected. Please go back and select an app.");
//       navigate("/apps");
//       return;
//     }

//     setAppId(passedAppId);
//   }, [location, navigate]);

//   // 2 → LOAD TABLE LIST
//   const { stopTimer, startTimer, getLastElapsed } = useWizard();

//   useEffect(() => {
//     if (!appId) return;

//     // ensure we have an active timer for /summary (covers direct navigation)
//     if (sessionStorage.getItem("lastTimerTarget") !== "/summary") {
//       startTimer?.("/summary");
//     }
      
//       fetchTables(appId)
//       .then((data) => {
//         // Sort table list alphabetically by name (strings or objects)
//         const sorted = (data || []).slice().sort((x: any, y: any) => {
//           const nx = typeof x === "string" ? x : x?.name || "";
//           const ny = typeof y === "string" ? y : y?.name || "";
//           return String(nx).localeCompare(String(ny), undefined, { sensitivity: 'base' });
//         });

//         setTables(sorted);
//         setFilteredTables(sorted);
//         console.log("All tables fetched:", sorted);

//         // AUTO-LOAD FIRST TABLE
//         if (sorted && sorted.length > 0) {
//           const firstTableName = typeof sorted[0] === "string" ? sorted[0] : sorted[0]?.name;
//           if (firstTableName) {
//             loadData(firstTableName);
//           }
//         }
//       })
//       .catch(() => {})
//       .finally(() => {
//         setLoading(false);
//         // Don't stop timer yet - wait for table data to load
//       });
//   }, [appId, stopTimer, startTimer]);



//   // 3 → LOAD DATA FOR SELECTED TABLE
//   const formatElapsed = (msTotal: number) => {
//     const minutes = Math.floor(msTotal / 60000);
//     const seconds = Math.floor((msTotal % 60000) / 1000);
//     const centis = Math.floor((msTotal % 1000) / 10);
//     const pad = (n: number, width = 2) => String(n).padStart(width, "0");
//     return `${pad(minutes)}m : ${pad(seconds)}s : ${pad(centis)}ms`;
//   };

//   const loadData = async (tableName: string) => {
//     if (!tableName || tableName === selectedTable) return;

//     setSelectedTable(tableName);
//     setTableLoading(true);
//     setRows([]);
//     setSummary(null);

//     // start timing this table's data load
//     startTimer?.(`/summary/data/${tableName}`);

//     try {
//       const data = await fetchTableData(appId, tableName);
//       setRows(data || []);

//       // Persist selection for Export fallback
//       try {
//         sessionStorage.setItem("selectedTable", tableName);
//         sessionStorage.setItem("selectedRows", JSON.stringify(data || []));
//       } catch (e) {
//         // ignore storage errors
//       }

//       // 2️⃣ SUMMARY DATA
//       const sum = await fetchVehicleSummary(appId, tableName);
//       setSummary(sum);
//     } catch (e) {
//       console.error(e);
//     } finally {
//       setTableLoading(false);

//       // Prefer the specific table/data load elapsed if available
//       const tableElapsed = stopTimer?.(`/summary/data/${tableName}`);
//       if (tableElapsed) {
//         console.debug(`Table ${tableName} load time:`, tableElapsed);
//         setPageLoadTime(tableElapsed);
//       } else {
//         // Fallback: show navigation/load time for the Summary page if available
//         const navElapsed = getLastElapsed?.("/summary");
//         if (navElapsed) {
//           setPageLoadTime(navElapsed);
//         } else if (pageStartTimeRef.current) {
//           // As a last resort, show local elapsed since page mount
//           const totalTime = Date.now() - pageStartTimeRef.current;
//           setPageLoadTime(formatElapsed(totalTime));
//         }
//       }
//     }
//   };

//   // CSV DOWNLOAD
//   const downloadCSV = () => {
//     if (!rows.length) {
//       alert("No data");
//       return;
//     }

//     const headers = Object.keys(rows[0]);
//     const csv = [
//       headers.join(","),
//       ...rows.map((r) => headers.map((h) => `"${r[h] ?? ""}"`).join(",")),
//     ].join("\n");

//     const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
//     const url = window.URL.createObjectURL(blob);

//     const a = document.createElement("a");
//     a.href = url;
//     a.download = `${selectedTable || "data"}.csv`;
//     a.click();
//     window.URL.revokeObjectURL(url);
//   };

//   if (loading) {
//     return <div className="wrap">Loading…</div>;
//   }

//   return (
//     <div className="summary-layout">
//       {/* LEFT – TABLE NAMES */}
//       <div className="left-panel">
//         <div className="panel-header">
//           <h3 className="title">Tables {`(${tables.length})`}</h3>
//         </div>

//         {/* Table list search (searches the list of table names) */}
//         <div className="table-search">
//           <input
//             type="search"
//             placeholder="Search tables..."
//             value={tableListQuery}
//             onChange={(e) => setTableListQuery(e.target.value)}
//             className="table-search-input"
//           />
//         </div>



//         {tables.length === 0 && (
//           <p className="no-tables">No tables found</p>
//         )}

//         {filteredTables.map((t, i) => {
//           const tableName = typeof t === "string" ? t : t?.name;
//           if (!tableName) return null;

//           return (
//             <div
//               key={i}
//               className={
//                 tableName === selectedTable
//                   ? "table-item active"
//                   : "table-item"
//               }
//               onClick={() => loadData(tableName)}
//             >
//               {tableName}
//             </div>
//           );
//         })}
//       </div>

//       {/* RIGHT – SUMMARY + DATA */}
//       <div className="right-panel">
//         {!selectedTable && (
//           <div className="empty">
//             <p>👈 Select a table on the left to view its data</p>
//           </div>
//         )}

//         {selectedTable && (
//           <>

//               {/* HEADER ONLY TITLE */}
//             <div className="header">
//               <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",width: "100%" }}>
//                 <h2>{selectedTable}</h2>
//                 {pageLoadTime && (
//                   <div className="timer-badge">Analysis Time: {pageLoadTime}</div>
//                 )}
//               </div>
//             </div>

//             <SummaryReport summary={summary} rows={rows} />

//             {/* ===== SEPARATE DIV FOR TABLE ===== */}
//             <div className="data-section">
              

//               {tableLoading && <p>Loading data…</p>}

//               {!tableLoading && rows.length > 0 && (
//                 <>
//                   {/* Top controls: page length + search */}
//                   <div className="data-controls">
//                     <div className="length">
//                       <label>
//                         <select
//                           value={pageSize}
//                           onChange={(e) => setPageSize(parseInt(e.target.value, 10))}
//                         >
//                           <option value={10}>10</option>
//                           <option value={25}>25</option>
//                           <option value={50}>50</option>
//                           <option value={100}>100</option>
//                         </select>
//                         records per page
//                       </label>
//                     </div>
//                     <div className="searchfilter">
//                       <label className="lable-search">
//                         Search:
//                         <input
//                           type="search"
//                           value={tableQuery}
//                           onChange={(e) => setTableQuery(e.target.value)}
//                           placeholder="Search..."
//                         />
//                       </label>
//                       <button
//                       className="csv-btn"
//                       disabled={!rows.length}
//                       onClick={downloadCSV}
//                     >
//                       <img src={Csvicon} alt="csv " className="btn-icon" /> 
//                     </button>
//                     </div>
//                   </div>

//                   <div className="table-wrapper">
//                     <TableContainer component={Paper}>
//                       <Table size="small">
//                         <TableHead>
//                           <TableRow>
//                             {rows[0] && Object.keys(rows[0]).map((k) => (
//                               <TableCell key={k} sortDirection={orderBy === k ? order : false}>
//                                 <TableSortLabel
//                                   active={orderBy === k}
//                                   direction={orderBy === k ? order : 'asc'}
//                                   onClick={() => handleRequestSort(k)}
//                                 >
//                                   {k}
//                                 </TableSortLabel>
//                               </TableCell>
//                             ))}
//                           </TableRow>
//                         </TableHead>

//                         <TableBody>
//                           {visibleRows.map((r, i) => (
//                             <TableRow key={i} hover>
//                               {Object.keys(rows[0]).map((k, j) => (
//                                 <TableCell key={j}>{String(r[k] ?? "")}</TableCell>
//                               ))}
//                             </TableRow>
//                           ))}
//                         </TableBody>
//                       </Table>
//                     </TableContainer>

//                     <div className="table-footer">
//                       {`Showing ${totalEntries ? startIndex + 1 : 0} to ${endIndex} of ${totalEntries} entries`}
//                     </div>
//                   </div>

//                   {/* Pagination */}
//                   <div className="pagination-bar">
//                     <button
//                       className="page-btn"
//                       disabled={current === 1}
//                       onClick={() => setCurrentPage(current - 1)}
//                     >
//                       Previous
//                     </button>
//                     {pageNumbers.map((p, idx) =>
//                       typeof p === "number" ? (
//                         <button
//                           key={idx}
//                           className={`page-btn ${p === current ? "active" : ""}`}
//                           onClick={() => setCurrentPage(p)}
//                         >
//                           {p}
//                         </button>
//                       ) : (
//                         <span key={idx} className="ellipsis">…</span>
//                       )
//                     )}
//                     <button
//                       className="page-btn"
//                       disabled={current === totalPages}
//                       onClick={() => setCurrentPage(current + 1)}
//                     >
//                       Next
//                     </button>
//                   </div>

//                   {/* BOTTOM RIGHT BUTTON */}
//                   <div className="bottom-actions">
//                     <button
//                       className="export-btn"
//                       onClick={() => {
//                         stopTimer?.("/summary");
//                         // Mark summary completed to enable export step
//                         sessionStorage.setItem("summaryComplete", "true");

//                         // Start timer for export page load
//                         startTimer?.("/export");

//                         navigate("/export", {
//                           state: {
//                             appId,
//                             appName: location.state?.appName || sessionStorage.getItem("appName") || appId,
//                             selectedTable,
//                             rows,
//                           },
//                         });
//                       }}
//                       title="Navigate to Export tab"
//                     >
//                       <img src={exportImg} alt="Export" />Continue to Export
//                     </button>
//                   </div>
//                 </>
//               )}

//             </div>

//           </>
//         )}
//       </div>
//     </div>
//   );
// }

// // ================= SUMMARY REPORT COMPONENT =================
// import React from "react";

// interface SummaryReportProps {
//   summary: any;
//   rows: Row[];
// }

// // Pie Chart Component
// const PieChart: React.FC<{ data: Record<string, number>; title: string }> = ({ data, title }) => {
//   const entries = Object.entries(data)
//     .sort((a, b) => b[1] - a[1])
//     .slice(0, 8);

//   const total = entries.reduce((sum, [_, val]) => sum + val, 0);

//   const colors = [
//     "#FF6B6B",
//     "#4ECDC4",
//     "#45B7D1",
//     "#FFA07A",
//     "#98D8C8",
//     "#F7DC6F",
//     "#BB8FCE",
//     "#85C1E2",
//   ];

//   let currentAngle = 0;
//   const slices = entries.map(([label, value], i) => {
//     const percentage = (value / total) * 100;
//     const sliceAngle = (percentage / 100) * 360;
//     const startAngle = currentAngle;
//     const endAngle = currentAngle + sliceAngle;

//     // Convert angles to radians
//     const startRad = (startAngle - 90) * (Math.PI / 180);
//     const endRad = (endAngle - 90) * (Math.PI / 180);

//     // Calculate path points
//     const x1 = 100 + 80 * Math.cos(startRad);
//     const y1 = 100 + 80 * Math.sin(startRad);
//     const x2 = 100 + 80 * Math.cos(endRad);
//     const y2 = 100 + 80 * Math.sin(endRad);

//     const largeArc = sliceAngle > 180 ? 1 : 0;

//     const pathData = [
//       `M 100 100`,
//       `L ${x1} ${y1}`,
//       `A 80 80 0 ${largeArc} 1 ${x2} ${y2}`,
//       `Z`,
//     ].join(" ");

//     // Label position
//     const labelAngle = (startAngle + endAngle) / 2;
//     const labelRad = (labelAngle - 90) * (Math.PI / 180);
//     const labelX = 100 + 50 * Math.cos(labelRad);
//     const labelY = 100 + 50 * Math.sin(labelRad);

//     currentAngle = endAngle;

//     return {
//       pathData,
//       color: colors[i % colors.length],
//       label,
//       percentage,
//       value,
//       labelX,
//       labelY,
//     };
//   });

//   return (
//     <div className="pie-chart-container">
//       <div className="pie-chart-content">
//         <div className="pie-chart-left">
//           {title && <h4>{title}</h4>}
//           <svg viewBox="0 0 200 200" className="pie-svg">
//             {slices.map((slice, i) => (
//               <g key={i}>
//                 <path d={slice.pathData} fill={slice.color} stroke="white" strokeWidth="2" />
//                 {slice.percentage > 8 && (
//                   <text
//                     x={slice.labelX}
//                     y={slice.labelY}
//                     textAnchor="middle"
//                     dominantBaseline="middle"
//                     className="pie-label"
//                   >
//                     {slice.percentage.toFixed(0)}%
//                   </text>
//                 )}
//               </g>
//             ))}
//           </svg>
//         </div>
//         <div className="pie-legend">
//           {slices.map((slice, i) => (
//             <div key={i} className="legend-item">
//               <span className="legend-color" style={{ backgroundColor: slice.color }}></span>
//               <span className="legend-text">
//                 {slice.label.substring(0, 20)}: {slice.percentage.toFixed(1)}%
//               </span>
//             </div>
//           ))}
//         </div>
//       </div>
//     </div>
//   );
// };

// export const SummaryReport: React.FC<SummaryReportProps> = ({
//   summary,
//   rows,
// }) => {
//   if (!summary && rows.length === 0) return null;

//   // Combine ALL categorical data into one pie chart
//   const allCategoricalCounts: Record<string, number> = {};
//   let topCityValue = "";
//   let topCityCount = 0;
//   const cityCount: Record<string, number> = {};

//   rows.forEach((row) => {
//     Object.entries(row).forEach(([key, value]) => {
//       if (key.toLowerCase().includes('id')) return;

//       const num = Number(value);
//       if (isNaN(num) || num === null || num === 0) {
//         // Categorical data
//         const strValue = String(value);
//         const label = `${key}: ${strValue}`;
//         allCategoricalCounts[label] = (allCategoricalCounts[label] || 0) + 1;
        
//         // Track top city
//         if (key.toLowerCase().includes('city')) {
//           cityCount[strValue] = (cityCount[strValue] || 0) + 1;
//           if (cityCount[strValue] > topCityCount) {
//             topCityCount = cityCount[strValue];
//             topCityValue = strValue;
//           }
//         }
//       }
//     });
//   });

//   // Calculate metrics
//   const totalVehicles = rows.length;
//   const totalSales = rows.reduce((sum, row) => {
//     const salesVal = Object.values(row).find(v => {
//       const num = Number(v);
//       return !isNaN(num) && num > 100;
//     });
//     return sum + (Number(salesVal) || 0);
//   }, 0);
//   const salesM = (totalSales / 1000000).toFixed(2);

//   // Generate executive summary text
//   const generateExecutiveSummary = () => {
//     const topCity = topCityValue || "leading";
//     const topEntries = Object.entries(allCategoricalCounts)
//       .sort((a, b) => b[1] - a[1])
//       .slice(0, 3);
    
//     const bulletPoints = [];
    
//     bulletPoints.push(`Dataset contains ${totalVehicles} vehicles with total sales value of ${salesM}M`);
//     bulletPoints.push(`${topCity} is the leading city with ${topCityCount} vehicles`);
    
//     if (topEntries.length > 0) {
//       const topItem = topEntries[0];
//       const percentage = ((topItem[1] / totalVehicles) * 100).toFixed(1);
//       bulletPoints.push(`Primary market segment: ${topItem[0].split(': ')[1]} (${percentage}% of dataset)`);
//     }
    
//     if (topEntries.length > 1) {
//       const secondItem = topEntries[1];
//       const percentage = ((secondItem[1] / totalVehicles) * 100).toFixed(1);
//       bulletPoints.push(`Secondary segment: ${secondItem[0].split(': ')[1]} (${percentage}% of dataset)`);
//     }
    
//     bulletPoints.push(`Strong market performance with significant concentration in key geographical regions`);
//     bulletPoints.push(`Diversified product portfolio across multiple categories`);
    
//     return bulletPoints;
//   };

//   return (
//     <div className="summary-report">
//       {/* Top Metrics Cards */}
//       {/* <div className="metrics-container">
//         <div className="metric-card">
//           <div className="metric-value">{totalVehicles}</div>
//           <div className="metric-label">Total Vehicles</div>
//         </div>
//         <div className="metric-card">
//           <div className="metric-value">{salesM}</div>
//           <div className="metric-label">Total Sales (M)</div>
//         </div>
//         <div className="metric-card">
//           <div className="metric-value">{(totalSales * 0.01).toFixed(1)}</div>
//           <div className="metric-label">2025 Sales (M)</div>
//         </div>
//         <div className="metric-card">
//           <div className="metric-value">{topCityValue}</div>
//           <div className="metric-label">Top City</div>
//         </div>
//       </div> */}

//       {/* Analytics Container - Pie Chart and Summary Side by Side */}
//       <div className="analytics-container">
//         {/* Left: Chart Section */}
//         {Object.keys(allCategoricalCounts).length > 0 && (
//           <div className="chart-section">
//             <h4>Top Cities by Sales Value</h4>
//             <PieChart data={allCategoricalCounts} title="" />
//           </div>
//         )}
        
//         {/* Right: AI Summary Section */}
//         <div className="hf-summary-section">
//           <h4>Executive Summary</h4>
//           <ul className="hf-summary-content">
//             {generateExecutiveSummary().map((point, idx) => (
//               <li key={idx}>{point}</li>
//             ))}
//           </ul>
//         </div>
//       </div>
//     </div>
//   );
// };










import "./SummaryPage.css";
import { useEffect, useState, useMemo, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { fetchTables, fetchTableData } from "../api/qlikApi";
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
import exportImg from "../assets/export2.png";
 
type TableInfo = string | { name: string; [key: string]: any };
type Row = Record<string, any>;


 
export default function SummaryPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const pageStartTimeRef = useRef<number | null>(null);
 
  const [appId, setAppId] = useState<string>("");
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [filteredTables, setFilteredTables] = useState<TableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [pageLoadTime, setPageLoadTime] = useState<string | null>(null);

  // Relationship / star-schema helpers
  const [mainTable, setMainTable] = useState<string | null>(null); // detected hub table
  const [relations, setRelations] = useState<Record<string, string[]>>({}); // name -> related table names

  // Helper: build relation graph from `tables` (uses fields when available)
  const buildRelations = (tableList: TableInfo[]) => {
    const map: Record<string, Set<string>> = {};

    const normalizeFields = (t: TableInfo): Set<string> => {
      if (!t) return new Set<string>();
      if (typeof t === "string") return new Set<string>();
      const fields = (t as any).fields || (t as any).columns || [];
      return new Set<string>((fields || []).map((f: any) => String(f).toLowerCase()));
    };

    const names = (tableList || []).map((t) => (typeof t === 'string' ? t : t?.name || '')).filter(Boolean);

    const fieldSets: Record<string, Set<string>> = {};
    for (const t of tableList) {
      const name = typeof t === 'string' ? t : t?.name || '';
      if (!name) continue;
      fieldSets[name] = normalizeFields(t);
      map[name] = new Set();
    }

    // Two tables are related if they share at least one field name (case-insensitive)
    for (let i = 0; i < names.length; i++) {
      for (let j = i + 1; j < names.length; j++) {
        const a = names[i];
        const b = names[j];
        const setA = fieldSets[a] || new Set();
        const setB = fieldSets[b] || new Set();
        let shared = 0;
        for (const f of setA) {
          if (setB.has(f)) {
            shared++;
            break; // one shared field is enough to consider them related
          }
        }
        if (shared > 0) {
          map[a].add(b);
          map[b].add(a);
        }
      }
    }

    // Convert sets -> arrays
    const out: Record<string, string[]> = {};
    for (const k of Object.keys(map)) {
      out[k] = Array.from(map[k]);
    }
    return out;
  };

  // Helper: check whether two tables share at least one field (case-insensitive)
  const shareFields = (aName: string, bName: string) => {
    if (!aName || !bName) return false;
    const find = (n: string) => (tables || []).find(t => (typeof t === 'string' ? t : t?.name) === n) as any;
    const a = find(aName);
    const b = find(bName);
    const fieldsA: string[] = a && typeof a !== 'string' ? (a.fields || a.columns || []) : [];
    const fieldsB: string[] = b && typeof b !== 'string' ? (b.fields || b.columns || []) : [];
    if (!fieldsA.length || !fieldsB.length) return false;
    const setA = new Set(fieldsA.map(f => String(f).toLowerCase()));
    for (const f of fieldsB) {
      if (setA.has(String(f).toLowerCase())) return true;
    }
    return false;
  }; 

  // Multi-select removed — clicking a master table will automatically include related tables when exporting
  // (Manual multi-select UI was removed per UX request)
 
  // Track page load start time
  useEffect(() => {
    pageStartTimeRef.current = Date.now();
  }, []);
  // Data-table controls
  const [tableQuery, setTableQuery] = useState<string>("");
  const [pageSize, setPageSize] = useState<number>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);
  // Search for table list on the left panel
  const [tableListQuery, setTableListQuery] = useState<string>("");
 
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
 
  // Filter the left-side table list when the user types in the table search box
  useEffect(() => {
    if (!tableListQuery) {
      // Already sorted by recency, no need to reverse
      setFilteredTables((tables || []).slice());
      return;
    }
 
    const q = tableListQuery.toLowerCase();
    const filtered = (tables || [])
      .filter((t) => {
        const name = typeof t === "string" ? t : t?.name || "";
        return String(name).toLowerCase().includes(q);
      })
      .slice();
    // Already sorted by recency, no need to reverse
    setFilteredTables(filtered);
  }, [tableListQuery, tables]);
 
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
        // Remove Qlik Cloud "@syn" system tables from the UI (user requested)
        const cleaned = (data || []).filter((t: any) => {
          const name = typeof t === 'string' ? t : t?.name || '';
          if (!name) return false;
          return !name.toLowerCase().startsWith('@syn');
        });

        // Sort table list by creation/added timestamp (newest first).
        const getTimestamp = (t: any) => {
          if (!t || typeof t === 'string') return 0;
          const candidates = ['added_timestamp','created','createdAt','created_at','createdDate','modifiedDate','lastModifiedDate','lastReloadTime','lastReload'];
          for (const k of candidates) {
            const v = t[k];
            if (v) {
              const asNum = typeof v === 'number' ? v : Number(v);
              if (!isNaN(asNum) && asNum > 0) return asNum;
              const parsed = Date.parse(String(v));
              if (!isNaN(parsed)) return parsed;
            }
          }
          return 0;
        };

        const sorted = (cleaned || []).slice().sort((x: any, y: any) => {
          const tx = getTimestamp(x);
          const ty = getTimestamp(y);
          if (tx !== ty) return ty - tx; // newest first

          // Prefer explicitly flagged 'is_new' items
          const xi = (typeof x === 'string') ? false : !!x.is_new;
          const yi = (typeof y === 'string') ? false : !!y.is_new;
          if (xi && !yi) return -1;
          if (!xi && yi) return 1;

          // fallback to case-insensitive alphabetical order
          const nx = typeof x === 'string' ? x : x?.name || '';
          const ny = typeof y === 'string' ? y : y?.name || '';
          return String(nx).localeCompare(String(ny), undefined, { sensitivity: 'base' });
        });

        setTables(sorted);
        // Build relation graph (by shared field names) and detect hub (main) table
        const rel = buildRelations(sorted);
        setRelations(rel);

        // Choose main table (hub) — prefer explicit names with relations, otherwise highest degree
        const degreeOf = (n: string) => (rel[n] || []).length || 0;
        const nameOf = (t: any) => (typeof t === 'string' ? t : t?.name || '');

        let detectedMain: string | null = null;
        // 1) explicit master-like name that has >=1 relation
        for (const t of sorted) {
          const n = nameOf(t);
          if (!n) continue;
          if (/\b(master|fact|main)\b/i.test(n) && degreeOf(n) > 0) {
            detectedMain = n;
            break;
          }
        }

        // 2) otherwise choose table with largest number of related tables
        if (!detectedMain) {
          let bestName: string | null = null;
          let bestDeg = -1;
          for (const t of sorted) {
            const n = nameOf(t);
            const deg = degreeOf(n);
            if (deg > bestDeg) {
              bestDeg = deg;
              bestName = n;
            } else if (deg === bestDeg && deg > 0) {
              // tie-breaker: prefer table with more fields
              const fcount = typeof t === 'string' ? 0 : (t?.fields || []).length || 0;
              const found = sorted.find((s: TableInfo) => nameOf(s) === bestName);
              const currentFcount = typeof found === 'string' ? 0 : ((found as any)?.fields || []).length || 0;
              if (fcount > currentFcount) bestName = n;
            }
          }
          if (bestName && bestDeg > 0) detectedMain = bestName;
        }

        // 3) fallback: prefer explicit master-like even without relations, else most-recent
        if (!detectedMain) {
          const explicit = sorted.find((t: any) => /\b(master|fact|main)\b/i.test(nameOf(t)));
          if (explicit) detectedMain = nameOf(explicit);
        }

        // Only mark a detected mainTable when it either has related tables (degree>0)
        // or when an explicit name contains master/fact/main. Do NOT auto-promote a table
        // with no relationships to avoid confusing the UI.
        if (detectedMain) {
          // verify degree>0 OR explicit name
          const degree = (rel[detectedMain] || []).length || 0;
          const isExplicit = /\b(master|fact|main)\b/i.test(detectedMain);
          if (degree > 0 || isExplicit) {
            setMainTable(detectedMain);
          } else {
            setMainTable(null);
          }
        } else {
          setMainTable(null);
        }

        // Display list already sorted by recency, no need to reverse
        setFilteredTables(sorted);
        console.log("All tables fetched (sorted by recency, @syn filtered). Detected main:", detectedMain, "relations:", rel);

        // AUTO-LOAD: open the detected main table (if any), otherwise first table
        if (detectedMain) {
          loadData(detectedMain);
        } else if (sorted && sorted.length > 0) {
          const firstTableName = typeof sorted[0] === "string" ? sorted[0] : sorted[0]?.name;
          if (firstTableName) loadData(firstTableName);
        }
      })
      .catch(() => {})
      .finally(() => {
        setLoading(false);
        // Don't stop timer yet - wait for table data to load
      });
  }, [appId, stopTimer, startTimer]);
 
 
 
  // 3 → LOAD DATA FOR SELECTED TABLE
  const formatElapsed = (msTotal: number) => {
    const minutes = Math.floor(msTotal / 60000);
    const seconds = Math.floor((msTotal % 60000) / 1000);
    const centis = Math.floor((msTotal % 1000) / 10);
    const pad = (n: number, width = 2) => String(n).padStart(width, "0");
    return `${pad(minutes)}m : ${pad(seconds)}s : ${pad(centis)}ms`;
  };
 
  const loadData = async (tableName: string) => {
    if (!tableName || tableName === selectedTable) return;
 
    setSelectedTable(tableName);
    setTableLoading(true);
    setRows([]);
    setSummary(null);
 
    // start timing this table's data load
    startTimer?.(`/summary/data/${tableName}`);
 
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
 
      // 2️⃣ SUMMARY DATA - Calculate locally from the fetched data
      // This avoids backend dependency and works with any data format
      const { generateSummaryFromData } = await import("../api/qlikApi");
      const summary = generateSummaryFromData(data, tableName);
      setSummary(summary);
    } catch (e) {
      console.error("❌ Error loading table data:", e);
      
      // Show helpful error message
      const errorMessage = e instanceof Error ? e.message : String(e);
      alert(
        `Failed to load table "${tableName}".\n\n` +
        `Error: ${errorMessage}\n\n` +
        `Suggestions:\n` +
        `1. Verify the table name is correct\n` +
        `2. Ensure the app has been reloaded with the latest data in QlikCloud\n` +
        `3. Check the backend is running (http://127.0.0.1:8000)`
      );
    } finally {
      setTableLoading(false);
 
      // Prefer the specific table/data load elapsed if available
      const tableElapsed = stopTimer?.(`/summary/data/${tableName}`);
      if (tableElapsed) {
        console.debug(`Table ${tableName} load time:`, tableElapsed);
        setPageLoadTime(tableElapsed);
      } else {
        // Fallback: show navigation/load time for the Summary page if available
        const navElapsed = getLastElapsed?.("/summary");
        if (navElapsed) {
          setPageLoadTime(navElapsed);
        } else if (pageStartTimeRef.current) {
          // As a last resort, show local elapsed since page mount
          const totalTime = Date.now() - pageStartTimeRef.current;
          setPageLoadTime(formatElapsed(totalTime));
        }
      }
    }
  };

  // related-table prefetch is handled when exporting a master table (no per-table cache required here) 
 
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
 
  // Compute master table per-prefix (heuristic: prefer name containing "fact/master/main", else use largest field count)
  const masterMap = useMemo(() => {
    const map = new Map<string, string>();
    const groups: Record<string, any[]> = {};
    (tables || []).forEach((t) => {
      const name = typeof t === "string" ? t : t?.name || "";
      if (!name) return;
      const prefix = name.includes("_") ? name.split("_")[0] : "__noprefix__";
      groups[prefix] = groups[prefix] || [];
      groups[prefix].push(t);
    });

    Object.keys(groups).forEach((prefix) => {
      const group = groups[prefix];
      if (!group || group.length <= 1) return;

      const candidates = group.map((g: any) => {
        const name = typeof g === "string" ? g : g?.name || "";
        const fields = typeof g === "string" ? 0 : (g?.fields || []).length || 0;
        return { name, fields };
      });

      // explicit override: if a table named exactly 'Ford_Vehicle_Fact' exists use it as the master
      const fordExplicit = candidates.find((c: any) => c.name.toLowerCase() === 'ford_vehicle_fact');
      if (fordExplicit) {
        map.set(prefix, fordExplicit.name);
        return;
      }

      // prefer explicit names (Fact / Master / Main)
      const explicit = candidates.find((c: any) => /fact|master|main/i.test(c.name));
      if (explicit) {
        map.set(prefix, explicit.name);
        return;
      }

      // fallback to table with most fields
      candidates.sort((a: any, b: any) => (b.fields || 0) - (a.fields || 0));
      map.set(prefix, candidates[0].name);
    });

    return map;
  }, [tables]);

  const isMasterTable = (name: string) => {
    if (!name) return false;
    // If we detected a mainTable via relationships, prefer that
    if (mainTable) return name === mainTable || name.toLowerCase() === "ford_vehicle_fact";

    const lower = name.toLowerCase();
    // Explicit override: treat Ford_Vehicle_Fact as master (case-insensitive)
    if (lower === "ford_vehicle_fact") return true;
    const prefix = name.includes("_") ? name.split("_")[0] : null;
    if (!prefix) return false;
    return masterMap.get(prefix) === name;
  };

  const isRelatedTable = (name: string) => {
    if (!name) return false;
    // If relations were computed, use them (relation to detected main table)
    if (mainTable && relations && relations[mainTable]) {
      return relations[mainTable].includes(name);
    }

    // Fallback: prefix-based relationship (legacy behavior)
    const prefix = name.includes("_") ? name.split("_")[0] : null;
    if (!prefix) return false;
    const master = masterMap.get(prefix);
    if (!master || master === name) return false;

    // Only mark as related if the candidate actually shares at least one field with the master
    if (shareFields(master, name)) return true;

    return false;
  }; 

  const sortedFilteredTables = useMemo(() => {
    const arr = (filteredTables || []).slice();

    // If we detected a main table, place it first, then its related tables, then the rest
    if (mainTable) {
      arr.sort((a, b) => {
        const an = typeof a === 'string' ? a : a?.name || '';
        const bn = typeof b === 'string' ? b : b?.name || '';

        if (an === mainTable && bn !== mainTable) return -1;
        if (bn === mainTable && an !== mainTable) return 1;

        const relSet = new Set(relations[mainTable] || []);
        const aRel = relSet.has(an);
        const bRel = relSet.has(bn);
        if (aRel && !bRel) return -1;
        if (!aRel && bRel) return 1;

        // Leave other master tables (from masterMap) above unrelated tables
        const aMaster = isMasterTable(an);
        const bMaster = isMasterTable(bn);
        if (aMaster && !bMaster) return -1;
        if (!aMaster && bMaster) return 1;

        // final fallback: alphabetical
        return an.localeCompare(bn);
      });
      return arr;
    }

    // No detected main table: fallback to previous master-first alphabetical order
    arr.sort((a, b) => {
      const an = typeof a === 'string' ? a : a?.name || '';
      const bn = typeof b === 'string' ? b : b?.name || '';
      const aMaster = isMasterTable(an);
      const bMaster = isMasterTable(bn);
      if (aMaster && !bMaster) return -1;
      if (!aMaster && bMaster) return 1;
      return an.localeCompare(bn);
    });
    return arr;
  }, [filteredTables, masterMap, mainTable, relations]);

  const isSelectionMaster = !!(selectedTable && isMasterTable(selectedTable));
  // Export allowed when either master is selected or the selected table has no related tables
  const exportAllowed = Boolean(selectedTable && (isSelectionMaster || !isRelatedTable(selectedTable)));


  if (loading) {
    return <div className="wrap">Loading…</div>;
  }
 
  return (
    <div className="summary-layout">
      {/* LEFT – TABLE NAMES */}
      <div className="left-panel">
        <div className="panel-header">
          <h3 className="title">Tables {`(${tables.length})`}</h3>
          {mainTable && (
            <div style={{ marginTop: 6, fontSize: 12, color: '#444' }}>
              Detected main table: <strong style={{ color: '#0b3a66' }}>{mainTable}</strong>
            </div>
          )}
        </div>
 
        {/* Table list search (searches the list of table names) */}
        <div className="table-search">
          <input
            type="search"
            placeholder="Search tables..."
            value={tableListQuery}
            onChange={(e) => setTableListQuery(e.target.value)}
            className="table-search-input"
          />
        </div>
 
 
 
        {tables.length === 0 && (
          <p className="no-tables">No tables found</p>
        )}
 
        {sortedFilteredTables.map((t, i) => {
          const tableName = typeof t === "string" ? t : t?.name;
          const isNew = typeof t === "string" ? false : t?.is_new;
          if (!tableName) return null;

          const master = isMasterTable(tableName);
          const related = isRelatedTable(tableName);
          const cls = `${tableName === selectedTable ? "table-item active" : "table-item"}${master ? " master-row" : ""}${related && !master ? " related-row" : ""}`;

          return (
            <div
              key={i}
              className={cls}
              onClick={() => loadData(tableName)}
              title={master ? "Master table — click to export master + its related tables" : related ? "Related table — preview only — export disabled (select master to export)" : "Click to preview table"}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{tableName}</span>
              </span>
              {isNew && <span className="new-badge">NEW</span>}
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
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",width: "100%" }}>
                <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span>{selectedTable}</span>
                  {isSelectionMaster && <span className="master-indicator">master</span>}
                </h2>
                {pageLoadTime && (
                  <div className="timer-badge">Analysis Time: {pageLoadTime}</div>
                )}
              </div>
            </div>
 
            <SummaryReport summary={summary} rows={rows} />
 
            {/* ===== SEPARATE DIV FOR TABLE ===== */}
            <div className="data-section">
             
 
              {tableLoading && <p>Loading data…</p>}

              {!tableLoading && (
                <>
                  {rows.length > 0 ? (
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
                    </>
                  ) : (
                    <div className="no-data-placeholder" style={{ padding: 20 }}>
                      <p style={{ margin: 0, color: '#444' }}>No rows available for this table — preview not available.</p>
                      <p style={{ marginTop: 8, color: '#666' }}>You can still export this table; clicking <strong>Continue to Export</strong> will attempt to load the table data.</p>
                    </div>
                  )}

                  {/* BOTTOM RIGHT BUTTON - Export (single table or auto-include related tables for master) */}
                  <div className="bottom-actions">
                    <button
                      className="export-btn"
                      disabled={!exportAllowed || tableLoading}
                      title={!exportAllowed ? "Export disabled: select the master table (or a standalone table) to export" : "Continue to export selected table(s)"}
                      onClick={async () => {
                        try {
                          stopTimer?.("/summary");
                          sessionStorage.setItem("summaryComplete", "true");
                          startTimer?.("/export");

                          const sel = selectedTable || sessionStorage.getItem("selectedTable") || "";

                          // If we don't have rows for the selected table yet, try to fetch them now
                          let masterRows = rows;
                          if ((!masterRows || masterRows.length === 0) && sel) {
                            try {
                              setTableLoading(true);
                              const loaded = await fetchTableData(appId, sel);
                              masterRows = loaded || [];
                              setRows(masterRows);
                              // regenerate summary for the newly loaded data
                              const { generateSummaryFromData } = await import("../api/qlikApi");
                              setSummary(generateSummaryFromData(masterRows, sel));
                            } catch (e) {
                              console.warn("Failed to load selected table prior to export:", e);
                              alert("Failed to load table data for export. See console for details.");
                              setTableLoading(false);
                              return;
                            } finally {
                              setTableLoading(false);
                            }
                          }

                          const prefix = sel && sel.includes("_") ? sel.split("_")[0] : null;
                          const candidateNames = (tables || []).map((t) => (typeof t === "string" ? t : t?.name)).filter(Boolean) as string[];
                          let related: string[] = [];
                          // Prefer relation-graph when available and the selected table is the detected main table
                          if (mainTable && sel === mainTable && relations && relations[mainTable]) {
                            related = relations[mainTable].slice();
                          } else if (prefix) {
                            // Only auto-include prefix-matching tables that actually share fields with the selected table
                            related = candidateNames
                              .filter(n => n.startsWith(prefix + "_") && n !== sel)
                              .filter(n => shareFields(sel, n));
                          }

                          if (!related || related.length === 0) {
                            // No related tables — continue with single-table export
                            navigate("/export", {
                              state: {
                                appId,
                                appName: location.state?.appName || sessionStorage.getItem("appName") || appId,
                                selectedTable: sel,
                                rows: masterRows || [],
                              },
                            });
                            return;
                          }

                          // Prefetch related tables (master first)
                          setTableLoading(true);
                          const selectedData: any[] = [];
                          selectedData.push({ name: sel, data: { name: sel, rows: masterRows || [], summary } });

                          for (const relName of related) {
                            try {
                              const relRows = await fetchTableData(appId, relName);
                              const { generateSummaryFromData } = await import("../api/qlikApi");
                              const relSummary = generateSummaryFromData(relRows, relName);
                              selectedData.push({ name: relName, data: { name: relName, rows: relRows, summary: relSummary } });
                            } catch (e) {
                              console.warn("Failed to load related table:", relName, e);
                            }
                          }

                          setTableLoading(false);

                          navigate("/export", {
                            state: {
                              appId,
                              appName: location.state?.appName || sessionStorage.getItem("appName") || appId,
                              selectedTables: selectedData,
                            },
                          });
                        } catch (err) {
                          setTableLoading(false);
                          console.error(err);
                          alert("Failed to prepare related tables for export. See console for details.");
                        }
                      }}
                    >
                      <img src={exportImg} alt="Export" />Continue to Export
                    </button>

                    {/* Hint shown when export is disabled because a related table is selected */}
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
            {/* <h4>Top Cities by Sales Value</h4> */}
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