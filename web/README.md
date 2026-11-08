# IronGuard browser runtime

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

`/reef` reads `/v1/metrics`, streams `/v1/events`, and submits an explicit zero-day alert to `/v1/zero-day`. It correlates completion/error with the returned job ID, buffers events racing the POST response, and only says `CHLOROPLAST ABSORBED · {size} bytes · {train_seconds} s` after downloading and validating the published adapter. A demo response never claims training occurred. Charts show available evaluation data; absent values remain `--`. The API on shared main currently returns a demo job until B connects training.

Safety Cards and block/report actions remain local demos; no verification or report is sent. Suspicious addresses remain non-interactive; the Cool-Down Shield reveals plain text after ten seconds. Current stages come from script labels and predicted stages come from the runtime. Animations honor reduced motion.

## Prove privacy in DevTools

1. Start with `VITE_USE_MOCKS=0 make web` after preparing A's artifacts. Open `/phone` without the debug query.
2. Open DevTools → **Network**, choose **All**, enable **Preserve log**, and clear existing entries.
3. Enter a unique synthetic message in **Message to score locally** and press **Score on this device**. Wait for the local result. First use downloads model/tokenizer/WASM assets; later uses reuse the model cache.
4. Inspect every new request's URL, Query String Parameters and Payload. Search for your unique phrase. No request may contain the phrase, and there must be no `POST /v1/score`. Manifest GETs, SSE and fixed asset downloads contain no message text.
5. Repeat after switching the browser offline, once model assets are cached. Local scoring must still work; optional manifest/stream refreshes can fail without disabling base inference. A fixture result or an unavailable-artifact message proves only the UI boundary, not real local inference.

Checks: `make validate check-web check-bridge`, `pnpm --dir web test`, `pnpm --dir web build`. Runtime tests cover calibration, prefixes, global attention after truncation, lock boundaries, adapter arithmetic/thresholds, malformed weights, vitality and parity failures.
