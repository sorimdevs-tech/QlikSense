import { Routes, Route } from "react-router-dom";
import ConnectPage from "../pages/Connect/ConnectPage";
import AppsPage from "../Apps/AppsPage";
import ExportPage from "../Export/ExportPage";
import MultiMigrationPage from "../MultiMigration/MultiMigrationPage";
import LoadScriptConverterPage from "../LoadScriptConverter/LoadScriptConverterPage";
// import MigrationPage from "../Migration/MigrationPage"; // Commented out - now going directly to Publish
import PublishPage from "../Publish/PublishPage";
import SummaryPage from "../Summary/SummaryPage";
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ConnectPage />} />
      <Route path="/connect" element={<ConnectPage />} />
      <Route path="/apps" element={<AppsPage />} />
      <Route path="/summary" element={<SummaryPage /> } />
      <Route path="/export" element={<ExportPage />} />
      <Route path="/multi-migrate" element={<MultiMigrationPage />} />
      <Route path="/loadscript-converter" element={<LoadScriptConverterPage />} />
      {/* <Route path="/migration" element={<MigrationPage />} /> */}
      <Route path="/publish" element={<PublishPage />} />
    </Routes>
  );
}


