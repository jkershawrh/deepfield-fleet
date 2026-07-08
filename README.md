# DeepField Fleet

**Predictive Intelligence Layer for fleet-llm-d Inference Orchestration**

Composable predictive brain that sits above fleet-llm-d (deterministic actuator) and the ARE Immutable Ledger (shared audit spine). Classifies fleet signals, forecasts SLO breaches, emits typed intents, and produces verifiable prediction→action→outcome chains.

Forked from [deepfield-multimodal](https://github.com/deepfield-fleet/deepfield-multimodal) — the agentic signal classification engine on Intel Xeon 6.

## Three-Layer Architecture

```
deepfield-fleet (this repo)              fleet-llm-d
┌──────────────────────────┐              ┌─────────────────────┐
│ Nano: slo_drift,         │   intents    │ POST /api/v1/intents│
│   capacity, queue,       │─────────────▶│ Evaluate policy     │
│   event_calendar         │              │ Execute or refuse   │
│ Micro: slo_forecaster    │              │ Record to ledger    │
│ Macro: consequence_scoper│              └─────────────────────┘
│ A/B: toggle on/off       │                       │
│ Profiles: YAML           │                       ▼
│ DB: intents, runs        │              ┌──────────────────┐
└──────────────────────────┘              │  ARE Ledger      │
         │                                │  predict→act→out │
         └───────────────────────────────▶│                  │
                                          └──────────────────┘
```

## Core Loop

```
Signals → Classify → Predict → Decide → Act → Verify → Learn
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
podman run -p 8000:8000 quay.io/deepfield-fleet/deepfield-multimodal:latest

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

98% of signals classified on CPU before anything expensive runs. Verified by benchmark CLI at 100% in rule-backed mode.

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

Container: `quay.io/deepfield-fleet/deepfield-multimodal:latest`

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

**288 tests (278 unit + 10 integration), zero failures. 9 EDD rubric dimensions. All green.**

## Fleet-Specific Components

| Component | Purpose | Tests |
|-----------|---------|-------|
| **FleetIntent types** | PreWarm, Scale, ShedLoad, Alert — typed recommendations to fleet-llm-d | 8 |
| **IntentEmitter** | POST intents to fleet-llm-d, record predictions to ARE Ledger | integrated |
| **slo_drift** nanoagent | Detects P95/P99 trending toward SLO threshold | 5 |
| **capacity_pressure** nanoagent | CPU utilization approaching saturation | 3 |
| **queue_depth** nanoagent | Inference queue growing beyond capacity | 2 |
| **event_calendar** nanoagent | Scheduled event approaching — triggers pre-warm | 3 |
| **SLO forecaster** microagent | Linear regression on P95, predicts breach T+N minutes | 9 |
| **consequence_scoper** macroagent | Blast radius: affected models × users × severity | 8 |
| **FleetPredictor** | A/B toggle (predictive vs reactive), event profiles | 7 |
| **Event profiles** | YAML-driven calendar pre-warming (Summit Connect) | 8 |
| **Persistence** | fleet_intents, ab_runs, prediction_outcomes tables | 7 |
| **Integration tests** | End-to-end against live fleet-llm-d on dev-cluster-1 | 10 |

## Integration Benchmarks

Tested against fleet-llm-d on dev-cluster-1 (Intel Xeon, Red Hat OpenShift 4.19):

| Test | Result | What it proves |
|------|--------|---------------|
| PreWarm intent → executed | PASS | Valid intent accepted by policy evaluator |
| Low confidence → deferred | PASS | Confidence threshold gate works (< 0.5) |
| Excessive replicas → refused | PASS | Replica limit enforced (max 8) |
| Critical alert → human gate | PASS | Critical actions require human approval |
| Latency ramp → SLO forecast → ScaleIntent | PASS | Full pipeline: classify → forecast → intent |
| Event profile → PreWarm per model | PASS | Calendar-driven pre-warming works |
| Consequence scoper → blast radius | PASS | Affected models, users, severity score computed |

## Project Structure

```
deepfield-fleet/
├── app/
│   ├── domain/
│   │   ├── models.py              # 12 Pydantic models (inherited)
│   │   ├── fleet_intents.py       # FleetIntent, PreWarm, Scale, ShedLoad, Alert
│   │   └── event_profile.py       # EventProfile, LoadProfile, SLOTargets
│   ├── nanoagents/                # 11 agents (7 inherited + 4 fleet-specific)
│   ├── microagents/               # 6 agents (5 inherited + slo_forecaster)
│   ├── macroagents/               # 6 agents (5 inherited + consequence_scoper)
│   ├── intents/                   # Emitter, predictor, scheduler, persistence, ledger verifier
│   ├── agent_loop/                # Decide → Act → Verify → Learn (+ Predict)
│   ├── classification/            # Engine, cascade, taxonomy
│   ├── baseline/                  # Compiler, profiles
│   ├── connectors/                # File, Prometheus, Kubernetes
│   ├── bootstrap/                 # Semantic classifier, promotion, rule engine
│   ├── api/                       # FastAPI routers + SSE
│   └── tests/                     # 288 tests (CDD/TDD/BDD/EDD/CBT)
├── config/
│   └── defaults/
│       └── event_profiles/        # Summit Connect, daily enterprise (YAML)
├── migrations/                    # 001_initial + 002_fleet_intents
├── frontend/                      # React 19
└── deploy/                        # OpenShift manifests
```

## Quick Start

```bash
# Run with fleet-llm-d (predictive mode)
FLEET_URL=http://fleet-controller:8080 \
FLEET_TOKEN=<token> \
python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port 8090

# Run standalone (classification only, no intent emission)
python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port 8090

# Run tests
python3 -m pytest app/tests/ -v

# Run integration tests (requires live fleet-llm-d)
FLEET_URL=http://localhost:8080 FLEET_TOKEN=<token> python3 -m pytest app/tests/test_integration_fleet.py -v
```

## Powered By

Red Hat OpenShift · Intel Xeon 6 · Intel Gaudi 3 · fleet-llm-d · ARE Immutable Ledger
