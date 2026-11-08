export type Turn = { sender: "them" | "me"; text: string };
export const EMB_DIM = 384;
export const TURN_DIM = 385;
export const MAX_TURNS = 12;

// Only model assets use the browser cache. Text and embeddings stay in memory.
let encoder: Promise<(text: string) => Promise<Float32Array>> | undefined;
export function roleText(turn: Turn): string {
  return `${turn.sender === "them" ? "[THEM] " : "[ME] "}${turn.text}`;
}
export async function embedTurns(turns: Turn[], onStatus?: (status: string) => void): Promise<Float32Array[]> {
  if (!encoder) {
    onStatus?.("Loading MiniLM… First use requires an internet download of model assets. Message text stays on this device.");
    encoder = (async () => {
      const { pipeline, env } = await import("@huggingface/transformers");
      env.allowLocalModels = false;
      env.useBrowserCache = true;
      if (env.backends.onnx.wasm) {
        env.backends.onnx.wasm.wasmPaths = { wasm: "/transformers/ort-wasm-simd-threaded.jsep.wasm", mjs: new URL("/transformers/ort-wasm-simd-threaded.jsep.mjs", location.href).href };
        env.backends.onnx.wasm.numThreads = 1;
      }
      const extract = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2", { dtype: "fp32", device: "wasm" });
      return async (text: string) => {
        const output = await extract(text, { pooling: "mean", normalize: true });
        if (output.data.length !== EMB_DIM) throw new Error("MiniLM must produce 384 features");
        return Float32Array.from(output.data as Float32Array);
      };
    })().catch(error => { encoder = undefined; throw error; });
  }
  const extract = await encoder;
  const vectors: Float32Array[] = [];
  for (const turn of turns) {
    const vector = new Float32Array(TURN_DIM);
    vector.set(await extract(roleText(turn)));
    vector[EMB_DIM] = turn.sender === "them" ? 1 : 0;
    vectors.push(vector);
  }
  return vectors;
}
