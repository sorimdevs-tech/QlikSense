import "./Header.css";
import qlikaiLogo from "../../assets/qlikai.png";

export default function Header() {
  return (
    <header className="header">
      <div className="logo-section">
        <img
          src={qlikaiLogo}
          alt="QlikAI Logo"
          className="logo-image"
        />
        <div className="logo-description">
          <p className="logo-subtitle">
            QlikAI is an AI-powered analytics acceleration platform designed to transform how enterprises consume, understand, and act on QlikSense data. By leveraging advanced AI/LLM capabilities, QlikAI automatically summarizes complex dashboards, generates contextual insights, and enables seamless export of analytics into downstream platforms such as Power BI—reducing manual effort and accelerating decision-making.
          </p>
        </div>
      </div>

      <div className="header-right">
        <a href="#">Docs</a>
        <a href="#">Support</a>
        <div className="profile">👤</div>
      </div>
    </header>
  );
}
