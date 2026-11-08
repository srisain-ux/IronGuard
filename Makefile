# IronGuard: one entry point for humans and agents. Owner: B.
# Targets for code that doesn't exist yet are part of the plan; each owner makes theirs work in P0.
SHELL := /bin/bash
UV := $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)
.PHONY: doctor algae brev-tunnel nemotron-check sync validate check-ml check-api check-web check-bridge smoke api api-stub web bridge tunnel train eval export setup-a setup-b setup-c

doctor:              ## is THIS laptop ready? prints ✅/❌ with fixes
	@./scripts/doctor.sh

validate:            ## contracts + taxonomy + examples
	$(UV) run --quiet --with jsonschema python scripts/validate_contracts.py

validate-data:       ## validate every generated dataset file against conversation.schema.json
	$(UV) run --quiet --with jsonschema python scripts/validate_contracts.py $$(ls data/generated/*/*.jsonl data/seed/*.jsonl data/test_human/*.jsonl 2>/dev/null)

# ---------- per-area checks (each owner keeps theirs green) ----------
check-ml:
	cd ml && $(UV) run ruff check . && $(UV) run pytest -q
check-api:
	python3 scripts/run_api.py ruff check .
	python3 scripts/run_api.py pytest -q
check-web:
	cd web && pnpm -s tsc --noEmit && pnpm -s run --if-present lint
check-bridge:
	cd bridge && pnpm -s tsc --noEmit

# ---------- run ----------
api:                 ## real model (needs ml/artifacts/preynet.pt)
	IRONGUARD_MODEL=preynet python3 scripts/run_api.py uvicorn ironguard_api.main:app --port 8000 --reload
api-stub:            ## stub model, no artifacts needed
	IRONGUARD_MODEL=stub python3 scripts/run_api.py uvicorn ironguard_api.main:app --port 8000 --reload
web:                 ## live API by default; VITE_USE_MOCKS=1 make web for fixtures
	cd web && VITE_USE_MOCKS=$${VITE_USE_MOCKS:-0} pnpm dev --port 5173
bridge:
	cd bridge && pnpm dev
tunnel:              ## public URL for the Photon webhook → bridge
	cloudflared tunnel --url http://localhost:8787

sync:                ## after every merge: install whatever packages exist, then smoke (safe before ml/web/bridge land)
	@if [ -f ml/pyproject.toml ]; then (cd ml && $(UV) sync); else echo "ml package pending (member A)"; fi
	@if [ -f web/package.json ]; then (cd web && pnpm install); else echo "web package pending (member C)"; fi
	@if [ -f bridge/package.json ]; then (cd bridge && pnpm install); else echo "bridge package pending (member C)"; fi
	$(MAKE) smoke

smoke:               ## must pass before every PR and at every merge window
	$(MAKE) validate
	IRONGUARD_MODEL=$${IRONGUARD_MODEL:-stub} python3 scripts/run_api.py pytest -q tests/test_smoke.py
	@if [ -f web/package.json ]; then cd web && pnpm -s tsc --noEmit; else echo "web typecheck pending: member C package not present"; fi
	@if [ -f bridge/package.json ]; then cd bridge && pnpm -s tsc --noEmit; else echo "bridge typecheck pending: member C package not present"; fi

# ---------- Nemotron (B only; settings come from api/.env) ----------
BREV_INSTANCE ?= ironguard-nemotron
brev-tunnel:         ## keep running in its own Terminal tab: Brev GPU port 8000 → this laptop's port 8001
	brev port-forward $(BREV_INSTANCE) --port 8001:8000
nemotron-check:      ## one tiny Nemotron call to prove the connection works (Brev or build.nvidia.com)
	python3 scripts/run_api.py python ../scripts/nemotron_check.py
algae:
	python3 scripts/run_api.py python -m ironguard_api.agent.algae --version v1 --per-family 150

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
	./scripts/install-hooks.sh B && python3 scripts/run_api.py python -c "print('api deps ready')"
setup-c:
	./scripts/install-hooks.sh C && cd web && pnpm install && cd ../bridge && pnpm install
