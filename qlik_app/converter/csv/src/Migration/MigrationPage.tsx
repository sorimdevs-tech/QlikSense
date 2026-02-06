import "./MigrationPage.css";
import { useLocation } from "react-router-dom";
import { useWizard } from "../context/WizardContext";

export default function MigrationPage() {
  const { state } = useLocation() as any;
  const appName = state?.appName || sessionStorage.getItem("appName") || "Unknown";
  const { getLastElapsed } = useWizard();

  return (
    <div className="wrap">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h2>Migration</h2>
        {getLastElapsed?.("/migration") && (
          <div className="analysis-badge">AnalysisTime - {getLastElapsed!("/migration")}</div>
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
