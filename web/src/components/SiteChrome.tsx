import { useEffect } from "react";
import { NavLink } from "react-router-dom";
import { useMocks } from "../api/client";

export function SiteHeader({ page }: { page: "phone" | "reef" }) {
  useEffect(() => {
    document.title = `Reef Guard · ${page === "phone" ? "Your quiet lookout" : "Reef Lab"}`;
  }, [page]);
  return <header className="site-header">
    <NavLink to="/phone" className="wordmark" aria-label="Reef Guard home">
      <img src="/botanical/reef-guard-logo.png" width="2000" height="667" alt="Reef Guard" />
    </NavLink>
    <nav className="site-nav" aria-label="Main navigation">
      <NavLink to="/phone"><span aria-hidden="true">◉</span> Phone</NavLink>
      <NavLink to="/reef"><span aria-hidden="true">❧</span> Reef Lab</NavLink>
    </nav>
    <span className="header-status"><i />{useMocks ? "Local demo" : "On-device protection"}</span>
  </header>;
}

export function BotanicalScene({ reef = false }: { reef?: boolean }) {
  return <div className={`botanical-scene ${reef ? "sea-scene" : "pond-scene"}`} aria-hidden="true">
    <img className="scene-texture" src={`/botanical/${reef ? "reef" : "pond"}-texture.svg`} alt="" />
    <img className="scene-flora" src={`/botanical/${reef ? "reef" : "pond"}-flora.webp`} alt="" />
  </div>;
}

export function SiteFooter() {
  return <footer className="site-footer">
    <span><span aria-hidden="true">❧</span> Small signals. Thoughtful protection.</span>
    <span>Reef Guard <span aria-hidden="true">·</span> HackUTD 2026</span>
  </footer>;
}
