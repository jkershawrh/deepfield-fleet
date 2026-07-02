export interface ApiCall<T> {
  request: { method: string; path: string; body?: unknown };
  response: { status: number; data: T };
  elapsed: number;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<ApiCall<T>> {
  const start = performance.now();
  const res = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json() as T;
  return {
    request: { method, path, body },
    response: { status: res.status, data },
    elapsed: performance.now() - start,
  };
}

export interface EvidenceArtifact {
  evidence_id: string;
  modality: string;
  artifact_type: string;
  source: string;
  content_text: string | null;
  features: Record<string, unknown>;
  labels: Record<string, unknown>;
  sensitivity: string;
  timestamp: string;
}

export interface ClassificationRecord {
  classification_id: string;
  target_type: string;
  agent_tier: string;
  agent_name: string;
  taxonomy: string;
  class_name: string;
  severity: string;
  confidence: number;
  rationale: string;
  evidence_ids: string[];
  metrics?: Record<string, unknown>;
}

export interface BaselineProfile {
  baseline_id: string;
  scope_type: string;
  scope_id: string;
  modality: string;
  confidence: number;
  status: string;
  normal_ranges: Record<string, unknown>;
  thresholds: Record<string, unknown>;
  feature_stats: Record<string, unknown>;
}

export interface AgentAction {
  action_id: string;
  action_type: string;
  status: string;
  requires_human_approval: boolean;
  payload: Record<string, unknown>;
  created_by_agent: string;
}

export interface VerificationRecord {
  verification_id: string;
  verification_type: string;
  status: string;
  confidence: number;
  expected_outcome: Record<string, unknown>;
}

export interface LearningProposal {
  proposal_id: string;
  proposal_type: string;
  rationale: string;
  confidence: number;
  status: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}

export interface LoopResult {
  classifications: ClassificationRecord[];
  actions: AgentAction[];
  verifications: VerificationRecord[];
  learning_proposals: LearningProposal[];
}

export const api = {
  health: () => request<{ status: string }>('GET', '/health'),

  ingestFixture: () =>
    request<EvidenceArtifact[]>('POST', '/api/v1/demo/ingest'),

  buildBaseline: () =>
    request<BaselineProfile>('POST', '/api/v1/demo/baseline'),

  runCascade: () =>
    request<ClassificationRecord[]>('POST', '/api/v1/demo/classify'),

  runLoop: () =>
    request<LoopResult>('POST', '/api/v1/demo/loop'),

  listEvidence: () =>
    request<EvidenceArtifact[]>('GET', '/api/v1/multimodal/evidence'),

  classifyNano: () =>
    request<{ tier: string; records: ClassificationRecord[]; count: number; elapsed_ms: number; agents: string[]; decision_type: string; runtime: string }>('POST', '/api/v1/demo/classify/nano'),

  classifyMicro: () =>
    request<{ tier: string; records: ClassificationRecord[]; count: number; elapsed_ms: number; escalated_from_nano: number; agents: string[]; decision_type: string; runtime: string }>('POST', '/api/v1/demo/classify/micro'),

  classifyMacro: () =>
    request<{ tier: string; records: ClassificationRecord[]; count: number; elapsed_ms: number; agents: string[]; decision_type: string; runtime: string }>('POST', '/api/v1/demo/classify/macro'),
};
