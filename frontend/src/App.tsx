import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Header } from './components/Header';
import { StepCard } from './components/StepCard';
import { MetricCard } from './components/MetricCard';
import { CascadeDiagram } from './components/CascadeDiagram';
import { JsonViewer } from './components/JsonViewer';
import { PipelineFunnel } from './components/PipelineFunnel';
import { LiveAgentFeed } from './components/LiveAgentFeed';
import type { AgentEvent } from './components/LiveAgentFeed';
import { StepProgress } from './components/StepProgress';
import { DetailModal, KeyValueTable, ComparisonTable } from './components/DetailModal';
import { FlowDescription } from './components/FlowDescription';
import { api } from './api/client';
import type { EvidenceArtifact, ClassificationRecord, BaselineProfile, LoopResult, ApiCall } from './api/client';

/*
 * Joseph Campbell's Hero's Journey — DeepField Multimodal
 *
 * Two modes:
 * - Manual: click through acts, run steps yourself
 * - Auto: click "Run the story" and watch it unfold via SSE streaming
 */

const MODALITY_COLORS: Record<string, string> = {
  metric: 'var(--rh-blue)', log: 'var(--rh-green)', document: 'var(--rh-orange)',
  image: 'var(--rh-purple)', audio: 'var(--rh-red)', event: 'var(--rh-yellow)',
};

const STEP_TO_ACT: Record<string, number> = {
  ordinary: 0, call: 1, threshold: 2,
  ordeal_nano: 3, ordeal_micro: 4, ordeal_macro: 5,
  reward: 6, return: 7,
  scale_10: 8, scale_50: 9, stress: 10, recovery: 11, claim: 12,
};

const ACT_LABELS = [
  'Ordinary', 'Call', 'Threshold', 'Nano', 'Micro', 'Macro',
  'Reward', 'Return', '10x', '50x', 'Stress', 'Recovery', 'Claim',
];

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
}

export default function App() {
  const [started, setStarted] = useState(false);
  const [mode, setMode] = useState<'choose' | 'manual' | 'auto'>('choose');
  const [actIndex, setActIndex] = useState(0);
  const [demoState, setDemoState] = useState<DemoState>({ status: 'idle' });
  const eventSourceRef = useRef<EventSource | null>(null);

  // Manual mode state
  const [evidence, setEvidence] = useState<EvidenceArtifact[]>([]);
  const [baseline, setBaseline] = useState<BaselineProfile | null>(null);
  const [classifications, setClassifications] = useState<ClassificationRecord[]>([]);
  const [loopResult, setLoopResult] = useState<LoopResult | null>(null);
  const [ingestStatus, setIngestStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [baselineStatus, setBaselineStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [cascadeStatus, setCascadeStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [loopStatus, setLoopStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [apiCalls, setApiCalls] = useState<ApiCall<unknown>[]>([]);
  const addCall = (call: ApiCall<unknown>) => setApiCalls(prev => [...prev, call]);

  // Detail modal state
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailTitle, setDetailTitle] = useState('');
  const [detailContent, setDetailContent] = useState<Record<string, unknown> | null>(null);
  const [detailType, setDetailType] = useState<'agent' | 'evidence' | 'baseline' | 'action' | 'learning'>('agent');

  const openDetail = (title: string, content: Record<string, unknown>, type: typeof detailType) => {
    setDetailTitle(title);
    setDetailContent(content);
    setDetailType(type);
    setDetailOpen(true);
  };

  const onAgentEventClick = (event: AgentEvent) => {
    openDetail(`Agent: ${event.agent_name}`, {
      tier: event.tier,
      taxonomy: event.taxonomy,
      class_name: event.class_name,
      severity: event.severity,
      confidence: event.confidence,
      rationale: event.rationale || '(no rationale recorded)',
      decision_type: event.tier === 'nano' ? 'Deterministic (no LLM)' : event.tier === 'micro' ? 'Rule-backed (CPU)' : 'Template-based (CPU)',
      runtime: 'CPU — no GPU, no LLM API',
    }, 'agent');
  };

  // SSE connection for auto mode
  useEffect(() => {
    if (mode !== 'auto') return;
    const es = new EventSource('/api/v1/stream');
    eventSourceRef.current = es;
    es.addEventListener('demo', (e) => {
      const data = JSON.parse(e.data) as DemoState;
      setDemoState(data);
      if (data.step_id) {
        const act = STEP_TO_ACT[data.step_id];
        if (act !== undefined) setActIndex(act);
      }
    });
    return () => { es.close(); eventSourceRef.current = null; };
  }, [mode]);

  const startAuto = useCallback(async () => {
    setMode('auto');
    await fetch('/api/v1/demo/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  }, []);

  const stopAuto = useCallback(async () => {
    await fetch('/api/v1/demo/stop', { method: 'POST' });
    setDemoState({ status: 'stopped' });
  }, []);

  // Manual callbacks
  const doIngest = useCallback(async () => {
    setIngestStatus('running');
    const call = await api.ingestFixture();
    addCall(call as ApiCall<unknown>);
    setEvidence(call.response.data);
    setIngestStatus('done');
  }, []);
  const doBaseline = useCallback(async () => {
    setBaselineStatus('running');
    const call = await api.buildBaseline();
    addCall(call as ApiCall<unknown>);
    setBaseline(call.response.data);
    setBaselineStatus('done');
  }, []);
  const doCascade = useCallback(async () => {
    setCascadeStatus('running');
    const call = await api.runCascade();
    addCall(call as ApiCall<unknown>);
    setClassifications(call.response.data);
    setCascadeStatus('done');
  }, []);
  const doLoop = useCallback(async () => {
    setLoopStatus('running');
    const call = await api.runLoop();
    addCall(call as ApiCall<unknown>);
    setLoopResult(call.response.data);
    setLoopStatus('done');
  }, []);

  // --- Hero screen ---
  if (!started) {
    return (
      <div onClick={() => setStarted(true)}
        style={{ height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', background: 'var(--bg-dark)' }}>
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.2 }}>
              DeepField<span style={{ color: 'var(--rh-red)' }}> Multimodal</span>
            </div>
            <div style={{ fontSize: 18, color: 'var(--text-dim)', marginTop: 12 }}>Enterprise Signal Intelligence</div>
            <div style={{ fontSize: 14, color: 'var(--text-disabled)', marginTop: 24, fontFamily: 'Red Hat Mono, monospace' }}>
              Signals → Decide → Act → Verify → Learn
            </div>
          </div>
        </motion.div>
        <motion.div animate={{ opacity: [0.3, 0.8, 0.3] }} transition={{ repeat: Infinity, duration: 2.5 }}
          style={{ marginTop: 48, fontSize: 13, color: 'var(--text-dim)' }}>
          Click anywhere to begin
        </motion.div>
      </div>
    );
  }

  // --- Mode selection ---
  if (mode === 'choose') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ display: 'flex', gap: 24 }}>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              onClick={startAuto}
              style={{
                background: 'var(--surface-1)', border: '2px solid var(--rh-red)', borderRadius: 12,
                padding: '32px 40px', cursor: 'pointer', textAlign: 'center', maxWidth: 280,
              }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>▶</div>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Run the Story</div>
              <div style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6 }}>
                Watch the full Hero's Journey unfold automatically with live agent activity streaming.
              </div>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              onClick={() => setMode('manual')}
              style={{
                background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 12,
                padding: '32px 40px', cursor: 'pointer', textAlign: 'center', maxWidth: 280,
              }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🎮</div>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Step Through</div>
              <div style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6 }}>
                Navigate each act manually. Run each step yourself and explore the data.
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    );
  }

  // --- Auto mode ---
  if (mode === 'auto') {
    const isRunning = demoState.status === 'running' || demoState.status === 'starting';
    const isComplete = demoState.status === 'completed';
    const allRecords = [
      ...(demoState.nano_records || []),
      ...(demoState.micro_records || []),
      ...(demoState.macro_records || []),
    ];

    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header />

        {/* Act indicator dots */}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 6, padding: '10px 0', borderBottom: '1px solid var(--border)', background: 'var(--bg-dark)' }}>
          {ACT_LABELS.map((label, i) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: i === actIndex ? 'var(--rh-red)' : i < actIndex ? 'var(--rh-green)' : 'var(--border)',
                transition: 'background 0.3s',
              }} />
              <span style={{ fontSize: 10, color: i === actIndex ? 'var(--text-primary)' : 'var(--text-disabled)' }}>{label}</span>
            </div>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, maxWidth: 900, margin: '0 auto', padding: '24px 24px', width: '100%' }}>
          {/* Step progress */}
          {isRunning && demoState.step_title && (
            <StepProgress
              progress={demoState.step_progress || 0}
              title={demoState.step_title}
              subtitle={demoState.step_subtitle || ''}
            />
          )}

          {/* Narrative */}
          <AnimatePresence mode="wait">
            {demoState.narrative && (
              <motion.div key={demoState.narrative.slice(0, 30)}
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                style={{
                  padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)',
                  borderRadius: 10, marginBottom: 12, fontSize: 14, color: 'var(--text-secondary)',
                  lineHeight: 1.7, fontStyle: 'italic',
                }}>
                {demoState.narrative}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Flow description — always visible in auto mode */}
          {demoState.flow_description && (
            <FlowDescription text={demoState.flow_description} alwaysOpen />
          )}

          {/* Live agent indicator */}
          {isRunning && demoState.live_agent && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16,
                padding: '8px 12px', background: 'var(--surface-2)', borderRadius: 8,
                border: '1px solid var(--border)',
              }}>
              <motion.div
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 1 }}
                style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--rh-green)' }}
              />
              <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                <strong style={{ color: 'var(--text-primary)' }}>{demoState.live_agent.name}</strong>
                {' '}{demoState.live_agent.status}
                {demoState.live_agent.tier && <span style={{ marginLeft: 8, color: 'var(--text-disabled)' }}>({demoState.live_agent.tier})</span>}
                {'decision_type' in demoState.live_agent && (
                  <span style={{ marginLeft: 8, fontSize: 10, color: 'var(--rh-teal)' }}>
                    {String((demoState.live_agent as Record<string, string>).decision_type)} · {String((demoState.live_agent as Record<string, string>).runtime)}
                  </span>
                )}
              </span>
            </motion.div>
          )}

          {/* Scale metrics (for scale/stress/recovery acts) */}
          {demoState.scale_metrics && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
              <MetricCard label="Lines" value={String((demoState.scale_metrics as Record<string, unknown>).lines || '—')} color="var(--rh-blue)" />
              <MetricCard label="Evidence" value={String((demoState.scale_metrics as Record<string, unknown>).evidence || '—')} color="var(--rh-teal)" />
              <MetricCard label="Classifications" value={String((demoState.scale_metrics as Record<string, unknown>).classifications || '—')} color="var(--rh-green)" />
              <MetricCard label="CPU Time" value={`${(demoState.scale_metrics as Record<string, unknown>).elapsed_ms || '—'}ms`} color="var(--rh-orange)" />
            </div>
          )}

          {/* Cumulative totals (during scale acts) */}
          {demoState.cumulative && (demoState.step_id || '').startsWith('scale') || (demoState.step_id || '') === 'stress' || (demoState.step_id || '') === 'recovery' ? (
            demoState.cumulative && (
              <div style={{ fontSize: 11, color: 'var(--text-disabled)', marginBottom: 12, fontFamily: 'Red Hat Mono, monospace', display: 'flex', gap: 16, justifyContent: 'center' }}>
                <span>Total evidence: {String((demoState.cumulative as Record<string, unknown>).total_evidence || 0)}</span>
                <span>Total classifications: {String((demoState.cumulative as Record<string, unknown>).total_classifications || 0)}</span>
                <span>Lines monitored: {String((demoState.cumulative as Record<string, unknown>).lines_monitored || 0)}</span>
              </div>
            )
          ) : null}

          {/* Two-column layout: funnel + agent feed */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {demoState.funnel && <PipelineFunnel funnel={demoState.funnel} />}
            {demoState.agent_events && <LiveAgentFeed events={demoState.agent_events} onEventClick={onAgentEventClick} />}
          </div>

          {/* Cascade diagram when we have records */}
          {allRecords.length > 0 && (
            <CascadeDiagram records={allRecords}
              activeStage={demoState.step_id === 'ordeal_nano' ? 'nano' : demoState.step_id === 'ordeal_micro' ? 'micro' : demoState.step_id === 'ordeal_macro' ? 'macro' : 'all'} />
          )}

          {/* The Claim — final metrics on completion */}
          {isComplete && demoState.claim && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 16 }}>
                <MetricCard label="Evidence Processed" value={String((demoState.claim as Record<string, unknown>).total_evidence_processed || '—')} color="var(--rh-blue)" />
                <MetricCard label="Classifications" value={String((demoState.claim as Record<string, unknown>).total_classifications || '—')} color="var(--rh-green)" />
                <MetricCard label="Peak Lines" value={String((demoState.claim as Record<string, unknown>).peak_lines_monitored || '—')} color="var(--rh-teal)" />
                <MetricCard label="Actions Proposed" value={String((demoState.claim as Record<string, unknown>).total_actions_proposed || '—')} color="var(--rh-orange)" />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 8 }}>
                <MetricCard label="Agents" value={String((demoState.claim as Record<string, unknown>).agents || 17)} color="var(--rh-purple)" />
                <MetricCard label="Tiers" value={String((demoState.claim as Record<string, unknown>).tiers || 3)} color="var(--rh-purple)" />
                <MetricCard label="GPU" value={String((demoState.claim as Record<string, unknown>).gpu || 'none')} color="var(--rh-green)" />
                <MetricCard label="LLM" value={String((demoState.claim as Record<string, unknown>).llm || 'none')} color="var(--rh-green)" />
              </div>
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
                style={{
                  marginTop: 24, padding: 20, background: 'var(--surface-1)',
                  border: '1px solid var(--rh-red)40', borderRadius: 10, textAlign: 'center',
                }}>
                <p style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', margin: 0, fontFamily: 'Red Hat Display, sans-serif' }}>
                  All on CPU. No GPU. No LLM.
                </p>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 12, lineHeight: 1.8 }}>
                  17 deterministic and rule-backed agents. Three classification tiers.
                  Scaled to 50 factory lines. Survived a 15% failure storm.
                  Signals → Decide → Act → Verify → Learn — in milliseconds.
                </p>
                <p style={{ fontSize: 13, color: 'var(--rh-red)', marginTop: 12, fontWeight: 700 }}>
                  The hero returns. The cycle begins again.
                </p>
              </motion.div>
              {demoState.flow_description && <FlowDescription text={demoState.flow_description} alwaysOpen />}
            </motion.div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '14px 32px', borderTop: '1px solid var(--border)', background: 'var(--surface-1)',
        }}>
          <button onClick={() => { stopAuto(); setMode('choose'); setActIndex(0); }}
            style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-dim)', padding: '6px 16px', borderRadius: 6, fontSize: 13 }}>
            ← Exit
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
            {isRunning ? `Step ${(demoState.current_step || 0) + 1} / ${demoState.total_steps || 8}` : demoState.status}
          </span>
          {isComplete && (
            <button onClick={startAuto}
              style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '6px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600 }}>
              Run Again
            </button>
          )}
          {isRunning && (
            <button onClick={stopAuto}
              style={{ background: 'none', border: '1px solid var(--rh-red)', color: 'var(--rh-red)', padding: '6px 18px', borderRadius: 6, fontSize: 13 }}>
              Stop
            </button>
          )}
          {!isRunning && !isComplete && <div />}
        </div>

        {/* Detail modal — slides in when user clicks an agent event */}
        <DetailModal open={detailOpen} title={detailTitle} onClose={() => setDetailOpen(false)}>
          {detailContent && detailType === 'agent' && (
            <div>
              <div style={{ fontSize: 12, color: 'var(--rh-teal)', marginBottom: 12, fontWeight: 700 }}>
                {String(detailContent.decision_type)} · {String(detailContent.runtime)}
              </div>
              <KeyValueTable data={{
                Tier: detailContent.tier,
                Taxonomy: detailContent.taxonomy,
                Classification: detailContent.class_name,
                Severity: detailContent.severity,
                Confidence: `${Number(detailContent.confidence) * 100}%`,
              }} label="Classification" />
              <div style={{
                padding: 12, background: 'var(--surface-2)', borderRadius: 6, marginBottom: 12,
                fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7,
              }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4, fontWeight: 600 }}>RATIONALE</div>
                {String(detailContent.rationale)}
              </div>
            </div>
          )}
          {detailContent && detailType !== 'agent' && (
            <KeyValueTable data={detailContent} />
          )}
        </DetailModal>
      </div>
    );
  }

  // --- Manual mode (existing, simplified) ---
  const manualActs = ['ordinary', 'call', 'threshold', 'ordeal', 'reward', 'return'] as const;
  const manualMeta: Record<string, { title: string; subtitle: string; next: string }> = {
    ordinary:  { title: 'The Ordinary World',     subtitle: 'Everything is normal. The factory hums.',       next: 'Begin the story →' },
    call:      { title: 'The Call to Adventure',   subtitle: 'Signals arrive. Something is different.',      next: 'Cross the threshold →' },
    threshold: { title: 'Crossing the Threshold',  subtitle: 'The baseline reveals the shape of normal.',    next: 'Face the ordeal →' },
    ordeal:    { title: 'The Ordeal',              subtitle: 'Multi-modal evidence converges on the truth.', next: 'Claim the reward →' },
    reward:    { title: 'The Reward',              subtitle: 'The system proposes what to do — safely.',     next: 'Begin the return →' },
    return:    { title: 'The Return',              subtitle: 'What was learned will protect the future.',    next: '' },
  };
  const currentAct = manualActs[actIndex];
  const meta = manualMeta[currentAct];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />
      <div style={{ display: 'flex', justifyContent: 'center', gap: 6, padding: '12px 0', borderBottom: '1px solid var(--border)', background: 'var(--bg-dark)' }}>
        {manualActs.map((act, i) => (
          <div key={act} onClick={() => { if (i <= actIndex) setActIndex(i); }}
            style={{ width: 8, height: 8, borderRadius: '50%', cursor: i <= actIndex ? 'pointer' : 'default',
              background: i === actIndex ? 'var(--rh-red)' : i < actIndex ? 'var(--rh-green)' : 'var(--border)' }} />
        ))}
      </div>
      <div style={{ flex: 1, maxWidth: 840, margin: '0 auto', padding: '32px 24px', width: '100%' }}>
        <AnimatePresence mode="wait">
          <motion.div key={currentAct} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={{ duration: 0.3 }}>
            <div style={{ marginBottom: 32 }}>
              <div style={{ fontSize: 12, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 800, marginBottom: 4 }}>ACT {actIndex + 1} OF {manualActs.length}</div>
              <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>{meta.title}</h2>
              <p style={{ fontSize: 16, color: 'var(--text-dim)', margin: 0 }}>{meta.subtitle}</p>
            </div>

            {currentAct === 'ordinary' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>A factory production line hums with the rhythm of precision machinery. Bearings spin, temperatures hold steady. Every signal says: <em>normal</em>.</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 24 }}>
                  <MetricCard label="Vibration RMS" value="0.22" color="var(--rh-green)" detail="Within baseline" />
                  <MetricCard label="Temperature" value="38.2°C" color="var(--rh-green)" detail="Stable" />
                  <MetricCard label="Defect Rate" value="0.1%" color="var(--rh-green)" detail="Normal" />
                </div>
              </div>
            )}
            {currentAct === 'call' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>Then the signals change. Vibration drifts upward. Temperature creeps. An inspection camera captures something. An operator writes a note.</p>
                <StepCard num={1} title="Ingest Multimodal Evidence" status={ingestStatus} onRun={doIngest} buttonLabel="Ingest signals">
                  {evidence.length > 0 && (
                    <div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
                        <MetricCard label="Artifacts" value={evidence.length} color="var(--rh-blue)" />
                        <MetricCard label="Modalities" value={new Set(evidence.map(e => e.modality)).size} color="var(--rh-teal)" />
                        <MetricCard label="Sources" value={new Set(evidence.map(e => e.source)).size} color="var(--rh-orange)" />
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {evidence.map(e => (
                          <span key={e.evidence_id} style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: (MODALITY_COLORS[e.modality] || 'var(--border)') + '20', border: `1px solid ${MODALITY_COLORS[e.modality] || 'var(--border)'}40`, color: 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace' }}>
                            {e.modality}/{e.artifact_type}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </StepCard>
              </div>
            )}
            {currentAct === 'threshold' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>DeepField compiles everything into a <strong>baseline profile</strong> — thresholds, ranges, and statistical signatures.</p>
                {evidence.length === 0 && <StepCard num={1} title="Ingest evidence first" status={ingestStatus} onRun={doIngest} buttonLabel="Ingest" />}
                <StepCard num={2} title="Build Baseline Profile" status={baselineStatus} onRun={evidence.length > 0 ? doBaseline : undefined} buttonLabel="Compile baseline">
                  {baseline && <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}><MetricCard label="Confidence" value={`${(baseline.confidence * 100).toFixed(0)}%`} color="var(--rh-green)" /><MetricCard label="Thresholds" value={Object.keys(baseline.thresholds).length} color="var(--rh-orange)" /><MetricCard label="Ranges" value={Object.keys(baseline.normal_ranges).length} color="var(--rh-teal)" /></div>}
                </StepCard>
              </div>
            )}
            {currentAct === 'ordeal' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>Evidence flows through three tiers: <strong>nanoagents</strong> detect drift, <strong>microagents</strong> classify defects, <strong>macroagents</strong> build the timeline.</p>
                {evidence.length === 0 && <StepCard num={1} title="Ingest evidence first" status={ingestStatus} onRun={doIngest} buttonLabel="Ingest" />}
                {evidence.length > 0 && !baseline && <StepCard num={2} title="Build baseline first" status={baselineStatus} onRun={doBaseline} buttonLabel="Build baseline" />}
                <StepCard num={3} title="Run Classification Cascade" status={cascadeStatus} onRun={baseline ? doCascade : undefined} buttonLabel="Run cascade">
                  {classifications.length > 0 && (
                    <div>
                      <CascadeDiagram records={classifications} activeStage="all" />
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                        <MetricCard label="Total" value={classifications.length} />
                        <MetricCard label="Nano" value={classifications.filter(c => c.agent_tier === 'nano').length} color="var(--rh-blue)" />
                        <MetricCard label="Micro" value={classifications.filter(c => c.agent_tier === 'micro').length} color="var(--rh-green)" />
                        <MetricCard label="Macro" value={classifications.filter(c => c.agent_tier === 'macro').length} color="var(--rh-purple)" />
                      </div>
                    </div>
                  )}
                </StepCard>
              </div>
            )}
            {currentAct === 'reward' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>DeepField proposes a <strong>safe, governed action</strong> — never destructive, always requiring human approval.</p>
                {evidence.length === 0 && <StepCard num={1} title="Ingest evidence first" status={ingestStatus} onRun={doIngest} buttonLabel="Ingest" />}
                {evidence.length > 0 && !baseline && <StepCard num={2} title="Build baseline first" status={baselineStatus} onRun={doBaseline} buttonLabel="Build baseline" />}
                <StepCard num={4} title="Run Full Agent Loop" status={loopStatus} onRun={baseline ? doLoop : undefined} buttonLabel="Decide → Act → Verify → Learn">
                  {loopResult && (
                    <div>
                      {loopResult.actions.map(a => (
                        <div key={a.action_id} style={{ padding: 10, background: 'var(--surface-2)', borderRadius: 8, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
                          <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--rh-blue)' }} />
                          <div><div style={{ fontSize: 14, fontWeight: 600 }}>{a.action_type}</div><div style={{ fontSize: 11, color: 'var(--text-dim)' }}>Status: {a.status} · {a.requires_human_approval ? 'Requires approval' : 'Auto'}</div></div>
                          <span style={{ marginLeft: 'auto', padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, background: 'var(--rh-green-dim)', color: 'var(--rh-green)' }}>SAFE</span>
                        </div>
                      ))}
                    </div>
                  )}
                </StepCard>
              </div>
            )}
            {currentAct === 'return' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>The hero returns transformed. DeepField captures what was learned as <strong>proposals</strong> that require human review.</p>
                {loopResult?.learning_proposals.map(p => (
                  <div key={p.proposal_id} style={{ padding: 14, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, marginBottom: 8 }}>
                    <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, background: 'var(--rh-purple-dim)', color: 'var(--rh-purple)' }}>{p.proposal_type}</span>
                    <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>{p.rationale}</p>
                  </div>
                ))}
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
                  style={{ marginTop: 24, padding: 20, background: 'var(--surface-1)', border: '1px solid var(--rh-red)40', borderRadius: 10, textAlign: 'center' }}>
                  <p style={{ fontSize: 15, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.8 }}>
                    The hero returns. The cycle begins again.
                  </p>
                </motion.div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 32px', borderTop: '1px solid var(--border)', background: 'var(--surface-1)' }}>
        <button onClick={() => actIndex > 0 ? setActIndex(actIndex - 1) : setMode('choose')}
          style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-dim)', padding: '6px 16px', borderRadius: 6, fontSize: 13 }}>
          ← {actIndex === 0 ? 'Exit' : 'Back'}
        </button>
        <span style={{ fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>{actIndex + 1} / {manualActs.length}</span>
        {meta.next ? (
          <button onClick={() => setActIndex(Math.min(manualActs.length - 1, actIndex + 1))}
            style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '6px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600 }}>
            {meta.next}
          </button>
        ) : <div />}
      </div>
    </div>
  );
}
