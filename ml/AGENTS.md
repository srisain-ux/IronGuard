# ml/AGENTS.md: Member A (Dragonfly). Root AGENTS.md rules still apply.

**You build the model, which is the main thing judges score.** The spec is in `../docs/MODEL_SPEC.md`. Read §2–§7 before writing code.

## Stack
Python 3.11, `uv`, PyTorch (CPU is fine; on Apple Silicon, `mps` is optional), sentence-transformers (`all-MiniLM-L6-v2`), scikit-learn, numpy, onnx + onnxruntime, pytest, ruff. Everything goes in `ml/pyproject.toml`.

## Package layout (`ironguard_ml/`)
| File | Responsibility | Test required |
|---|---|---|
| `data.py` | load JSONL → Conversation objects; `make_prefixes()`; **conversation-level** stratified split | ✅ no prefix of one conversation in two splits |
| `features.py` | role-prefixed MiniLM embeddings, cached by sha1(text) in `.cache/emb/` | |
| `baselines.py` | B0 rules, B1 TF-IDF+LR, B2 MiniLM+LR, B3 mean-MiniLM+LR | |
| `preynet.py` | `PreyNet` (Linear→GRU→CstmdAttention→3 heads), `features()` output (640-d) | ✅ shape test |
| `train.py` | multi-task training, early stop on val EWR@2, seeds 0/1/2 | |
| `calibrate.py` | temperature scaling on val → `artifacts/temperature.json`, ECE | ✅ ECE on a toy case |
| `metrics.py` | `ewr_at_k`, `lead_time`, `strike_recall`, `hard_neg_fpr`, `flicker_rate`, threshold @1% FPR | ✅ hand-computed cases (+ Codex re-implementation cross-check) |
| `evaluate.py` | runs everything → `artifacts/eval_summary.json` (exact shape in MODEL_SPEC §6.4) | |
| `chloroplast.py` | `train(pos, neg, family_id, label, alert, progress_cb) -> manifest dict` (< 10 s CPU) | ✅ manifest validates against the schema |
| `infer.py` | `load(artifacts_dir) -> Model`; `Model.score(turns, chloroplasts=[]) -> dict` (validates as `score_response`); `LockOn` hysteresis | ✅ output validates |
| `stub.py` | **same signatures as infer + chloroplast**, keyword heuristics, deterministic. **Ship by H1** | ✅ output validates |
| `export.py` | ONNX opset 17 (outputs `family_logits, stage_logits, tts_logits, attention, features`) | ✅ parity < 1e-4 |

## Interfaces other members depend on (do not change after M0 without a Request round)
```python
from ironguard_ml.infer import load          # or: from ironguard_ml.stub import load
model = load("ml/artifacts")               # stub ignores the path
resp: dict = model.score(turns=[{"sender": "them", "text": "..."}], chloroplasts=[manifest_dict, ...])
from ironguard_ml.chloroplast import train   # stub version returns a schema-valid fake manifest
manifest: dict = train(pos=[conv_dict...], neg=[conv_dict...], family_id="zd_x", label="...", alert="...", progress_cb=lambda step, total, loss: None)
```

## Rules specific to ML
- **Never** tune thresholds, temperature or early stopping on `test` or `test_human`. Val only.
- Every number in `eval_summary.json` is produced by code in this folder from committed data. No hand edits.
- Commit `artifacts/` only at merge windows (binary files; no merges needed because only A writes them).
- Before any metric goes into the pitch, run the `leakage-hunter` subagent (Claude) on `data.py`, `train.py` and `evaluate.py`.
- Keep the model small (about 160k params). If an idea needs a GPU, it is out of scope tonight.
