import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Phone } from "./phone";
import ReefPage from "./pages/ReefPage";
import { BotanicalScene, SiteHeader, SiteFooter } from "./components/SiteChrome";
import "./theme/zero-day.css";
import "./style.css";
import "./reef.css";

function ReefRoute() {
  return (
    <main className="app-shell reef-shell">
      <BotanicalScene reef />
      <a className="skip" href="#reef-content">Skip to Reef Lab</a>
      <SiteHeader page="reef" />
      <ReefPage />
      <SiteFooter />
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
