

import "./ConnectPage.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { validateLogin } from "../../pages/LoginPage/authApi";


export default function ConnectPage() {
  const [url, setUrl] = useState("");
  const [connectAsUser, setConnectAsUser] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const validateUrl = (input: string) => {
    try {
      const parsed = new URL(input);
      return parsed.hostname.endsWith("qlikcloud.com");
    } catch {
      return false;
    }
  };

  const handleConnect = async () => {
    if (!validateUrl(url)) {
      setError(
        "Please enter a valid Qlik Sense Cloud URL (e.g., https://your-tenant.qlikcloud.com)"
      );
      return;
    }

    if (!connectAsUser) {
      setError("Please select 'Connect as test User' to continue.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await validateLogin(
        url,
        true,
        "ponnuchamy.vellaikannu@sorimtechnologies.com",
        "qlikCloud000"
      );

      localStorage.setItem("tenant_url", url);
      navigate("/apps");
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          "Connection failed. Please check your credentials and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const isValidUrl = validateUrl(url);

  return (
    <div className="connect-wrapper">
      <div className="connect-card">
        {/* <div className="card-header">
          <div className="icon">
            <img className="qlikimg" src={qlikImg} alt="Qlik Icon" />
          </div>
          <div>
            <h2>Connect to Qlik Sense</h2>
          </div>
        </div> */}

        <label htmlFor="qlik-url">Enter your QlikSense Cloud URL</label>
        <input
          id="qlik-url"
          type="text"
          placeholder="https://your-tenant.qlikcloud.com"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setError("");
          }}
          className={url && !isValidUrl ? "invalid" : ""}
          disabled={loading}
        />

        {url && !isValidUrl && (
          <p className="error">
            ⚠️ Please enter a valid Qlik Sense Cloud URL ending with
            .qlikcloud.com
          </p>
        )}

        <label className="checkbox">
          <input
            type="checkbox"
            checked={connectAsUser}
            onChange={(e) => {
              setConnectAsUser(e.target.checked);
              setError("");
            }}
            disabled={loading}
          />
          <span>Connect as test User</span>
        </label>

        {error && (
          <div className="error">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "18px" }}>⚠️</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        <div className="actions">
          <button
            onClick={handleConnect}
            disabled={!isValidUrl || loading}
            style={{
              opacity: isValidUrl ? 1 : 0.5,
              cursor: isValidUrl ? "pointer" : "not-allowed",
            }}
          >
            {loading ? "Connecting..." : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
