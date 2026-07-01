"""Classification engine — orchestrates the nano->micro->macro cascade."""

from typing import Optional

from app.classification.cascade import should_escalate_to_macro, should_escalate_to_micro
from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact
from app.macroagents.action_planner import ActionPlannerAgent
from app.macroagents.incident_timeline import IncidentTimelineAgent
from app.macroagents.learning_proposal_agent import LearningProposalMacroAgent
from app.macroagents.root_cause_hypothesis import RootCauseHypothesisAgent
from app.macroagents.verification_planner import VerificationPlannerAgent
from app.microagents.audio_classifier import AudioAnomalyClassifierAgent
from app.microagents.document_classifier import DocumentClassifierAgent
from app.microagents.image_classifier import ImageDefectClassifierAgent
from app.microagents.text_classifier import TextClassifierAgent
from app.nanoagents.pipeline import run_pipeline


class ClassificationEngine:
    def __init__(self):
        self._micro_agents = [
            TextClassifierAgent(),
            DocumentClassifierAgent(),
            ImageDefectClassifierAgent(),
            AudioAnomalyClassifierAgent(),
        ]
        self._macro_agents = [
            IncidentTimelineAgent(),
            RootCauseHypothesisAgent(),
            ActionPlannerAgent(),
            VerificationPlannerAgent(),
            LearningProposalMacroAgent(),
        ]

    def classify(
        self,
        evidence: list[EvidenceArtifact],
        baseline: Optional[BaselineProfile],
    ) -> list[ClassificationRecord]:
        all_records = []

        nano_records = run_pipeline(evidence, baseline)
        all_records.extend(nano_records)

        micro_evidence = [
            ev for ev in evidence
            if should_escalate_to_micro(nano_records, ev)
        ]

        micro_records = []
        if micro_evidence:
            for agent in self._micro_agents:
                relevant = [ev for ev in micro_evidence if ev.modality in getattr(agent, "modalities", {ev.modality})]
                if relevant:
                    micro_records.extend(agent.classify(relevant))
            all_records.extend(micro_records)

        if should_escalate_to_macro(micro_records, evidence):
            for agent in self._macro_agents:
                macro_records = agent.reason(evidence, nano_records + micro_records, baseline)
                all_records.extend(macro_records)

        return all_records
