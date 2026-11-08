# Reef Guard web app

The botanical interface uses the supplied watercolor artwork, paper surfaces, and Reef Guard shield. `/phone` retains the three conversation simulations, local scoring, trajectory compass, safety cards, protected addresses, cooldown, and adapter vitality. Below a selected conversation, the turn inspector shows risk history, family probabilities, and message attention using only revealed messages.

`/reef` retains the zero-day form, job-correlated event journal, loss curve, validated adapter download, and masked Photon feed. The evaluation section adds model filters, a prefix inspector, lead-time comparisons, calibration sample counts, human/synthetic test-set selection, and measurement tables. **Published evaluation** is bundled directly from `ml/artifacts/eval_summary.json` at build time; **service feed** reads `/v1/metrics` (the unavailable contract fixture in mock mode). The source and generation time are visible. Rebuild to refresh the published snapshot. Overall and zero-day `available: false` flags suppress their numbers, and missing data remains `--`.

Design tokens and behavior are documented in `docs/THEME.md`. Original asset provenance is in `web/public/botanical/README.md`. No new dependencies or remote fonts are needed for the redesign.

Run `pnpm --dir web install`, then `VITE_USE_MOCKS=1 make web` and open http://localhost:5173/phone. Mocks use bundled contract fixtures, with three scripted incident timelines; no inference or training quality is claimed. The typed-message scorer returns the score contract fixture in mock mode.

For real inference, run `VITE_USE_MOCKS=0 make web`. The predev/prebuild step (`pnpm --dir web models:prepare`) copies A's `ml/artifacts/preynet.onnx` and `temperature.json` into ignored `web/public/models/`, and stages each installed runtime's matching WASM. No model is trained or exported by the web build. A missing export shows an unavailable message; customer text is never used as an API fallback. Refresh after installing new artifacts. The A3 express drop is on `origin/a/main` until its main merge; it can be tested without modifying ML files:

```sh
git fetch origin
git show origin/a/main:ml/artifacts/preynet.onnx > web/public/models/preynet.onnx
git show origin/a/main:ml/artifacts/temperature.json > web/public/models/temperature.json
VITE_USE_MOCKS=0 make web
```

`src/runtime/embed.ts` uses transformers.js v3, `Xenova/all-MiniLM-L6-v2` fp32, mean pooling, L2 normalization, and exact `[THEM] ` / `[ME] ` prefixes. Only model assets use the browser cache. `preynet.ts` sends `turn_vecs` float32 `[1, turns, 385]` into onnxruntime-web, left-truncates to 12 turns, and reads `family_logits`, `stage_logits`, `tts_logits`, `attention`, `features` per A3's handoff. It calibrates each head with `{family,next_stage,tts}` temperatures and replays prefix risks for hysteresis, reading `theta_lock` from the artifact (fallback .70), release threshold .40, two THEM turns below release. ME turns do not reset or advance that count.

`chloroplast.ts` decodes row-major float32 little-endian weights and computes the erf GELU adapter on 640 features. Fired adapters raise risk, can replace the family and always lock. Malformed adapters are contained; vitality never gates inference. `/phone` downloads manifests from `GET /v1/chloroplasts`, refreshes on `chloroplast.ready` and every minute, and draws a green cerata badge and vitality meter per manifest. Vitality is `0.5^(age_hours/half_life_hours)` and is display only. Mock badge weights are deliberately placeholder contract data and cannot protect a message.

Open `/phone?debug=1` and press **Compare public example** to compare the full bundled public pig-butchering example thread with `/v1/score`. Both sides disable adapters. The table checks risk, each family probability, winning stage/TTS probability, attention, and agreement on labels/confidence/lock. A PASS requires all numeric differences ≤ .02 and a real API model; fixture/stub mode remains UNVERIFIED. Run `make api` with the matching checkpoint and temperatures for real parity. The comparison never accepts typed customer text.

`/reef` reads `/v1/metrics`, streams `/v1/events`, and submits an explicit zero-day alert to `/v1/zero-day`. It correlates completion/error with the returned job ID, buffers events racing the POST response, and only says `CHLOROPLAST ABSORBED · {size} bytes · {train_seconds} s` after downloading and validating the published adapter. A demo response never claims training occurred. Real training requires B's Algae/Nemotron service and A's model artifacts.

Safety Cards and block/report actions remain local demos; no verification or report is sent. Suspicious addresses remain non-interactive; the Cool-Down Shield reveals plain text after ten seconds. Current stages come from script labels and predicted stages come from the runtime. Animations honor reduced motion.

## Prove privacy in DevTools

1. Start with `VITE_USE_MOCKS=0 make web` after preparing A's artifacts. Open `/phone` without the debug query.
2. Open DevTools → **Network**, choose **All**, enable **Preserve log**, and clear existing entries.
3. Enter a unique synthetic message in **Message to score locally** and press **Score on this device**. Wait for the local result. First use downloads model/tokenizer/WASM assets; later uses reuse the model cache.
4. Inspect every new request's URL, Query String Parameters and Payload. Search for your unique phrase. No request may contain the phrase, and there must be no `POST /v1/score`. Manifest GETs, SSE and fixed asset downloads contain no message text.
5. Keep the loaded page open, switch the browser offline, and score another synthetic message. Local scoring must still work; optional manifest/stream refreshes can fail without disabling base inference. A fixture result or an unavailable-artifact message proves only the UI boundary, not real local inference. First use requires internet: MiniLM is fetched from Hugging Face. This app has no service worker or complete offline app cache, so a fresh offline launch/reload is not supported. Browser cache eviction can require downloading the encoder again. Local inference is not a claim of offline-first installation.

Checks: `make validate check-web check-bridge`, `pnpm --dir web test`, `pnpm --dir web build`. Runtime tests cover calibration, prefixes, global attention after truncation, lock boundaries, adapter arithmetic/thresholds, malformed weights, vitality and parity failures.
