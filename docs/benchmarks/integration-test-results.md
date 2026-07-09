# DeepField Fleet — Integration Test & Benchmark Results

**Date**: 2026-07-08
**Cluster**: dev-cluster-1 (Intel Xeon, Red Hat OpenShift 4.19)
**Architecture**: deepfield-fleet (predictive brain) → fleet-llm-d (actuator) → ARE Ledger (audit spine)

---

## 1. Test Summary

| Suite | Tests | Passed | Failed | Status |
|-------|-------|--------|--------|--------|
| **deepfield-fleet unit** | 278 | 278 | 0 | GREEN |
| **deepfield-fleet integration** | 10 | 10 | 0 | GREEN |
| **fleet-llm-d harness: smoke** | 24 | 24 | 0 | GREEN |
| **fleet-llm-d harness: stress** | 6 | 6 | 0 | GREEN |
| **fleet-llm-d harness: pressure** | 4 | 4 | 0 | GREEN |
| **fleet-llm-d harness: chaos** | 8 | 8 | 0 | GREEN |
| **fleet-llm-d harness: chaos-recovery** | 3 | 3 | 0 | GREEN |
| **fleet-llm-d harness: redteam** | 11 | 11 | 0 | GREEN |
| **fleet-llm-d harness: latency** | 4 | 4 | 0 | GREEN |
| **fleet-llm-d harness: throughput** | 3 | 3 | 0 | GREEN |
| **fleet-llm-d harness: soak (5 min)** | 9 | 9 | 0 | GREEN |
| **Total** | **360** | **360** | **0** | **ALL GREEN** |

---

## 2. Unit Test Breakdown (deepfield-fleet — 278 tests)

| Component | Tests | What's Covered |
|-----------|-------|---------------|
| Inherited (deepfield-multimodal) | 217 | Nanoagents, microagents, macroagents, baseline, classification, agent loop, contracts, constraints, promotion, scenarios, benchmark, normalizer, microagent lifecycle |
| FleetIntent models | 8 | PreWarm, Scale, ShedLoad, Alert serialization, confidence validation, IntentResponse |
| Fleet nanoagents | 14 | slo_drift (5), capacity_pressure (3), queue_depth (2), event_calendar (3), pipeline integration (1) |
| SLO forecaster | 9 | Breach prediction, safe forecast, approaching threshold, insufficient data, minutes-to-breach, declining trends, regression accuracy, non-latency filtering, custom horizons |
| Consequence scoper | 8 | SLO breach assessment, human gate threshold, small blast radius, healthy no-op, queue overflow, multiple classifications, severity score math, rationale content |
| Event profiles | 8 | Profile schema, burst RPS calculation, YAML loading, pre-warm emission, far event no-op, live event alert, early warning, Summit Connect profile |
| FleetPredictor A/B | 7 | Mode toggle, pre-warm emission, disabled passthrough, SLO forecast→scale, healthy no-op, stats tracking, ledger verifier |
| Intent persistence | 7 | Save intent, A/B run save, start/end lifecycle, prediction outcomes, accuracy calculation, predictor integration |

---

## 3. Integration Tests (deepfield-fleet → fleet-llm-d — 10 tests)

All tests ran against live fleet-llm-d on dev-cluster-1 via port-forward.

### Intent Round-Trip (7 tests)

| Test | Intent Type | Expected | Actual | Status |
|------|------------|----------|--------|--------|
| Valid PreWarm (confidence 0.85, 4 replicas) | PreWarm | executed | **executed** | PASS |
| Low confidence (0.3) | PreWarm | deferred | **deferred** — "confidence 0.30 below threshold 0.50" | PASS |
| Excessive replicas (20) | PreWarm | refused | **refused** — "requested 20 replicas exceeds max 8" | PASS |
| Critical alert with human gate | Alert | deferred | **deferred** — "critical alert requires human approval" | PASS |
| Valid ScaleIntent | Scale | executed | **executed** | PASS |
| Valid ShedLoadIntent | ShedLoad | executed | **executed** | PASS |
| Ledger entry returned | PreWarm | ledger_entry_id present | **entry-N** returned | PASS |

### Full Pipeline (3 tests)

| Test | Pipeline | Result | Status |
|------|----------|--------|--------|
| Latency ramp → SLO forecast → ScaleIntent | 30 data points, slope +50ms/min, SLO 5000ms | ScaleIntent emitted with metric="slo_forecast" | PASS |
| Event profile → PreWarm per model | 2 models, event in 20 min | 2 PreWarmIntents, target_replicas=4 each | PASS |
| Consequence scoper → blast radius | 2 models, 50 users, forecast 7000ms vs 5000ms SLO | affected_models=2, estimated_users=50, severity scored | PASS |

---

## 4. Fleet-LLM-D Harness Results (dev-cluster-1 — 63 tests)

### Control Plane (60 tests)

| Suite | Tests | Highlights |
|-------|-------|-----------|
| **Smoke** | 24/24 | All endpoints healthy, auth working, CRUD operations, metrics reachable |
| **Stress** | 6/6 | Survived 500 concurrent goroutines, no breaking point |
| **Pressure** | 4/4 | 50 concurrent same-ID, race detection, 1000x register/deregister, burst 500 |
| **Chaos** | 8/8 | 1MB body, invalid JSON, unicode, burst 1000, null bytes |
| **Red Team** | 11/11 | Expired/tampered tokens, SQL injection, path traversal, XSS — all rejected |
| **Latency** | 4/4 | health p50<1ms, auth-reads p50<1ms |
| **Throughput** | 3/3 | healthz 2000 rps, clusters 2000 rps |

### Resilience (3 tests)

| Suite | Tests | Highlights |
|-------|-------|-----------|
| **Chaos Recovery** | 3/3 | Steady state <1% errors → inject failure → graceful 502/503 → recovery <1% errors |

---

## 5. Soak Test Results (dev-cluster-1 — 9 tests)

5-minute sustained load with SLO gates.

| Metric | Value | SLO Target | Status |
|--------|-------|------------|--------|
| Snapshots | 5/5 pass | — | PASS |
| Error rate | **0.00%** | < 0.1% | PASS |
| P95 latency | **6.8ms** | < 5,000ms | PASS |
| P99 latency | **30.2ms** | < 10,000ms | PASS |
| Memory stability | Stable | < 100MB growth | PASS |
| P50 latency | 0.8ms | — | — |
| Max latency | 71.5ms | — | — |
| Mean latency | 2.6ms | — | — |
| Total errors | 0 | — | — |

---

## 6. SLO Forecaster Accuracy (Unit Test Data)

| Scenario | Input | Predicted | Expected | Result |
|----------|-------|-----------|----------|--------|
| Linear ramp (+50ms/min, 30 samples) | 3000→4500ms | Breach at T+30 (~6000ms) | SLO breach predicted | PASS |
| Flat at 1000ms | Stable | Safe (~1000ms) | slo_forecast_safe | PASS |
| Moderate ramp (+35ms/min) | 2000→3050ms | Approaching (~4100ms, 82% of SLO) | slo_approaching | PASS |
| Steep ramp (+100ms/min) | 4000→5000ms | Breach in <10 min | critical severity | PASS |
| Declining trend (-33ms/min) | 4000→3000ms | Improving | slo_forecast_safe | PASS |
| Perfect linear data (R²) | 1000→1190ms | R² > 0.95 | High confidence | PASS |

---

## 7. Consequence Scoper Severity Scoring

Formula: `severity_score = estimated_users × violation_magnitude × affected_models`

| Scenario | Users | Magnitude | Models | Score | Human Gate | Severity |
|----------|-------|-----------|--------|-------|-----------|----------|
| 50 users, 2 models, 1.4× SLO | 50 | 1.4 | 2 | 140 | Yes | critical |
| 5 users, 1 model, 1.2× SLO | 5 | 1.2 | 1 | 6 | No | medium |
| 200 users, 3 models, 1.4× SLO | 200 | 1.4 | 3 | 840 | Yes | critical |
| 30 users, 1 model, queue overflow | 30 | 2.0 | 1 | 60 | No | high |

Threshold: score > 100 → requires human approval.

---

## 8. Security Scan Results

| Scan | Repo | Critical | High | Medium | Low |
|------|------|----------|------|--------|-----|
| **DarkScope** | deepfield-fleet | 0 | 0 | 1 | 0 |
| **DarkScope** | fleet-llm-d | 0 | 0 | 0 | 0 |
| **NovaScan** | deepfield-fleet | Partner tier, 5 models, 4 CPU / 8GB | | | |

---

## 9. Deployment Topology (dev-cluster-1)

```
dev-cluster-1 Cluster (Intel Xeon, OpenShift 4.19)
└── fleet-llm-d namespace
    ├── fleet-controller (1/1 Running)     — actuator, intent consumer
    │   ├── 27 REST endpoints + POST /api/v1/intents
    │   ├── gRPC server (port configurable)
    │   ├── Auth + rate limiting + load shedding
    │   └── ARE Ledger recording
    ├── deepfield-fleet (1/1 Running)      — predictive brain
    │   ├── 11 nanoagents + SLO forecaster + consequence scoper
    │   ├── FleetPredictor with A/B toggle
    │   ├── Event profile scheduler
    │   └── Intent emitter → fleet-controller
    └── modelplane-mock (1/1 Running)      — ModelPlane test data
```

---

## 10. Reproducibility

```bash
# deepfield-fleet tests
cd deepfield-fleet
python3 -m pytest app/tests/ -v                    # 278 unit tests
FLEET_URL=http://... FLEET_TOKEN=... \
  python3 -m pytest app/tests/test_integration_fleet.py -v  # 10 integration tests

# fleet-llm-d harness
oc apply -f harness-job.yaml  # --suite=smoke,stress,pressure,chaos,chaos-recovery,redteam,latency,throughput
oc apply -f soak-job.yaml     # --suite=soak --duration=5m
```
