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
          <p className="logo-text">QlikAI</p>
          <p className="logo-subtitle">QlikAI is an AI-powered analytics acceleration platform designed to transform how enterprises consume, understand, and act on QlikSense data.</p>
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
