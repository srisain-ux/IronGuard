# MODEL_SPEC.md: Dragonfly (PreyNet) and Leaf Sheep (Chloroplasts)

> Owner: **A**. Everyone reads it. This is the heart of the project; the pitch is built from §8.
> When the spec and the code disagree, fix the code or log a decision in `PROGRESS.md` → Decisions.

---

## 0. The gap we fill (say this in the first 20 seconds of the pitch)

Today's text-scam defenses answer **"Is this message a scam?"** They react once the dangerous content (a link, a payment ask, a code request) is already on the screen, by which point the victim is often emotionally hooked. Multi-turn scams (pig butchering, "wrong number", fake jobs, bank impersonation) are built to get past that: turn 1 looks harmless.

The strongest shipping system we know of, Google Messages Scam Detection, uses on-device Gemini Nano to spot conversational scam patterns. Reports say it runs only on recent flagship Android phones. **Three gaps remain:**

| Gap | Status quo | IronGuard |
|---|---|---|
| **1. Forecast, not detection** | Flags a pattern once it shows up; no lead time; no honest confidence | PreyNet forecasts **family, next stage and turns to strike** from turn 1–2, with **calibrated** probabilities and an explicit "uncertain" band. New metric: **lead time** (turns of warning before the ask) |
| **2. Zero-day adaptation without data** | New scam types wait for the vendor's model-update cycle, and training needs real traffic | **Klepto-distillation:** a one-sentence alert → Nemotron synthesizes conversations → a chloroplast head trains in seconds → phones absorb it. **Zero customer data is used** |
| **3. Reach + action** | Flagship Android only; result is a label | Works on any phone through Photon (iMessage/SMS), and in the browser fully on-device. The Safeguard Agent turns the forecast into verified next steps |

**One-line claim (only make it once numbers exist):** *"PreyNet warns __ turns before the scammer's ask, at a 1% false-alarm rate, where per-message filters warn ~0 turns before. It learned a scam it had never seen in __ minutes, from one sentence, without reading anyone's texts."*

---

## 1. Biology → architecture mapping (keep it honest)

| Biology (sources in §10) | What it does in the animal | What we build | Where in code |
|---|---|---|---|
| **Internal models** (Mischiati et al., *Nature* 2015) | The dragonfly steers mostly with forward/inverse models that **predict** prey motion; vision only corrects for surprises | PreyNet predicts **future** stages and turns-to-strike; each new turn is an observation that **corrects** the forecast (a causal GRU state update) | `preynet.py` heads `next_stage`, `tts` |
| **TSDN population vector** (Gonzalez-Bellido et al., *PNAS* 2013) | 8 pairs of descending neurons jointly encode prey **direction** as a population vector | The family-probability vector is drawn as a **Trajectory Compass**: each family is a direction, and the needle is the probability-weighted sum | `infer.py` → `family_probs`; UI compass |
| **CSTMD1 selective attention** (Wiederman & O'Carroll, *Curr Biol* 2013; Lancer et al., *J Neurosci* 2019) | A neuron **locks on** to one target among distracters; a target seen earlier on the same trajectory **primes** selection | (a) Attention pooling over turns, where the weights show *which turn primed the lock* (our explanation). (b) **Lock-on hysteresis** at inference, so one innocent-looking message can't make the warning flicker off | `preynet.py` `CstmdAttention`; `infer.py` `LockOn` |
| **Kleptoplasty** (Christa et al., *J Molluscan Stud* 2014) | *Costasiella kuroshimae* eats *Avrainvillea* algae and keeps **only the chloroplasts** in its cerata. In this species they are **short-term**: they degrade and the slug must keep feeding | The phone keeps **only a tiny adapter** (never the teacher model, never the data). Adapters carry a **half-life**: the UI's vitality bar fades until the reef "re-feeds" them with fresh mutations | `chloroplast.py`; manifest `half_life_hours` |

**Honesty notes for Q&A:**
- We don't claim the slug runs fully on sunlight. Research suggests the stolen chloroplasts may act more like a food store, and *C. kuroshimae* is a short-term retainer. That is exactly why our chloroplasts expire and get refreshed.
- The interception "internal model" work is from the Leonardo lab (HHMI Janelia). Cite the papers, not a university press release.

---

## 2. Taxonomy (single source: `contracts/taxonomy.json`)

**Families** (7 base classes + zero-day slots):
`benign`, `pig_butchering` (wrong number → romance → crypto), `bank_impersonation` (fraud alert → call this number / read me the code), `family_emergency` ("Hi Mom, new phone"), `job_task` (remote job → pay to unlock tasks), `toll_delivery` (unpaid toll or parcel), `carrier_support` (account suspended, SIM swap, OTP theft). Zero-day families get IDs like `zd_parking_boot`.

**Kill-chain stages** (labeled per turn): `benign` → `bait` (first contact) → `pivot` (rapport or identity) → `hook` (pretext, urgency, opportunity) → `strike` (link, money, code, gift card or credential ask).

**Index conventions (everyone uses these exact definitions):**
- `turns` is 0-indexed. `strike_turn` is the **0-based index** of the first `strike` turn, or `null` for benign conversations.
- A **prefix of length k** means the model has seen `turns[0:k]`, so the last turn seen is index k−1.
- A flag at prefix k is **early** if and only if `k ≤ strike_turn` (the strike hasn't arrived yet).
- **Lead time** of a flag at prefix k = `strike_turn − (k − 1)`. Flagging right before the strike gives 1; flagging at the strike itself gives 0.

---

## 3. Data (B generates it; A specifies, audits and owns the splits)

### 3.1 Volumes (v1 target, about 2,000 conversations)
- 6 base scam families × 150 = 900 scam conversations (length 4–10 turns, median 6)
- 900 benign, of which **at least 40% are hard negatives**: real wrong-number texts that stay harmless, legitimate bank or carrier alerts that tell you to use the official app, real delivery notices, real recruiters, golf-plan chats that look like turn 1 of pig butchering
- One family (`job_task`) is **held out entirely** for the zero-day LOFO experiment (§6.3)

### 3.2 Diversity knobs (the Algae factory randomizes them per call)
persona (age, region: Dallas, campus, rural), channel (SMS, iMessage, WhatsApp), scammer patience (2–6 turns before the strike), victim behavior (cooperative, skeptical, silent), typos, emoji, slang, a 10% Spanish share (stretch), brand names from `contracts/taxonomy.json`.

### 3.3 Fighting synthetic-data leakage (the judges will ask)
1. **Cross-generator test set:** train only on Nemotron output. `data/test_human/` (40+ conversations hand-written by the team plus a few made with a *different* LLM and different prompt style) is **test only**. Report the in-distribution vs cross-generator gap honestly.
2. **Conversation-level splits** (70/15/15, stratified by family). Prefixes of one conversation never cross splits. A unit test enforces this.
3. **Near-duplicate removal:** drop conversations whose mean-turn embedding has cosine > 0.95 with any other.
4. **Label-word leakage check** (`data-auditor`): generated text must not contain stage or family words like "scam", "bait" or "pig butchering".
5. Benign and scam conversations come from the **same generator with the same prompt skeleton**, so style alone can't separate them.

### 3.4 Record format: see `contracts/schemas/conversation.schema.json`

---

## 4. PreyNet (the Dragonfly model)

### 4.1 Inputs
- Each turn's text gets a role prefix: `"[THEM] ..."` or `"[ME] ..."`. It is embedded with **`all-MiniLM-L6-v2`** (384-d, mean pooling, L2-normalized) and cached to `ml/.cache/emb/<sha1>.npy` (gitignored).
- Per-turn vector = `[emb(384), is_them(1)]` → 385-d. Max 12 turns, left-truncated.
- **Embedding parity rule:** the browser uses `Xenova/all-MiniLM-L6-v2` through transformers.js. Before training the final model, A checks cosine(python, browser) > 0.99 on 20 sample texts. If the quantized browser model drifts, either load the fp32 ONNX in the browser or compute training embeddings with the same ONNX file through onnxruntime in Python.

### 4.2 Architecture (about 160k params, about 0.6 MB fp32: the "1 MB brain")
```
turn_vec(385) ─► Linear 385→128 + GELU + Dropout 0.1
              ─► GRU(128→128, 1 layer, unidirectional = causal, streams turn by turn)
              ─► states h_1..h_t
CstmdAttention: q = W_q h_t ; α_i = softmax(q·W_k h_i / √128) over i ≤ t ; pooled = Σ α_i h_i
features f = [pooled(128) ; h_t(128) ; mean_emb(384)]  → 640-d   ← exported as ONNX output "features"
heads (from f):
  family   : Linear 640→7     (softmax)
  next_stage: Linear 640→5    (softmax over benign/bait/pivot/hook/strike)
  tts      : Linear 640→5     (ordinal buckets: 0, 1, 2, 3+, none)
```

### 4.3 Training examples
Every conversation of length n yields n prefixes (turns 1..k for k = 1..n). Labels per prefix: final `family`, `next_stage` (the stage of turn k+1, or `benign` at the end), and `tts` (strike_turn − k, bucketed; `none` for benign or past-strike). Only prefixes with k ≤ strike_turn are used for `tts`.

### 4.4 Loss and optimization
`L = CE(family) + 0.5·CE(next_stage) + 0.5·CE(tts)`, with class weights from inverse frequency. AdamW (lr 2e-3, wd 1e-4), batch 64, up to 20 epochs, early stopping on **val EWR@2**. CPU training takes under 2 min with cached embeddings. Run seeds {0, 1, 2} and report mean ± std.

### 4.5 Calibration (T-Mobile's "honest confidence")
- **Temperature scaling** per head, fit on **val** (never test). Saved in `ml/artifacts/temperature.json`.
- `risk = 1 − P(benign)` after calibration.
- `confidence_band`: `high` if risk ≥ 0.80 or ≤ 0.10; `uncertain` if the top family prob < 0.5 or 0.35 ≤ risk < 0.80; otherwise `low`. The UI shows "We're not sure yet" for `uncertain`; that's honesty, not a bug.
- Report **ECE (15 bins)** before and after, plus a reliability diagram (pitch chart #3).

### 4.6 Lock-on hysteresis (CSTMD1)
`locked` becomes true when risk ≥ θ_lock (0.70, tuned on val) and becomes false only after risk < θ_release (0.40) for **2 consecutive scammer turns**. Report a **flicker rate** (warnings that disappear and reappear) with and without lock-on.

### 4.7 Explanations
- `attention`: α over turns. The UI highlights the turn that primed the lock.
- `evidence`: up to 3 `{turn_idx, reason}` items. Reasons come from cheap rules applied to the highest-attention turns (urgency words, an identity switch, a money or crypto mention, a link present, a request to move to another app). No LLM call is needed on device.

---

## 5. Leaf Sheep: chloroplast adapters (klepto-distillation)

### 5.1 Pipeline (the `/v1/zero-day` job: B orchestrates, A implements `train()`)
1. **Alert:** one sentence, e.g. *"Texts claim UTD parking issued a boot; pay $45 at a link within 1 hour."*
2. **Algae (Nemotron, multi-step):** plan 8 mutation axes → generate N positive conversations (default 120) **plus** N hard-negative look-alikes (legitimate parking notices) → **critique pass** (Nemotron as judge: realism 1–5, label correctness; drop anything < 4) → dedupe.
3. **Feature extraction:** run frozen PreyNet → `features` (640-d) for every prefix k ≥ 1.
4. **Train the chloroplast head:** `Linear 640→32 → GELU → Linear 32→1`, weighted BCE. Positives = prefixes of new-family conversations; negatives = hard negatives + a random 1,000 base benign prefixes + 500 prefixes from other scam families. 300 steps of AdamW (lr 3e-3). Target: **< 10 s on a laptop CPU**, about 20.6k params ≈ **82 KB** fp32.
5. **Threshold** = the value that gives 1% FPR on a held-out 20% of the synthetic negatives.
6. **Publish** a manifest (`contracts/schemas/chloroplast.schema.json`) with weights base64-encoded as float32 little-endian, plus metrics, train seconds, size and sha256.

### 5.2 On-device use (C implements in JS; A provides a reference implementation in `infer.py`)
`p_new = sigmoid(W2·gelu(W1·f + b1) + b2)`. Final risk = max(base risk, each chloroplast's p_new ≥ its threshold). The family label comes from whichever wins. Vitality = 0.5^(age_hours / half_life_hours) is **display only**: decay **never** silently turns protection off. It prompts a refresh.

### 5.3 Stretch (only if P3 finishes early)
A real **LoRA** (rank 4) on `CstmdAttention.W_q`, merged into a per-chloroplast ONNX. Until this ships, never call chloroplasts "LoRA". Call them **adapter heads**.

---

## 6. Evaluation (`make eval` → `ml/artifacts/eval_summary.json`)

### 6.1 Baselines
| ID | Model | Represents |
|---|---|---|
| B0 | Keyword/regex rules (URL, $, gift card, code, crypto, "click") on the latest message | Classic filters that wait for the strike |
| B1 | TF-IDF + logistic regression on the latest message only | Per-message ML filter |
| B2 | MiniLM(latest message) + LR | A strong per-message filter |
| B3 | Mean of MiniLM over turns + LR | Context without order (ablation) |
| **PreyNet** | §4 | Trajectory forecasting |
| Ablations | PreyNet without attention, without lock-on, without multitask | What each biology piece adds |

### 6.2 Metrics (implemented once in `metrics.py`; Codex independently re-implements EWR@k and lead time as a cross-check test)
- **EWR@k (Early Warning Rate):** the fraction of scam conversations flagged at some prefix ≤ k **and** before `strike_turn`. The threshold is set so the **benign false-alarm rate is 1%**, conversation-level, on val. Report k = 1..6. → **Pitch chart #1** (lines per model).
- **Lead time:** using the §2 definition for the **first** flag in each scam conversation, take the mean over all scam conversations. A conversation flagged only at or after the strike (or never) counts as 0. → **headline number**.
- **Strike recall:** flagged at any prefix ≤ strike_turn (the "is it caught at all" number).
- **Hard-negative FPR:** false alarms on hard negatives only.
- **ECE** before/after temperature scaling. → **Pitch chart #3**.
- **Flicker rate** with and without lock-on.
- **Cross-generator gap:** every metric on `test` (Nemotron) vs `test_human`.

### 6.3 Zero-day experiment (LOFO) → **Pitch chart #2**
1. Train the base PreyNet **without** `job_task`.
2. Measure EWR@k on the held-out `job_task` test conversations (expected: weak).
3. Run the §5.1 pipeline from a one-sentence `job_task` alert, **never** touching the held-out test conversations.
4. Re-measure with the chloroplast. Also check base-family metrics and hard-negative FPR don't regress.
5. **Sample-efficiency curve:** N ∈ {25, 50, 100, 200} synthetic positives → EWR@3. Report **time-to-protection** (generation + training wall clock).

### 6.4 `eval_summary.json` shape (C's charts read exactly this)
```json
{
  "generated_at": "ISO-8601",
  "dataset": {"version": "v1", "n_conversations": 0, "n_test": 0, "n_test_human": 0},
  "models": {
    "B0": {"ewr_at_k": [0,0,0,0,0,0], "lead_time": 0, "strike_recall": 0, "hard_neg_fpr": 0},
    "PreyNet": {"ewr_at_k": [], "lead_time": 0, "lead_time_std": 0, "strike_recall": 0,
                "hard_neg_fpr": 0, "ece_before": 0, "ece_after": 0,
                "flicker_rate": 0, "flicker_rate_no_lock": 0,
                "test_human": {"ewr_at_k": [], "lead_time": 0}}
  },
  "zero_day": {"family": "job_task", "base_ewr_at_3": 0, "chloroplast_ewr_at_3": 0,
               "sample_efficiency": [{"n": 25, "ewr_at_3": 0}], "time_to_protection_s": 0},
  "reliability": {"bins": [], "acc": [], "conf": []}
}
```

---

## 7. Export and runtime
- `make export` → `ml/artifacts/preynet.onnx` (opset 17, dynamic turn axis, outputs `family_logits`, `stage_logits`, `tts_logits`, `attention`, `features`) plus `temperature.json`.
- **Parity test:** onnxruntime vs PyTorch on 50 random prefixes, max abs diff < 1e-4.
- `ironguard_ml.infer.load()` / `Model.score(turns, chloroplasts)` returns a dict that validates against `score_response.schema.json`. **`stub.py` has the same signature from H1** (keyword heuristics) so B and C are never blocked.

---

## 8. What we highlight (the order of the demo)
1. **The lead-time chart.** PreyNet's line rises at turn 1–2, while per-message filters stay flat until the strike.
2. **A live Photon forward.** A judge forwards turn 2 of a "wrong number" chat; the reply says *"72% heading toward a pig-butchering scam, about 2 turns before a money ask. Uncertain? No, high confidence. Why: identity switch at turn 2."*
3. **A live zero-day.** A judge types a new scam idea → Algae → chloroplast in about 2 min → the phone flags it; the DevTools Network tab shows **no message text leaving the browser**.
4. **The reliability diagram:** "when we say 80%, we're right about 80% of the time."
5. **Honest limits:** the cross-generator gap and what we'd need from real (consented) data.

---

## 9. Appendix: Algae prompt skeletons (B implements; A reviews)

**Generator (Nemotron 3 Nano; JSON mode or strict JSON instruction; temperature 0.9, top_p 0.95):**
```
You write realistic text-message conversations for training a scam-defense model.
Return ONLY JSON: {"conversations":[{"family":..., "channel":..., "turns":[{"sender":"them|me","text":...,"stage":"benign|bait|pivot|hook|strike"}]}]}
Write {n} conversations. Family: {family} — {family_description}. Persona: {persona}. Channel: {channel}.
Scammer patience: strike at turn {strike_turn} (1-indexed among THEM turns). Victim style: {victim_style}.
Rules: natural texting (typos/emoji ok), no words like "scam", "fraud", "phishing", "bait" in the messages,
use placeholder-safe fake numbers (555-01xx) and fake domains (.example, .test), vary length 4-10 turns.
For benign: same style and openings that LOOK like bait but stay legitimate; stage is "benign" for every turn.
```
**Critic (Nemotron 3 Super, temperature 0.2):** score each conversation for `realism` (1–5) and `label_correct` (bool), and return the IDs to drop.

**Mutation planner (zero-day):** from the alert, produce 8 axes (sender identity, pretext, payment rail, urgency device, channel switch, language register, link style, victim profile), then sample combinations for the generator.

---

## 10. Sources
- Mischiati M., Lin H.-T., Herold P., Imler E., Olberg R., Leonardo A. (2015). *Internal models direct dragonfly interception steering.* Nature 517, 333–338. https://www.nature.com/articles/nature14045
- Gonzalez-Bellido P.T., Peng H., Yang J., Georgopoulos A.P., Olberg R.M. (2013). *Eight pairs of descending visual neurons in the dragonfly give wing motor centers accurate population vector of prey direction.* PNAS 110(2).
- Wiederman S.D., O'Carroll D.C. (2013). *Selective attention in an insect visual neuron.* Current Biology 23(2).
- Lancer B.H., Evans B.J.E., Fabian J.M., O'Carroll D.C., Wiederman S.D. (2019). *A target-detecting visual neuron in the dragonfly locks on to selectively attended targets.* J Neurosci. Preprint: https://www.biorxiv.org/content/10.1101/496562v1
- Christa G. et al. (2014). *Functional kleptoplasty in a limapontioidean genus: phylogeny, food preferences and photosynthesis in Costasiella.* J Molluscan Studies. doi:10.1093/mollus/eyu026
- Google Messages scam detection with Gemini Nano: https://9to5google.com/2026/02/25/google-messages-scam-detection-gemini/
