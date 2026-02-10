import "./ExportPage.css";
import { useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { useWizard } from "../context/WizardContext";
import migrationImg from "../assets/migration2.png";

export default function ExportPage() {
  const { state } = useLocation() as any;
  const navigate = useNavigate();
  const [pageLoadTime, setPageLoadTime] = useState<string | null>(null);

  const { stopTimer } = useWizard();

  useEffect(() => {
    const elapsed = stopTimer?.("/export");
    setPageLoadTime(elapsed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  // Prefer friendly appName; fallback to appId or session storage
  const appNameRaw = state?.appName || state?.appId || sessionStorage.getItem("appName") || "Unknown";
  let selectedTable = state?.selectedTable || sessionStorage.getItem("selectedTable");
  let rows = state?.rows || [];

  // try to hydrate rows from storage if not passed
  if ((!rows || !rows.length) && sessionStorage.getItem("selectedRows")) {
    try {
      rows = JSON.parse(sessionStorage.getItem("selectedRows") || "[]");
    } catch (_) {
      rows = [];
    }
  }

  const appName = appNameRaw;

  // start with nothing selected — user must choose
  const [options, setOptions] = useState<{ csv: boolean; dax: boolean }>({ csv: false, dax: false });
  const [selectAll, setSelectAll] = useState(false);

  // SSRS card state (kept separate) — will be rendered disabled by UI
  const [ssrsOptions, setSSRSOptions] = useState<{ csv: boolean; dax: boolean }>({ csv: false, dax: false });
  const [ssrsSelectAll, setSSRSSelectAll] = useState(false);

  if (!selectedTable) {
    // if the summary step completed previously, send user to Summary to pick a table
    if (sessionStorage.getItem("summaryComplete") === "true") {
      navigate("/summary");
      return null;
    }

    return (
      <div className="export-wrap">
        <p>No export data found.</p>
        <button onClick={() => navigate("/apps")}>Go Back</button>
      </div>
    );
  }

  // CSV EXPORT (REUSED LOGIC)
  const exportCSV = () => {
    if (!rows?.length) return;

    const headers = Object.keys(rows[0]);
    const csv = [
      headers.join(","),
      ...rows.map((r: any) =>
        headers.map((h) => `"${r[h] ?? ""}"`).join(",")
      ),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedTable}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    // Mark export done
    sessionStorage.setItem("exportCSV", "true");
    sessionStorage.setItem("exportComplete", "true");
  };

  // small DAX exporter - writes a lightweight skeleton .dax file containing columns and a sample measure
  const exportDAX = () => {
    if (!rows?.length) return;

    const cols = Object.keys(rows[0]);
    const daxLines = [] as string[];
    daxLines.push(`-- DAX export skeleton for table: ${selectedTable}`);
    daxLines.push(`-- Columns:`);
    cols.forEach((c) => daxLines.push(`-- ${c}`));
    daxLines.push(`\n-- Sample measure`);
    daxLines.push(`[${selectedTable} Count] = COUNTROWS('${selectedTable}')`);

    const blob = new Blob([daxLines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedTable}.dax`;
    a.click();
    URL.revokeObjectURL(url);

    sessionStorage.setItem("exportDAX", "true");
    sessionStorage.setItem("exportComplete", "true");
  };

  return (
    <div className="export-wrap">
      <div className="timerStyle">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",width: "100%" }}>
          <h2>📤 Export Data</h2>
          {pageLoadTime && (
            <div className="timer-badge">Analysis Loading Time: {pageLoadTime}</div>
          )}
        </div>
      </div>

      {/* 🔹 TOP INFO BOXES */}
      <div className="info-grid">
          <div className="info-box">
  <span className="label">Application</span>
  <span className="value">{appName}</span>
</div>

        <div className="info-box">
          <span className="label">Table Name</span>
          <span className="value">{selectedTable}</span>
        </div>

        <div className="info-box">
          <span className="label">Total Rows</span>
          <span className="value">{rows?.length || 0}</span>
        </div>

        
      </div>

      {/* 🔹 EXPORT OPTIONS */}
      {/* <div className="export-options">
        

        <div className="export-box disabled">
          Export to SSRS (Coming Soon)
        </div>
      </div> */}
      

      {/* 🔹 EXPORT CHECKBOX OPTIONS (inside one box) */}
      <div className="powerbi-options">
        <div className="export-box sub">
          <div className="export-box powerbi">
          Export To PowerBI
        </div>
          <div className="checkbox-row">
            <label>
              <input
                type="checkbox"
                checked={selectAll}
                onChange={() => {
                  const newVal = !selectAll;
                  setSelectAll(newVal);
                  setOptions({ csv: newVal, dax: newVal });
                }}
              />
              <strong> Select All</strong>
            </label>
          </div>

          <div className="checkbox-row">
            <label>
              <input
                type="checkbox"
                checked={options.csv}
                onChange={() => {
                  const csv = !options.csv;
                  setOptions((s) => ({ ...s, csv }));
                  setSelectAll(csv && options.dax);
                }}
              />
              📄 Export as CSV
            </label>
          </div>

          <div className="checkbox-row">
            <label>
              <input
                type="checkbox"
                checked={options.dax}
                onChange={() => {
                  const dax = !options.dax;
                  setOptions((s) => ({ ...s, dax }));
                  setSelectAll(options.csv && dax);
                }}
              />
              📊 Export as DAX (Coming Soon)
            </label>
          </div>

          <div className="actions-row">
            <button
              className="export-btn"
              onClick={() => {
                // Export selected options
                if (options.csv) exportCSV();
                if (options.dax) exportDAX();
              }}
              disabled={!options.csv && !options.dax}
            >
              ✅ Export Selected
            </button>
          </div>
        </div>

        {/* <div className="export-box sub">
          <div className="export-box ssrs disabled">
            Export To SSRS
          </div>
          <div className="checkbox-row">
            <label>
              <input
                type="checkbox"
                checked={ssrsSelectAll}
                disabled
                onChange={() => {
                  const newVal = !ssrsSelectAll;
                  setSSRSSelectAll(newVal);
                  setSSRSOptions({ csv: newVal, dax: newVal });
                }}
              />
              <strong> Select All</strong>
            </label>
          </div>

          <div className="checkbox-row">
            <label>
              <input
                type="checkbox"
                checked={ssrsOptions.csv}
                disabled
                onChange={() => {
                  const csv = !ssrsOptions.csv;
                  setSSRSOptions((s) => ({ ...s, csv }));
                  setSSRSSelectAll(csv && ssrsOptions.dax);
                }}
              />
              📄 Export as CSV
            </label>
          </div>

          <div className="checkbox-row">
            <label>
              <input
                type="checkbox"
                checked={ssrsOptions.dax}
                disabled
                onChange={() => {
                  const dax = !ssrsOptions.dax;
                  setSSRSOptions((s) => ({ ...s, dax }));
                  setSSRSSelectAll(ssrsOptions.csv && dax);
                }}
              />
              📊 Export as DAX 
            </label>
          </div>

          <div className="actions-row">
            <button
              className="export-btn"
              onClick={() => {
                // Export selected options (SSRS currently disabled)
                if (ssrsOptions.csv) exportCSV();
                if (ssrsOptions.dax) exportDAX();
              }}
              disabled
            >
              ✅ Export Selected
            </button>
          </div>
        </div> */}


        <div className="export-box sub ssrs-disabled">
  <div className="export-box ssrs">
    Export To SSRS
  </div>

  <div className="checkbox-row">
    <label>
      <input type="checkbox" checked={ssrsSelectAll} />
      <strong> Select All</strong>
    </label>
  </div>

  <div className="checkbox-row">
    <label>
      <input type="checkbox" checked={ssrsOptions.csv} />
      📄 Export as CSV
    </label>
  </div>

  <div className="checkbox-row">
    <label>
      <input type="checkbox" checked={ssrsOptions.dax} />
      📊 Export as DAX
    </label>
  </div>

  <div className="actions-row">
    <button className="export-btn">
      ✅ Export Selected
    </button>
  </div>
</div>
        
      </div>

      



              <div className="page-actions">
  <button
    className="continue-btn"
    onClick={() => {
      sessionStorage.setItem("exportComplete", "true");
      // start migration timer and navigate
      // Note: startTimer kept for potential future use
      navigate("/migration", { state: { appId: state?.appId, appName } });
    }}
  >
    <img src={migrationImg} alt="migration" /> Continue to Migration
  </button>
</div>
    </div>
  );
}