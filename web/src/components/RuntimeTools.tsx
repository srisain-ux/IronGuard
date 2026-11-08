import { useState, type FormEvent } from "react";
import { scoreExampleWithApi, useMocks } from "../api/client";
import { scoreLocal } from "../runtime/browser";
import { compareScores } from "../runtime/parity";
import type { ScoreResponse } from "../contracts/score_response";
import example from "../mocks/conversation.pig_butchering.json";
import type { ChloroplastManifest } from "../contracts/chloroplast";
import type { Turn } from "../runtime/embed";

type Comparison = ReturnType<typeof compareScores>;
export function DebugParity() {
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  async function compare() {
    setBusy(true); setComparison(null);
    // The only POST is the bundled public example, regardless of the phone's text.
    const [local, api] = await Promise.allSettled([
      scoreLocal(example.turns as Turn[], [], setStatus), scoreExampleWithApi(),
    ]);
    if (local.status === "fulfilled" && api.status === "fulfilled") {
      const result = compareScores(local.value.at(-1)!, api.value);
      setComparison(result);
      setStatus(useMocks || api.value.model.name === "stub" ? "UNVERIFIED · fixture/stub comparison; real PreyNet parity pending" : result.passed ? "PASS · all probabilities within ±0.02; labels and lock agree" : "FAIL · model probabilities or labels differ");
    } else setStatus(`UNVERIFIED · ${local.status === "rejected" ? "Browser artifacts unavailable. " : ""}${api.status === "fulfilled" ? `API ${api.value.model.name} risk ${api.value.risk.toFixed(4)}. ` : "API unavailable. "}Real PreyNet comparison pending.`);
    setBusy(false);
  }
  return <section className="zd-panel runtime-tools"><h2>Browser / API parity</h2><p>Only the bundled public example thread is sent to the API. Adapters are disabled on both sides. Tolerance: ±0.02.</p><button disabled={busy} onClick={() => void compare()}>Compare public example</button><p role="status">{status}</p>{comparison && <><p>Labels / lock: {comparison.labelsMatch ? "agree" : "differ"}</p><div className="parity-scroll"><table><thead><tr><th>Score</th><th>Browser</th><th>API</th><th>Δ</th></tr></thead><tbody>{comparison.rows.map(row => <tr key={row.field}><th>{row.field}</th><td>{row.browser?.toFixed(4) ?? "--"}</td><td>{row.api?.toFixed(4) ?? "--"}</td><td>{Number.isFinite(row.delta) ? row.delta.toFixed(4) : "--"}</td></tr>)}</tbody></table></div></>}</section>;
}
export function LocalMessage({ manifests }: { manifests: ChloroplastManifest[] }) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState("");
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || !text.trim()) return;
    setBusy(true); setScore(null);
    try { const result = await scoreLocal([{ sender: "them", text }], manifests, setStatus); setScore(result.at(-1)!); setStatus(useMocks ? "Contract fixture · model inference pending" : "Scored on this device"); }
    catch { setStatus("Browser model unavailable. Install A’s exported artifacts, then retry."); }
    finally { setBusy(false); }
  }
  return <section className="zd-panel runtime-tools"><form onSubmit={event => void submit(event)}><label htmlFor="local-message">Message to score locally</label><textarea id="local-message" value={text} onChange={event => setText(event.target.value)} maxLength={1000} rows={3} placeholder="Type a test message" /><button disabled={busy || !text.trim()}>Score on this device</button></form><p role="status">{status}</p>{score && <p>Risk {score.risk.toFixed(4)} · {score.confidence_band.toUpperCase()} · {score.family.label}</p>}<small>Text stays in memory. No API scoring request is made.</small></section>;
}
