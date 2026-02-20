import "./SummaryPage.css";
import { useEffect, useState, useMemo, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { fetchTables, fetchTableData, fetchAISummaryFromBackend } from "../api/qlikApi";
import Csvicon from "../assets/Csvicon.png";
import { useWizard } from "../context/WizardContext";
import SchemaModal from "../components/SchemaModal/SchemaModal";
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
  const [mainTable, setMainTable] = useState<string | null>(null);
  const [relations, setRelations] = useState<Record<string, string[]>>({});
  const [isSchemaModalOpen, setIsSchemaModalOpen] = useState(false);

  // Helper: build relation graph from `tables` (uses fields when available)
  const buildRelations = (tableList: TableInfo[]) => {
    const map: Record<string, Set<string>> = {};

    const normalizeFields = (t: TableInfo): Set<string> => {
      const out = new Set<string>();
      if (!t || typeof t === "string") return out;

      const raw = (t as any).fields || (t as any).columns || [];
      for (const f of (raw || [])) {
        if (!f) continue;
        if (typeof f === "string") {
          out.add(f.toLowerCase());
          continue;
        }
        const fname = (f.name || f.qName || f.field || f.key || "").toString();
        if (fname) out.add(fname.toLowerCase());
      }
      return out;
    };

    const names = (tableList || []).map((t) => (typeof t === 'string' ? t : t?.name || '')).filter(Boolean);

    const fieldSets: Record<string, Set<string>> = {};
    for (const t of tableList) {
      const name = typeof t === 'string' ? t : t?.name || '';
      if (!name) continue;
      fieldSets[name] = normalizeFields(t);
      map[name] = new Set();
    }

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
            break;
          }
        }
        if (shared > 0) {
          map[a].add(b);
          map[b].add(a);
        }
      }
    }

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

    const getNames = (tbl: any) => {
      const raw = tbl && typeof tbl !== 'string' ? (tbl.fields || tbl.columns || []) : [];
      return (raw || []).map((x: any) => (typeof x === 'string' ? x : (x.name || x.qName || String(x))).toLowerCase());
    };

    const fieldsA = getNames(a);
    const fieldsB = getNames(b);
    if (!fieldsA.length || !fieldsB.length) return false;

    const setA = new Set(fieldsA);
    for (const f of fieldsB) {
      if (setA.has(f)) return true;
    }
    return false;
  };

  // Track page load start time
  useEffect(() => {
    pageStartTimeRef.current = Date.now();
  }, []);

  // Data-table controls
  const [tableQuery, setTableQuery] = useState<string>("");
  const [pageSize, setPageSize] = useState<number>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [tableListQuery, setTableListQuery] = useState<string>("");

  // Sorting
  const [orderBy, setOrderBy] = useState<string>("");
  const [order, setOrder] = useState<"asc" | "desc">("asc");

  const processedRows = useMemo(() => {
    let out = rows || [];

    if (tableQuery.trim()) {
      const q = tableQuery.toLowerCase();
      out = out.filter((r) =>
        Object.values(r).some((v) =>
          String(v ?? "").toLowerCase().includes(q)
        )
      );
    }

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

  useEffect(() => {
    if (!tableListQuery) {
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

    if (sessionStorage.getItem("lastTimerTarget") !== "/summary") {
      startTimer?.("/summary");
    }

    fetchTables(appId)
      .then((data) => {
        const cleaned = (data || []).filter((t: any) => {
          const name = typeof t === 'string' ? t : t?.name || '';
          if (!name) return false;
          return !name.toLowerCase().startsWith('@syn');
        });

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
          if (tx !== ty) return ty - tx;

          const xi = (typeof x === 'string') ? false : !!x.is_new;
          const yi = (typeof y === 'string') ? false : !!y.is_new;
          if (xi && !yi) return -1;
          if (!xi && yi) return 1;

          const nx = typeof x === 'string' ? x : x?.name || '';
          const ny = typeof y === 'string' ? y : y?.name || '';
          return String(nx).localeCompare(String(ny), undefined, { sensitivity: 'base' });
        });

        setTables(sorted);
        const rel = buildRelations(sorted);
        setRelations(rel);

        const degreeOf = (n: string) => (rel[n] || []).length || 0;
        const nameOf = (t: any) => (typeof t === 'string' ? t : t?.name || '');

        let detectedMain: string | null = null;
        for (const t of sorted) {
          const n = nameOf(t);
          if (!n) continue;
          if (/\b(master|fact|main)\b/i.test(n) && degreeOf(n) > 0) {
            detectedMain = n;
            break;
          }
        }

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
              const fcount = typeof t === 'string' ? 0 : (t?.fields || []).length || 0;
              const found = sorted.find((s: TableInfo) => nameOf(s) === bestName);
              const currentFcount = typeof found === 'string' ? 0 : ((found as any)?.fields || []).length || 0;
              if (fcount > currentFcount) bestName = n;
            }
          }
          if (bestName && bestDeg > 0) detectedMain = bestName;
        }

        if (!detectedMain) {
          const explicit = sorted.find((t: any) => /\b(master|fact|main)\b/i.test(nameOf(t)));
          if (explicit) detectedMain = nameOf(explicit);
        }

        if (detectedMain) {
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

        setFilteredTables(sorted);

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

    startTimer?.(`/summary/data/${tableName}`);

    try {
      const data = await fetchTableData(appId, tableName);
      setRows(data || []);

      try {
        sessionStorage.setItem("selectedTable", tableName);
        sessionStorage.setItem("selectedRows", JSON.stringify(data || []));
      } catch (e) {
        // ignore storage errors
      }

      const { generateSummaryFromData } = await import("../api/qlikApi");
      const summary = generateSummaryFromData(data, tableName);
      setSummary(summary);
    } catch (e) {
      console.error("❌ Error loading table data:", e);

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

      const tableElapsed = stopTimer?.(`/summary/data/${tableName}`);
      if (tableElapsed) {
        setPageLoadTime(tableElapsed);
      } else {
        const navElapsed = getLastElapsed?.("/summary");
        if (navElapsed) {
          setPageLoadTime(navElapsed);
        } else if (pageStartTimeRef.current) {
          const totalTime = Date.now() - pageStartTimeRef.current;
          setPageLoadTime(formatElapsed(totalTime));
        }
      }
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

  // Compute master table per-prefix
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

      const fordExplicit = candidates.find((c: any) => c.name.toLowerCase() === 'ford_vehicle_fact');
      if (fordExplicit) {
        map.set(prefix, fordExplicit.name);
        return;
      }

      const explicit = candidates.find((c: any) => /fact|master|main/i.test(c.name));
      if (explicit) {
        map.set(prefix, explicit.name);
        return;
      }

      candidates.sort((a: any, b: any) => (b.fields || 0) - (a.fields || 0));
      map.set(prefix, candidates[0].name);
    });

    return map;
  }, [tables]);

  const isMasterTable = (name: string) => {
    if (!name) return false;
    if (mainTable) return name === mainTable || name.toLowerCase() === "ford_vehicle_fact";

    const lower = name.toLowerCase();
    if (lower === "ford_vehicle_fact") return true;
    const prefix = name.includes("_") ? name.split("_")[0] : null;
    if (!prefix) return false;
    return masterMap.get(prefix) === name;
  };

  const isRelatedTable = (name: string) => {
    if (!name) return false;
    if (mainTable && relations && relations[mainTable]) {
      return relations[mainTable].includes(name);
    }

    const prefix = name.includes("_") ? name.split("_")[0] : null;
    if (!prefix) return false;
    const master = masterMap.get(prefix);
    if (!master || master === name) return false;

    if (shareFields(master, name)) return true;

    return false;
  };

  const sortedFilteredTables = useMemo(() => {
    const arr = (filteredTables || []).slice();

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

        const aMaster = isMasterTable(an);
        const bMaster = isMasterTable(bn);
        if (aMaster && !bMaster) return -1;
        if (!aMaster && bMaster) return 1;

        return an.localeCompare(bn);
      });
      return arr;
    }

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
  const exportAllowed = Boolean(selectedTable && (isSelectionMaster || !isRelatedTable(selectedTable)));

  // Helper: prepare export payload and navigate to /export
  const prepareAndNavigateToExport = async (tableToExport?: string) => {
    try {
      stopTimer?.("/summary");
      sessionStorage.setItem("summaryComplete", "true");
      startTimer?.("/export");

      const sel = tableToExport || selectedTable || (sessionStorage.getItem("selectedTable") || "");
      if (!sel) {
        alert("No table selected for export.");
        return;
      }

      let masterRows = rows;
      if ((tableToExport && tableToExport !== selectedTable) || (!masterRows || masterRows.length === 0)) {
        try {
          setTableLoading(true);
          const loaded = await fetchTableData(appId, sel);
          masterRows = loaded || [];
          setSelectedTable(sel);
          setRows(masterRows);
          const { generateSummaryFromData } = await import("../api/qlikApi");
          setSummary(generateSummaryFromData(masterRows, sel));
        } catch (e) {
          console.warn("Failed to load table prior to export:", e);
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
      if (mainTable && sel === mainTable && relations && relations[mainTable]) {
        related = relations[mainTable].slice();
      } else if (prefix) {
        related = candidateNames
          .filter(n => n.startsWith(prefix + "_") && n !== sel)
          .filter(n => shareFields(sel, n));
      }

      if (!related || related.length === 0) {
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
          {mainTable && (
            <div style={{ marginTop: 6, fontSize: 12, color: '#444' }}>
              Detected main table: <strong style={{ color: '#0b3a66' }}>{mainTable}</strong>
            </div>
          )}
        </div>

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

              {!related && (
                <button
                  className="inline-export"
                  title={master ? "Export master + related tables" : "Export this standalone table"}
                  onClick={(e) => { e.stopPropagation(); prepareAndNavigateToExport(tableName); }}
                >
                </button>
              )}

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
            <div className="header">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
                <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span>{selectedTable}</span>
                  {isSelectionMaster && <span className="master-indicator">master</span>}
                  <button
                    onClick={() => setIsSchemaModalOpen(true)}
                    style={{
                      marginLeft: '12px',
                      padding: '6px 12px',
                      fontSize: '12px',
                      backgroundColor: '#f59e0b',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: '500',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      const target = e.currentTarget as HTMLButtonElement;
                      target.style.backgroundColor = 'rgb(11 131 245)';
                      target.style.transform = 'scale(1.05)';
                    }}
                    onMouseLeave={(e) => {
                      const target = e.currentTarget as HTMLButtonElement;
                      target.style.backgroundColor = 'rgb(11 131 245)';
                      target.style.transform = 'scale(1)';
                    }}
                  >
                    Schema
                  </button>
                </h2>
                {pageLoadTime && (
                  <div className="timer-badge">Analysis Time: {pageLoadTime}</div>
                )}
              </div>
            </div>

            <SummaryReport summary={summary} rows={rows} />

            {/* DATA TABLE SECTION */}
            <div className="data-section">
              {tableLoading && <p>Loading data…</p>}

              {!tableLoading && (
                <>
                  {rows.length > 0 ? (
                    <>
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
                            <img src={Csvicon} alt="csv" className="btn-icon" />
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

                  <div className="bottom-actions">
                    {exportAllowed ? (
                      <button
                        className="export-btn"
                        disabled={tableLoading}
                        title={"Continue to export selected table(s)"}
                        onClick={() => prepareAndNavigateToExport()}
                      >
                        <img src={exportImg} alt="Export" />Continue to Export
                      </button>
                    ) : (
                      selectedTable && isRelatedTable(selectedTable) &&
                      (
                        <div className="export-hint"></div>
                      )
                    )}
                  </div>
                </>
              )}
            </div>
          </>
        )}
      </div>

      <SchemaModal
        isOpen={isSchemaModalOpen}
        onClose={() => setIsSchemaModalOpen(false)}
        appId={appId}
        masterTable={mainTable || selectedTable}
        tables={tables}
      />
    </div>
  );
}

// ================= SUMMARY REPORT COMPONENT =================
import React from "react";

interface SummaryReportProps {
  summary: any;
  rows: Row[];
}

// ─── Types for backend-driven chart data ───────────────────────────────────────
interface ChartSlice {
  label: string;
  value: number;
}

// ─── Pie Chart Component ───────────────────────────────────────────────────────
// Now accepts ChartSlice[] directly from the backend instead of a Record<string,number>
const PieChart: React.FC<{ slices: ChartSlice[]; title: string }> = ({ slices, title }) => {
  if (!slices || slices.length === 0) return null;

  const total = slices.reduce((sum, s) => sum + s.value, 0);
  if (total === 0) return null;

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
  const paths = slices.slice(0, 8).map((slice, i) => {
    const percentage = (slice.value / total) * 100;
    const sliceAngle = (percentage / 100) * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + sliceAngle;

    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);

    const x1 = 100 + 80 * Math.cos(startRad);
    const y1 = 100 + 80 * Math.sin(startRad);
    const x2 = 100 + 80 * Math.cos(endRad);
    const y2 = 100 + 80 * Math.sin(endRad);

    const largeArc = sliceAngle > 180 ? 1 : 0;
    const pathData = `M 100 100 L ${x1} ${y1} A 80 80 0 ${largeArc} 1 ${x2} ${y2} Z`;

    const labelAngle = (startAngle + endAngle) / 2;
    const labelRad = (labelAngle - 90) * (Math.PI / 180);
    const labelX = 100 + 50 * Math.cos(labelRad);
    const labelY = 100 + 50 * Math.sin(labelRad);

    currentAngle = endAngle;

    return { pathData, color: colors[i % colors.length], label: slice.label, percentage, value: slice.value, labelX, labelY };
  });

  return (
    <div className="pie-chart-container">
      <div className="pie-chart-content">
        <div className="pie-chart-left">
          {title && <h4>{title}</h4>}
          <svg viewBox="0 0 200 200" className="pie-svg">
            {paths.map((p, i) => (
              <g key={i}>
                <path d={p.pathData} fill={p.color} stroke="white" strokeWidth="2" />
                {p.percentage > 8 && (
                  <text
                    x={p.labelX}
                    y={p.labelY}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="pie-label"
                  >
                    {p.percentage.toFixed(0)}%
                  </text>
                )}
              </g>
            ))}
          </svg>
        </div>
        <div className="pie-legend">
          {paths.map((p, i) => (
            <div key={i} className="legend-item">
              <span className="legend-color" style={{ backgroundColor: p.color }}></span>
              <span className="legend-text">
                {p.label.substring(0, 20)}: {p.percentage.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ─── SummaryReport ─────────────────────────────────────────────────────────────
export const SummaryReport: React.FC<SummaryReportProps> = ({ summary, rows }) => {
  // AI response from backend — holds the full response object
  const [aiResponse, setAiResponse] = useState<{
    bullets: string[];          // exactly 3 clean bullet strings
    chartSlices: ChartSlice[];  // backend-selected categorical column data
    chartLabel: string;         // column name used for the pie chart
    isAI: boolean;
  } | null>(null);

  const [aiLoading, setAiLoading] = useState(false);
  const [lastTableName, setLastTableName] = useState<string>("");

  const currentTableName = summary?.table || "Dataset";

  // ── Fetch AI summary + chart data from backend ────────────────────────────
  useEffect(() => {
    if (!rows || rows.length === 0 || !summary) {
      setAiResponse(null);
      return;
    }

    // Avoid re-fetching for the same table
    if (currentTableName === lastTableName && aiResponse !== null) {
      return;
    }

    setLastTableName(currentTableName);
    setAiLoading(true);

    fetchAISummaryFromBackend(currentTableName, rows, summary)
      .then((raw: any) => {
        // ── Parse bullet points ──────────────────────────────────────────────
        // The backend returns summary as a newline-separated string of "• text" lines.
        // We strip the leading "• " and any stray whitespace before rendering,
        // so the <li> elements use the browser's own list bullet — no double bullets.
        let bulletLines: string[] = [];

        if (typeof raw === 'string') {
          // raw string — split by newline and clean
          bulletLines = raw
            .split('\n')
            .map((line: string) => line.replace(/^[•\-\*]\s*/, '').trim())
            .filter((line: string) => line.length > 0)
            .slice(0, 7); // hard cap at 7 bullets
        } else if (Array.isArray(raw)) {
          // already an array (legacy path)
          bulletLines = (raw as string[])
            .map((line: string) => line.replace(/^[•\-\*]\s*/, '').trim())
            .filter((line: string) => line.length > 0)
            .slice(0, 7);
        } else if (raw && typeof raw === 'object') {
          // Full response object from fetchAISummaryFromBackend — preferred path
          const summaryStr: string = raw.summary || '';
          bulletLines = summaryStr
            .split('\n')
            .map((line: string) => line.replace(/^[•\-\*]\s*/, '').trim())
            .filter((line: string) => line.length > 0)
            .slice(0, 7);
        }

        // ── Parse chart data from backend ────────────────────────────────────
        // chart_data is [{label, value}, ...] and chart_label is the column name.
        // These come directly from _extract_chart_data_from_sample() in main.py.
        let chartSlices: ChartSlice[] = [];
        let chartLabel = '';

        if (raw && typeof raw === 'object') {
          const cd = (raw as any).chart_data;
          if (Array.isArray(cd) && cd.length > 0) {
            chartSlices = cd as ChartSlice[];
          }
          chartLabel = (raw as any).chart_label || '';
        }

        setAiResponse({
          bullets: bulletLines,
          chartSlices,
          chartLabel,
          isAI: bulletLines.length > 0,
        });
      })
      .catch((err: any) => {
        console.error("AI Summary fetch failed:", err);
        setAiResponse(null);
      })
      .finally(() => {
        setAiLoading(false);
      });
  }, [rows, summary, currentTableName]);

  // ── Local fallback summary (used when AI is loading or unavailable) ────────
  const generateLocalBullets = (): string[] => {
    const totalVehicles = rows.length;
    const columns = rows[0] ? Object.keys(rows[0]) : [];

    const totalSales = rows.reduce((sum, row) => {
      const salesVal = Object.values(row).find(v => {
        const num = Number(v);
        return !isNaN(num) && num > 100;
      });
      return sum + (Number(salesVal) || 0);
    }, 0);
    const salesM = (totalSales / 1000000).toFixed(2);

    // Find a categorical column for the fallback description
    const catCounts: Record<string, number> = {};
    rows.forEach((row) => {
      Object.entries(row).forEach(([key, value]) => {
        if (key.toLowerCase().includes('city') || key.toLowerCase().includes('status') || key.toLowerCase().includes('type')) {
          const strValue = String(value);
          catCounts[strValue] = (catCounts[strValue] || 0) + 1;
        }
      });
    });

    const topEntries = Object.entries(catCounts).sort((a, b) => b[1] - a[1]).slice(0, 2);

    // Find numeric columns for statistics
    const numericCols: string[] = [];
    columns.forEach(col => {
      const vals = rows.slice(0, 10).map(r => Number(r[col]));
      if (vals.every(v => !isNaN(v))) {
        numericCols.push(col);
      }
    });

    const bullets: string[] = [];

    // Bullet 1: Dataset size
    bullets.push(`Dataset contains ${totalVehicles.toLocaleString()} records across ${columns.length} columns with total value of ${salesM}M`);

    // Bullet 2: Primary segment
    if (topEntries.length > 0) {
      const pct = ((topEntries[0][1] / totalVehicles) * 100).toFixed(1);
      bullets.push(`Primary segment: ${topEntries[0][0]} (${pct}% of dataset)`);
    } else {
      bullets.push(`Data contains ${columns.length} columns available for analysis`);
    }

    // Bullet 3: Numeric analysis
    if (numericCols.length > 0) {
      bullets.push(`Numeric analysis available for ${numericCols.length} columns: ${numericCols.slice(0, 3).join(', ')}`);
    } else {
      bullets.push(`Statistical summary computed for all numeric fields`);
    }

    // Bullet 4: Data quality
    bullets.push(`Data quality assessment shows the dataset is structured and ready for analysis`);

    // Bullet 5: Segment distribution
    if (topEntries.length > 1) {
      const pct = ((topEntries[1][1] / totalVehicles) * 100).toFixed(1);
      bullets.push(`Secondary segment: ${topEntries[1][0]} (${pct}% of dataset)`);
    } else {
      bullets.push(`Distribution patterns indicate balanced representation across key dimensions`);
    }

    // Bullet 6: Recommendation
    bullets.push(`Consider exploring relationships between categorical and numeric columns for deeper insights`);

    // Bullet 7: Next steps
    bullets.push(`Review individual columns for detailed breakdowns, trends, and anomaly detection`);

    return bullets.slice(0, 7);
  };

  // ── Local fallback chart (used when backend provides no chart_data) ────────
  // This mirrors the original analyzeDataForChart() logic but converts to ChartSlice[]
  const generateLocalChartSlices = (): { slices: ChartSlice[]; label: string } => {
    if (!rows || rows.length === 0) return { slices: [], label: '' };

    const highPriorityKeywords = ['city', 'country', 'state', 'region', 'location', 'branch', 'store'];
    const mediumPriorityKeywords = ['status', 'type', 'category', 'segment', 'group', 'class', 'brand', 'product', 'model', 'make'];

    interface ColAnalysis { uniqueCount: number; counts: Record<string, number>; priority: number; }
    const columnAnalysis: Record<string, ColAnalysis> = {};

    rows.forEach((row) => {
      Object.entries(row).forEach(([key, value]) => {
        const num = Number(value);
        const isNumeric = !isNaN(num) && num !== null && String(value).trim() !== '';
        const isIdColumn = key.toLowerCase().endsWith('_id') || key.toLowerCase() === 'id' || key.toLowerCase().includes('guid');
        if (isNumeric || isIdColumn) return;

        const strValue = String(value).trim();
        if (!strValue || strValue.length > 50) return;

        if (!columnAnalysis[key]) {
          const lowerKey = key.toLowerCase();
          let priority = 1;
          if (highPriorityKeywords.some(kw => lowerKey.includes(kw))) priority = 3;
          else if (mediumPriorityKeywords.some(kw => lowerKey.includes(kw))) priority = 2;
          columnAnalysis[key] = { uniqueCount: 0, counts: {}, priority };
        }
        columnAnalysis[key].counts[strValue] = (columnAnalysis[key].counts[strValue] || 0) + 1;
      });
    });

    Object.keys(columnAnalysis).forEach(key => {
      columnAnalysis[key].uniqueCount = Object.keys(columnAnalysis[key].counts).length;
    });

    let bestColumn: string | null = null;
    let bestScore = -1;

    Object.entries(columnAnalysis).forEach(([key, analysis]) => {
      const uniqueRatio = analysis.uniqueCount / rows.length;
      if (analysis.uniqueCount <= 1 || uniqueRatio > 0.8) return;
      if (analysis.uniqueCount > 12) return;

      const idealUniqueCount = 5;
      const uniqueCountScore = 10 - Math.abs(idealUniqueCount - analysis.uniqueCount);
      const score = analysis.priority * 10 + uniqueCountScore;

      if (score > bestScore) {
        bestScore = score;
        bestColumn = key;
      }
    });

    if (!bestColumn) {
      const fallback = Object.entries(columnAnalysis)
        .filter(([_, a]) => a.uniqueCount >= 2 && a.uniqueCount <= 10)
        .sort((a, b) => a[1].uniqueCount - b[1].uniqueCount)[0];
      if (fallback) bestColumn = fallback[0];
    }

    if (!bestColumn) return { slices: [], label: '' };

    const slices: ChartSlice[] = Object.entries(columnAnalysis[bestColumn].counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([label, value]) => ({ label, value }));

    return { slices, label: `${bestColumn} Distribution` };
  };

  // ── Decide what to render ─────────────────────────────────────────────────
  const displayBullets = (aiResponse?.bullets && aiResponse.bullets.length > 0)
    ? aiResponse.bullets
    : generateLocalBullets();

  // Use backend chart data when available; fall back to local analysis
  let chartSlices: ChartSlice[] = [];
  let chartTitle = '';

  if (aiResponse?.chartSlices && aiResponse.chartSlices.length > 0) {
    chartSlices = aiResponse.chartSlices;
    chartTitle = aiResponse.chartLabel
      ? `${aiResponse.chartLabel} Distribution`
      : 'Data Distribution';
  } else {
    const local = generateLocalChartSlices();
    chartSlices = local.slices;
    chartTitle = local.label;
  }

  if (!summary && rows.length === 0) return null;

  return (
    <div className="summary-report">
      <div className="analytics-container">
        {/* Left: Data-driven Pie Chart */}
        {chartSlices.length > 0 && (
          <div className="chart-section">
            <PieChart slices={chartSlices} title={chartTitle} />
          </div>
        )}

        {/* Right: Executive Summary — exactly 3 bullet points */}
        <div className="hf-summary-section">
          <h4>
            Executive Summary
            {aiLoading && (
              <span style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>
                (Generating AI insights…)
              </span>
            )}
            {aiResponse?.isAI && !aiLoading && (
              <span style={{ marginLeft: 8, fontSize: 10, color: '#10b981', fontWeight: 'normal' }}>
                🤖 AI Generated
              </span>
            )}
          </h4>
          <ul className="hf-summary-content">
            {displayBullets.map((point, idx) => (
              // point already has the leading "• " stripped — browser renders the <li> bullet
              <li key={idx}>{point}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};