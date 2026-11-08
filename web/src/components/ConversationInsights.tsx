import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Demo, Score } from "../demo";
import { useMocks } from "../api/client";
import taxonomy from "../../../contracts/taxonomy.json";

export function ConversationInsights({ scores, conversation }: { scores: Score[]; conversation: Demo["conversation"] }) {
  const [turn, setTurn] = useState(scores.length);
  const [view, setView] = useState<"families" | "attention">("families");
  useEffect(() => setTurn(scores.length), [scores.length]);
  const selectedTurn = Math.max(1, Math.min(turn, scores.length));
  const score = scores[selectedTurn - 1];
  if (!score) return null;
  const history = scores.map((value, i) => ({ turn: i + 1, risk: value.risk }));
  const distribution = view === "families"
    ? Object.entries(score.family_probs).sort((a, b) => b[1] - a[1]).map(([id, value]) => ({ label: taxonomy.families.find(f => f.id === id)?.label ?? id.replaceAll("_", " "), value }))
    : score.attention.map((value, i) => ({ label: `Turn ${i + 1} · ${conversation.turns[i]?.sender === "me" ? "you" : "sender"}`, value }));
  return <section className="conversation-insights" aria-labelledby="insights-title">
    <div className="section-heading"><div><p className="eyebrow">A CLOSER LOOK</p><h2 id="insights-title">The story behind the signal.</h2></div><p>{useMocks ? "Scripted forecast fixtures, not evaluation results." : "Forecasts computed on this device."} Only the messages revealed so far appear here.</p></div>
    <div className="insights-grid">
      <section className="zd-panel insight-panel" aria-label="Risk across revealed messages">
        <h3>A conversation in motion.</h3><p>Estimated scam risk as each message adds context.</p>
        <div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><AreaChart data={history} margin={{ top: 20, right: 18, left: -16, bottom: 5 }} accessibilityLayer>
          <defs><linearGradient id="risk-wash" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#719865" stopOpacity={.3} /><stop offset="100%" stopColor="#719865" stopOpacity={.02} /></linearGradient></defs>
          <CartesianGrid stroke="#dce3cf" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="turn" type="number" domain={[1, Math.max(2, scores.length)]} allowDecimals={false} tick={{ fontSize: 10, fill: "#60705c" }} tickLine={false} axisLine={false} tickFormatter={v => `T${v}`} />
          <YAxis domain={[0, 1]} tickFormatter={v => `${Math.round(v * 100)}%`} tick={{ fontSize: 10, fill: "#60705c" }} axisLine={false} tickLine={false} />
          <Tooltip labelFormatter={value => `After turn ${value}`} formatter={value => [`${(Number(value) * 100).toFixed(1)}%`, "Scam risk"]} />
          <Area dataKey="risk" name="Scam risk" type="linear" stroke="#527b4c" strokeWidth={2.5} fill="url(#risk-wash)" dot={{ r: 3, fill: "#527b4c" }} isAnimationActive={false} />
          <ReferenceDot x={selectedTurn} y={score.risk} r={6} fill="#a9503c" stroke="#fffef6" strokeWidth={2} />
        </AreaChart></ResponsiveContainer></div>
        <div className="insight-controls"><label htmlFor="inspect-turn">Inspect a turn</label><input id="inspect-turn" type="range" min={1} max={scores.length} step={1} value={selectedTurn} disabled={scores.length < 2} onChange={event => setTurn(Number(event.target.value))} /><output htmlFor="inspect-turn">{selectedTurn} / {scores.length}</output></div>
        <p className="evidence-note">Turn {selectedTurn}: {(score.risk * 100).toFixed(1)}% risk · {score.confidence_band} confidence · {score.locked ? "trajectory locked" : "observing"}. Next stage: {score.next_stage.stage} ({(score.next_stage.p * 100).toFixed(1)}%).</p>
      </section>
      <section className="zd-panel insight-panel" aria-label="Forecast breakdown">
        <h3>What caught its attention?</h3><p>The model’s view after turn {selectedTurn}.</p>
        <div className="segmented" role="group" aria-label="Forecast breakdown"><button aria-pressed={view === "families"} onClick={() => setView("families")}>Family likelihood</button><button aria-pressed={view === "attention"} onClick={() => setView("attention")}>Message attention</button></div>
        {distribution.map(item => <div className="probability-row" key={item.label}><span>{item.label}</span><div className="probability-track" aria-hidden="true"><span style={{ width: `${item.value * 100}%` }} /></div><output>{(item.value * 100).toFixed(1)}%</output></div>)}
        <p className="evidence-note">{view === "attention" ? "Attention shows which messages influenced this forecast. A high weight is not proof of a scam." : "Probabilities show the model’s competing explanations, including a benign conversation."}</p>
        {score.evidence.map(item => <p key={`${item.turn_idx}-${item.reason}`} className="evidence-note"><strong>Turn {item.turn_idx + 1}:</strong> {item.reason}</p>)}
      </section>
    </div>
  </section>;
}
