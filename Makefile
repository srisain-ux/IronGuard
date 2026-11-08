# IronGuard: one entry point for humans and agents. Owner: B.
# Targets for code that doesn't exist yet are part of the plan; each owner makes theirs work in P0.
SHELL := /bin/bash
.PHONY: validate check-ml check-api check-web check-bridge smoke api api-stub web bridge tunnel train eval export setup-a setup-b setup-c

validate:            ## contracts + taxonomy + examples
	uv run --quiet --with jsonschema python scripts/validate_contracts.py

validate-data:       ## validate every generated dataset file against conversation.schema.json
	uv run --quiet --with jsonschema python scripts/validate_contracts.py $$(ls data/generated/*/*.jsonl data/seed/*.jsonl data/test_human/*.jsonl 2>/dev/null)

# ---------- per-area checks (each owner keeps theirs green) ----------
check-ml:
	cd ml && uv run ruff check . && uv run pytest -q
check-api:
	cd api && uv run ruff check . && uv run pytest -q
check-web:
	cd web && pnpm -s tsc --noEmit && pnpm -s lint
check-bridge:
	cd bridge && pnpm -s tsc --noEmit

# ---------- run ----------
api:                 ## real model (needs ml/artifacts/preynet.pt)
	cd api && IRONGUARD_MODEL=preynet uv run uvicorn ironguard_api.main:app --port 8000 --reload
api-stub:            ## stub model, no artifacts needed
	cd api && IRONGUARD_MODEL=stub uv run uvicorn ironguard_api.main:app --port 8000 --reload
web:
	cd web && pnpm dev --port 5173
bridge:
	cd bridge && pnpm dev
tunnel:              ## public URL for the Photon webhook → bridge
	cloudflared tunnel --url http://localhost:8787

smoke:               ## must pass before every PR and at every merge window
	$(MAKE) validate
	cd api && IRONGUARD_MODEL=$${IRONGUARD_MODEL:-stub} uv run pytest -q tests/test_smoke.py
	cd web && pnpm -s tsc --noEmit
	cd bridge && pnpm -s tsc --noEmit

# ---------- ML (A only) ----------
train:
	cd ml && uv run python -m ironguard_ml.train --data ../data/generated/v1 --out artifacts
eval:
	cd ml && uv run python -m ironguard_ml.evaluate --data ../data/generated/v1 --human ../data/test_human --out artifacts/eval_summary.json
export:
	cd ml && uv run python -m ironguard_ml.export --out artifacts/preynet.onnx && uv run pytest -q tests/test_onnx_parity.py

# ---------- first-time setup ----------
setup-a:
	./scripts/install-hooks.sh A && cd ml && uv sync
setup-b:
	./scripts/install-hooks.sh B && cd api && uv sync
setup-c:
	./scripts/install-hooks.sh C && cd web && pnpm install && cd ../bridge && pnpm install
