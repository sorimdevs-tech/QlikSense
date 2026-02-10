import "./MigrationPage.css";
import { useLocation } from "react-router-dom";
import { useEffect, useState } from "react";

export default function MigrationPage() {
  const [pageLoadTime, setPageLoadTime] = useState<string | null>(null);
  const { state } = useLocation() as any;
  const appName = state?.appName || sessionStorage.getItem("appName") || "Unknown";

  const formatElapsed = (msTotal: number) => {
    const minutes = Math.floor(msTotal / 60000);
    const seconds = Math.floor((msTotal % 60000) / 1000);
    const centis = Math.floor((msTotal % 1000) / 10);
    const pad = (n: number, width = 2) => String(n).padStart(width, "0");
    return `${pad(minutes)}m : ${pad(seconds)}s : ${pad(centis)}ms`;
  };

  useEffect(() => {
    const pageStartTime = Date.now();
    
    // Wait a tick to let the page render before measuring
    const timer = setTimeout(() => {
      const elapsed = Date.now() - pageStartTime;
      setPageLoadTime(formatElapsed(elapsed));
    }, 50);
    
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="wrap">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h2>Migration</h2>
        {pageLoadTime && (
          <div className="timer-badge">Analysis Loading Time: {pageLoadTime}</div>
        )}
      </div>

      <p>Application: <strong>{appName}</strong></p>

      <div style={{ marginTop: 12 }}>
        <p>Migration results and progress will appear here once migration is executed.</p>
        <p>✅ Export flags: CSV: {sessionStorage.getItem("exportCSV") || "false"}, DAX: {sessionStorage.getItem("exportDAX") || "false"}</p>
      </div>
    </div>
  );
}
