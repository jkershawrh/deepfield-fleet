# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Backend — run from repo root
pip install -e ".[dev]"
python3 -m pytest app/tests/ -v          # 217 tests
python3 -m pytest app/tests/test_contracts.py  # single test file
uvicorn app.main:app --reload            # dev server on :8000
python3 -m app.demo                      # CLI demo (no server needed)

# Frontend — run from frontend/
cd frontend
npm install --legacy-peer-deps           # required due to peer dep conflicts
npx tsc -b                              # type check
npx vite build                           # production build → dist/
npm run dev                              # dev server on :3000 (proxies /api to :8000)

# Container
podman build --platform linux/amd64 -t deepfield-multimodal -f Containerfile .
podman run -p 8000:8000 deepfield-multimodal

# Deploy to OpenShift
oc apply -f deploy/deployment.yaml
bash deploy/verify.sh
```

## Architecture

### Three-Tier Classification Cascade

Signals flow through three agent tiers. Each tier has a different contract:

**Nanoagents** (7, deterministic, CPU) — module-level `name` string + `classify(evidence, baseline) → list[ClassificationRecord]`. Loaded dynamically via `importlib` in `app/nanoagents/pipeline.py`. No classes, just functions.

**Microagents** (5, rule-backed or LLM) — classes inheriting `BaseMicroagent` with `classify(evidence) → list[ClassificationRecord]`. Each declares `modalities: set` for filtering. `text_classifier.py` shows the LLM-with-fallback pattern: try `infer()`, parse JSON, fall back to regex rules.

**Macroagents** (5, template-based or LLM) — classes with `reason(evidence, classifications, baseline) → list[ClassificationRecord]`. Correlate across modalities. `root_cause_hypothesis.py` shows the LLM pattern.

Escalation logic in `app/classification/cascade.py`: nano→micro when modality is image/audio/document or severity is high. Micro→macro when 2+ modalities have high-severity findings.

### Agent Promotion Pipeline

`app/bootstrap/promotion.py` — agents earn their tier through empirical validation:
- Draft → Candidate (50 samples, 60% accuracy)
- Candidate → Nano (200 samples, 75% accuracy, <15% FP)
- Nano → Micro (500 samples, 85% accuracy, human reviewed)
- Micro → Macro (1000 samples, 85% accuracy, human reviewed, cross-modal agreement)

Ground truth is baseline-derived: evidence within `BaselineProfile.normal_ranges` = normal. Thresholds in `config/defaults/promotion.yaml`.

### Inference Client

`app/inference/client.py` — two separate model configs:
- **Runtime** (per-signal): `LITELLM_API_BASE` + `LITELLM_API_KEY` → CPU models (Granite). Used by micro/macro agents.
- **Bootstrap** (one-time): `BOOTSTRAP_API_BASE` + `BOOTSTRAP_API_KEY` → frontier models (Qwen 235B). Used only by semantic classifier.

`infer(prompt, system_prompt, tier, max_tokens)` returns `Optional[InferenceResult]`. Returns `None` when no API is configured — agents must handle this by falling back to rules. `set_force_rules(True)` globally disables LLM (used during scale demo acts).

### DB Graceful Degradation

`app/db.py` — everything works in-memory when `DATABASE_URL` is not set. `enqueue_write(table, data)` silently drops writes. `query()` returns `[]`. New tables must be added to `_ALLOWED_TABLES` frozenset.

### Config-Driven Loading

`app/bootstrap/config_loader.py` — YAML configs loaded from `config/` (user) → `config/defaults/` (built-in) → hardcoded fallback. Taxonomy, pipeline agent list, and promotion thresholds are all config-driven with backward-compatible defaults.

### Frontend

React 19 + `motion/react` (not Framer Motion) + inline styles (no Tailwind). Red Hat design system CSS variables in `theme.css`. No React Router — state-based mode switching (`slides` → `manual` → `auto` → `lab`).

The app is a presentation-first demo: 7 click-through slides → 6-act manual walkthrough → 13-step auto-run with SSE streaming → Bootstrap Lab with scenario selector and rubric matrix.

### Demo API

`app/api/demo.py` — auto-orchestrated demo runs in a background thread. Each step updates `_demo_state` which SSE (`app/api/sse.py`) pushes to the frontend every 500ms. Auto-pauses between steps (`_auto_pause_between_steps`) so the presenter controls pacing. Scale acts use `set_force_rules(True)` to avoid LLM calls.

### Bootstrap Lab

`app/api/bootstrap.py` — connect → analyze → validate → approve flow. Three paths:
1. **Scenarios** (`app/bootstrap/scenarios.py`) — pre-built synthetic data in `fixtures/scenarios/`
2. **Profiles** (`app/bootstrap/profiles.py`) — pre-built YAML rules in `config/profiles/`, no LLM needed
3. **Connectors** (`app/connectors/`) — live data from file/Prometheus/Kubernetes

## Key Conventions

- **Development methodology**: CDD (contracts in models.py first) → TDD (write failing tests) → implement → BDD (scenario tests) → EDD (rubric scoring)
- **Pydantic models**: `Field(default_factory=uuid4)` for IDs, `_now()` for timestamps, `Literal[...]` for enums, `Field(ge=0.0, le=1.0)` for confidence
- **Classification records**: every classification from any tier returns `ClassificationRecord` with `agent_tier`, `rationale`, and `evidence_ids`
- **Taxonomy validation**: `is_valid_classification(taxonomy, class_name)` in `app/classification/taxonomy.py` — loads from YAML config, falls back to hardcoded
- **"unclassified" not "unknown"**: microagents that can't match return `class_name="unclassified"` with low confidence
- **Container image**: `quay.io/deepfield-fleet/deepfield-multimodal` — must build `--platform linux/amd64` for OpenShift
- **OAuth proxy**: deployment includes `ose-oauth-proxy-rhel9` sidecar. Route targets port 8080 (proxy), not 8000 (app). `/health` is bypassed via `-skip-auth-regex`

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `LITELLM_API_BASE` | Runtime model endpoint | (none — rule-backed mode) |
| `LITELLM_API_KEY` | Runtime model auth | (none) |
| `LITELLM_MODEL_MICRO` | Micro tier model | `granite-3-2-8b-instruct-cpu` |
| `LITELLM_MODEL_MACRO` | Macro tier model | `granite-3-2-8b-instruct-cpu` |
| `BOOTSTRAP_API_BASE` | Bootstrap model endpoint | (falls back to LITELLM_API_BASE) |
| `BOOTSTRAP_API_KEY` | Bootstrap model auth | (falls back to LITELLM_API_KEY) |
| `BOOTSTRAP_MODEL` | Bootstrap model name | `claude-sonnet-4-6` |
| `DATABASE_URL` | PostgreSQL connection | (none — in-memory mode) |
