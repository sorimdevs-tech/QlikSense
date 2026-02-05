import "./Header.css";
import logo from "../../assets/logo.png";

export default function Header() {
  return (
    <header className="header">
      <div className="header-left">
        <h1 className="qlik-title">
  Qlik <span className="AI">AI</span>
  <span className="tagline"> – Transform Your QlikSense Data with AI</span>
</h1>
   {/* <img src={logo} alt="Qlik Logo" className="qlik-logo" /> */}
      </div>

      <div className="header-right">
        <a href="#">Docs</a>
        <a href="#">Support</a>
        <div className="profile">👤</div>
      </div>
    </header>
  );
}
