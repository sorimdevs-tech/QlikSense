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
      </div>

      <div className="header-right">
        <a href="#">Docs</a>
        <a href="#">Support</a>
        <div className="profile">👤</div>
      </div>
    </header>
  );
}
