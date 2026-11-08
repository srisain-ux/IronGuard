import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import PhonePage from "./pages/PhonePage";
import ReefPage from "./pages/ReefPage";
import "./theme/zero-day.css";
import "./style.css";

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell zd-scanlines">
        <div className="cityline" aria-hidden="true" />
        <div className="zd-grid-floor" aria-hidden="true" />
        <header className="site-header">
          <NavLink className="wordmark zd-neon-sign zd-flicker" to="/phone" aria-label="OdonataGuard home">ODONATAGUARD</NavLink>
          <nav aria-label="Main navigation">
            <NavLink to="/phone">PHONE</NavLink>
            <NavLink to="/reef">REEF LAB</NavLink>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/phone" replace />} />
            <Route path="/phone" element={<PhonePage />} />
            <Route path="/reef" element={<ReefPage />} />
          </Routes>
        </main>
        <footer>ODONATAGUARD // ZERO DAY 2026 <span>PRIVACY BY DESIGN · ON DEVICE FORECAST</span></footer>
      </div>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
