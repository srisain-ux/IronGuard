import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Phone } from "./phone";
import "./theme/zero-day.css";
import "./style.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/phone" element={<Phone />} />
        <Route path="*" element={<Navigate to="/phone" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
