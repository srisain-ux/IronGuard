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
