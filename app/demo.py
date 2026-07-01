"""Demo runner — walks through the full DeepField Multimodal story.

Usage:
    python -m app.demo
"""

import json
import sys
from pathlib import Path

from app.agent_loop.loop import AgentLoop
from app.baseline.compiler import BaselineCompiler
from app.classification.taxonomy import is_valid_classification
from app.multimodal.normalizer import normalize_fixture

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


def _header(text: str):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def _step(n: int, text: str):
    print(f"  [{n}] {text}")


def run_demo():
    _header("DeepField Multimodal — End-to-End Demo")
    print("  Scenario: Factory Line Bearing Failure")
    print("  Loop: Signals -> Decide -> Act -> Verify -> Learn\n")

    # Step 1: Ingest
    _header("STEP 1: Ingest Multimodal Evidence")
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    modalities = {}
    for e in evidence:
        modalities[e.modality] = modalities.get(e.modality, 0) + 1
    _step(1, f"Ingested {len(evidence)} evidence artifacts")
    for mod, count in sorted(modalities.items()):
        _step(1, f"  {mod}: {count} artifact(s)")

    # Step 2: Baseline
    _header("STEP 2: Build Baseline Profile")
    compiler = BaselineCompiler()
    baseline = compiler.compile(
        evidence=evidence,
        scope={"scope_type": "site", "scope_id": "factory-line-01"},
    )
    baseline.status = "active"
    _step(2, f"Profile scope: {baseline.scope_type}/{baseline.scope_id}")
    _step(2, f"Modality: {baseline.modality}")
    _step(2, f"Confidence: {baseline.confidence:.0%}")
    _step(2, f"Threshold groups: {len(baseline.thresholds)}")
    _step(2, f"Normal range groups: {len(baseline.normal_ranges)}")
    _step(2, f"Status: {baseline.status}")

    # Step 3: Full agent loop
    _header("STEP 3: Run Agent Loop (Decide -> Act -> Verify -> Learn)")
    loop = AgentLoop()
    result = loop.run(evidence, baseline)

    # Classifications
    classifications = result["classifications"]
    tiers = {}
    for c in classifications:
        tiers[c.agent_tier] = tiers.get(c.agent_tier, 0) + 1
    _step(3, f"Classifications: {len(classifications)} total")
    for tier in ["nano", "micro", "macro"]:
        count = tiers.get(tier, 0)
        tier_records = [c for c in classifications if c.agent_tier == tier]
        agents = {c.agent_name for c in tier_records}
        _step(3, f"  {tier}: {count} records from {len(agents)} agents ({', '.join(sorted(agents))})")

    # Key findings
    high_conf = [c for c in classifications if c.confidence >= 0.7 and c.severity in ("high", "critical")]
    if high_conf:
        _step(3, f"\n  Key findings ({len(high_conf)} high-confidence):")
        for c in high_conf[:5]:
            _step(3, f"    {c.agent_name}: {c.taxonomy}/{c.class_name} "
                      f"(sev={c.severity}, conf={c.confidence:.0%})")

    # Actions
    actions = result["actions"]
    _step(3, f"\n  Actions: {len(actions)}")
    for a in actions:
        _step(3, f"    {a.action_type} (status={a.status}, "
                  f"approval={'required' if a.requires_human_approval else 'auto'})")

    # Verifications
    verifications = result["verifications"]
    _step(3, f"\n  Verifications: {len(verifications)}")
    for v in verifications:
        _step(3, f"    {v.verification_type} (status={v.status})")

    # Learning
    proposals = result["learning_proposals"]
    _step(3, f"\n  Learning proposals: {len(proposals)}")
    for p in proposals:
        _step(3, f"    {p.proposal_type}: {p.rationale[:80]}")

    # Taxonomy validation
    invalid = [c for c in classifications if not is_valid_classification(c.taxonomy, c.class_name)]
    _step(3, f"\n  Taxonomy validation: {'PASS' if not invalid else f'FAIL ({len(invalid)} invalid)'}")

    # Summary
    _header("DEMO COMPLETE")
    print(f"  Evidence:        {len(evidence)} artifacts across {len(modalities)} modalities")
    print(f"  Baseline:        {baseline.confidence:.0%} confidence, {len(baseline.thresholds)} threshold groups")
    print(f"  Classifications: {len(classifications)} records across {len(tiers)} tiers")
    print(f"  Actions:         {len(actions)} proposed (all non-destructive)")
    print(f"  Verifications:   {len(verifications)} pending")
    print(f"  Learning:        {len(proposals)} proposals awaiting review")
    print()
    print("  Story: DeepField studied past enterprise signals, learned the shape")
    print("  of normal, classified new multimodal evidence, proposed safe action,")
    print("  created verification checks, and captured what should be learned next.")
    print()


if __name__ == "__main__":
    run_demo()
