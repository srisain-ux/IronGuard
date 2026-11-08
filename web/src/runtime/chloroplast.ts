import type { ChloroplastManifest } from "../contracts/chloroplast";

/** Validate downloaded metadata before it can supply a score label or badge. */
export function isChloroplastManifest(value: unknown): value is ChloroplastManifest {
  if (!value || typeof value !== "object") return false;
  const m = value as ChloroplastManifest;
  const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
  return typeof m.id === "string" && /^cp_[a-z0-9_]+$/.test(m.id)
    && typeof m.family_id === "string" && /^zd_[a-z0-9_]+$/.test(m.family_id)
    && typeof m.label === "string" && m.label.length <= 80 && typeof m.alert === "string" && m.alert.length <= 400
    && typeof m.created_at === "string" && Number.isFinite(Date.parse(m.created_at))
    && finite(m.half_life_hours) && m.half_life_hours > 0 && m.feature_dim === 640
    && Number.isInteger(m.hidden_dim) && m.hidden_dim >= 4 && m.hidden_dim <= 128
    && !!m.weights && [m.weights.w1, m.weights.b1, m.weights.w2, m.weights.b2].every(v => typeof v === "string")
    && finite(m.threshold) && m.threshold >= 0 && m.threshold <= 1
    && !!m.metrics && Number.isInteger(m.metrics.n_pos) && Number.isInteger(m.metrics.n_neg) && finite(m.metrics.train_seconds)
    && Number.isInteger(m.size_bytes) && m.size_bytes >= 1 && typeof m.sha256 === "string" && /^[a-f0-9]{64}$/.test(m.sha256);
}

export function decodeFloat32(encoded: string, count: number): Float32Array {
  if (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encoded)) throw new Error("Invalid base64 weights");
  const raw = atob(encoded);
  if (raw.length !== count * 4) throw new Error("Chloroplast weight shape mismatch");
  const view = new DataView(Uint8Array.from(raw, c => c.charCodeAt(0)).buffer);
  const values = Float32Array.from({ length: count }, (_, i) => view.getFloat32(i * 4, true));
  if (!values.every(Number.isFinite)) throw new Error("Non-finite chloroplast weights");
  return values;
}
// erf approximation (maximum error 1.5e-7); PyTorch GELU uses erf, not tanh.
export function gelu(x: number): number {
  const z = Math.abs(x) / Math.SQRT2;
  const t = 1 / (1 + 0.3275911 * z);
  const erf = Math.sign(x) * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-z * z));
  return 0.5 * x * (1 + erf);
}
export function compileChloroplast(manifest: ChloroplastManifest) {
  if (!isChloroplastManifest(manifest)) throw new Error("Invalid chloroplast manifest");
  const { hidden_dim: h, weights: w, threshold } = manifest;
  const w1 = decodeFloat32(w.w1, h * 640);
  const b1 = decodeFloat32(w.b1, h);
  const w2 = decodeFloat32(w.w2, h);
  const b2 = decodeFloat32(w.b2, 1);
  return (features: ArrayLike<number>) => {
    if (features.length !== 640) throw new Error("Chloroplast requires 640 features");
    let logit = b2[0];
    for (let row = 0; row < h; row++) {
      let value = b1[row];
      for (let col = 0; col < 640; col++) value += w1[row * 640 + col] * features[col];
      logit += w2[row] * gelu(value);
    }
    const p = 1 / (1 + Math.exp(-logit));
    if (!Number.isFinite(p)) throw new Error("Non-finite chloroplast output");
    return { id: manifest.id, p, fired: p >= threshold };
  };
}
export function vitality(manifest: Pick<ChloroplastManifest, "created_at" | "half_life_hours">, now = Date.now()): number {
  const age = Math.max(0, (now - Date.parse(manifest.created_at)) / 3_600_000);
  return Number.isFinite(age) && manifest.half_life_hours > 0 ? Math.pow(0.5, age / manifest.half_life_hours) : 0;
}
