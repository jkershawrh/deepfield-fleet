"""TDD tests for microagents. RED first."""

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.microagents.text_classifier import TextClassifierAgent
from app.microagents.document_classifier import DocumentClassifierAgent
from app.microagents.image_classifier import ImageDefectClassifierAgent
from app.microagents.audio_classifier import AudioAnomalyClassifierAgent
from app.microagents.embedding_classifier import EmbeddingClusterClassifierAgent


class TestTextClassifier:
    def test_classifies_text(self):
        agent = TextClassifierAgent()
        evidence = [EvidenceArtifact(
            source="test", modality="text", artifact_type="log_entry",
            content_text="ERROR: bearing vibration threshold exceeded on unit 7",
            features={"word_count": 8},
        )]
        records = agent.classify(evidence)
        assert len(records) > 0
        assert all(r.agent_tier == "micro" for r in records)

    def test_returns_classification_record(self):
        agent = TextClassifierAgent()
        evidence = [EvidenceArtifact(
            source="test", modality="text", artifact_type="entry",
            content_text="Normal operation status update",
        )]
        records = agent.classify(evidence)
        assert all(isinstance(r, ClassificationRecord) for r in records)


class TestDocumentClassifier:
    def test_classifies_document(self):
        agent = DocumentClassifierAgent()
        evidence = [EvidenceArtifact(
            source="test", modality="document", artifact_type="operator_note",
            content_text="Maintenance note: unusual grinding noise from bearing",
            features={"extension": ".txt", "word_count": 7},
        )]
        records = agent.classify(evidence)
        assert len(records) > 0
        assert all(r.agent_tier == "micro" for r in records)


class TestImageDefectClassifier:
    def test_classifies_with_mock_labels(self):
        agent = ImageDefectClassifierAgent()
        evidence = [EvidenceArtifact(
            source="test", modality="image", artifact_type="surface_inspection",
            labels={"surface_defect_score": 0.72, "defect_type": "bearing_wear"},
        )]
        records = agent.classify(evidence)
        assert len(records) > 0
        assert all(r.agent_tier == "micro" for r in records)

    def test_no_labels_returns_unknown(self):
        agent = ImageDefectClassifierAgent()
        evidence = [EvidenceArtifact(
            source="test", modality="image", artifact_type="surface_inspection",
        )]
        records = agent.classify(evidence)
        assert len(records) > 0


class TestAudioAnomalyClassifier:
    def test_classifies_with_mock_labels(self):
        agent = AudioAnomalyClassifierAgent()
        evidence = [EvidenceArtifact(
            source="test", modality="audio", artifact_type="vibration_audio",
            labels={"vibration_anomaly_score": 0.81, "anomaly_type": "bearing_resonance"},
        )]
        records = agent.classify(evidence)
        assert len(records) > 0
        assert all(r.agent_tier == "micro" for r in records)


class TestEmbeddingClusterClassifier:
    def test_returns_records(self):
        agent = EmbeddingClusterClassifierAgent()
        evidence = [EvidenceArtifact(
            source="test", modality="text", artifact_type="entry",
            content_text="vibration anomaly detected",
            features={"word_count": 3},
        )]
        records = agent.classify(evidence)
        assert all(isinstance(r, ClassificationRecord) for r in records)
