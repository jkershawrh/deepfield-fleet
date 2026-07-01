# DeepField Multimodal

Multimodal agent pack for enterprise signal classification and action loops. Turns enterprise signals into classified, governed, verified action.

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
  Baseline Profiles    Nanoagent Classification (7 agents)
        │                    │
        └─────────┬──────────┘
                  ▼
         Microagent Inference (5 agents)
                  │
                  ▼
         Macroagent Reasoning (5 agents)
                  │
                  ▼
     Decide → Act → Verify → Learn
                  │
                  ▼
        Dashboard + API
```

**Three-tier classification cascade:**

- **Nanoagents** (7) — Deterministic, no LLM. Baseline distance, metric drift, log patterns, document heuristics, image/audio metadata, evidence gating.
- **Microagents** (5) — Rule-backed classifiers. Text, document, image defect, audio anomaly, embedding clustering. Extension points for OpenVINO/ONNX.
- **Macroagents** (5) — Higher-level reasoning. Incident timeline, root cause hypothesis, action planning, verification planning, learning proposals.

**Agent Loop:**

- **Actions** — Propose/approve/execute safe actions (notify, observe, ticket). Non-destructive by design. Human approval gates.
- **Verification** — Compare post-action observations to expected outcomes.
- **Learning** — Propose threshold/rule updates. Never applied silently — always reviewed.

## Quick Start

```bash
# Backend
pip install -e ".[dev]"
pytest app/tests/ -v          # 180 tests
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install --legacy-peer-deps
npm run dev                    # http://localhost:5173

# Health check
curl http://localhost:8000/health
```

## API Endpoints

| Route | Description |
|-------|-------------|
| **Evidence** | |
| `POST /api/v1/multimodal/evidence` | Submit evidence |
| `GET /api/v1/multimodal/evidence` | List evidence |
| `GET /api/v1/multimodal/evidence/{id}` | Get evidence |
| **Baseline** | |
| `POST /api/v1/baseline/jobs` | Start baseline build |
| `GET /api/v1/baseline/jobs` | List jobs |
| `GET /api/v1/baseline/profiles` | List profiles |
| `POST /api/v1/baseline/profiles/{id}/activate` | Activate profile |
| **Classification** | |
| `POST /api/v1/classification/run` | Run classification cascade |
| `GET /api/v1/classification/records` | List records |
| **Agent Loop** | |
| `POST /api/v1/agent-loop/actions` | Propose action |
| `POST /api/v1/agent-loop/actions/{id}/approve` | Approve action |
| `POST /api/v1/agent-loop/actions/{id}/execute` | Execute action |
| `GET /api/v1/agent-loop/verifications` | List verifications |
| `GET /api/v1/agent-loop/learning-proposals` | List proposals |
| `POST /api/v1/agent-loop/learning-proposals/{id}/accept` | Accept proposal |

## Frontend Pages

| Page | Route | Features |
|------|-------|----------|
| Evidence | `/` | Artifact table, modality badges, pie chart distribution |
| Baselines | `/baselines` | Job management, profile viewer, activation controls |
| Classification | `/classification` | Nano/micro/macro swimlanes, tier and severity charts |
| Agent Loop | `/agent-loop` | Loop visualization, action approve/execute, proposal review |

## Development Methodology

**CDD → TDD → BDD → EDD**

1. **CDD** — Contracts defined as Pydantic models and function signatures
2. **TDD** — Tests written RED first, then implemented to GREEN
3. **BDD** — Given/When/Then scenario tests for end-to-end flows
4. **EDD** — Rubric scoring (healthy/warning/failing) across quality dimensions

## EDD Rubric Matrix

| Dimension | Status |
|-----------|--------|
| Contract Compliance | healthy |
| Fixture Scenarios | healthy |
| Evidence Normalization | healthy |
| Baseline Quality | healthy |
| Classification Accuracy | healthy |
| Cascade Efficiency | healthy |
| Agent Coverage | healthy |
| DB Graceful Degradation | healthy |
| Safety | healthy |

**180 tests. 9 rubric dimensions. All green.**

## Synthetic Scenario

**factory-line-bearing-failure** — Simulated bearing failure on a factory production line:

1. Historical baseline shows normal vibration, temperature, and maintenance log patterns
2. Runtime signals include vibration drift, thermal increase, surface defect image, maintenance note
3. Nanoagents detect baseline distance drift and error patterns
4. Microagents classify image defects and audio anomalies
5. Macroagent builds incident timeline and proposes bearing failure root cause
6. Action proposed: notify maintenance (non-destructive, requires human approval)
7. Verification checks whether metrics return to baseline
8. Learning proposes tightened thresholds for earlier detection

## Project Structure

```
deepfield-multimodal/
├── app/
│   ├── domain/models.py          # 10 Pydantic models (CDD contracts)
│   ├── multimodal/               # Normalizer, feature extractors, storage
│   ├── baseline/                 # Compiler, profiles, sources
│   ├── classification/           # Engine, taxonomy, cascade, registry
│   ├── nanoagents/               # 7 deterministic agents
│   ├── microagents/              # 5 rule-backed classifiers
│   ├── macroagents/              # 5 reasoning agents
│   ├── agent_loop/               # Actions, verification, learning, orchestrator
│   ├── analysis/evaluator.py     # EDD rubric scoring engine
│   ├── api/                      # FastAPI routes (4 routers)
│   └── tests/                    # 180 tests (CDD/TDD/BDD/EDD)
├── frontend/                     # React 19, Vite, Tailwind, recharts
├── fixtures/multimodal/          # Synthetic scenarios
└── migrations/                   # PostgreSQL schema
```
