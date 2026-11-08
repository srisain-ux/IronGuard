import { useEffect, useRef, useState, type FormEvent } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getChloroplasts, openEvents, submitZeroDay, useMocks } from "../api/client";
import { compileChloroplast } from "../runtime/chloroplast";
import type { Event } from "../contracts/event";
import { EvaluationDashboard } from "../components/EvaluationDashboard";

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

export default function ReefPage() {
  const [connected, setConnected] = useState(false);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [photon, setPhoton] = useState<PhotonLine[]>([]);
  const [loss, setLoss] = useState<{ step: number; loss: number }[]>([]);
  const [adapter, setAdapter] = useState<Event["data"] | null>(null);
  const [alert, setAlert] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [pipeline, setPipeline] = useState<"idle" | "queued" | "examples" | "training" | "downloading" | "ready" | "error">("idle");
  const activeJob = useRef<string | null>(null);
  const submitting = useRef(false);
  const pendingEvents = useRef<Event[]>([]);
  async function jobEvent(event: Event) {
    if (!activeJob.current || event.job_id !== activeJob.current) return;
    if (event.type === "algae.progress") setPipeline("examples");
    if (event.type === "train.progress") setPipeline("training");
    if (event.type === "error") {
      setPipeline("error");
      setJobStatus("Job failed. No chloroplast was absorbed."); setBusy(false); activeJob.current = null;
    } else if (event.type === "chloroplast.ready") {
      const job = activeJob.current;
      setPipeline("downloading");
      try {
        const manifests = await getChloroplasts();
        const manifest = manifests.find(item => item.id === event.data.id);
        if (!manifest) throw new Error("Published adapter unavailable");
        compileChloroplast(manifest);
        if (activeJob.current !== job) return;
        setPipeline("ready");
        setAdapter({ id: manifest.id, size_bytes: manifest.size_bytes, metrics: manifest.metrics });
        setJobStatus(`CHLOROPLAST ABSORBED · ${manifest.size_bytes} bytes · ${manifest.metrics.train_seconds.toFixed(1)} s`);
      } catch { if (activeJob.current === job) { setPipeline("error"); setJobStatus("Adapter announced, but download or validation failed. No absorption confirmed."); } }
      if (activeJob.current === job) { setBusy(false); activeJob.current = null; }
    }
  }
  const seenEvents = useRef(new Set<string>());
  const adapterMetrics = adapter?.metrics && typeof adapter.metrics === "object" ? adapter.metrics as Record<string, unknown> : null;

  useEffect(() => {
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
      if (submitting.current) pendingEvents.current = [...pendingEvents.current, event].slice(-100);
      else void jobEvent(event);
      if (event.type === "train.progress" && (!activeJob.current || event.job_id === activeJob.current) && valid(event.data.step) && valid(event.data.loss)) {
        setLoss(current => [...current, { step: event.data.step as number, loss: event.data.loss as number }].slice(-100));
      }

    }, setConnected);
    return () => { stream?.close(); };
  }, []);

  async function launch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!alert.trim() || busy) return;
    if (!useMocks && !connected) { setJobStatus("Wait for the event stream to connect, then retry."); return; }
    setPipeline("queued");
    setBusy(true); setLoss([]); setAdapter(null); setJobStatus("Submitting alert…");
    submitting.current = true; pendingEvents.current = [];
    try {
      const result = await submitZeroDay(alert.trim());
      activeJob.current = result.status === "queued" ? result.job_id : null;
      submitting.current = false;
      setJobStatus(result.status === "demo" ? "Demo endpoint: training is not connected. No adapter trained." : `Job ${result.job_id} queued.`);
      if (result.status === "demo") { setBusy(false); setPipeline("idle"); }
      else for (const buffered of pendingEvents.current) void jobEvent(buffered);
      pendingEvents.current = [];
      setAlert("");
    } catch {
      setPipeline("error");
      setJobStatus("Alert could not be submitted. Check the API connection."); setBusy(false);
      activeJob.current = null;
    } finally { submitting.current = false; }
  }

  const stageIndex = pipeline === "ready" ? 3 : pipeline === "downloading" ? 2 : pipeline === "training" ? 1 : 0;

  return <div className="reef-layout" id="reef-content">
    <section className="page-intro reef-intro" aria-labelledby="reef-title">
      <div><p className="eyebrow"><span className="tiny-line" /> A LIVING LAYER OF PROTECTION</p><h1 id="reef-title">A little wiser.<br /><em>With every leaf.</em></h1><p>New scam patterns become small, downloadable protections.<br className="desktop-break" /> No private conversations needed.</p></div>
      <figure className="field-illustration"><img src="/botanical/leaf-sheep.webp" width="270" height="270" alt="A watercolor leaf sheep with pink-tipped green leaves" /><figcaption><span>02 / THE LEAF SHEEP</span>Keep the protection. Leave the rest.</figcaption></figure>
    </section>
    <div className="lab-content">
      <div className="workbench">
        <section className="pattern-book" aria-labelledby="pattern-title">
          <p className="eyebrow">A NEW PATTERN TO LEARN</p><h2 id="pattern-title">What are you seeing?</h2><p>Describe the scam’s approach.<br />Leave people’s private messages out.</p>
          <form className="reef-command" onSubmit={launch}>
            <label htmlFor="zero-day-alert">New zero-day alert</label>
            <textarea aria-describedby="zero-day-privacy" id="zero-day-alert" value={alert} onChange={e => setAlert(e.target.value)} maxLength={400} rows={3} placeholder="Fake parking notices threaten a tow unless you pay immediately through a link…" required disabled={busy} />
            <div className="form-foot"><span>{alert.length} / 400</span><button className="primary" disabled={busy || !alert.trim() || (!useMocks && !connected)} type="submit">{busy ? "Growing protection…" : "Grow a new protection"}<span aria-hidden="true"> ↗</span></button></div>
          </form>
          <p id="zero-day-privacy" className="reef-note">{useMocks ? "Demo mode · no data is sent and no adapter is trained." : "Submitting sends this pattern to Algae. Never include private messages."}</p>
          {!useMocks && !connected && <p className="reef-note" role="status">Waiting for the event stream to connect before you can submit.</p>}
          {jobStatus && <p className="reef-status" role="status">{jobStatus}</p>}
        </section>
        <section className="growth" aria-labelledby="growth-title">
          <p className="eyebrow">FROM A PATTERN TO PROTECTION</p><h2 id="growth-title">Small by nature.<br /><em>Stronger together.</em></h2>
          <ol className="growth-trail">{[
            { title: "Create & review examples", detail: "Nemotron generates synthetic conversations, critiques them, and removes duplicates.", symbol: "·" },
            { title: "Train a small adapter", detail: "A chloroplast learns the pattern while the base model stays frozen.", symbol: "❧" },
            { title: "Ready for your device", detail: "Download only the adapter. Its training conversations stay behind.", symbol: "✧" },
          ].map((step, index) => <li key={step.title} className={stageIndex > index ? "complete" : stageIndex === index && busy ? "growing" : ""} aria-current={stageIndex === index && busy ? "step" : undefined}><span className="seed" aria-hidden="true">{stageIndex > index ? "✓" : step.symbol}</span><div><strong>{step.title}</strong><p>{step.detail}</p></div></li>)}</ol>
          <p className="growth-status">{pipeline === "error" ? "The last job could not complete. Review the status and try again." : pipeline === "ready" ? "Adapter downloaded and validated. A new leaf of protection." : busy ? "Following your job through the reef…" : "Ready for a new pattern. No training job is running."}</p>
        </section>
      </div>
      <section className="adapter-shelf" aria-label="Chloroplast status"><span className="adapter-leaf" aria-hidden="true">❧</span><div><h3>{adapter ? "A new protection has arrived." : "A place for the next protection."}</h3><p>{adapter ? String(adapter.id) : "A chloroplast appears here after a real job finishes and its download is validated."}</p></div><dl><div><dt>Size</dt><dd>{adapter ? number(adapter.size_bytes) + " B" : "--"}</dd></div><div><dt>Training</dt><dd>{valid(adapterMetrics?.train_seconds) ? number(adapterMetrics.train_seconds, 1) + " s" : "--"}</dd></div><div><dt>Val recall @ 1% FPR</dt><dd>{pct(valid(adapterMetrics?.val_recall_at_1fpr) ? adapterMetrics.val_recall_at_1fpr : null)}</dd></div></dl></section>
      <div className="live-grid">
        <section className="event-journal" aria-labelledby="journal-title">
          <div className="panel-label"><h3 id="journal-title">The growth journal</h3><small>{useMocks ? "EXAMPLE EVENT" : connected ? "● LIVE STREAM" : "STREAM OFFLINE"}</small></div>
          <div className="reef-terminal-log" role="log" aria-label="Algae event log" aria-live="polite">{logs.length ? logs.map(line => <p key={line.id}><span className={`reef-prefix prefix-${line.prefix}`}>[{line.prefix}]</span> {line.message}</p>) : <p className="reef-muted">[reef] Waiting for Algae events. No training job running.</p>}</div>
          <div className="loss-heading"><span className="reef-kicker">TRAINING LOSS {useMocks ? "· FIXTURE" : ""}</span><strong>{number(loss.at(-1)?.loss, 3)}</strong></div>
          {loss.length ? <div className="loss-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={loss} margin={{ top: 8, left: -24, right: 12, bottom: 0 }} accessibilityLayer><CartesianGrid stroke="#dce3d3" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="step" tick={{ fontSize: 9, fill: "#60705c" }} axisLine={false} tickLine={false} /><YAxis domain={[0, "auto"]} tick={{ fontSize: 9, fill: "#60705c" }} axisLine={false} tickLine={false} /><Tooltip labelFormatter={value => `Step ${value}`} formatter={value => [number(value, 3), "Loss"]} /><Line dataKey="loss" stroke="#598550" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} /></LineChart></ResponsiveContainer></div> : <p className="reef-note">-- · The loss curve appears as training events arrive.</p>}
        </section>
        <section className="photon-panel" aria-labelledby="photon-title"><div className="panel-label"><h3 id="photon-title">Ripples from Photon</h3><small>MASKED PREVIEWS</small></div><p className="reef-note">Opt-in iMessage &amp; SMS protection, connected to the reef.</p><div className="photon-list" role="log" aria-label="Masked Photon messages" aria-live="polite">{photon.length ? photon.map(item => <p key={item.id}><span aria-hidden="true">↳</span> {item.preview}</p>) : <div className="photon-empty"><span aria-hidden="true">⌁</span><strong>A quiet patch of water.</strong><p>No Photon messages in this session.<br />Masked previews will appear here.</p></div>}</div></section>
      </div>
      <EvaluationDashboard />
    </div>
  </div>;
}
