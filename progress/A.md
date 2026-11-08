# progress/A.md: Member A (double), Dragonfly (ML lead)

> Only member A (and their agents) edits this file. Append; don't rewrite history.
> Format for each entry: `[HH:MM][P<phase>] what changed | skipped | unverified`

## Now
- Phase: P0
- Working on:
- Blocked by:

## Log
- 

## Requests (changes I need from another owner; they pick these up)
<!-- e.g. - [ ] @B contracts/score_response: add optional field `latency_ms` (number). Why: HUD shows it. -->

## Handoffs (things I've shipped that others can now use)
<!-- e.g. - [x] ml/artifacts/preynet.onnx v2 (features output = 640-d) merged in M2 -->

- [23:36][P0] Created Python 3.11 uv package odonata_ml, layout placeholders, deterministic score stub, zero-weight chloroplast trainer, and ironguard_ml.stub compatibility imports. Added contract, heuristic, attention, adapter packing/checksum and metadata tests. | Skipped real training, inference, calibration and evaluation; layout modules intentionally empty. | make validate passes (7 schemas, 8 examples); make check-ml passes (ruff and 14 tests). Real ML behavior and cross-platform dependency installation remain unverified. Stub outputs are integration fixtures, not measured model performance.

- [01:55][P1] **A1a data pipeline** (branch `a/data`, built on A0 `a/ml-stub`; I committed A0 first and renamed `odonata_ml` to `ironguard_ml`).
  - **Done:** `ml/ironguard_ml/data.py` (loader with schema + semantic checks, `make_prefixes`, `stratified_split`, `exclude_held_out`, `drop_near_duplicates`, `prepare_splits`), `ml/ironguard_ml/features.py` (role-prefixed MiniLM, L2-normalized, sha1 cache in `ml/.cache/emb/`), 64 tests, `data/seed/seed.jsonl` (30 conversations, 6 families x 3, 12 benign of which 6 hard negatives, all schema-valid). Reviewed by data-auditor, leakage-hunter, ecc:code-reviewer and ponytail-review; real findings fixed.
  - **Skipped:** browser/Python embedding parity check (§4.1, cosine > 0.99 on 20 texts); first-turn overlap check across splits; hash-based split assignment.
  - **Unverified:** speed and cache size at the real ~2,000-conversation scale; `make check-ml` uses a fake encoder (the real MiniLM test is opt-in: `IRONGUARD_REAL_ENCODER=1 uv run pytest tests/test_features.py -k real`, passed once).
  - **Known limits:** the 30-row seed is a smoke fixture, not training data. It is labeled `other_llm` (honest; `human` stays reserved for `data/test_human/`). Per-family val/test are mostly empty on it. `job_task` has 3 seed rows, so its LOFO test pool is tiny until Nemotron data lands. Split quotas shift as the corpus grows: refit after new data, keep split `seed` fixed (0) across training seeds 0/1/2.

## Handoffs (A1a)
- `from ironguard_ml.data import load_corpus, prepare_splits, make_prefixes, exclude_held_out, stratified_split, drop_near_duplicates, tts_bucket, Conversation, Turn, Prefix, DataError`
- `from ironguard_ml.features import turn_vectors, prefix_sequence, mean_turn_embedding, embed_texts, TURN_DIM (385), EMB_DIM (384), MAX_TURNS (12)`
- Standard call: `splits, dropped = prepare_splits(None | "v1", mean_turn_embedding, seed=0)` -> `splits["train"|"val"|"test"|"test_human"]` (tuples of `Conversation`). `version=None` loads `data/seed/` only; a version loads `data/generated/<v>/` only and fails if it is empty. Zero-day (`zd_*`) families are rejected from the base corpus.
- For LOFO: `exclude_held_out(splits, "job_task")` removes job_task from train/val and adds `["held_out"]` = every job_task conversation. Do not feed `held_out` to the chloroplast.
- Per prefix: `make_prefixes(conv)` -> `Prefix(k, family, next_stage, tts, early, lead_time)`. **`tts` = bucket of `strike_turn - k` (= lead time - 1; "0" means the strike is the next turn). Use `early` as the mask for the tts head** (post-strike and benign are both "none").
- Model input for prefix k: `prefix_sequence(turn_vectors(conv.turns), k)` -> (<=12, 385). Pass `model_id=` with any non-default encoder (e.g. ONNX) so cache entries never mix.

## Requests (A1a)
- [ ] @B `Makefile` `validate-data`: the glob `data/generated/*/*.jsonl` misses files placed directly under `data/generated/`. Why: silent skip of a dataset file. Also: please keep zero-day (`zd_*`) output out of `data/generated/<v>/`; the loader now rejects it there.

## A1b · Baselines and first evaluation (`a/baselines`)
- [02:05][P1] **Done:** created `a/baselines` from the clean member checkout and ran `git rebase a/data` before implementation. Fetched origin; `origin/main` has no `data/generated/v1`, so the real-encoder evaluation uses the 30-row seed smoke fixture. No generated data or other owner's files were edited.
- Implemented `ml/ironguard_ml/baselines.py`: `Baseline("B0"|"B1"|"B2"|"B3").fit(train).score(conversations)` returns one list of prefix risks per conversation. B0 regexes use latest text; B1 fits TRAIN-only TF-IDF+LR on latest raw text; B2 fits LR on latest role-prefixed MiniLM vector; B3 fits LR on the causal arithmetic mean of seen MiniLM vectors. Uses existing dependencies only.
- Implemented `ml/ironguard_ml/metrics.py`: `ScoredConversation`, `threshold_at_fpr`, `ewr_at_k`, `lead_time`, `strike_recall`, `benign_fpr`, `hard_neg_fpr`, `summarize`. Thresholds use benign VAL conversation maxima, the >= alarm comparison, and an empirical FPR cap of 1% without interpolation; ties can force lower FPR or complete abstention. No benign VAL rows is an error. Empty metric denominators are `None`/JSON null.
- Implemented `ml/ironguard_ml/evaluate.py`: `evaluate(splits, dataset)` and the `make eval` CLI. Uses `prepare_splits` (dedupe before splitting, split seed 0), fits TRAIN only, freezes each model's VAL threshold, reports TEST and test-only human metrics in the §6.4 baseline fields. Adds thresholds, achieved VAL FPR, abstention flags, split counts/denominators and dataset provenance. Missing v1 falls back to seed; an existing but empty/invalid version fails rather than silently falling back. Seed output carries `available: false, display: "--"` so it is not presented as pitch evidence. Missing PreyNet/zero-day/calibration results are omitted/null/empty rather than invented.
- **Validation:** `make validate` passes (15 schemas, 16 examples), `make check-ml` passes (78 passed, 1 opt-in real-encoder test skipped), and `make eval` passes with the actual all-MiniLM-L6-v2 encoder and schema-valid JSON. Added small hand-computed metric cases, an independent zero-based EWR/lead-time cross-check, threshold tie/conversation-max tests, causal baseline feature tests, and a wiring test proving that changing TEST/human data cannot change thresholds or TRAIN fitting. Actual MiniLM B2/B3 evaluation covers the real dependency despite the opt-in parity/cache test being skipped.
- **Review:** read every added source/test file using ECC's local code-review checklist; reviewed excess code and ownership. Ran the repository's read-only Claude Opus leakage-hunter review: no leakage found. Fixed its confirmed issue by marking seed output unavailable, corrected the embedding docstring, removed unnecessary prefix construction, and documented threshold-driven abstention. Strike recall was changed to follow the literal spec, resolving its other concern. The Ponytail review skill is absent from the available catalog and local skill/plugin locations; its named command was skipped, with a manual minimal-code review performed instead. No secrets or raw conversation text are logged by the new modules.
- **Measured smoke results only:** train/val/test = 20/6/4, test_human = 0, near-duplicates dropped = 0. TEST has only 2 scams, 2 benign and 1 hard negative; VAL has only 2 benign. B0/B1/B2/B3 lead times = 0/1/5.5/5.5; hard-negative FPRs = 0/1/1/1. All achieved benign VAL FPRs are 0. These tiny-sample results are NOT pitch claims or evidence of population-level 1% FPR.
- **Skipped / unverified:** v1-scale results and cross-generator gap (data absent); PreyNet, LOFO, calibration, ECE and flicker metrics (outside this baseline task); browser embedding parity and statistical confidence at scale. `ml/artifacts/eval_summary.json` was generated locally but is intentionally untracked: `ml/AGENTS.md` permits artifact commits only at merge windows. No merge, push or PR was performed (§F only).

## Requests / decisions (A1b)
- [ ] @A spec clarification: §6.2 calls strike recall "caught at all" but explicitly requires flag prefix <= strike_turn. The implementation follows that literal inequality, which under §2 excludes the strike message and equals unlimited-k EWR. If detection ON the strike should count, explicitly revise §6.2 to `k <= strike_turn + 1` before changing the metric and regenerating artifacts.

## Handoffs (A1b)
- Run `make eval` (v1 if present, otherwise clearly marked seed smoke) or `cd ml && uv run python -m ironguard_ml.evaluate --data ../data/seed --out artifacts/eval_summary.json`.
- `ScoredConversation(conversation, tuple(risks))` validates one finite [0,1] risk per turn; prefix indices are 1-based, `strike_turn` is 0-based. `summarize(rows, threshold)` returns six EWR values plus lead time, literal-spec strike recall and hard-negative FPR. Reuse `threshold_at_fpr(val_rows)` for future PreyNet comparisons; never pass TEST rows.
- `Baseline.fit` is binary benign-vs-scam and uses all base families; this is not the separate LOFO experiment. All four models share the same conversation splits and threshold procedure.
- C/B consumers: honor `available: false` / `display: "--"` on seed smoke summaries; handle null metrics and `zero_day: null`. Only `models.B0`–`B3` are populated. The generated local artifact is ready for inspection and regeneration/commit at the member's merge window.

- [03:49][P1] M1 preparation: inventoried every local and remote-tracking branch against a/main; outstanding local branches are a/ml-stub, a/data and a/baselines (no outstanding remote-tracking branches). Both auxiliary worktrees are clean. Commit the generated seed-smoke eval_summary.json at this authorized merge window. | Skipped new model work and PR creation (member will open PR). | make validate passes (15 schemas, 16 examples); make check-ml passes (78 passed, 1 real-encoder opt-in test skipped). Artifact is unavailable for pitch claims; real v1 data and PreyNet remain unverified. Merge/rebase/push and cleanup pending.

- [03:50][P1] M1 result: merged a/ml-stub, a/data and a/baselines into a/main; rebased onto origin/main without conflicts and pushed successfully. Removed both auxiliary worktrees. Rebase changed commit IDs, so git branch -d refused cleanup; git cherry confirms every source commit is patch-equivalent in a/main, and diff against a/baselines is empty across all A-owned paths. Delete these verified duplicate branch pointers after final push. | Validation: make validate passes (15 schemas, 16 examples), make check-ml passes (78 passed, 1 optional real-encoder test skipped), make smoke passes (3 API tests); web/bridge typechecks skipped because packages are absent. Removed the untracked API lockfile generated by smoke; no other owner files retained. | Skipped PR creation per requested manual handoff. Existing branch review results remain documented above; Ponytail skill unavailable. No real v1/PreyNet/pitch-quality claims or browser parity verified. Final progress-only commit and script rerun complete this handoff.

- [03:52][P1] User requested merging all changes into shared main. All A work is consolidated in a/main; creating the M1 PR and using GitHub merge without bypassing required checks. Rechecked source correctness, causal baseline inputs, VAL-only thresholds, ownership and minimal implementation; no blocking findings. make validate passes (15 schemas, 16 examples), make check-ml passes (78 passed, 1 optional real-encoder test skipped), git diff --check passes; prior smoke passed. | Skipped unavailable named Ponytail skill (manual bloat review performed); no model changes or fabricated pitch claims. | Real v1/PreyNet and browser parity remain unverified; GitHub merge outcome will be verified after submission.

## A2 · PreyNet, training, calibration, inference, evaluation (`a/preynet`)
- [04:19–05:10][P2] **Done:** `ml/ironguard_ml/preynet.py` (Linear 385→128+GELU+Dropout → causal GRU 128 → `CstmdAttention` → 640-d features → family 7 / next_stage 5 / tts 5; 192k params, slightly over the spec's "about 160k" because the spec'd layers add up to that), `train.py` (all prefixes, `CE_f + 0.5·CE_s + 0.5·CE_tts`, inverse-frequency class weights from TRAIN, AdamW 2e-3/1e-4, batch 64, ≤20 epochs, patience 5, early stop on VAL EWR@2 with VAL NLL as tie-break, seeds 0/1/2; ships the best-VAL seed), `calibrate.py` (per-head temperature by LBFGS on VAL, 15-bin ECE, reliability bins), `infer.py` (`load(dir, encoder=None).score(turns, chloroplasts)`; LockOn; §4.5 bands; rule evidence on the top-attention THEM turns; §5.2 chloroplast reference math; malformed adapters are skipped), `metrics.flicker_rate`, and `evaluate.py` (B0–B3 + PreyNet + `PreyNet_no_attention` + `PreyNet_no_multitask`, means over 3 seeds). 108 tests pass (+30).
- **Decisions (user-approved plan, plus a leakage fix):** (1) tts loss covers early scam prefixes **plus benign prefixes ("none")**; post-strike prefixes are excluded. (2) flicker = share of warned TEST conversations whose warning goes off and back on. (3) ECE/reliability = family-head top-label on TEST prefixes; `ece_risk_*` adds binary calibration of risk. (4) evaluate re-trains in-process (27 s total); `shipped_matches_eval: true` confirms it matches `preynet.pt`. (5) **θ_lock = VAL 1%-FPR threshold on calibrated risk (0.986 for the shipped seed)**, saved as `theta_lock` in `temperature.json` (fallback 0.70), logged in MODEL_SPEC §4.6. A fired chloroplast also locks.
- **Privacy:** inference embeds with `cache_dir=None`, so nothing derived from customer text touches disk.
- **Express drop:** `ml/artifacts/preynet.pt` + `temperature.json` merged into `a/main` and pushed (`88bfd11`). The later `theta_lock` artifact update and eval summary are on `a/preynet` for the next merge window.
- **Reviews:** leakage-hunter found **no train/test leakage** and reproduced seed 0 exactly. Fixed its CONFIRMED items (θ_lock vs reported operating point, TEST `fpr`, B0 `native` point, job_task note, schema → Request). /code-review: fixed chloroplast containment, PreyNet `abstains`, single-seed std NaN, shipped-model check, duplicate encode path. /ponytail-review: fixed "fired adapter never locks" and the duplicate `BENIGN`. contract-guardian: PASS (ownership, contracts, secrets).
- **Headline (make eval, v1: 705/152/152 split, TEST 65 scam / 87 benign / 33 hard-neg, 7 near-dupes dropped, test_human 0). Numbers exactly as produced, 3 dp:**
  - PreyNet EWR@1..6 = 0.374, 0.482, 0.564, 0.590, 0.595, 0.610; lead time 2.149 ± 0.100 turns; strike recall 0.615; TEST fpr 0.023; hard-neg FPR 0.061; ECE 0.088 → 0.040 (risk ECE 0.080 → 0.057); flicker 0.000 with lock-on vs 0.104 without.
  - B3 (mean-MiniLM) lead 1.800, B2 0.985, B1 0.200; B0 abstains at the 1% cap (native point: lead 2.231 at TEST fpr 0.264).
  - Ablations **beat** full PreyNet: no_attention lead 2.313, EWR@2 0.549; no_multitask lead 2.262, EWR@2 0.513 (but fpr 0.038). With 65 TEST scams this is partly noise, **but "attention/multitask help" is not supported by this data. Don't claim it.**
- **Skipped:** LOFO zero-day (`zero_day: null`), `chloroplast.py`, `export.py` + ONNX parity, browser embedding parity, bootstrap CIs, single VAL pass in eval (perf nit), atomic two-file artifact save.
- **Unverified / honest limits:** `data/test_human/` is empty, so the cross-generator gap is unmeasured, and on a hand-written "wrong number → crypto" chat the shipped model gave risk 0.004. v1 scams score 0.84–1.0 already at turn 1 on TRAIN, which suggests style separability in synthetic data. Achieved VAL FPR is 0/87 (the 1% cap allows 0 alarms), so TEST fpr 0.023 is the honest number. API end-to-end with `IRONGUARD_MODEL=preynet` is not verified by me (B2).

## Handoffs (A2)
- `from ironguard_ml.infer import load` → `load("ml/artifacts").score(turns=[{"sender": "them"|"me", "text": str}], chloroplasts=[manifest...])` returns a valid `score_response`; `model.name = "preynet"`, version `0.1.0-v1-s2`. Raises `FileNotFoundError` if artifacts are missing and `ValueError` on bad turns. First call loads MiniLM (HF cache).
- `ml/artifacts/temperature.json`: `{family, next_stage, tts, theta_lock}`. **C (browser):** use `theta_lock` for the lock threshold (not 0.70), θ_release 0.40, release only after 2 consecutive THEM turns below it, "me" turns ignored. A fired chloroplast locks.
- `eval_summary.json` (C's charts): PreyNet adds `lead_time_std`, `fpr`, `ece_*`, `ece_risk_*`, `flicker_rate(_no_lock)`, `seeds[]`, `abstains`, `shipped_matches_eval`; ablation keys `PreyNet_no_attention`, `PreyNet_no_multitask`; B0 has `abstains: true` + `native`. `reliability` lists non-empty bins only (+`count`). `zero_day` is `null` and test_human metrics are `null`: show `--`.
- Zero-day (next step): the shipped model **has seen job_task**. LOFO must train a separate base with `exclude_held_out(splits, "job_task")`.

## Requests (A2)
- [ ] @B `contracts/schemas/metrics.schema.json`: (additive) describe the §6.4 shape (`generated_at`, `dataset`, `models.*.ewr_at_k`, `zero_day` as object-or-null, `reliability{bins,acc,conf,count}`) so `make eval` validation catches shape drift. Why: today it only requires `models`.
- [ ] @B `PROGRESS.md` → Decisions: "θ_lock = VAL 1%-FPR threshold (temperature.json `theta_lock`), see MODEL_SPEC §4.6."
- [ ] @A (self) fill `data/test_human/` (40+ human-written conversations) before any cross-generator claim.

## A2-x · Independent metrics cross-check (`a/metrics-check`)
- [04:19][P2] **Done:** added `ml/tests/test_metrics_crosscheck.py` using only MODEL_SPEC §2/§6.2 for EWR and lead-time logic. Did not read or modify `ml/ironguard_ml/metrics.py`; imported its public API as a black box. Generates exactly 200 deterministic random flag sequences (seed 20261108), compares each sequence and mixed batches at k=1..6 with absolute tolerance 1e-9 and no relative tolerance. Covers first-turn strikes, last-chance warning, on/after-strike flags, missed scams, flickering flags, k=6 boundary, 20-turn conversations and benign denominator exclusion.
- **Diagnostics:** a mismatch prints flags, zero-based strike index, k, threshold, seed, expected and actual. Exhaustive single-conversation search returns the smallest witness by length, strike and flags; batch witnesses are deletion-minimal. An in-memory injected off-by-one EWR bug was detected and reduced to flags=(True,), strike_turn=0. Simulated an absent module and verified the clear skip message: re-run after A2's express drop. Existing-module import errors are not swallowed.
- **Validation / review:** `make validate` passes (15 schemas, 16 examples); `make check-ml` passes (ruff, 91 passed, 1 existing optional real-encoder test skipped); `git diff --check` and the ownership guard pass. Reviewed the entire new file against ECC's local code-review checklist and manually checked bloat; no blocking findings. Only A-owned paths changed. Test commit: `5a89802`.
- **Skipped:** Ponytail review skill is absent from the available catalog and local skill/plugin search; performed manual bloat review instead. No dependency changes, artifact generation, PR, push or merge. The pre-existing untracked `api/uv.lock` in the member checkout was left untouched.
- **Unverified / handoff:** the current branch's metrics pass; A2's future implementation is not yet verified. Re-run `cd ml && uv run pytest -q -rs tests/test_metrics_crosscheck.py` after A2's express drop. Public test helpers are `reference_ewr(cases, k)` and `reference_lead_time(cases)`, where each case is `(tuple[bool, ...], strike_turn | None)`. No production code consumes these helpers.

## M2 · Member merge window
- [04:53][P2] **Done:** verified member A; inventoried all local branches and worktrees, including names outside a/. The complete outstanding local list was a/preynet (4 commits) and a/metrics-check (2 commits); all three worktrees were clean, so no finish-work commits were needed. Merged both into a/main with scripts/merge-window.sh; preserved both appended sections in the sole conflict (progress/A.md). Rebase onto origin/main succeeded without conflicts; pushed a/main and removed both merged worktrees and branches with git worktree remove / git branch -d.
- **Validation:** make validate passed (15 schemas, 16 examples); make check-ml passed (ruff, 121 passed, 1 optional real-encoder test skipped); UV_NO_SYNC=1 make smoke passed (3 API tests and web/bridge typechecks); git diff --check passed. Merge diff contains only A-owned files. No model or artifact changes beyond the reviewed source branches.
- **Skipped:** PR creation (user requested a manual compare-link handoff). Remote member branches are not local work branches: origin/c/main had one C progress commit at initial inventory; fetch then revealed B M2 integration on origin/b/main. Left both for their owners. Source-branch review findings are documented above; named Ponytail skill remains unavailable, and the merge/conflict resolution received a manual correctness and bloat check.
- **Unverified:** optional real-encoder test, ONNX/browser parity, human cross-generator evaluation, LOFO zero-day and real-model API integration remain outside this merge-window validation. Final progress-only commit and script rerun will push this record; no shared-main push or PR merge requested.

## M2 · Post-merge sync
- [05:23][P2] **Done:** confirmed member A and clean checkout; switched to a/main, pulled origin/main with rebase (fast-forward to 8dfcbbb), and pushed with the requested force-with-lease. Only a/main and its single worktree remain, so no worktree branches needed rebasing and no conflicts occurred. `make sync` passed: dependency installation, contract validation (15 schemas, 16 examples), API smoke (3 tests), and web/bridge typechecks. `make check-ml` passed (ruff, 121 tests passed, 1 skipped).
- **Skipped:** code fixes and PR creation (all checks green); B-only shared gate/phase updates do not apply. **Unverified:** the optional real-encoder test remains skipped; this sync uses stub API smoke and does not establish real-model integration, ONNX/browser parity, or model quality on the newly merged generated data.

## A3 · Chloroplast, LOFO, ONNX export (`a/chloroplast`)
- [05:45][P3] **Done (part 1, ONNX):** `ml/ironguard_ml/export.py` (`make export`) and `ml/tests/test_onnx_parity.py`. Opset 17, legacy TorchScript exporter (`dynamo=False`; `onnxscript` isn't needed). Parity over 50 random prefixes (lengths 1–12): shipped weights max abs diff **1.1e-5** (limit 1e-4); a random-init export is checked too. Fixed one bug: `torch.onnx.export` restores the wrapper's mode afterwards, so the wrapper must be built `.eval()`, or dropout comes back on in the caller's net (regression test added). `make validate` and `make check-ml` pass (123 passed, 1 skipped). **Express drop:** `ml/artifacts/preynet.onnx` (774 KB).
- **Unverified:** browser (onnxruntime-web) execution and the MiniLM embedding parity between Python and transformers.js (§4.1) are still not checked.

## Handoffs (A3): for jcubed (browser ONNX)
- **File:** `ml/artifacts/preynet.onnx` (opset 17, 774 KB, fp32). Same weights as `preynet.pt` (version **`0.1.0-v1-s1`**, retrained on full v1 at 05:40; the first express drop carried the older `-s2` model, so re-pull after the second drop).
- **Input:** `turn_vecs`, float32 `[batch, turns, 385]`, both axes dynamic. Use batch 1, every row a real turn (no padding), **left-truncate to the last 12 turns**. Per turn: `[MiniLM(role_text) (384, mean-pooled, L2-normalized), is_them (1.0 for "them", 0.0 for "me")]`, where `role_text = "[THEM] " + text` or `"[ME] " + text` (exact prefix, one space). Encoder: `Xenova/all-MiniLM-L6-v2`, `pooling: "mean", normalize: true`.
- **Outputs** (all for the LAST turn of the input):
  - `family_logits` `[batch, 7]`, order `benign, pig_butchering, bank_impersonation, family_emergency, job_task, toll_delivery, carrier_support`
  - `stage_logits` `[batch, 5]`, order `benign, bait, pivot, hook, strike` (this is the NEXT stage forecast)
  - `tts_logits` `[batch, 5]`, order `0, 1, 2, 3+, none` (turns to strike)
  - `attention` `[batch, turns]` sums to 1 over the input turns (turns dropped by truncation get 0 in the UI)
  - `features` `[batch, 640]`: the chloroplast input
- **Calibration** (`ml/artifacts/temperature.json`): `{"family": T_f, "next_stage": T_s, "tts": T_t, "theta_lock": θ}`. Probabilities = `softmax(logits / T)` per head. `risk = 1 − P_family(benign)`.
- **Per message:** run the model once on turns `[0..k]` after each new turn k (keep the per-turn risks; the lock needs history).
- **Lock-on (§4.6):** lock when `risk ≥ theta_lock` (**use the file value, currently 0.966, not 0.70**). Once locked, release only after **2 consecutive "them" turns** with `risk < 0.40`. "me" turns never change the counter. A fired chloroplast also locks.
- **Confidence band (§4.5):** `high` if risk ≥ 0.80 or ≤ 0.10; else `uncertain` if top family p < 0.5 or 0.35 ≤ risk < 0.80; else `low`.
- **Chloroplast (§5.2):** `p = sigmoid(W2·gelu(W1·f + b1) + b2)` with `f = features`, exact erf GELU. W1 `[hidden_dim × 640]` and W2 `[1 × hidden_dim]` are row-major, base64 float32 little-endian. Fired if `p ≥ manifest.threshold`; then risk = max(risk, p) and the family label comes from the chloroplast if `p` beats the base risk. Vitality is display-only.
- Reference: `ml/ironguard_ml/infer.py` (`Model.score`, `lock_states`, `confidence_band`) matches this; the parity test is `ml/tests/test_onnx_parity.py`.

- [05:57][P3] **Done (part 2):**
  - **Retrain.** The shipped `preynet.pt` came from the partial v1 (1,009 conversations, 10:35 UTC). B's full v1 (1,773 after dedupe) merged later, so `make eval` reported `shipped_matches_eval: false`. Ran `make train`, then `make export` and `make eval`: it ships seed 1, version `0.1.0-v1-s1`, `theta_lock` 0.966, and `shipped_matches_eval: true`.
  - **`ml/ironguard_ml/chloroplast.py`** (`train()` and `python -m ironguard_ml.chloroplast` benchmark):
    - frozen PreyNet features → 640→32→GELU→1, weighted BCE, 300 full-batch AdamW steps (lr 3e-3)
    - threshold = the larger of the 1%-FPR thresholds on a held-out 20% of (a) the caller's hard negatives and (b) the base negative bank, both by conversation, stepped in float32. It raises instead of publishing an adapter that can't reach 1%.
    - weights base64 float32 LE (w1|b1|w2|b2); 82,180 bytes, sha256, `train_seconds`, `val_auc`, `val_recall_at_1fpr`
    - **Timing:** the benchmark (120 pos / 120 neg, real MiniLM, memory only) gives **1.17–1.32 s total** (about 1.1 s features, 0.15 s fit) against the 10 s budget.
  - **`ml/artifacts/negative_bank.npz`** (3.9 MB, built by `make export`): whole TRAIN conversations, about 1,000 benign plus about 500 other-family prefixes, pinned to the sha256 of `preynet.pt`.
  - **`infer.apply_chloroplast()`:** the §5.2 reference, renamed from `chloroplast_probs` (no external callers).
  - **`ml/ironguard_ml/zero_day.py`:** LOFO and the sample-efficiency curve, written into `eval_summary.json → zero_day`.
  - **Tests:** `test_chloroplast.py` (schema, packing, threshold, determinism, input errors, stale bank, bank exclusion) and `test_zero_day.py` (proxy halves are disjoint, Algae near-copy filter, a wiring test showing that changing the test conversations can't change θ or the chloroplast threshold, seed-fixture skip). 141 passed, 1 skipped.
- **LOFO numbers (make eval, v1, source `v1_proxy` → `available: false`, NOT pitch evidence; means over seeds 0/1/2, 3 dp):**
  - job_task EWR@3: base (without job_task) **0.107 ± 0.013**, with chloroplast **0.867 ± 0.035**. Lead time 0.551 → 3.858 turns.
  - Sample efficiency EWR@3: N=25 0.804, N=50 0.871, N=100 and 200 `null` (the proxy only has 74 positives).
  - Chloroplast `train_seconds` 0.214 (cached embeddings).
  - **Regression on TEST without job_task (honest):** benign FPR 0.015 → **0.020**, hard-negative FPR 0.028 → **0.040**, base-family EWR@3 0.679 → 0.679. The chloroplast adds false alarms; the 1% cap is on synthetic held-out negatives, not TEST. Before the per-source threshold fix this was 0.033 / 0.068.
  - `time_to_protection_s` is null (no generation time for the proxy).
- **New PreyNet headline (full v1, TEST 266 conversations):** EWR@1..6 = 0.471, 0.591, 0.667, 0.719, 0.739, 0.739; lead time **2.799 ± 0.324**; TEST fpr 0.018; hard-negative FPR 0.034; ECE 0.072 → 0.025; flicker 0.000 with lock-on vs 0.067 without. B3 lead 2.113, B2 1.639. Ablations: no_attention 2.779, no_multitask 2.649. Full PreyNet now leads, but by less than one std, so still don't claim attention helps.
- **Reviews:**
  - leakage-hunter: **no train/test leakage**. Fixed all CONFIRMED items: per-source threshold, whole-conversation bank, no double group ids, the seed-fallback crash, seed stds, and the regression disclosure in `notes`. Also added the PLAUSIBLE Algae near-copy filter and refuse-at-saturation.
  - /code-review: fixed 8 of 10. Skipped: stub leniency (documented below) and the `infer.load`/`load_net` dedupe (`infer` needs checkpoint meta).
  - /ponytail-review: merged the two JSONL readers into `data.read_records`, added the seed-fallback test, used `loss.item()`.
  - contract-guardian: PASS on all 5 items.
- **Skipped:** real Algae zero-day data (B's; see Requests); `time_to_protection_s`; browser ONNX run; MiniLM Python↔browser embedding parity (§4.1); LoRA stretch (§5.3).
- **Unverified:** cross-generator (`test_human` is empty); `make eval` is not bit-reproducible in the 7th digit (a CPU float order effect seen by the leakage-hunter).

## Handoffs (A3): for ss (B3 `/v1/zero-day`)
- `from ironguard_ml.chloroplast import train, load_base` → `train(pos, neg, family_id, label, alert, progress_cb)` returns a schema-valid manifest.
  - `pos` and `neg` are lists of **conversation-schema dicts** (each side needs **at least 5**). Non-dicts raise `TypeError`; schema or semantic errors raise `DataError` (a `ValueError`); bad `family_id`, `label` or `alert` raise `ValueError`. The stub is more lenient.
  - `progress_cb(step, 300, loss)` fires every 10 steps.
  - A `ValueError` "cannot reach 1% FPR" means the data can't separate. Fail the job; don't publish.
- **Use the same artifacts as the scorer:** `train(..., base=load_base(Path(app.state.artifacts)))`. Otherwise it trains on `ml/artifacts` even when `IRONGUARD_ARTIFACTS` points elsewhere.
- **Needs** `ml/artifacts/negative_bank.npz` (it ships with the next drop). `load_base` is cached per process, so restart the API after a new `make export`.
- **Privacy:** it embeds in memory only and logs only the family id and timings.

## Requests (A3)
- [ ] @B Algae zero-day run for the LOFO: alert *"Texts offer an easy remote job, then ask you to pay a deposit to unlock higher-paying tasks."* → `data/generated/zd_job_task/*.jsonl` with 200 positives (`family: "zd_job_task"`) and 200 hard negatives (`family: "benign"`, `hard_negative: true`), plus `data/generated/zd_job_task/meta.json` `{"alert": ..., "generate_seconds": <wall clock>}`. Do not show the generator any v1 job_task text. Why: the zero_day block becomes `available: true` with N=100/200 and `time_to_protection_s`.
- [ ] @B `contracts/schemas/chloroplast.schema.json` (additive, optional): `base_sha256` (sha256 of the `preynet.pt` the adapter was trained on). Why: after a retrain, old adapters read different features and silently mis-fire. With this field, `infer` and the browser can skip mismatched ones.

