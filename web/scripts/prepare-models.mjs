import { copyFile, mkdir, access } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
const require = createRequire(import.meta.url);
// Keep each runtime's WASM version paired with its own JS package.
const hf = require.resolve("@huggingface/transformers");
for (const [folder, base, stem] of [
  ["ort", dirname(require.resolve("onnxruntime-web")), "ort-wasm-simd-threaded"],
  ["transformers", dirname(require.resolve("onnxruntime-web", { paths: [dirname(hf)] })), "ort-wasm-simd-threaded.jsep"],
]) {
  const out = new URL(`../public/${folder}/`, import.meta.url);
  await mkdir(out, { recursive: true });
  for (const ext of ["mjs", "wasm"]) await copyFile(join(base, `${stem}.${ext}`), new URL(`${stem}.${ext}`, out));
}
const source = new URL("../../ml/artifacts/", import.meta.url);
const target = new URL("../public/models/", import.meta.url);
await mkdir(target, { recursive: true });
const files = ["preynet.onnx", "temperature.json"];
try { await Promise.all(files.map(name => access(new URL(name, source)))); }
catch {
  console.warn(`Browser model pair pending in ${fileURLToPath(source)}; existing staged artifacts retained.`);
  process.exit(0);
}
for (const name of files) await copyFile(new URL(name, source), new URL(name, target));
