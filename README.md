# DeepField Multimodal

Multimodal agent pack for enterprise signal classification and action loops. Ported from DeepField's core patterns into a standalone, demo-oriented platform.

## Core Loop

```
Signals → Decide → Act → Verify → Learn
```

## Architecture

**Three-tier classification cascade:**

- **Nanoagents** (7) — Deterministic, no LLM. Baseline distance, metric drift, log patterns, document heuristics, image/audio metadata, evidence gating.
- **Microagents** (5) — Rule-backed classifiers. Text, document, image defect, audio anomaly, embedding clustering. Extension points for OpenVINO/ONNX.
- **Macroagents** (5) — Higher-level reasoning. Incident timeline, root cause hypothesis, action planning, verification planning, learning proposals.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest app/tests/ -v

# Start server
uvicorn app.main:app --reload

# Health check
curl http://localhost:8000/health
```

## API Endpoints

| Route | Description |
|-------|-------------|
| `POST /api/v1/multimodal/evidence` | Submit evidence |
| `GET /api/v1/multimodal/evidence` | List evidence |
| `POST /api/v1/baseline/jobs` | Start baseline build |
| `GET /api/v1/baseline/profiles` | List profiles |
| `POST /api/v1/classification/run` | Run classification cascade |
| `GET /api/v1/classification/records` | List classification records |

## Development Methodology

**CDD → TDD → BDD → EDD**

1. **CDD** — Contracts defined as Pydantic models and function signatures
2. **TDD** — Tests written RED first, then implemented to GREEN
3. **BDD** — Given/When/Then scenario tests for end-to-end flows
4. **EDD** — Rubric scoring (healthy/warning/failing) across quality dimensions

## Rubric Matrix (M3 Complete)

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

## Synthetic Scenario

**factory-line-bearing-failure** — Simulated bearing failure with vibration drift, thermal increase, surface defect, and maintenance notes. Demonstrates the full classification cascade from nanoagent detection through macroagent root cause hypothesis.
