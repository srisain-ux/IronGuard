import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { Phone } from "./phone";
import ReefPage from "./pages/ReefPage";
import "./theme/zero-day.css";
import "./style.css";
import "./reef.css";

function ReefRoute() {
  return (
    <main className="app-shell zd-scanlines reef-shell">
      <div className="zd-grid-floor" aria-hidden="true" />
      <header className="site-header">
        <Link
          to="/phone"
          className="wordmark zd-neon-sign"
          aria-label="IronGuard home"
        >
          IRONGUARD
        </Link>
        <nav aria-label="Main navigation">
          <Link className="reef-nav" to="/phone">
            PHONE
          </Link>
          <Link className="reef-nav" to="/reef" aria-current="page">
            REEF LAB
          </Link>
        </nav>
      </header>
      <ReefPage />
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/phone" element={<Phone />} />
        <Route path="/reef" element={<ReefRoute />} />
        <Route path="*" element={<Navigate to="/phone" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
