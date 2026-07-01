"""Macroagent: generates root-cause hypotheses from correlated evidence."""

from collections import Counter
from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact


class RootCauseHypothesisAgent:
    name = "root_cause_hypothesis"

    def reason(
        self,
        evidence: list[EvidenceArtifact],
        classifications: list[ClassificationRecord],
        baseline: Optional[BaselineProfile],
    ) -> list[ClassificationRecord]:
        family_counts = Counter(c.class_name for c in classifications if c.taxonomy == "incident_family")
        modalities = {e.modality for e in evidence}

        if family_counts:
            top_family = family_counts.most_common(1)[0][0]
        else:
            top_family = "unknown"

        hypothesis = (
            f"Root cause hypothesis: {top_family}. "
            f"Based on {len(evidence)} evidence artifacts across {len(modalities)} modalities "
            f"({', '.join(sorted(modalities))}). "
            f"Classification distribution: {dict(family_counts)}."
        )

        return [ClassificationRecord(
            target_type="incident",
            target_id=evidence[0].evidence_id if evidence else classifications[0].target_id,
            agent_tier="macro", agent_name=self.name,
            taxonomy="incident_family", class_name=top_family,
            severity="high" if len(modalities) >= 3 else "medium",
            confidence=0.7 if len(modalities) >= 3 else 0.5,
            rationale=hypothesis,
            evidence_ids=[e.evidence_id for e in evidence],
        )]
