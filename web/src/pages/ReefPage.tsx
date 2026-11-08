import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getMetrics, openEvents, submitZeroDay, useMocks, type EvalSummary } from "../api/client";
import type { Event } from "../contracts/event";

const colors: Record<string, string> = { PreyNet: "#e83f8f", B0: "#3fc1c0", B1: "#b9a2cf", B2: "#544ea5", B3: "#83d8d7" };
const pct = (value: number | null | undefined) => typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(0)}%` : "--";
const number = (value: unknown, digits = 0) => typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "--";
const valid = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const field = (data: Event["data"], key: string) => typeof data[key] === "string" ? data[key] as string : "--";
const mask = (value: string) => value.replace(/https?:\/\/\S+|www\.\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:[\w-]+\.)+[A-Za-z]{2,}(?:\/\S*)?|\+?\d[\d ()-]{5,}\d/gi, "[masked]").slice(0, 60);

type LogLine = { id: number; prefix: string; message: string };
type PhotonLine = { id: number; preview: string };

function describe(event: Event): LogLine | null {
  const { data } = event;
  let prefix = "reef";
  let message = "";
  if (event.type === "algae.progress") {
    prefix = data.stage === "critique" ? "critic" : "algae";
    message = `${field(data, "stage")} · ${number(data.done)}/${number(data.total)}`;
  } else if (event.type === "train.progress") {
    prefix = "train";
    message = `step ${number(data.step)}/${number(data.total)} · loss ${number(data.loss, 3)}`;
  } else if (event.type === "chloroplast.ready") {
    message = "chloroplast ready";
  } else if (event.type === "reef.report") {
    message = `anonymous report · ${field(data, "family_guess")}`;
  } else if (event.type === "error") {
    message = "job reported an error";
  } else return null;
  return { id: Date.now() + Math.random(), prefix, message };
}

function EmptyChart({ label }: { label: string }) {
  return <div className="chart-empty">--<small>{label}</small></div>;
}

export default function ReefPage() {
  const [metrics, setMetrics] = useState<EvalSummary | null>(null);
  const [connected, setConnected] = useState(false);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [photon, setPhoton] = useState<PhotonLine[]>([]);
  const [loss, setLoss] = useState<{ step: number; loss: number }[]>([]);
  const [adapter, setAdapter] = useState<Event["data"] | null>(null);
  const [alert, setAlert] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const seenEvents = useRef(new Set<string>());
  const adapterMetrics = adapter?.metrics && typeof adapter.metrics === "object" ? adapter.metrics as Record<string, unknown> : null;

  useEffect(() => {
    let active = true;
    void getMetrics().then(value => { if (active) setMetrics(value); }).catch(() => { if (active) setMetrics(null); });
    const stream = openEvents(event => {
      const eventKey = `${event.type}:${event.ts}:${event.job_id ?? ""}:${JSON.stringify(event.data)}`;
      if (seenEvents.current.has(eventKey)) return;
      if (seenEvents.current.size >= 100) seenEvents.current.clear();
      seenEvents.current.add(eventKey);
      if (event.type === "photon.message") {
        const preview = field(event.data, "preview");
        setPhoton(current => [{ id: Date.now() + Math.random(), preview: mask(preview) }, ...current].slice(0, 12));
      }
      const line = describe(event);
      if (line) setLogs(current => [...current, line].slice(-60));
      if (event.type === "train.progress" && valid(event.data.step) && valid(event.data.loss)) {
        setLoss(current => [...current, { step: event.data.step as number, loss: event.data.loss as number }].slice(-100));
      }
      if (event.type === "chloroplast.ready") setAdapter(event.data);
    }, setConnected);
    return () => { active = false; stream?.close(); };
  }, []);

  async function launch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!alert.trim() || busy) return;
    setBusy(true);
    try {
      const result = await submitZeroDay(alert.trim());
      setJobStatus(result.status === "demo" ? "Demo endpoint: training is not connected." : `Job ${result.job_id} queued.`);
      setAlert("");
    } catch {
      setJobStatus("Alert could not be submitted. Check the API connection.");
    } finally { setBusy(false); }
  }

  const models = metrics?.models ?? {};
  const modelNames = Object.keys(models).filter(name => models[name]?.ewr_at_k?.some(valid));
  const ewrRows = Array.from({ length: Math.max(0, ...modelNames.map(name => models[name].ewr_at_k?.length ?? 0)) }, (_, i) =>
    Object.fromEntries([["k", i + 1], ...modelNames.map(name => [name, valid(models[name].ewr_at_k?.[i]) ? models[name].ewr_at_k?.[i] : null])]));
  const zeroDay = metrics?.zero_day;
  const beforeAfter = [
    { label: "Before", ewr: zeroDay?.base_ewr_at_3 ?? null },
    { label: "After", ewr: zeroDay?.chloroplast_ewr_at_3 ?? null },
  ];
  const samples = zeroDay?.sample_efficiency?.filter(point => valid(point.n) && valid(point.ewr_at_3)) ?? [];
  const reliability = metrics?.reliability;
  const reliabilityRows = (reliability?.conf ?? []).map((conf, i) => ({ conf, acc: reliability?.acc?.[i] ?? null })).filter(point => valid(point.conf) && valid(point.acc));
  const hasZeroDay = beforeAfter.some(point => valid(point.ewr));

  return <div className="page-content reef-layout">
    <section className="reef-heading"><p className="eyebrow">ALGAE REEF LAB // OBSERVATION DECK</p><h1 className="zd-title">WATCH THE <em>MODEL</em> LEARN.</h1><p className="intro">Synthetic conversations feed a small adapter for a new scam pattern. Phones download the adapter without its training data.</p></section>
    <div className="reef-grid">
      <section className="zd-panel terminal reef-wide"><div className="panel-label">ZERO-DAY TERMINAL <small>{useMocks ? "MOCK EVENT FIXTURE" : connected ? "● LIVE EVENT STREAM" : "STREAM OFFLINE / WAITING"}</small></div>
        <form className="reef-command" onSubmit={launch}><label htmlFor="zero-day-alert">&gt; new zero-day alert:</label><input id="zero-day-alert" value={alert} onChange={e => setAlert(e.target.value)} maxLength={400} placeholder="Describe a new scam pattern" /><button disabled={busy || !alert.trim()} type="submit">SEND ALERT</button></form>
        {jobStatus && <p className="reef-status" role="status">{jobStatus}</p>}
        <div className="reef-terminal-log" role="log" aria-label="Algae event log" aria-live="polite">{logs.length ? logs.map(line => <p key={line.id}><span className={`reef-prefix prefix-${line.prefix}`}>[{line.prefix}]</span> {line.message}</p>) : <p className="reef-muted">[reef] Waiting for Algae events. No training job running.</p>}</div>
        <div className="reef-terminal-bottom"><div><span className="reef-kicker">TRAINING LOSS</span>{loss.length > 1 ? <ResponsiveContainer width="100%" height={74}><LineChart data={loss}><Line dataKey="loss" stroke="#5dff9b" strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer> : <span className="reef-value">--</span>}</div><div><span className="reef-kicker">CHLOROPLAST</span><span className="reef-value">{adapter ? "READY" : "--"}</span><small>Size {number(adapter?.size_bytes)} bytes · Train {number(adapterMetrics?.train_seconds, 1)} s · Val recall {pct(valid(adapterMetrics?.val_recall_at_1fpr) ? adapterMetrics.val_recall_at_1fpr : null)}</small></div></div>
      </section>
      <section className="zd-panel photon-panel"><div className="panel-label">PHOTON LIVE FEED <small>MASKED PREVIEWS</small></div><div className="photon-list" role="log" aria-label="Masked Photon messages" aria-live="polite">{photon.length ? photon.map(item => <p key={item.id}><span>↳</span> {item.preview}</p>) : <p className="reef-muted">No Photon messages in this session.</p>}</div></section>
      <section className="zd-panel metric-panel reef-wide"><div className="panel-label">EARLY WARNING RATE <small>EWR@k · 1% FALSE ALARM TARGET</small></div>{ewrRows.length ? <><div className="reef-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={ewrRows} margin={{ top: 18, right: 22, bottom: 4, left: 0 }}><CartesianGrid stroke="#b9a2cf33" /><XAxis dataKey="k" stroke="#b3b6d7" label={{ value: "Turn k", position: "insideBottomRight", offset: -2, fill: "#b3b6d7" }} /><YAxis stroke="#b3b6d7" domain={[0, 1]} tickFormatter={pct} /><Tooltip formatter={value => pct(typeof value === "number" ? value : null)} /><Legend />{modelNames.map(name => <Line key={name} name={name} dataKey={name} stroke={colors[name] ?? "#b9a2cf"} strokeWidth={name === "PreyNet" ? 3 : 2} dot={false} connectNulls={false} isAnimationActive={false} />)}</LineChart></ResponsiveContainer></div><p className="reef-note">Dataset: {metrics?.dataset?.version ?? "--"} · PreyNet: {models.PreyNet?.ewr_at_k?.some(valid) ? "measured" : "--"}{metrics?.available === false ? " · Full evaluation unavailable" : ""}</p></> : <EmptyChart label="No measured EWR@k results." />}</section>
      <section className="zd-panel metric-panel"><div className="panel-label">ZERO-DAY ADAPTATION <small>EWR@3 · BEFORE / AFTER</small></div>{hasZeroDay ? <div className="reef-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={beforeAfter}><CartesianGrid stroke="#b9a2cf33" /><XAxis dataKey="label" stroke="#b3b6d7" /><YAxis stroke="#b3b6d7" domain={[0, 1]} tickFormatter={pct} /><Tooltip formatter={value => pct(typeof value === "number" ? value : null)} /><Bar dataKey="ewr" name="EWR@3" fill="#e83f8f" isAnimationActive={false} /></BarChart></ResponsiveContainer></div> : <EmptyChart label="Before / after evaluation unavailable." />}<p className="reef-note">Time to protection: {number(zeroDay?.time_to_protection_s, 1)} s</p></section>
      <section className="zd-panel metric-panel"><div className="panel-label">SAMPLE EFFICIENCY <small>SYNTHETIC POSITIVES → EWR@3</small></div>{samples.length ? <div className="reef-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={samples}><CartesianGrid stroke="#b9a2cf33" /><XAxis dataKey="n" stroke="#b3b6d7" /><YAxis stroke="#b3b6d7" domain={[0, 1]} tickFormatter={pct} /><Tooltip formatter={value => pct(typeof value === "number" ? value : null)} /><Line dataKey="ewr_at_3" name="EWR@3" stroke="#3fc1c0" strokeWidth={3} isAnimationActive={false} /></LineChart></ResponsiveContainer></div> : <EmptyChart label="Sample efficiency unavailable." />}</section>
      <section className="zd-panel metric-panel reef-wide"><div className="panel-label">RELIABILITY DIAGRAM <small>CONFIDENCE VS. OBSERVED ACCURACY</small></div>{reliabilityRows.length ? <div className="reef-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={reliabilityRows}><CartesianGrid stroke="#b9a2cf33" /><XAxis dataKey="conf" stroke="#b3b6d7" domain={[0, 1]} type="number" tickFormatter={pct} /><YAxis stroke="#b3b6d7" domain={[0, 1]} tickFormatter={pct} /><Tooltip formatter={value => pct(typeof value === "number" ? value : null)} /><Line dataKey="acc" name="Observed accuracy" stroke="#e83f8f" strokeWidth={3} isAnimationActive={false} /></LineChart></ResponsiveContainer></div> : <EmptyChart label="Calibration results unavailable." />}<p className="reef-note">ECE before: {pct(models.PreyNet?.ece_before)} · after: {pct(models.PreyNet?.ece_after)}</p></section>
    </div>
  </div>;
}
