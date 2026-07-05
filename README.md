# DeepField Multimodal

**Agentic Signal Classification Engine on Intel Xeon 6**

Three-tier agent cascade that classifies enterprise signals into governed, verified action. Deterministic nanoagents compress on CPU. LLM reasoning when you need it. Agents earn their tier through empirical validation.

> "The first job of enterprise AI is not generation. It is classifying reality well enough to know what should happen next."

## Core Loop

```
Signals → Decide → Act → Verify → Learn
```

## Architecture

```
Historical / Live / Synthetic Sources
        │
        ▼
  Evidence Normalizer
        │
        ├────────────────────┐
        ▼                    ▼
  Baseline Compiler    Runtime Signal Flow
        │                    │
        ▼                    ▼
  Baseline Profiles    Nanoagent Classification (7 agents, Intel Xeon 6)
        │                    │
        └─────────┬──────────┘
                  ▼
         Microagent Inference (5 agents, CPU / LLM)
                  │
                  ▼
         Macroagent Reasoning (5 agents, CPU / Gaudi)
                  │
                  ▼
     Decide → Act → Verify → Learn
                  │
                  ▼
        Dashboard + API + Bootstrap Lab
```

**Three-tier classification cascade:**

- **Nanoagents** (7) — Deterministic, no LLM, Intel Xeon 6. Baseline distance, metric drift, log patterns, document heuristics, image/audio metadata, evidence gating. Zero inference cost.
- **Microagents** (5) — Rule-backed classifiers on CPU. Text, document, image defect, audio anomaly, embedding clustering. Optional LLM via Granite 3.2 8B. Extension points for Intel OpenVINO/ONNX.
- **Macroagents** (5) — Higher-level reasoning. Incident timeline, root cause hypothesis, action planning, verification planning, learning proposals. Template-based on CPU, or LLM-backed via Gaudi/Xeon.

Image/audio microagents are fixture-backed by default for a dependency-free demo. Set `DEEPFIELD_MEDIA_BACKEND=onnx` with `DEEPFIELD_IMAGE_ONNX_MODEL` or `DEEPFIELD_AUDIO_ONNX_MODEL` to enable optional CPU media adapters.

**Agent Promotion Pipeline:**

- Agents start as **draft** and earn their tier through empirical validation
- Draft → Candidate (50 samples, 60% accuracy) → Nano (200 samples, 75%) → Micro (500 samples, human reviewed) → Macro (1000 samples, cross-modal agreement)
- Red/yellow/green rubric matrix tracks every agent's maturity
- Only promoted (green) agents run in the active pipeline

**Agent Loop:**

- **Actions** — Propose/approve/execute safe actions (notify, observe, ticket). Non-destructive by design. Human approval gates.
- **Verification** — Compare post-action observations to expected outcomes.
- **Learning** — Propose threshold/rule updates. Never applied silently — always reviewed.

## Quick Start

```bash
# Backend
pip install -e ".[dev]"
pytest app/tests/ -v          # 217 backend tests
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install --legacy-peer-deps
npm run dev                    # http://localhost:3000 (proxies to :8000)

# Container
podman run -p 8000:8000 quay.io/deepfield-fleet/deepfield-multimodal:v1.0.1

# CLI demo (no server needed)
python3 -m app.demo

# Measured proof report
python3 -m app.benchmark --profile enterprise-signal-volume --iterations 5 --include-project-tests --out benchmark-results/latest.json

# Health check
curl http://localhost:8000/health
```

## Demo Experience

| Section | Duration | What happens |
|---------|----------|-------------|
| **Presentation** | ~5 min | 7 click-through slides — business case, measured CPU compression, three tiers |
| **Walkthrough** | ~10 min | 6 manual acts — ingest, baseline, nano/micro/macro cascade, act, learn |
| **Scale Run** | ~5 min | 13 auto steps — 10→50 lines, stress test, recovery, the claim |
| **Bootstrap Lab** | ~20 min | Pick scenario → analyze → validate → rubric matrix → promote agents |

## Bootstrap Lab

Four synthetic scenarios for self-paced labs:

| Scenario | Domain | Signals | Profile |
|----------|--------|---------|---------|
| OpenShift Cluster Health | IT Ops | 156 (pods, events, nodes) | openshift-monitoring |
| Factory Floor Monitoring | Manufacturing | 6 (vibration, temp, logs, image, audio) | — |
| Telecom Network Operations | Telecom | 150 (signal strength, events, logs) | — (frontier model optional) |
| AAP Job Failures | IT Ops | 100 (jobs, workflows) | aap-job-health |

Two analysis paths:
- **Quick Start** — pre-built profile, instant, no LLM needed
- **Deep Analyze** — frontier-model semantic analysis when configured, generates domain-specific rules

## Model Architecture

| Tier | Model | Hardware | When |
|------|-------|----------|------|
| Nano (runtime) | None — deterministic rules | Intel Xeon 6 CPU | Every signal, always |
| Micro (runtime) | Granite 3.2 8B (optional) | Intel Xeon 6 CPU | Escalated evidence only |
| Macro (runtime) | Granite 3.2 8B (optional) | Intel Xeon 6 / Gaudi 3 | Cross-modal correlation |
| Bootstrap (one-time) | Qwen 3 235B | Intel Gaudi / MaaS | Initial data analysis |

The benchmark panel reports whether the current runtime meets the 98% CPU pre-expensive target before anything costly runs.

## API Endpoints

| Route | Description |
|-------|-------------|
| `GET /health` | Health check |
| **Demo** | |
| `POST /api/v1/demo/start` | Start auto-run demo |
| `GET /api/v1/demo/state` | Poll demo state (SSE at `/api/v1/stream`) |
| `GET /api/v1/demo/infrastructure` | Runtime + agent inventory |
| **Benchmark** | |
| `GET /api/v1/benchmark/latest` | Latest measured CPU-compression report |
| `POST /api/v1/benchmark/run` | Run benchmark profile and optionally save report; pass `include_project_tests: true` for backend/frontend validation |
| **Bootstrap** | |
| `GET /api/v1/bootstrap/scenarios` | List lab scenarios |
| `POST /api/v1/bootstrap/scenarios/{id}/load` | Load scenario data |
| `GET /api/v1/bootstrap/profiles` | List pre-built profiles |
| `POST /api/v1/bootstrap/profiles/{id}/apply` | Apply profile (no LLM) |
| `POST /api/v1/bootstrap/connect` | Connect live data source |
| `POST /api/v1/bootstrap/analyze` | Semantic analysis (Qwen/Sonnet) |
| `POST /api/v1/bootstrap/validate` | Run validation round |
| `GET /api/v1/bootstrap/rubric` | Agent maturity rubric matrix |
| `POST /api/v1/bootstrap/promote/{id}` | Promote agent (human review) |
| **Classification** | |
| `POST /api/v1/classification/run` | Run classification cascade |
| `POST /api/v1/demo/classify/nano` | Nano tier only |
| `POST /api/v1/demo/classify/micro` | Micro tier only |
| `POST /api/v1/demo/classify/macro` | Macro tier only |

## Deployment

```bash
# OpenShift with OAuth proxy
oc apply -f deploy/deployment.yaml

# Verify (13 checks)
bash deploy/verify.sh
```

Container: `quay.io/deepfield-fleet/deepfield-multimodal:v1.0.1`

Requires: `cluster-reader` + `cluster-monitoring-view` ClusterRoles on ServiceAccount.

## LiftOff Readiness

| Check | Grade |
|-------|-------|
| NovaScan | Partner / Self-Serve / $0 per session |
| DarkScope | **A** — 0 findings, score 0 |
| Brand Audit | **A** — 155/170, Intel + Red Hat aligned |
| Preflight | **READY** |

## Development Methodology

**CDD → TDD → BDD → EDD**

1. **CDD** — Contracts defined as Pydantic models and function signatures
2. **TDD** — Tests written RED first, then implemented to GREEN
3. **BDD** — Given/When/Then scenario tests for end-to-end flows
4. **EDD** — Rubric scoring (healthy/warning/failing) across quality dimensions

**217 backend tests plus frontend component tests and production build validation. 9 EDD rubric dimensions. All green.**

## Project Structure

```
deepfield-multimodal/
├── app/
│   ├── domain/models.py          # 12 Pydantic models (CDD contracts)
│   ├── multimodal/               # Normalizer, feature extractors, storage, scale generator
│   ├── baseline/                 # Compiler, profiles, sources
│   ├── classification/           # Engine, taxonomy, cascade, registry
│   ├── nanoagents/               # 7 deterministic agents + pipeline
│   ├── microagents/              # 5 rule-backed + 1 configurable (LLM)
│   ├── macroagents/              # 5 reasoning agents
│   ├── agent_loop/               # Actions, verification, learning, orchestrator
│   ├── bootstrap/                # Semantic classifier, promotion, constraints, scenarios
│   ├── connectors/               # File, Prometheus, Kubernetes
│   ├── inference/                # LiteLLM client (runtime + bootstrap)
│   ├── benchmark.py              # Measured CPU-compression benchmark CLI/API engine
│   ├── analysis/evaluator.py     # EDD rubric scoring engine
│   ├── api/                      # 7 FastAPI routers + SSE streaming
│   └── tests/                    # 217 backend tests (CDD/TDD/BDD/EDD)
├── frontend/                     # React 19, motion/react, inline styles
├── fixtures/                     # Factory scenario + 4 lab scenarios
├── config/                       # YAML configs (taxonomies, profiles, promotion thresholds)
├── deploy/                       # OpenShift manifests + verify.sh
├── agnosticv/                    # RHDP catalog config
├── docs/                         # Antora documentation and presenter/lab guides
└── migrations/                   # PostgreSQL schema (optional)
```

## Powered By

Red Hat OpenShift · Intel Xeon 6 · Intel Gaudi 3 · Intel TDX
