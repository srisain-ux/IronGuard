import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getMetrics, type EvalSummary } from "../api/client";

export default function ReefPage() {
  const [metrics, setMetrics] = useState<EvalSummary | null>(null);
  useEffect(() => { void getMetrics().then(setMetrics).catch(() => setMetrics(null)); }, []);
  const preynet = metrics?.models?.PreyNet;
  const baseline = metrics?.models?.B0;
  const rows = preynet?.ewr_at_k?.map((value, index) => ({ turn: index + 1, PreyNet: value, B0: baseline?.ewr_at_k?.[index] })) || [];
  return <div className="page-content reef-layout">
    <section className="reef-heading"><p className="eyebrow">ALGAE REEF LAB // OBSERVATION DECK</p><h1 className="zd-title">WATCH THE <em>MODEL</em> LEARN.</h1><p className="intro">Synthetic conversations feed a small adapter for a new scam pattern. Phones download the new adapter without its training data.</p></section>
    <div className="reef-grid">
      <section className="zd-panel terminal"><div className="panel-label"><span>●</span> ZERO-DAY TERMINAL <small>AWAITING ALERT</small></div><div className="terminal-content"><p><span>&gt;</span> new zero-day alert: <i>_</i></p><div className="terminal-empty">No training job running.<br />When a new pattern appears, Algae plans, generates, critiques, and trains here.</div></div></section>
      <section className="zd-panel metric-panel"><div className="panel-label">EARLY WARNING RATE <small>1% FALSE ALARM TARGET</small></div>{rows.length ? <ResponsiveContainer width="100%" height={250}><LineChart data={rows}><XAxis dataKey="turn" stroke="#b3b6d7" /><YAxis stroke="#b3b6d7" domain={[0, 1]} /><Tooltip /><Line dataKey="PreyNet" stroke="#e83f8f" strokeWidth={3} dot={false} /><Line dataKey="B0" stroke="#3fc1c0" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer> : <div className="chart-empty">--<small>Run make eval to populate measured results.</small></div>}</section>
      <section className="zd-panel stat-panel"><div className="panel-label">LEAD TIME <small>TURNS BEFORE STRIKE</small></div><strong>{preynet?.lead_time?.toFixed(1) ?? "--"}</strong><p>Mean warning lead time. The number appears only after evaluation.</p></section>
      <section className="zd-panel stat-panel"><div className="panel-label">CHLOROPLAST VITALITY <small>ADAPTER FEED</small></div><strong>--</strong><p>Waiting for the first validated adapter manifest.</p></section>
    </div>
  </div>;
}
