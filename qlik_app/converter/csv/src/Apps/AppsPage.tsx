
import "./AppsPage.css";
import { useEffect, useState } from "react";
import { fetchApps, fetchTables } from "../api/qlikApi";
import { useNavigate } from "react-router-dom";

interface App {
  id: string;
  name: string;
}

export default function AppsPage() {
  const [apps, setApps] = useState<App[]>([]);
  const [tableCount, setTableCount] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [favourites, setFavourites] = useState<string[]>([]);

  const nav = useNavigate();

  useEffect(() => {
    // 🔑 Get tenant URL saved during login
    const tenantUrl = localStorage.getItem("tenant_url");

    if (!tenantUrl) {
      alert("Tenant URL missing. Please login again.");
      nav("/");
      return;
    }

    fetchApps(tenantUrl)
      .then(async (appList) => {
        setApps(appList);

        const counts: Record<string, number> = {};

        for (const app of appList) {
          try {
            const tables = await fetchTables(app.id);
            counts[app.id] = tables.length;
          } catch {
            counts[app.id] = 0;
          }
        }

        setTableCount(counts);
      })
      .catch(() => {
        alert("Backend not connected");
      })
      .finally(() => setLoading(false));
  }, [nav]);

  const toggleFav = (id: string) => {
    setFavourites((prev) =>
      prev.includes(id)
        ? prev.filter((i) => i !== id)
        : [...prev, id]
    );
  };

  const openSummary = (appId: string) => {
    nav("/summary", { state: { appId } });
  };

  if (loading) {
    return <div className="wrap">Loading apps…</div>;
  }

  return (
    <div className="wrap">
      {/* HEADER */}
      <div className="qlik-header">
        <div className="qlik-header-left">
          Applications to explore
        </div>

        <div className="qlik-header-right">
          View all
        </div>
      </div>

      {/* APP CARDS */}
      <div className="card-container">
        {apps.map((app) => (
          <div
            key={app.id}
            className="app-card"
            onClick={() => openSummary(app.id)}
          >
            {/* IMAGE */}
            <div className="card-center">
              <img
                src="/qlik-chart.png"
                className="qlik-img"
                alt="qlik"
              />
            </div>

            {/* FOOTER */}
            <div className="card-footer">
              <span className="app-label">
                {app.name}
              </span>

              <div className="right-actions">
                {/* TABLE COUNT */}
                <span className="badge">
                  {tableCount[app.id] ?? 0}
                </span>

                {/* FAVORITE */}
                <span
                  className="fav-icon"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFav(app.id);
                  }}
                >
                  {favourites.includes(app.id) ? "★" : "☆"}
                </span>

                {/* MENU */}
                <span className="dot-menu">⋯</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
