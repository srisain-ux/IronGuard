# web/AGENTS.md: Member C (Leaf Sheep UI). Root AGENTS.md rules still apply.

## Stack
Vite + React 18 + TypeScript + Tailwind CSS, `react-router-dom`, `recharts` (charts), `@huggingface/transformers` (transformers.js v3: MiniLM in the browser), `onnxruntime-web` (PreyNet ONNX). pnpm. No other UI framework. Use CSS animations, not an animation library.

## Routes
- `/phone`: the customer view inside a phone frame. Thread list → thread view. Each incoming message runs **on-device** inference and shows: the Trajectory HUD (risk meter, Trajectory Compass, `T-2 TURNS TO STRIKE`, LOCKED badge), locked links (not clickable; strikethrough + lock), the Cool-Down Shield modal, the Safety Card with 1-tap steps, and the leaf-sheep avatar with chloroplast badges (vitality bar).
- `/reef`: the "Algae Reef Lab" for judges. Terminal-style zero-day input (`> new zero-day alert:`), a live SSE log (algae plan → generate → critique → train), a loss sparkline, a chloroplast card (size, train seconds, metrics), and the **three pitch charts** read from `/v1/metrics`: EWR@k lines, zero-day before/after + sample efficiency, reliability diagram. Plus a live Photon feed (masked previews).

## On-device runtime (`src/runtime/`) is the privacy proof
- `embed.ts`: transformers.js `Xenova/all-MiniLM-L6-v2`, mean pooling, normalize. Cache the model in the browser (first load shows a "Hatching dragonfly…" loader).
- `preynet.ts`: onnxruntime-web session for `/models/preynet.onnx`; build the `[turns, 385]` input; apply `temperature.json`; produce a **`score_response`-shaped object** (same shape as Python).
- `lockon.ts`: hysteresis identical to `ml/ironguard_ml/infer.py` (θ_lock 0.70, θ_release 0.40, 2 turns). Read the values from the artifacts manifest if A provides them.
- `chloroplast.ts`: decode base64 float32 weights, run `sigmoid(W2·gelu(W1·f+b1)+b2)` on the 640-d `features`.
- **Network rule:** the runtime never sends message text anywhere. Only the Report flow sends text, and only after the user sees a scrubbed preview and taps "Send".
- Parity check page (`/phone?debug=1`): shows browser vs API scores for the example thread. They must match within ±0.02.

## Mocks
`VITE_USE_MOCKS=1` → every fetch reads from `src/mocks/` (copied from `contracts/examples/`) and runtime calls return `score_response.turn3.json`. The UI must be fully demoable on mocks by M1.

## Style
Follow `docs/THEME.md` and import `src/theme/zero-day.css` once in `main.tsx`. Every screen should look like it belongs in the HackUTD Zero Day deck.
