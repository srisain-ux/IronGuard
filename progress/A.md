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
