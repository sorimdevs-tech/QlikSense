import { Routes, Route } from "react-router-dom";
import ConnectPage from "../pages/Connect/ConnectPage";
import AppsPage from "../Apps/AppsPage";
import SummaryPage from "../Summary/SummaryPage";
import ExportPage from "../Export/ExportPage";
import MigrationPage from "../Migration/MigrationPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ConnectPage />} />
      <Route path="/apps" element={<AppsPage />} />
      <Route path="/summary" element={<SummaryPage />} />
      <Route path="/export" element={<ExportPage />} />
      <Route path="/migration" element={<MigrationPage />} />
    </Routes>
  );
}
