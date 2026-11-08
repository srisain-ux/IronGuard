import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getMetrics, useMocks, type EvalSummary, type EvaluationModel } from "../api/client";
import { pitchMetrics } from "../api/metrics";

// Bundle the actual evaluation artifact, if present. This is a dated snapshot, never a mock metric.
const artifacts = import.meta.glob("../../../ml/artifacts/eval_summary.json", { eager: true, import: "default" });
const published = (Object.values(artifacts)[0] ?? null) as EvalSummary | null;
const colors: Record<string, string> = { PreyNet: "#456d45", B0: "#917523", B1: "#b2654e", B2: "#3b8585", B3: "#827297", PreyNet_no_attention: "#8c983f", PreyNet_no_multitask: "#537c9c" };
const labels: Record<string, string> = { PreyNet: "PreyNet", B0: "B0 · Rules", B1: "B1 · TF-IDF", B2: "B2 · MiniLM", B3: "B3 · Mean context", PreyNet_no_attention: "Without attention", PreyNet_no_multitask: "Without multitask" };
const valid = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const pct = (value: unknown, digits = 1) => valid(value) ? `${(value * 100).toFixed(digits)}%` : "--";
const num = (value: unknown, digits = 0) => valid(value) ? value.toFixed(digits) : "--";
const tick = { fontSize: 10, fill: "#60705c" };
const percentTooltip = (value: unknown) => pct(value);

export function EmptyChart({ label, detail }: { label: string; detail?: string }) {
  return <div className="chart-empty"><span aria-hidden="true">⌁</span><strong>--</strong><p>{label}</p>{detail && <small>{detail}</small>}</div>;
}

function MetricTitle({ number, title, note }: { number: string; title: string; note: string }) {
  return <div className="metric-title"><span className="chart-number">{number}</span><div><h3>{title}</h3><p>{note}</p></div></div>;
}

export function EvaluationDashboard() {
  const [source, setSource] = useState<"published" | "service">(published ? "published" : "service");
  const [service, setService] = useState<EvalSummary | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [refresh, setRefresh] = useState(0);
  const [split, setSplit] = useState<"test" | "test_human">("test");
  const [hidden, setHidden] = useState<string[]>(["PreyNet_no_attention", "PreyNet_no_multitask"]);
  const [prefix, setPrefix] = useState(2);
  const [calibration, setCalibration] = useState<"reliability" | "counts">("reliability");
  useEffect(() => {
    let active = true;
    setStatus("loading");
    void getMetrics().then(value => { if (active) { setService(value); setStatus("ready"); } }).catch(() => { if (active) { setService(null); setStatus("error"); } });
    return () => { active = false; };
  }, [refresh]);

  const metrics = pitchMetrics(source === "published" ? published : service);
  const models: Record<string, EvaluationModel> = Object.fromEntries(Object.entries(metrics?.models ?? {}).map(([name, model]) => [name, split === "test" ? model : model.test_human ?? {}]));
  const allNames = Object.keys(models);
  const measuredNames = allNames.filter(name => models[name].ewr_at_k?.some(valid));
  const visibleNames = measuredNames.filter(name => !hidden.includes(name));
  const maxPrefix = Math.max(1, ...measuredNames.map(name => models[name].ewr_at_k?.length ?? 0));
  const selectedPrefix = Math.min(prefix, maxPrefix);
  const ewrRows = Array.from({ length: maxPrefix }, (_, i) => Object.fromEntries([["k", i + 1], ...visibleNames.map(name => [name, valid(models[name].ewr_at_k?.[i]) ? models[name].ewr_at_k?.[i] : null])]));
  const leadRows = visibleNames.filter(name => valid(models[name].lead_time)).map(name => ({ name, label: labels[name] ?? name, lead: models[name].lead_time }));
  const preynet = models.PreyNet;
  const denominators = metrics?.dataset?.split_denominators?.[split];
  const sampleCount = split === "test" ? metrics?.dataset?.n_test : metrics?.dataset?.n_test_human;
  const reliability = split === "test" ? metrics?.reliability : undefined;
  const reliabilityRows = (reliability?.conf ?? []).map((conf, i) => ({ conf, accuracy: reliability?.acc?.[i] ?? null, ideal: conf, count: reliability?.count?.[i] ?? null, bin: reliability?.bins?.[i] ?? conf })).filter(row => valid(row.conf));
  const zeroDay = metrics?.zero_day;
  const beforeAfter = [{ label: "Base model", ewr: zeroDay?.base_ewr_at_3 ?? null }, { label: "+ Chloroplast", ewr: zeroDay?.chloroplast_ewr_at_3 ?? null }];
  // Retain null measurements so the chart never draws a line across missing results.
  const samples = (zeroDay?.sample_efficiency ?? []).filter(point => valid(point.n)).sort((a, b) => a.n - b.n);
  const generated = metrics?.generated_at ? new Date(metrics.generated_at) : null;
  const date = generated && Number.isFinite(generated.valueOf()) ? generated.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " UTC" : "--";
  const toggle = (name: string) => setHidden(current => current.includes(name) ? current.filter(item => item !== name) : [...current, name]);

  return <section className="evaluation" id="evaluation" aria-labelledby="evaluation-title">
    <div className="section-heading"><div><p className="eyebrow">THE FIELD NOTES / MODEL EVALUATION</p><h2 id="evaluation-title">Evidence, in the open.</h2></div><p>Explore what the model catches, how early it warns, and where its confidence needs care.</p></div>
    <div className="evaluation-toolbar">
      <div className="segmented" role="group" aria-label="Evaluation source"><button aria-pressed={source === "published"} onClick={() => setSource("published")}>Published evaluation</button><button aria-pressed={source === "service"} onClick={() => setSource("service")}>{useMocks ? "Mock service feed" : "Live service feed"}</button></div>
      <label className="dataset-select">Test set <select value={split} onChange={event => setSplit(event.target.value as typeof split)}><option value="test">Synthetic conversations</option><option value="test_human">Human-written conversations</option></select></label>
      {source === "service" && <button className="text-button" onClick={() => setRefresh(value => value + 1)} disabled={status === "loading"}>Refresh ↻</button>}
    </div>
    <div className="evaluation-provenance" role="status">
      <span className="source-badge">{source === "published" ? "SAVED EVALUATION" : useMocks ? "CONTRACT FIXTURE" : "API EVALUATION"}</span>
      <span>{source === "service" && status === "loading" ? "Loading evaluation…" : source === "service" && status === "error" ? "The evaluation service is unavailable. Use Refresh to retry." : !metrics ? "No eligible evaluation is available from this source." : `Dataset ${metrics.dataset?.version ?? "--"} · ${num(sampleCount)} test conversations · ${date}`}</span>
    </div>
    {split === "test_human" && !measuredNames.length && <p className="evaluation-caveat">Human-written evaluation is not available. Synthetic results do not establish performance on real customer conversations.</p>}
    <div className="stat-strip">
      <div><span>Early warnings · turn 2</span><strong>{pct(preynet?.ewr_at_k?.[1])}</strong><small>PreyNet · before the strike</small></div>
      <div><span>Mean warning lead time</span><strong>{num(preynet?.lead_time, 2)}<em> turns</em></strong><small>{valid(preynet?.lead_time_std) ? `± ${num(preynet.lead_time_std, 2)} across seeds` : "Uncaught scams contribute zero"}</small></div>
      <div><span>Observed false alarms</span><strong>{pct(preynet?.fpr, 2)}</strong><small>Benign test conversations</small></div>
      <div><span>Calibrated family ECE</span><strong>{pct(preynet?.ece_after, 2)}</strong><small>Lower calibration error is better</small></div>
    </div>
    <div className="evaluation-grid">
      <section className="metric-panel chart-wide">
        <MetricTitle number="01" title="A warning before the ask." note="Early warning rate by conversation prefix · EWR@k" />
        <div className="model-filters" role="group" aria-label="Models shown in comparison charts">{allNames.map(name => <button key={name} aria-pressed={!hidden.includes(name)} onClick={() => toggle(name)}><i style={{ background: colors[name] ?? "#718368" }} />{labels[name] ?? name}</button>)}</div>
        {visibleNames.length ? <div className="reef-chart chart-tall"><ResponsiveContainer width="100%" height="100%"><LineChart data={ewrRows} margin={{ top: 22, right: 24, bottom: 8, left: -10 }} accessibilityLayer>
          <CartesianGrid stroke="#dce3d3" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="k" tick={tick} tickFormatter={value => `Turn ${value}`} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 1]} tick={tick} tickFormatter={value => pct(value, 0)} axisLine={false} tickLine={false} />
          <Tooltip labelFormatter={value => `After ${value} messages`} formatter={percentTooltip} />
          <ReferenceLine x={selectedPrefix} stroke="#a7b597" strokeDasharray="4 4" />
          {visibleNames.map(name => <Line key={name} name={labels[name] ?? name} dataKey={name} type="linear" stroke={colors[name] ?? "#718368"} strokeWidth={name === "PreyNet" ? 3 : 1.8} strokeDasharray={name.includes("no_") ? "5 4" : undefined} dot={{ r: name === "PreyNet" ? 4 : 2.5 }} connectNulls={false} isAnimationActive={false} />)}
        </LineChart></ResponsiveContainer></div> : <EmptyChart label={measuredNames.length ? "Select a model to compare." : "No measured early-warning results."} detail="Only published measurements appear here." />}
        {measuredNames.length > 0 && <div className="prefix-inspector"><label htmlFor="ewr-prefix">Inspect prefix</label><input id="ewr-prefix" type="range" min={1} max={maxPrefix} step={1} value={selectedPrefix} onChange={event => setPrefix(Number(event.target.value))} /><output htmlFor="ewr-prefix">Turn {selectedPrefix}</output><div>{visibleNames.map(name => <span key={name}><i style={{ background: colors[name] ?? "#718368" }} />{labels[name] ?? name} <b>{pct(models[name].ewr_at_k?.[selectedPrefix - 1])}</b></span>)}</div></div>}
        <p className="chart-explanation">EWR@k is the share of scam conversations flagged by message k, while the strike is still ahead. Thresholds target at most 1% false alarms on validation data; observed test false alarms are reported separately.</p>
      </section>
      <section className="metric-panel">
        <MetricTitle number="02" title="Time to take a breath." note="Mean warning lead time · turns before the strike" />
        {leadRows.length ? <div className="reef-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={leadRows} layout="vertical" margin={{ top: 15, right: 22, bottom: 6, left: 0 }} accessibilityLayer>
          <CartesianGrid stroke="#dce3d3" strokeDasharray="3 5" horizontal={false} />
          <XAxis type="number" tick={tick} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="label" tick={{ ...tick, fontSize: 9 }} width={122} axisLine={false} tickLine={false} />
          <Tooltip formatter={value => [`${num(value, 2)} turns`, "Lead time"]} />
          <Bar dataKey="lead" radius={[0, 5, 5, 0]} maxBarSize={22} isAnimationActive={false}>{leadRows.map(row => <Cell key={row.name} fill={colors[row.name] ?? "#718368"} />)}</Bar>
        </BarChart></ResponsiveContainer></div> : <EmptyChart label="Lead-time results are unavailable." />}
        <p className="chart-explanation">An earlier warning gives more room to verify. The mean includes uncaught scams as zero. Model selection follows the comparison above.</p>
      </section>
      <section className="metric-panel">
        <MetricTitle number="03" title="Confidence that earns its place." note="Family confidence vs. observed accuracy" />
        <div className="segmented" role="group" aria-label="Calibration view"><button aria-pressed={calibration === "reliability"} onClick={() => setCalibration("reliability")}>Reliability</button><button aria-pressed={calibration === "counts"} onClick={() => setCalibration("counts")}>Samples per bin</button></div>
        {reliabilityRows.some(row => valid(calibration === "reliability" ? row.accuracy : row.count)) ? <div className="reef-chart"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={reliabilityRows} margin={{ top: 12, right: 22, bottom: 8, left: -12 }} accessibilityLayer>
          <CartesianGrid stroke="#dce3d3" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="conf" type="number" domain={[0, 1]} tick={tick} tickFormatter={value => pct(value, 0)} axisLine={false} tickLine={false} />
          <YAxis domain={calibration === "reliability" ? [0, 1] : [0, "auto"]} tick={tick} tickFormatter={value => calibration === "reliability" ? pct(value, 0) : num(value)} axisLine={false} tickLine={false} />
          <Tooltip labelFormatter={value => `${pct(Number(value))} mean family confidence`} formatter={(value, name) => name === "Samples" ? num(value) : pct(value)} />
          {calibration === "reliability" ? <><ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#a3af96" strokeDasharray="5 5" /><Line dataKey="accuracy" name="Observed accuracy" stroke="#3c8176" strokeWidth={2.5} dot={{ r: 4 }} connectNulls={false} isAnimationActive={false} /></> : <Bar dataKey="count" name="Samples" fill="#7c9c71" barSize={14} radius={[4, 4, 0, 0]} isAnimationActive={false} />}
        </ComposedChart></ResponsiveContainer></div> : <EmptyChart label="Calibration results are unavailable." />}
        <div className="metric-pair"><span>ECE before <b>{pct(preynet?.ece_before, 2)}</b></span><span>After calibration <b>{pct(preynet?.ece_after, 2)}</b></span></div>
        <p className="chart-explanation">The dashed diagonal is perfect calibration. Each point groups test prefixes by top family confidence. Small bins have less evidence; inspect their sample counts. This measures family confidence, not scam-risk calibration.</p>
      </section>
      <section className="metric-panel">
        <MetricTitle number="04" title="A new leaf of protection." note="Zero-day adaptation · EWR@3 before and after" />
        {beforeAfter.some(row => valid(row.ewr)) ? <div className="reef-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={beforeAfter} margin={{ top: 12, right: 22, bottom: 8, left: -12 }} accessibilityLayer>
          <CartesianGrid stroke="#dce3d3" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="label" tick={tick} axisLine={false} tickLine={false} /><YAxis domain={[0, 1]} tick={tick} tickFormatter={value => pct(value, 0)} axisLine={false} tickLine={false} /><Tooltip formatter={percentTooltip} /><Bar dataKey="ewr" name="EWR@3" radius={[7, 7, 0, 0]} maxBarSize={65} isAnimationActive={false}><Cell fill="#c4c7a2" /><Cell fill="#5c8559" /></Bar>
        </BarChart></ResponsiveContainer></div> : <EmptyChart label="Waiting for an eligible zero-day evaluation." detail="Unvalidated proxy results are excluded." />}
        <div className="metric-pair"><span>Before <b>{pct(zeroDay?.base_ewr_at_3)}</b></span><span>After <b>{pct(zeroDay?.chloroplast_ewr_at_3)}</b></span><span>Time to protection <b>{valid(zeroDay?.time_to_protection_s) ? `${num(zeroDay.time_to_protection_s, 1)} s` : "--"}</b></span></div>
        <p className="chart-explanation">The held-out scam family tests whether a small adapter adds protection. Results appear only when the evaluation marks them available.</p>
      </section>
      <section className="metric-panel">
        <MetricTitle number="05" title="How much does a new leaf need?" note="Sample efficiency · synthetic positives vs. EWR@3" />
        {samples.some(row => valid(row.ewr_at_3)) ? <div className="reef-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={samples} margin={{ top: 12, right: 22, bottom: 8, left: -12 }} accessibilityLayer>
          <CartesianGrid stroke="#dce3d3" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="n" type="number" domain={[0, "dataMax"]} tick={tick} axisLine={false} tickLine={false} /><YAxis domain={[0, 1]} tick={tick} tickFormatter={value => pct(value, 0)} axisLine={false} tickLine={false} /><Tooltip labelFormatter={value => `${value} synthetic positives`} formatter={percentTooltip} /><Line dataKey="ewr_at_3" name="EWR@3" stroke="#3c8176" strokeWidth={2.5} dot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
        </LineChart></ResponsiveContainer></div> : <EmptyChart label="Sample-efficiency measurements are pending." detail="Missing points stay missing; no estimated curve." />}
        <p className="chart-explanation">Each point uses a measured synthetic training-set size. Gaps remain visible where no result was produced. Customer messages are never training examples.</p>
      </section>
    </div>
    <details className="evaluation-details" open>
      <summary>Read the measurements <span>Model comparison &amp; operating points</span></summary>
      <div className="measurement-scroll" tabIndex={0} role="region" aria-label="Model evaluation measurements"><table><caption>Selected test set · EWR at prefix {selectedPrefix}</caption><thead><tr><th scope="col">Model</th><th scope="col">EWR@{selectedPrefix}</th><th scope="col">Lead time</th><th scope="col">Strike recall</th><th scope="col">False alarms</th><th scope="col">Hard negatives</th></tr></thead><tbody>{allNames.length ? allNames.map(name => <tr key={name} className={name === "PreyNet" ? "highlight-row" : ""}><th scope="row">{labels[name] ?? name}{models[name].abstains && <small>Abstains at target FPR</small>}</th><td>{pct(models[name].ewr_at_k?.[selectedPrefix - 1])}</td><td>{num(models[name].lead_time, 2)}{valid(models[name].lead_time) ? " turns" : ""}</td><td>{pct(models[name].strike_recall)}</td><td>{pct(models[name].fpr, 2)}</td><td>{pct(models[name].hard_neg_fpr, 2)}</td></tr>) : <tr><td colSpan={6}>-- · No eligible measurements.</td></tr>}</tbody></table></div>
      <p className="chart-explanation">Test denominators: {num(denominators?.scam)} scam conversations, {num(denominators?.benign)} benign conversations, including {num(denominators?.hard_negative)} hard negatives. A model that abstains at the validation false-alarm cap does not issue warnings at that operating point. Strike recall follows the evaluation’s pre-strike prefix convention.</p>
    </details>
    <details className="evaluation-details"><summary>Where these numbers come from <span>Provenance &amp; limitations</span></summary><div className="methodology"><p>{source === "published" ? "This snapshot is bundled directly from ml/artifacts/eval_summary.json at build time. Select the service feed to inspect the API’s current evaluation." : "These results come from /v1/metrics. In mock mode, the service returns the unavailable-metrics contract fixture."}</p><p>Generated: {date}. Missing values appear as --. Scripted phone forecasts and training-event fixtures are separate from evaluation evidence.</p>{metrics?.dataset?.notes?.map((note, i) => <p key={i}>{note}</p>)}</div></details>
  </section>;
}
