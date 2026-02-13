import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./PublishPage.css";

// Stepper Component
interface StepperProps {
  currentStep: number;
  steps: string[];
}

function Stepper({ currentStep, steps }: StepperProps) {
  return (
    <div className="stepper-container">
      <div className="stepper">
        {steps.map((step, idx) => (
          <div key={idx} className="step">
            <div
              className={`step-circle ${
                idx < currentStep
                  ? "completed"
                  : idx === currentStep
                  ? "active"
                  : ""
              }`}
            >
              {idx < currentStep ? "✓" : idx + 1}
            </div>
            <div
              className={`step-label ${
                idx < currentStep
                  ? "completed"
                  : idx === currentStep
                  ? "active"
                  : ""
              }`}
            >
              {step}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const STEPPER_STEPS = [
  "Prepare Data",
  "Authenticate",
  "Publish Dataset",
  "Generate URL",
  "Publish",
];

export default function PublishPage() {
  const navigate = useNavigate();

  // Get data from sessionStorage
  const tableName = sessionStorage.getItem("migration_selected_table") || "";
  const appName = sessionStorage.getItem("migration_appName") || sessionStorage.getItem("appName") || "Unknown";
  const hasCSV = sessionStorage.getItem("migration_has_csv") === "true";
  const hasDAX = sessionStorage.getItem("migration_has_dax") === "true";
  const rowCount = Number(sessionStorage.getItem("migration_row_count") || "0");
  const columns = JSON.parse(sessionStorage.getItem("migration_columns") || "[]");

  const [customTableName, setCustomTableName] = useState(tableName);
  const [datasetURL, setDatasetURL] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [statusBoxes, setStatusBoxes] = useState({ columns: false, powerbi: false, finished: false });
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>("");

  const handlePublish = async () => {
    try {
      setPublishing(true);
      setError("");
      setCurrentStep(0);

      // Step 1: Prepare data
      setCurrentStep(0);
      console.log("📦 Step 1: Preparing data...");
      const csvText = sessionStorage.getItem("migration_csv") || "";
      const daxText = sessionStorage.getItem("migration_dax") || "";

      if (!hasCSV && !hasDAX) {
        throw new Error("No formats selected. Please go back to Export page.");
      }

      // Step 2: Initiate authentication (Device Code Flow)
      setCurrentStep(1);
      setStatusBoxes({ columns: true, powerbi: false, finished: false });
      console.log("🔐 Step 2: Initiating Power BI authentication...");
      
      // const authRes = await fetch("http://localhost:8000/powerbi/login/acquire-token", {
      const authRes = await fetch("https://qlik-sense-cloud.onrender.com/powerbi/login/acquire-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!authRes.ok) {
        const errData = await authRes.json();
        throw new Error(errData?.detail || "Authentication initiation failed");
      }

      const authData = await authRes.json();
      console.log("✅ Device code generated. User needs to authenticate.");
      console.log("Instructions:", authData?.message || "Check backend logs");

      // Step 3: Wait for user to complete authentication (up to 30 seconds)
      let authAttempts = 0;
      const maxAttempts = 30; // 30 seconds total
      let isAuthenticated = false;

      while (authAttempts < maxAttempts && !isAuthenticated) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second between checks

        try {
          const statusRes = await fetch("https://qlik-sense-cloud.onrender.com/powerbi/login/status", {
            method: "POST",
          });
          const statusData = await statusRes.json();

          if (statusData.logged_in) {
            console.log("✅ Authentication successful!");
            isAuthenticated = true;
            break;
          }
        } catch (e) {
          console.warn("⚠️ Error checking auth status:", e);
        }

        authAttempts++;
        if (authAttempts % 5 === 0) {
          console.log(`⏳ Still waiting for authentication... (${authAttempts}s elapsed)`);
        }
      }

      if (!isAuthenticated) {
        throw new Error("Authentication timeout. Please login at microsoft.com/devicelogin and try again.");
      }

      // Step 4: Publish dataset
      setCurrentStep(2);
      setStatusBoxes({ columns: true, powerbi: true, finished: false });
      console.log("📤 Step 3: Publishing to Power BI...");

      const form = new FormData();
      if (hasCSV && csvText) {
        form.append("csv_file", new Blob([csvText], { type: "text/csv" }), `${customTableName}.csv`);
      }
      if (hasDAX && daxText) {
        form.append("dax_file", new Blob([daxText], { type: "text/plain" }), `${customTableName}.dax`);
      }
      form.append("meta_app_name", appName);
      form.append("meta_table", customTableName);
      form.append("has_csv", hasCSV ? "true" : "false");
      form.append("has_dax", hasDAX ? "true" : "false");

      const res = await fetch("https://qlik-sense-cloud.onrender.com/powerbi/process", {
        method: "POST",
        body: form,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.detail || "Publishing failed");
      }

      // Step 5: Generate URL
      setCurrentStep(3);
      console.log("🔗 Step 4: Generating dataset URL...");
      
      const realDatasetURL = data?.dataset?.urls?.dataset || 
                            data?.dataset?.urls?.report ||
                            (data?.dataset?.id ? `https://app.powerbi.com/groups/${data.dataset.workspace_id}/datasets/${data.dataset.id}` : "");
      
      if (!realDatasetURL) {
        throw new Error("No dataset URL returned from Power BI. Please check backend response.");
      }

      setDatasetURL(realDatasetURL);

      setStatusBoxes({ columns: true, powerbi: true, finished: true });
      setResult(data);
      console.log("✅ Dataset published successfully!");
      console.log("📎 Dataset URL:", realDatasetURL);
      console.log("🏢 Workspace ID:", data?.dataset?.workspace_id);
      console.log("📊 Dataset ID:", data?.dataset?.id);

    } catch (err: any) {
      console.error("❌ Publishing error:", err);
      setError(err.message || "Failed to publish");
      setStatusBoxes({ columns: false, powerbi: false, finished: false });
    } finally {
      setPublishing(false);
    }
  };

  const downloadPDF = () => {
    try {
      // Create PDF content from table data
      const pdfContent = `
POWER BI DATASET REPORT
====================

Application: ${appName}
Dataset Name: ${customTableName}
Generated Date: ${new Date().toLocaleString()}

Dataset Details:
- Total Rows: ${rowCount}
- Total Columns: ${columns.length}
- Export Format: ${hasCSV ? "CSV" : ""} ${hasDAX ? "DAX" : ""}

Columns:
${columns.map((col: string, idx: number) => `${idx + 1}. ${col}`).join("\n")}

Power BI URL: ${datasetURL}

Status:
- CSV Processed: ${hasCSV ? "✓" : "✗"}
- DAX Processed: ${hasDAX ? "✓" : "✗"}
- Dataset Published: ${result ? "✓" : "✗"}

This report was generated from Qlik to Power BI migration tool.
`;

      // Create blob and download
      const blob = new Blob([pdfContent], { type: "text/plain" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${customTableName}_Report_${new Date().getTime()}.txt`;
      link.click();
      URL.revokeObjectURL(link.href);

      console.log("📥 PDF downloaded successfully!");
    } catch (err) {
      console.error("❌ PDF download failed:", err);
      setError("Failed to download PDF");
    }
  };

  const openInPowerBI = () => {
    if (datasetURL) {
      window.open(datasetURL, "_blank");
    }
  };

  return (
    <div className="publish-container">
      <h2 className="publish-header">📤 Publish to Power BI</h2>

      {/* STEPPER */}
      {publishing && (
        <Stepper currentStep={currentStep} steps={STEPPER_STEPS} />
      )}

      {/* ERROR ALERT */}
      {error && !publishing && (
        <div className="error-alert">
          <div className="error-alert-title">❌ {error}</div>
          <div className="error-alert-tip">
            💡 Tip: Make sure you complete the authentication at microsoft.com/devicelogin before publishing
          </div>
        </div>
      )}

      {/* FORM SECTION */}
      {!result && (
        <div className="form-section">
          <div className="form-group">
            <label className="form-label">📋 Custom Table Name</label>
            <input
              type="text"
              value={customTableName}
              onChange={(e) => setCustomTableName(e.target.value)}
              placeholder="Enter table name"
              disabled={publishing}
              className="form-input"
            />
          </div>

          {/* STATUS BOXES */}
          <div className="status-boxes">
            {/* CSV Status */}
            <div className={`status-box ${statusBoxes.columns ? "active" : ""}`}>
              <div className="status-box-icon">📊</div>
              <div className="status-box-label">CSV Data</div>
              <div className="status-box-status">
                {statusBoxes.columns ? "✅ Prepared" : "⏳ Pending"}
              </div>
            </div>

            {/* Power BI Auth Status */}
            <div className={`status-box ${statusBoxes.powerbi ? "active" : ""}`}>
              <div className="status-box-icon">⚡</div>
              <div className="status-box-label">Power BI Auth</div>
              <div className="status-box-status">
                {statusBoxes.powerbi ? "✅ Authenticated" : "⏳ Pending"}
              </div>
            </div>

            {/* URL Status */}
            <div className={`status-box ${statusBoxes.finished ? "active" : ""}`}>
              <div className="status-box-icon">🔗</div>
              <div className="status-box-label">Dataset URL</div>
              <div className="status-box-status">
                {statusBoxes.finished ? "✅ Generated" : "⏳ Pending"}
              </div>
            </div>
          </div>

          {/* PUBLISH BUTTON */}
          <button
            onClick={handlePublish}
            disabled={publishing}
            className="btn btn-primary"
          >
            {publishing ? "⏳ Publishing..." : "🚀 Publish Now"}
          </button>

          {/* Authentication Instructions */}
          {publishing && (
            <div className="instruction-box">
              <div className="instruction-title">🔐 Authentication Required</div>
              <div className="instruction-line">1️⃣ A device code has been generated</div>
              <div className="instruction-line">2️⃣ Go to: <strong>https://microsoft.com/devicelogin</strong></div>
              <div className="instruction-line">3️⃣ Enter the code shown in the console</div>
              <div className="instruction-line">4️⃣ Wait for this page to complete...</div>
            </div>
          )}
        </div>
      )}

      {/* Publishing Progress */}
      {publishing && (
        <div className="progress-section">
          <div className="progress-title">📊 Publishing Progress...</div>
          <div className="progress-bars">
            <div className={`progress-bar ${statusBoxes.columns ? "active" : ""}`} />
            <div className={`progress-bar ${statusBoxes.powerbi ? "active" : ""}`} />
            <div className={`progress-bar ${statusBoxes.finished ? "active" : ""}`} />
          </div>
        </div>
      )}

      {/* SUCCESS SECTION */}
      {result && (
        <div className="success-section">
          <div className="success-title">✨ Success!</div>
          <div className="success-message">
            Dataset "{customTableName}" published to Power BI Cloud
          </div>

          {/* URL BOX - TURNS GREEN AFTER GENERATION */}
          <div className="url-box">
            <div className="url-label">🔗 Dataset URL (GREEN - Ready)</div>
            <input
              type="text"
              value={datasetURL}
              readOnly
              className="url-input"
            />
            <div className="url-note">
              ✓ This URL is ready to use. Click "Open in Power BI" to view your dataset.
            </div>
          </div>

          {/* INFO BOXES */}
          <div className="info-boxes">
            <div className="info-box">
              <div className="info-box-label">Total Rows</div>
              <div className="info-box-value">{rowCount}</div>
            </div>
            <div className="info-box">
              <div className="info-box-label">Total Columns</div>
              <div className="info-box-value">{columns.length}</div>
            </div>
            <div className="info-box">
              <div className="info-box-label">Status</div>
              <div className="info-box-value">✅ Published</div>
            </div>
          </div>

          {/* ACTION BUTTONS */}
          <div className="btn-group">
            <button
              onClick={openInPowerBI}
              className="btn btn-small btn-success"
            >
              ☁️ Open in Power BI
            </button>
            <button
              onClick={downloadPDF}
              className="btn btn-small btn-warning"
            >
              📥 Download Report
            </button>
          </div>

          {/* COMPLETION MESSAGE */}
          <div className="completion-message">
            🎉 Your dataset is now live in Power BI! You can start creating reports and dashboards with your data.
          </div>
        </div>
      )}

      {/* BACK BUTTON */}
      <div className="publish-footer">
        <button
          onClick={() => navigate("/")}
          className="btn btn-secondary"
        >
          ← Back to Connect
        </button>
      </div>
    </div>
  );
}
