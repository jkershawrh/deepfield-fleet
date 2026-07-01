const BASE = '';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// --- Types ---

export interface EvidenceArtifact {
  evidence_id: string;
  signal_id: string | null;
  cluster_id: string | null;
  namespace: string | null;
  source: string;
  modality: string;
  artifact_type: string;
  content_text: string | null;
  features: Record<string, unknown>;
  labels: Record<string, unknown>;
  sensitivity: string;
  timestamp: string;
  created_at: string;
}

export interface ClassificationRecord {
  classification_id: string;
  target_type: string;
  target_id: string;
  agent_tier: string;
  agent_name: string;
  taxonomy: string;
  class_name: string;
  severity: string;
  confidence: number;
  rationale: string;
  evidence_ids: string[];
  labels: Record<string, unknown>;
  metrics: Record<string, unknown>;
  created_at: string;
}

export interface BaselineProfile {
  baseline_id: string;
  scope_type: string;
  scope_id: string;
  modality: string;
  profile_version: number;
  normal_ranges: Record<string, unknown>;
  thresholds: Record<string, unknown>;
  feature_stats: Record<string, unknown>;
  confidence: number;
  status: string;
  created_at: string;
}

export interface BaselineBuildJob {
  job_id: string;
  status: string;
  source_specs: unknown[];
  scope: Record<string, unknown>;
  time_range: Record<string, unknown>;
  outputs: Record<string, unknown>;
  metrics: Record<string, unknown>;
  error: string | null;
  created_at: string;
}

export interface AgentAction {
  action_id: string;
  action_type: string;
  status: string;
  requires_human_approval: boolean;
  payload: Record<string, unknown>;
  created_by_agent: string;
  created_at: string;
  executed_at: string | null;
}

export interface VerificationRecord {
  verification_id: string;
  action_id: string;
  verification_type: string;
  expected_outcome: Record<string, unknown>;
  observed_outcome: Record<string, unknown>;
  status: string;
  confidence: number;
  created_at: string;
}

export interface LearningProposal {
  proposal_id: string;
  source_type: string;
  proposal_type: string;
  target_scope: Record<string, unknown>;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  rationale: string;
  confidence: number;
  status: string;
  created_at: string;
}

// --- API ---

export const api = {
  health: () => get<{ status: string }>('/health'),

  evidence: {
    list: (modality?: string) =>
      get<EvidenceArtifact[]>(`/api/v1/multimodal/evidence${modality ? `?modality=${modality}` : ''}`),
    get: (id: string) => get<EvidenceArtifact>(`/api/v1/multimodal/evidence/${id}`),
    submit: (data: Partial<EvidenceArtifact>) =>
      post<EvidenceArtifact>('/api/v1/multimodal/evidence', data),
  },

  baseline: {
    createJob: (spec: { source_specs?: unknown[]; scope?: Record<string, unknown>; time_range?: Record<string, unknown> }) =>
      post<BaselineBuildJob>('/api/v1/baseline/jobs', spec),
    listJobs: () => get<BaselineBuildJob[]>('/api/v1/baseline/jobs'),
    getJob: (id: string) => get<BaselineBuildJob>(`/api/v1/baseline/jobs/${id}`),
    cancelJob: (id: string) => post<BaselineBuildJob>(`/api/v1/baseline/jobs/${id}/cancel`),
    listProfiles: () => get<BaselineProfile[]>('/api/v1/baseline/profiles'),
    getProfile: (id: string) => get<BaselineProfile>(`/api/v1/baseline/profiles/${id}`),
    activate: (id: string) => post<BaselineProfile>(`/api/v1/baseline/profiles/${id}/activate`),
  },

  classification: {
    run: (evidence: EvidenceArtifact[], baselineId?: string) =>
      post<ClassificationRecord[]>('/api/v1/classification/run', {
        evidence,
        baseline_id: baselineId,
      }),
    listRecords: (tier?: string) =>
      get<ClassificationRecord[]>(`/api/v1/classification/records${tier ? `?agent_tier=${tier}` : ''}`),
    getRecord: (id: string) => get<ClassificationRecord>(`/api/v1/classification/records/${id}`),
  },

  agentLoop: {
    proposeAction: (data: { action_type: string; payload?: Record<string, unknown> }) =>
      post<AgentAction>('/api/v1/agent-loop/actions', data),
    listActions: (status?: string) =>
      get<AgentAction[]>(`/api/v1/agent-loop/actions${status ? `?status=${status}` : ''}`),
    approveAction: (id: string) => post<AgentAction>(`/api/v1/agent-loop/actions/${id}/approve`),
    executeAction: (id: string) => post<AgentAction>(`/api/v1/agent-loop/actions/${id}/execute`),
    listVerifications: () => get<VerificationRecord[]>('/api/v1/agent-loop/verifications'),
    listProposals: (status?: string) =>
      get<LearningProposal[]>(`/api/v1/agent-loop/learning-proposals${status ? `?status=${status}` : ''}`),
    acceptProposal: (id: string) =>
      post<LearningProposal>(`/api/v1/agent-loop/learning-proposals/${id}/accept`),
    rejectProposal: (id: string) =>
      post<LearningProposal>(`/api/v1/agent-loop/learning-proposals/${id}/reject`),
  },
};
