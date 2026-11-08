import taxonomy from "../../../contracts/taxonomy.json";
import type { ScoreResponse } from "../contracts/score_response";
import type { ChloroplastManifest } from "../contracts/chloroplast";
import { embedTurns, MAX_TURNS, TURN_DIM, type Turn } from "./embed";
import { compileChloroplast } from "./chloroplast";
import { DEFAULT_LOCK, lockStates } from "./lockon";

export interface Temperatures {
  family: number; next_stage: number; tts: number;
  theta_lock?: number; theta_release?: number; release_turns?: number; version?: string;
}
export type Outputs = Record<"family_logits" | "stage_logits" | "tts_logits" | "attention" | "features", ArrayLike<number>>;
export type Runner = (input: Float32Array, turns: number) => Promise<Outputs>;
export function softmax(logits: ArrayLike<number>, temperature: number): number[] {
  if (!(temperature > 0) || !Number.isFinite(temperature)) throw new Error("Invalid calibration temperature");
  const values = Array.from(logits, v => v / temperature);
  if (!values.length || !values.every(Number.isFinite)) throw new Error("Non-finite model logits");
  const max = Math.max(...values);
  const exp = values.map(v => Math.exp(v - max));
  const sum = exp.reduce((a, b) => a + b, 0);
  return exp.map(v => v / sum);
}
const rules: [string, RegExp][] = [
  ["Contains a link", /https?:\/\/|www\.|\b[\w-]+\.(?:com|net|org|io|co|ly|me|example|test)\b/i],
  ["Asks for money, crypto or a gift card", /\$\s?\d|\b(?:crypto|bitcoin|btc|usdt|wallet|wire|zelle|venmo|cash\s?app|gift\s*cards?|deposit|invest\w*|fees?|pay(?:ment)?)\b/i],
  ["Asks for a code or login details", /\b(?:codes?|otp|pin|password|passcode|verif\w*|ssn|log\s?in)\b/i],
  ["Moves the chat to another app or number", /\b(?:whatsapp|telegram|signal|wechat|text me at|call (?:me|this number)|new number)\b/i],
  ["Identity switch or unexpected sender", /\b(?:wrong number|new phone|it'?s me|lost my phone|who is this)\b/i],
  ["Urgency or pressure", /\b(?:urgent\w*|immediately|right now|asap|today|within \d+|final notice|expir\w*|suspend\w*|locked|last chance|hurry)\b/i],
];
export function confidenceBand(risk: number, familyP: number): ScoreResponse["confidence_band"] {
  if (risk >= 0.8 || risk <= 0.1) return "high";
  return familyP < 0.5 || risk >= 0.35 ? "uncertain" : "low";
}
function best(values: number[]): number { return values.indexOf(Math.max(...values)); }

let loaded: Promise<{ run: Runner; temperatures: Temperatures }> | undefined;
async function load() {
  if (!loaded) loaded = (async () => {
    const response = await fetch("/models/temperature.json");
    if (!response.ok) throw new Error("Calibrated browser artifacts unavailable; run pnpm models:prepare after A's export lands");
    const temperatures: Temperatures = await response.json();
    for (const key of ["family", "next_stage", "tts"] as const) softmax([0], temperatures[key]);
    const { InferenceSession, Tensor, env } = await import("onnxruntime-web/wasm");
    env.wasm.numThreads = 1;
    env.wasm.wasmPaths = { wasm: "/ort/ort-wasm-simd-threaded.wasm", mjs: new URL("/ort/ort-wasm-simd-threaded.mjs", location.href).href };
    // Vite serves local WASM assets; no text is passed to asset requests.
    const session = await InferenceSession.create("/models/preynet.onnx", { executionProviders: ["wasm"] });
    if (session.inputNames.length !== 1 || session.inputNames[0] !== "turn_vecs") throw new Error("PreyNet must accept turn_vecs [1, turns, 385] (A3 handoff)");
    const run: Runner = async (input, turns) => {
      const feeds = { turn_vecs: new Tensor("float32", input, [1, turns, TURN_DIM]) };
      const output = await session.run(feeds);
      const result = {} as Outputs;
      for (const name of ["family_logits", "stage_logits", "tts_logits", "attention", "features"] as const) {
        if (!output[name] || output[name].type !== "float32") throw new Error(`Missing PreyNet output: ${name}`);
        result[name] = output[name].data as Float32Array;
      }
      return result;
    };
    return { run, temperatures };
  })().catch(error => { loaded = undefined; throw error; });
  return loaded;
}

/** Replay all prefixes, including those before the 12-turn window, for Python lock parity. */
export async function scoreVectors(turns: Turn[], vectors: Float32Array[], run: Runner, temperatures: Temperatures, manifests: ChloroplastManifest[] = []): Promise<ScoreResponse[]> {
  if (!turns.length || turns.length > 20 || vectors.length !== turns.length || vectors.some(v => v.length !== TURN_DIM || !v.every(Number.isFinite))) throw new Error("Expected 1–20 valid turn vectors");
  const params = { ...DEFAULT_LOCK, ...Object.fromEntries(Object.entries(temperatures).filter(([key]) => key in DEFAULT_LOCK)) };
  if (![params.theta_lock, params.theta_release].every(v => Number.isFinite(v) && v >= 0 && v <= 1) || !Number.isInteger(params.release_turns) || params.release_turns < 1) throw new Error("Invalid lock-on parameters");
  const adapters = manifests.flatMap(manifest => {
    try { return [{ manifest, score: compileChloroplast(manifest) }]; }
    catch { return []; } // Malformed adapters never disable base protection.
  });
  const risks: number[] = [];
  const scores: ScoreResponse[] = [];
  const started = performance.now();
  for (let k = 1; k <= turns.length; k++) {
    const prefix = vectors.slice(Math.max(0, k - MAX_TURNS), k);
    const input = new Float32Array(prefix.length * TURN_DIM);
    prefix.forEach((v, i) => input.set(v, i * TURN_DIM));
    const out = await run(input, prefix.length);
    if (out.family_logits.length !== 7 || out.stage_logits.length !== 5 || out.tts_logits.length !== 5 || out.features.length !== 640 || out.attention.length !== prefix.length) throw new Error("PreyNet output shape mismatch");
    const family = softmax(out.family_logits, temperatures.family);
    const stage = softmax(out.stage_logits, temperatures.next_stage);
    const tts = softmax(out.tts_logits, temperatures.tts);
    if (!Array.from(out.features).every(Number.isFinite)) throw new Error("Non-finite PreyNet features");
    const baseRisk = 1 - family[0];
    let risk = baseRisk;
    let lockRisk = baseRisk;
    let winner: ScoreResponse["family"] = { ...taxonomy.families[best(family)], p: Math.max(...family), source: "base" };
    // Select only schema fields from taxonomy.
    winner = { id: winner.id, label: winner.label, p: winner.p, source: "base" };
    const hits: NonNullable<ScoreResponse["chloroplast_hits"]> = [];
    for (const adapter of adapters) {
      const hit = adapter.score(out.features);
      hits.push(hit);
      if (!hit.fired) continue;
      risk = Math.max(risk, hit.p);
      lockRisk = Math.max(lockRisk, params.theta_lock);
      if (hit.p > baseRisk && (winner.source === "base" || hit.p > winner.p)) winner = { id: adapter.manifest.family_id, label: adapter.manifest.label, p: hit.p, source: "chloroplast" };
    }
    risks.push(lockRisk);
    const attention = [...new Array(k - prefix.length).fill(0), ...Array.from(out.attention)];
    if (!attention.every(v => Number.isFinite(v) && v >= 0 && v <= 1) || Math.abs(attention.reduce((a, b) => a + b, 0) - 1) > 0.001) throw new Error("Invalid attention weights");
    const ranked = turns.slice(0, k).map((turn, i) => ({ turn, i })).filter(({ turn }) => turn.sender === "them").sort((a, b) => attention[b.i] - attention[a.i]).slice(0, 3);
    const evidence = ranked.flatMap(({ turn, i }) => { const rule = rules.find(([, rx]) => rx.test(turn.text)); return rule ? [{ turn_idx: i, reason: rule[0] }] : []; });
    scores.push({
      risk, confidence_band: confidenceBand(risk, winner.p), family: winner,
      family_probs: Object.fromEntries(taxonomy.families.map((f, i) => [f.id, family[i]])),
      next_stage: { stage: taxonomy.stages[best(stage)].id as ScoreResponse["next_stage"]["stage"], p: Math.max(...stage) },
      turns_to_strike: { bucket: taxonomy.tts_buckets[best(tts)] as ScoreResponse["turns_to_strike"]["bucket"], p: Math.max(...tts) },
      locked: lockStates(risks, turns.slice(0, k).map(t => t.sender), params).at(-1)!, attention, evidence,
      chloroplast_hits: hits, model: { name: "preynet", version: temperatures.version ?? "unversioned-artifact", runtime: "browser", latency_ms: performance.now() - started },
    });
  }
  return scores;
}
export async function scoreBrowser(turns: Turn[], manifests: ChloroplastManifest[] = [], onStatus?: (status: string) => void): Promise<ScoreResponse[]> {
  if (!turns.length || turns.length > 20 || turns.some(t => !["them", "me"].includes(t.sender) || !t.text.trim() || t.text.length > 1000)) throw new Error("Expected 1–20 nonempty messages, up to 1000 characters each");
  onStatus?.("Hatching dragonfly…");
  const { run, temperatures } = await load();
  const vectors = await embedTurns(turns, onStatus);
  return scoreVectors(turns, vectors, run, temperatures, manifests);
}
