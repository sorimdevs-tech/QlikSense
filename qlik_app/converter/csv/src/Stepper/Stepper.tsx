import "./Stepper.css";
import { useNavigate, useLocation } from "react-router-dom";

const steps = [
  { id: 1, label: "Connect", sub: "Connect to Qlik Cloud", icon: "🔗", path: "/" },

  { id: 2, label: "Discovery", sub: "Apps & Metadata", icon: "🔍", path: "/apps" },

  { id: 3, label: "Summary", sub: "Assessment", icon: "📋", path: "/summary" },

  { id: 4, label: "Export", sub: "Build & Convert", icon: "⚡", path: "/csv" },

  { id: 5, label: "Migration", sub: "Migration Results", icon: "📊", path: "/export" }
];

export default function Stepper() {
  const navigate = useNavigate();
  const location = useLocation();

  const getActive = () => {
    const url = location.pathname;

    if (url.includes("/apps")) return 2;
    if (url.includes("/summary")) return 3;
    if (url.includes("/export")) return 4;
    if (url.includes("/Migration")) return 5;

    return 1;
  };

  const activeStep = getActive();

  return (
    <div className="stepper">
      {steps.map((step) => (
        <div
          key={step.id}
          className="step"
          onClick={() => navigate(step.path)}
        >
          <div className={`circle ${activeStep === step.id ? "active" : ""}`}>
            {step.icon}
          </div>

          <div className="step-text">
            <div className="title">{step.label}</div>
            <div className="sub">{step.sub}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
