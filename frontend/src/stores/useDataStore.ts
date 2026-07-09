import { create } from 'zustand';
import type {
  EvidenceArtifact, ClassificationRecord, BaselineProfile, LoopResult, ApiCall,
  FleetHealthResponse, SLOForecastResponse, BlastRadiusResponse, IntentResponse,
  CostComparisonResponse, LedgerChainResponse,
} from '../api/client';

interface TierResult {
  records: ClassificationRecord[];
  elapsed_ms: number;
  decision_type: string;
  runtime: string;
  escalated_from_nano?: number;
}

interface DemoState {
  status: string;
  current_step?: number;
  step_id?: string;
  step_title?: string;
  step_subtitle?: string;
  step_progress?: number;
  total_steps?: number;
  narrative?: string;
  funnel?: Record<string, number>;
  agent_events?: Array<{
    agent_name: string; modality: string; class_name: string;
    taxonomy: string; severity: string; confidence: number; tier: string; timestamp: string;
  }>;
  live_agent?: { name: string; status: string; tier?: string; modality?: string; artifact_type?: string };
  baseline_metrics?: Record<string, number>;
  evidence?: EvidenceArtifact[];
  baseline?: BaselineProfile;
  nano_records?: ClassificationRecord[];
  micro_records?: ClassificationRecord[];
  macro_records?: ClassificationRecord[];
  action?: Record<string, unknown>;
  verification?: Record<string, unknown>;
  learning_proposal?: Record<string, unknown>;
  journey_summary?: Record<string, unknown>;
  flow_description?: string;
  scale_metrics?: Record<string, unknown>;
  cumulative?: Record<string, unknown>;
  claim?: Record<string, unknown>;
  evidence_detail?: Record<string, unknown>;
  inference_mode?: string;
  inference_stats?: { total_calls: number; total_tokens_out: number; avg_latency_ms: number; avg_tokens_per_sec: number; errors: number } | null;
  waiting_for_next?: boolean;
  // Fleet-specific SSE state
  fleet_metrics?: Record<string, unknown>;
  intent_flow?: Record<string, unknown>;
  slo_gauge?: Record<string, unknown>;
  replica_events?: Array<{ time: string; replicas: number; trigger: string }>;
  cost_data?: Record<string, unknown>;
  ledger_chains?: Array<{ type: string; valid: boolean; entries: number; latest_hash: string }>;
}

interface DataStore {
  demoState: DemoState;
  evidence: EvidenceArtifact[];
  baseline: BaselineProfile | null;
  classifications: ClassificationRecord[];
  loopResult: LoopResult | null;
  nanoResult: TierResult | null;
  microResult: TierResult | null;
  macroResult: TierResult | null;
  apiCalls: ApiCall<unknown>[];

  // Fleet-specific state
  fleetHealth: FleetHealthResponse | null;
  sloForecast: SLOForecastResponse | null;
  blastRadius: BlastRadiusResponse | null;
  intentResponse: IntentResponse | null;
  costComparison: CostComparisonResponse | null;
  ledgerChains: LedgerChainResponse | null;

  setDemoState: (state: DemoState) => void;
  setEvidence: (evidence: EvidenceArtifact[]) => void;
  setBaseline: (baseline: BaselineProfile | null) => void;
  setClassifications: (records: ClassificationRecord[] | ((prev: ClassificationRecord[]) => ClassificationRecord[])) => void;
  setLoopResult: (result: LoopResult | null) => void;
  setNanoResult: (result: TierResult | null) => void;
  setMicroResult: (result: TierResult | null) => void;
  setMacroResult: (result: TierResult | null) => void;
  addApiCall: (call: ApiCall<unknown>) => void;

  setFleetHealth: (health: FleetHealthResponse | null) => void;
  setSLOForecast: (forecast: SLOForecastResponse | null) => void;
  setBlastRadius: (radius: BlastRadiusResponse | null) => void;
  setIntentResponse: (response: IntentResponse | null) => void;
  setCostComparison: (cost: CostComparisonResponse | null) => void;
  setLedgerChains: (chains: LedgerChainResponse | null) => void;
}

export const useDataStore = create<DataStore>((set) => ({
  demoState: { status: 'idle' },
  evidence: [],
  baseline: null,
  classifications: [],
  loopResult: null,
  nanoResult: null,
  microResult: null,
  macroResult: null,
  apiCalls: [],

  fleetHealth: null,
  sloForecast: null,
  blastRadius: null,
  intentResponse: null,
  costComparison: null,
  ledgerChains: null,

  setDemoState: (demoState) => set({ demoState }),
  setEvidence: (evidence) => set({ evidence }),
  setBaseline: (baseline) => set({ baseline }),
  setClassifications: (records) => set((state) => ({
    classifications: typeof records === 'function' ? records(state.classifications) : records,
  })),
  setLoopResult: (loopResult) => set({ loopResult }),
  setNanoResult: (nanoResult) => set({ nanoResult }),
  setMicroResult: (microResult) => set({ microResult }),
  setMacroResult: (macroResult) => set({ macroResult }),
  addApiCall: (call) => set((state) => ({ apiCalls: [...state.apiCalls, call] })),

  setFleetHealth: (fleetHealth) => set({ fleetHealth }),
  setSLOForecast: (sloForecast) => set({ sloForecast }),
  setBlastRadius: (blastRadius) => set({ blastRadius }),
  setIntentResponse: (intentResponse) => set({ intentResponse }),
  setCostComparison: (costComparison) => set({ costComparison }),
  setLedgerChains: (ledgerChains) => set({ ledgerChains }),
}));

export const resetDataStore = () => useDataStore.setState({
  demoState: { status: 'idle' },
  evidence: [],
  baseline: null,
  classifications: [],
  loopResult: null,
  nanoResult: null,
  microResult: null,
  macroResult: null,
  apiCalls: [],
  fleetHealth: null,
  sloForecast: null,
  blastRadius: null,
  intentResponse: null,
  costComparison: null,
  ledgerChains: null,
});

export type { DemoState, TierResult };
