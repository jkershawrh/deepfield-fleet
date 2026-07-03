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
import { InfraPanel } from './components/InfraPanel';
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
  inference_mode?: string;
  inference_stats?: { total_calls: number; total_tokens_out: number; avg_latency_ms: number; avg_tokens_per_sec: number; errors: number } | null;
  waiting_for_next?: boolean;
}

export default function App() {
  const [mode, setMode] = useState<'slides' | 'manual' | 'auto'>('slides');
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
  const [nanoStatus, setNanoStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [microStatus, setMicroStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [macroStatus, setMacroStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [nanoResult, setNanoResult] = useState<{ records: ClassificationRecord[]; elapsed_ms: number; decision_type: string; runtime: string } | null>(null);
  const [microResult, setMicroResult] = useState<{ records: ClassificationRecord[]; elapsed_ms: number; escalated_from_nano: number; decision_type: string; runtime: string } | null>(null);
  const [macroResult, setMacroResult] = useState<{ records: ClassificationRecord[]; elapsed_ms: number; decision_type: string; runtime: string } | null>(null);
  const [cascadeStatus, setCascadeStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [loopStatus, setLoopStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [apiCalls, setApiCalls] = useState<ApiCall<unknown>[]>([]);
  const addCall = (call: ApiCall<unknown>) => setApiCalls(prev => [...prev, call]);

  // Detail modal state — single object to avoid stale renders
  const [detail, setDetail] = useState<{ open: boolean; title: string; content: Record<string, unknown> | null; type: 'agent' | 'evidence' | 'baseline' | 'action' | 'learning' }>({ open: false, title: '', content: null, type: 'agent' });

  const detailOpen = detail.open;
  const detailTitle = detail.title;
  const detailContent = detail.content;
  const detailType = detail.type;

  const openDetail = (title: string, content: Record<string, unknown>, type: typeof detailType) => {
    setDetail({ open: true, title, content, type });
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
    if (mode !== 'auto') { eventSourceRef.current?.close(); eventSourceRef.current = null; return; }
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
    await fetch('/api/v1/demo/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    setMode('auto');
  }, []);

  const pauseAuto = useCallback(async () => {
    await fetch('/api/v1/demo/pause', { method: 'POST' });
  }, []);

  const resumeAuto = useCallback(async () => {
    await fetch('/api/v1/demo/resume', { method: 'POST' });
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
  const doNano = useCallback(async () => {
    setNanoStatus('running');
    const call = await api.classifyNano();
    addCall(call as ApiCall<unknown>);
    setNanoResult(call.response.data);
    setClassifications(prev => [...prev, ...call.response.data.records]);
    setNanoStatus('done');
  }, []);
  const doMicro = useCallback(async () => {
    setMicroStatus('running');
    const call = await api.classifyMicro();
    addCall(call as ApiCall<unknown>);
    setMicroResult(call.response.data);
    setClassifications(prev => [...prev, ...call.response.data.records]);
    setMicroStatus('done');
  }, []);
  const doMacro = useCallback(async () => {
    setMacroStatus('running');
    const call = await api.classifyMacro();
    addCall(call as ApiCall<unknown>);
    setMacroResult(call.response.data);
    setClassifications(prev => [...prev, ...call.response.data.records]);
    setMacroStatus('done');
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

  // --- Presentation slides ---
  const [slide, setSlide] = useState(0);

  const SLIDES = [
    // 0: Title
    () => (
      <div style={{ textAlign: 'center' }}>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
          <img src="/logos/redhat.svg" alt="Red Hat" style={{ height: 28 }} />
          <span style={{ color: 'var(--text-disabled)', fontSize: 28, fontWeight: 300 }}>&times;</span>
          <img src="/logos/intel.png" alt="Intel" style={{ height: 28 }} />
        </motion.div>
        <motion.h1 initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.7 }}
          style={{ fontSize: 56, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.1, margin: '24px 0 0', maxWidth: 700 }}>
          DeepField<br /><span style={{ color: 'var(--rh-red)' }}>Multimodal</span>
        </motion.h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ fontSize: 20, color: 'var(--text-dim)', marginTop: 24 }}>
          Enterprise Signal Intelligence
        </motion.p>
      </div>
    ),
    // 1: The problem
    () => (
      <div style={{ textAlign: 'center', maxWidth: 700 }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 36, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3 }}>
          Your operations generate
          <br />thousands of signals per hour.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          style={{ fontSize: 20, color: 'var(--text-dim)', marginTop: 24, lineHeight: 1.6 }}>
          Metrics. Logs. Events. Images. Audio.
          <br />Streaming right now. <strong style={{ color: 'var(--rh-orange)' }}>Unclassified.</strong>
        </motion.p>
      </div>
    ),
    // 2: The thesis
    () => (
      <div style={{ textAlign: 'center', maxWidth: 700 }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 32, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, fontStyle: 'italic', color: 'var(--text-secondary)' }}>
          "The first job of enterprise AI
          <br />is not generation.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          style={{ fontSize: 32, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, marginTop: 16 }}>
          It is classifying reality well enough
          <br />to know what should happen next."
        </motion.p>
      </div>
    ),
    // 3: The proof — compression ratio
    () => (
      <div style={{ textAlign: 'center' }}>
        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15 }}>
          <div style={{ fontSize: 120, fontWeight: 800, color: 'var(--rh-red)', fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1 }}>
            98%
          </div>
        </motion.div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          style={{ fontSize: 22, color: 'var(--text-dim)', marginTop: 16, lineHeight: 1.5 }}>
          of signals classified on CPU
          <br />before anything expensive runs.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ fontSize: 16, color: 'var(--text-disabled)', marginTop: 24 }}>
          Deterministic nanoagents compress the noise. Only what matters reaches inference.
        </motion.p>
      </div>
    ),
    // 4: How — the three tiers
    () => (
      <div style={{ maxWidth: 700 }}>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          style={{ fontSize: 14, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 2, textAlign: 'center', marginBottom: 32 }}>
          THREE TIERS — ONE PIPELINE
        </motion.p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            { tier: 'Nanoagents', count: 7, desc: 'Deterministic rules. Z-score checks, pattern matching, gating. Always CPU. Zero inference cost.', color: 'var(--rh-blue)', delay: 0.2 },
            { tier: 'Microagents', count: 5, desc: 'Rule-backed classifiers. Image defect scoring, audio anomaly, text patterns. CPU with OpenVINO extension points. LLM when configured.', color: 'var(--rh-green)', delay: 0.4 },
            { tier: 'Macroagents', count: 5, desc: 'Incident reasoning. Timeline building, root cause hypothesis, action planning. Template-based or LLM-backed.', color: 'var(--rh-purple)', delay: 0.6 },
          ].map(t => (
            <motion.div key={t.tier} initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: t.delay }}
              style={{ display: 'flex', gap: 16, padding: 20, background: 'var(--surface-1)', border: `1px solid ${t.color}40`, borderLeft: `4px solid ${t.color}`, borderRadius: '0 10px 10px 0' }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 800, color: t.color }}>{t.tier} <span style={{ fontSize: 14, fontWeight: 400, color: 'var(--text-disabled)' }}>({t.count})</span></div>
                <div style={{ fontSize: 14, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>{t.desc}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    ),
    // 5: What you already have
    () => (
      <div style={{ textAlign: 'center', maxWidth: 700 }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.4 }}>
          Start deterministic. Add LLM when ready.
        </motion.p>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginTop: 32 }}>
          {[
            { num: '207 MB', label: 'Container image', sub: 'vs 4-15 GB for ML stack' },
            { num: '26', label: 'Dependencies', sub: 'vs 150-300 for PyTorch' },
            { num: '30s', label: 'To first demo', sub: 'podman run, done' },
          ].map(s => (
            <div key={s.label} style={{ padding: 20, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, textAlign: 'center' }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--rh-red)', fontFamily: 'Red Hat Display, sans-serif' }}>{s.num}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{s.label}</div>
              <div style={{ fontSize: 11, color: 'var(--text-disabled)', marginTop: 2 }}>{s.sub}</div>
            </div>
          ))}
        </motion.div>
      </div>
    ),
    // 6: CTA — enter the walkthrough
    () => (
      <div style={{ textAlign: 'center' }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 36, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, marginBottom: 16 }}>
          Let's see it work.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          style={{ fontSize: 16, color: 'var(--text-dim)', marginBottom: 40, lineHeight: 1.6 }}>
          First, we'll walk through the pipeline step by step.
          <br />Then, we'll run it at scale.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          <button onClick={() => setMode('manual')}
            style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '16px 48px', borderRadius: 10, fontSize: 18, fontWeight: 700, cursor: 'pointer' }}>
            Next
          </button>
        </motion.div>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ marginTop: 32, fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
          207 MB container · no GPU required · 30 seconds to first demo
        </motion.div>
      </div>
    ),
  ];

  if (mode === 'slides') {
    const isLastSlide = slide === SLIDES.length - 1;
    return (
      <div
        onClick={() => { if (!isLastSlide) setSlide(s => s + 1); }}
        style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-dark)', cursor: isLastSlide ? 'default' : 'pointer' }}
      >
        {/* Slide dots */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, padding: '20px 0' }}>
          {SLIDES.map((_, i) => (
            <div key={i}
              onClick={(e) => { e.stopPropagation(); setSlide(i); }}
              style={{
                width: 8, height: 8, borderRadius: '50%', cursor: 'pointer',
                background: i === slide ? 'var(--rh-red)' : i < slide ? 'var(--rh-green)' : 'var(--border)',
                transition: 'background 0.3s',
              }}
            />
          ))}
        </div>

        {/* Slide content */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 48px' }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={slide}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            >
              {SLIDES[slide]()}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer nav */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 32px' }}>
          <button
            onClick={(e) => { e.stopPropagation(); if (slide > 0) setSlide(s => s - 1); }}
            style={{ background: 'none', border: 'none', color: slide > 0 ? 'var(--text-dim)' : 'transparent', fontSize: 13, cursor: slide > 0 ? 'pointer' : 'default', padding: '6px 16px' }}>
            ← Back
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
            {slide + 1} / {SLIDES.length}
          </span>
          {!isLastSlide && (
            <button onClick={(e) => { e.stopPropagation(); setSlide(s => s + 1); }}
              style={{ background: 'none', border: 'none', color: 'var(--text-dim)', fontSize: 13, cursor: 'pointer', padding: '6px 16px' }}>
              Next →
            </button>
          )}
          {isLastSlide && <div style={{ width: 80 }} />}
        </div>
      </div>
    );
  }


  // --- Auto mode ---
  if (mode === 'auto') {
    const isRunning = demoState.status === 'running' || demoState.status === 'starting';
    const isPaused = demoState.status === 'paused';
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
          {/* Infrastructure panel — always available */}
          <InfraPanel />

          {/* Step progress */}
          {(isRunning || isPaused) && demoState.step_title && (
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

          {/* Inference stats bar — shown when LLM is connected */}
          {demoState.inference_stats && demoState.inference_stats.total_calls > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{
                display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12,
                padding: '8px 14px', background: 'var(--surface-2)', borderRadius: 8,
                border: '1px solid var(--border)', fontSize: 11,
              }}>
              <span style={{ color: 'var(--rh-green)', fontWeight: 700 }}>INFERENCE</span>
              <span style={{ color: 'var(--text-dim)' }}>Calls: <strong style={{ color: 'var(--text-secondary)' }}>{demoState.inference_stats.total_calls}</strong></span>
              <span style={{ color: 'var(--text-dim)' }}>Tokens: <strong style={{ color: 'var(--text-secondary)' }}>{demoState.inference_stats.total_tokens_out}</strong></span>
              <span style={{ color: 'var(--text-dim)' }}>Latency: <strong style={{ color: 'var(--rh-orange)' }}>{demoState.inference_stats.avg_latency_ms}ms</strong></span>
              <span style={{ color: 'var(--text-dim)' }}>Tok/s: <strong style={{ color: 'var(--rh-blue)' }}>{demoState.inference_stats.avg_tokens_per_sec}</strong></span>
              {demoState.inference_stats.errors > 0 && (
                <span style={{ color: 'var(--rh-red)' }}>Errors: {demoState.inference_stats.errors}</span>
              )}
            </motion.div>
          )}

          {/* Inference mode indicator */}
          {demoState.inference_mode && (
            <div style={{ fontSize: 10, color: 'var(--text-disabled)', marginBottom: 8, fontFamily: 'Red Hat Mono, monospace', textAlign: 'center' }}>
              Inference mode: {demoState.inference_mode === 'llm' ? 'Live LLM via LiteLLM' : 'Simulated (rule-backed) — set LITELLM_API_BASE for live inference'}
            </div>
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

          {/* The Claim — final metrics + use cases */}
          {isComplete && demoState.claim && (() => {
            const cl = demoState.claim as Record<string, unknown>;
            return (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              {/* Logos */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginBottom: 24 }}>
                <img src="/logos/redhat.svg" alt="Red Hat" style={{ height: 24 }} />
                <span style={{ color: 'var(--text-disabled)', fontSize: 24, fontWeight: 300 }}>&times;</span>
                <img src="/logos/intel.png" alt="Intel" style={{ height: 24 }} />
              </div>

              {/* Headline stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
                <div style={{ padding: 20, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, textAlign: 'center' }}>
                  <div style={{ fontSize: 40, fontWeight: 800, color: 'var(--rh-red)', fontFamily: 'Red Hat Display, sans-serif' }}>{String(cl.total_evidence_processed)}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>Evidence artifacts processed</div>
                </div>
                <div style={{ padding: 20, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, textAlign: 'center' }}>
                  <div style={{ fontSize: 40, fontWeight: 800, color: 'var(--rh-blue)', fontFamily: 'Red Hat Display, sans-serif' }}>{String(cl.total_classifications)}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>Classifications generated</div>
                </div>
                <div style={{ padding: 20, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, textAlign: 'center' }}>
                  <div style={{ fontSize: 40, fontWeight: 800, color: 'var(--rh-teal)', fontFamily: 'Red Hat Display, sans-serif' }}>{String(cl.peak_lines_monitored)}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>Factory lines at peak scale</div>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 24 }}>
                <MetricCard label="Agents" value={String(cl.agents || 17)} color="var(--rh-purple)" />
                <MetricCard label="Tiers" value={String(cl.tiers || 3)} />
                <MetricCard label="Actions" value={String(cl.total_actions_proposed)} color="var(--rh-orange)" detail="non-destructive" />
                <MetricCard label="Learning" value={String(cl.total_learning_proposals)} color="var(--rh-green)" detail="proposals generated" />
              </div>

              {/* The claim */}
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
                style={{ padding: 24, background: 'var(--surface-1)', border: '1px solid var(--rh-red)40', borderRadius: 10, textAlign: 'center', marginBottom: 24 }}>
                <p style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', margin: 0, fontFamily: 'Red Hat Display, sans-serif' }}>
                  Classify reality before you react to it.
                </p>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 12, lineHeight: 1.8 }}>
                  Three classification tiers. Deterministic compression on CPU.
                  LLM reasoning when you need it. Scaled to 50 lines under 15% failure storm.
                  {demoState.inference_stats?.total_calls
                    ? ` ${demoState.inference_stats.total_calls} live inference calls at ${demoState.inference_stats.avg_latency_ms}ms avg.`
                    : ' All on the infrastructure you already own.'}
                </p>
              </motion.div>

              {demoState.flow_description && <FlowDescription text={demoState.flow_description} alwaysOpen />}

              {/* Where else this applies */}
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
                <div style={{ fontSize: 14, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 2, textAlign: 'center', marginBottom: 16 }}>
                  BEYOND THE FACTORY FLOOR
                </div>
                <p style={{ fontSize: 14, color: 'var(--text-dim)', textAlign: 'center', marginBottom: 20, lineHeight: 1.6 }}>
                  The same three-tier agent architecture applies anywhere signals need classification.
                  Nanoagents compress. Microagents classify. Macroagents reason.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  {[
                    { title: 'Telecom Network Operations', color: 'var(--rh-blue)',
                      nano: 'Threshold checks on latency, packet loss, signal strength across cell towers',
                      micro: 'Classify outage type: hardware, software, capacity, weather-related',
                      macro: 'Correlate across regions — is this a local fault or a cascading failure?' },
                    { title: 'Energy Grid Monitoring', color: 'var(--rh-green)',
                      nano: 'Frequency deviation, voltage sag, transformer temperature drift detection',
                      micro: 'Classify asset health from SCADA signals, vibration, thermal imaging',
                      macro: 'Predict demand-supply imbalance, propose load shedding or rerouting' },
                    { title: 'Healthcare / Clinical Systems', color: 'var(--rh-teal)',
                      nano: 'Vitals threshold alerts, lab result anomaly flags, medication interaction checks',
                      micro: 'Classify diagnostic images (X-ray, MRI), lab panel patterns, clinical notes',
                      macro: 'Correlate patient history with current signals for differential diagnosis support' },
                    { title: 'Supply Chain & Logistics', color: 'var(--rh-orange)',
                      nano: 'Delivery SLA breach detection, inventory level threshold, route deviation alerts',
                      micro: 'Classify disruption type: weather, port congestion, supplier delay, customs hold',
                      macro: 'Build impact timeline across multi-tier suppliers, propose alternate sourcing' },
                    { title: 'Financial Services / Fraud', color: 'var(--rh-purple)',
                      nano: 'Transaction velocity checks, geo-impossible travel, amount threshold breaches',
                      micro: 'Classify transaction patterns against known fraud families, merchant risk scoring',
                      macro: 'Correlate across accounts and time windows for organized fraud ring detection' },
                    { title: 'Autonomous Vehicle / Fleet', color: 'var(--rh-red)',
                      nano: 'Sensor fusion anomaly detection: lidar, camera, IMU, GPS drift checks',
                      micro: 'Classify road conditions, obstacle types, weather impact on sensor reliability',
                      macro: 'Fleet-wide incident correlation, predictive maintenance scheduling, route optimization' },
                  ].map(uc => (
                    <motion.div key={uc.title} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                      style={{ padding: 16, background: 'var(--surface-1)', border: `1px solid ${uc.color}30`, borderRadius: 10 }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: uc.color, marginBottom: 10 }}>{uc.title}</div>
                      <div style={{ fontSize: 11, lineHeight: 1.7 }}>
                        <div style={{ marginBottom: 6 }}>
                          <span style={{ color: 'var(--rh-blue)', fontFamily: 'Red Hat Mono, monospace', fontSize: 9, fontWeight: 700 }}>NANO</span>
                          <span style={{ color: 'var(--text-dim)', marginLeft: 6 }}>{uc.nano}</span>
                        </div>
                        <div style={{ marginBottom: 6 }}>
                          <span style={{ color: 'var(--rh-green)', fontFamily: 'Red Hat Mono, monospace', fontSize: 9, fontWeight: 700 }}>MICRO</span>
                          <span style={{ color: 'var(--text-dim)', marginLeft: 6 }}>{uc.micro}</span>
                        </div>
                        <div>
                          <span style={{ color: 'var(--rh-purple)', fontFamily: 'Red Hat Mono, monospace', fontSize: 9, fontWeight: 700 }}>MACRO</span>
                          <span style={{ color: 'var(--text-dim)', marginLeft: 6 }}>{uc.macro}</span>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>

                <div style={{ textAlign: 'center', marginTop: 24, padding: 16, background: 'var(--surface-1)', borderRadius: 10, border: '1px solid var(--border)' }}>
                  <p style={{ fontSize: 15, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.7 }}>
                    Same architecture. Same three tiers. Same compression economics.
                    <br />Swap the signals, swap the classifiers — the pipeline stays.
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-disabled)', marginTop: 12, fontFamily: 'Red Hat Mono, monospace' }}>
                    207 MB · Intel Xeon · Red Hat OpenShift · 30 seconds to your first demo
                  </p>
                </div>
              </motion.div>
            </motion.div>
            );
          })()}
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '14px 32px', borderTop: '1px solid var(--border)', background: 'var(--surface-1)',
        }}>
          <button onClick={() => { stopAuto(); setMode('slides'); setActIndex(0); }}
            style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-dim)', padding: '6px 16px', borderRadius: 6, fontSize: 13 }}>
            ← Exit
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
            {isRunning || isPaused ? `Step ${(demoState.current_step || 0) + 1} / ${demoState.total_steps || 13}${isPaused ? ' — PAUSED' : ''}` : demoState.status}
          </span>
          {isComplete && (
            <button onClick={startAuto}
              style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '6px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600 }}>
              Run Again
            </button>
          )}
          {(isRunning || isPaused) && (
            <div style={{ display: 'flex', gap: 8 }}>
              {isRunning && (
                <button onClick={pauseAuto}
                  style={{ background: 'none', border: '1px solid var(--rh-yellow)', color: 'var(--rh-yellow)', padding: '6px 18px', borderRadius: 6, fontSize: 13 }}>
                  Pause
                </button>
              )}
              {isPaused && demoState.waiting_for_next && (
                <button onClick={resumeAuto}
                  style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '8px 24px', borderRadius: 6, fontSize: 14, fontWeight: 700 }}>
                  Next →
                </button>
              )}
              {isPaused && !demoState.waiting_for_next && (
                <button onClick={resumeAuto}
                  style={{ background: 'var(--rh-green)', border: 'none', color: '#fff', padding: '6px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600 }}>
                  Resume
                </button>
              )}
              <button onClick={stopAuto}
                style={{ background: 'none', border: '1px solid var(--rh-red)', color: 'var(--rh-red)', padding: '6px 18px', borderRadius: 6, fontSize: 13 }}>
                Stop
              </button>
            </div>
          )}
          {!isRunning && !isComplete && !isPaused && <div />}
        </div>

        {/* Detail modal — slides in when user clicks an agent event */}
        <DetailModal open={detailOpen} title={detailTitle} onClose={() => setDetail(d => ({ ...d, open: false }))}>
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
          {detailContent && detailType === 'learning' && (
            <div>
              <KeyValueTable data={{ proposal_type: detailContent.proposal_type, status: detailContent.status, confidence: `${Number(detailContent.confidence) * 100}%` }} label="Proposal" />
              <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 6, marginBottom: 12, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4, fontWeight: 600 }}>RATIONALE</div>
                {String(detailContent.rationale)}
              </div>
              {'before' in detailContent && 'after' in detailContent && (
                <ComparisonTable before={detailContent.before as Record<string, unknown>} after={detailContent.after as Record<string, unknown>} label="Before → After" />
              )}
            </div>
          )}
          {detailContent && detailType === 'action' && (
            <KeyValueTable data={detailContent} label="Details" />
          )}
          {detailContent && !['agent', 'learning', 'action'].includes(detailType) && (
            <KeyValueTable data={detailContent} />
          )}
        </DetailModal>
      </div>
    );
  }

  // --- Manual mode (existing, simplified) ---
  const manualActs = ['ordinary', 'call', 'threshold', 'ordeal', 'reward', 'return'] as const;
  const manualMeta: Record<string, { title: string; subtitle: string; next: string }> = {
    ordinary:  { title: 'Normal Operations',       subtitle: 'Everything is normal. The factory hums.',                next: 'See the signals →' },
    call:      { title: 'Signal Ingestion',        subtitle: 'Multimodal evidence arrives from the factory floor.',    next: 'Build the baseline →' },
    threshold: { title: 'Baseline Compilation',    subtitle: 'Learning the shape of normal from historical data.',     next: 'Run the cascade →' },
    ordeal:    { title: 'Classification Cascade',  subtitle: 'Three tiers of agents classify the evidence.',           next: 'See the action →' },
    reward:    { title: 'Decide & Act',            subtitle: 'The system proposes what to do — safely.',               next: 'See what was learned →' },
    return:    { title: 'Learn & Adapt',           subtitle: 'Capturing what changed for next time.',                  next: '' },
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
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>A factory production line runs 24/7. Vibration sensors, thermal monitors, inspection cameras, and maintenance logs generate thousands of signals per hour. Right now, everything reads normal.</p>
                <p style={{ color: 'var(--text-dim)', lineHeight: 1.8, fontSize: 14, marginTop: 8 }}>But "normal" only has meaning when you've learned what it looks like. DeepField compiled a baseline from historical data — the statistical shape of healthy operations.</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 24 }}>
                  <MetricCard label="Vibration RMS" value="0.22" color="var(--rh-green)" detail="Within baseline" />
                  <MetricCard label="Temperature" value="38.2°C" color="var(--rh-green)" detail="Stable" />
                  <MetricCard label="Defect Rate" value="0.1%" color="var(--rh-green)" detail="Normal" />
                </div>
                <FlowDescription text="These signals are already streaming from your infrastructure. The question isn't whether you have data — it's whether you're classifying it fast enough to act before damage occurs." />
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
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>Evidence flows through three tiers. Run each tier to see what it does.</p>
                {evidence.length === 0 && <StepCard num={1} title="Ingest evidence first" status={ingestStatus} onRun={doIngest} buttonLabel="Ingest" />}
                {evidence.length > 0 && !baseline && <StepCard num={2} title="Build baseline first" status={baselineStatus} onRun={doBaseline} buttonLabel="Build baseline" />}

                {/* Nano tier */}
                <StepCard num={3} title="Nano Tier — Deterministic Rules" status={nanoStatus} onRun={baseline ? doNano : undefined} buttonLabel="Run nanoagents">
                  {nanoResult && (
                    <div>
                      <FlowDescription text="Nanoagents are deterministic — no LLM, pure CPU. They run threshold checks (z-score > 2.0?), pattern matching (ERROR in log?), and gating decisions. This is the compression layer." />
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
                        <MetricCard label="Records" value={nanoResult.records.length} color="var(--rh-blue)" />
                        <MetricCard label="Time" value={`${nanoResult.elapsed_ms}ms`} color="var(--rh-teal)" />
                        <MetricCard label="Runtime" value={nanoResult.runtime} color="var(--rh-green)" detail={nanoResult.decision_type} />
                      </div>
                      {nanoResult.records.slice(0, 8).map(r => (
                        <div key={r.classification_id} onClick={() => openDetail(`${r.agent_name}`, { tier: 'nano', taxonomy: r.taxonomy, class_name: r.class_name, severity: r.severity, confidence: r.confidence, rationale: r.rationale, decision_type: 'Deterministic (no LLM)', runtime: 'CPU' }, 'agent')}
                          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', background: 'var(--surface-2)', borderRadius: 6, marginBottom: 4, fontSize: 11, cursor: 'pointer', border: '1px solid transparent' }}>
                          <span style={{ fontFamily: 'Red Hat Mono, monospace', color: 'var(--rh-blue)', minWidth: 110 }}>{r.agent_name}</span>
                          <span style={{ color: 'var(--text-dim)' }}>{r.taxonomy}/{r.class_name}</span>
                          <span style={{ marginLeft: 'auto', color: r.severity === 'high' || r.severity === 'critical' ? 'var(--rh-orange)' : 'var(--text-disabled)' }}>{r.severity}</span>
                          <span style={{ color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>{(r.confidence * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                      <div style={{ fontSize: 10, color: 'var(--text-disabled)', marginTop: 4 }}>Click any row for full rationale</div>
                    </div>
                  )}
                </StepCard>

                {/* Micro tier */}
                {nanoStatus === 'done' && (
                  <StepCard num={4} title="Micro Tier — Rule-Backed Classifiers" status={microStatus} onRun={doMicro} buttonLabel="Run microagents">
                    {microResult && (
                      <div>
                        <FlowDescription text="Microagents run rule-backed classifiers on CPU. Image defect scores, audio anomaly scores, text pattern matching. Extension points for OpenVINO/ONNX. When LLM is configured, this tier uses live model inference." />
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
                          <MetricCard label="Records" value={microResult.records.length} color="var(--rh-green)" />
                          <MetricCard label="Escalated" value={microResult.escalated_from_nano} color="var(--rh-orange)" detail="from nano" />
                          <MetricCard label="Time" value={`${microResult.elapsed_ms}ms`} color="var(--rh-teal)" />
                          <MetricCard label="Runtime" value={microResult.runtime} color="var(--rh-green)" detail={microResult.decision_type} />
                        </div>
                        {microResult.records.map(r => (
                          <div key={r.classification_id} onClick={() => openDetail(`${r.agent_name}`, { tier: 'micro', taxonomy: r.taxonomy, class_name: r.class_name, severity: r.severity, confidence: r.confidence, rationale: r.rationale, decision_type: microResult.decision_type, runtime: microResult.runtime, ...(r.metrics || {}) }, 'agent')}
                            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', background: 'var(--surface-2)', borderRadius: 6, marginBottom: 4, fontSize: 11, cursor: 'pointer' }}>
                            <span style={{ fontFamily: 'Red Hat Mono, monospace', color: 'var(--rh-green)', minWidth: 110 }}>{r.agent_name}</span>
                            <span style={{ color: 'var(--text-dim)' }}>{r.taxonomy}/{r.class_name}</span>
                            <span style={{ marginLeft: 'auto', color: r.severity === 'high' || r.severity === 'critical' ? 'var(--rh-orange)' : 'var(--text-disabled)' }}>{r.severity}</span>
                            <span style={{ color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>{(r.confidence * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </StepCard>
                )}

                {/* Macro tier */}
                {microStatus === 'done' && (
                  <StepCard num={5} title="Macro Tier — Incident Reasoning" status={macroStatus} onRun={doMacro} buttonLabel="Run macroagents">
                    {macroResult && (
                      <div>
                        <FlowDescription text="Macroagents correlate across modalities. The timeline agent sequences evidence. The root cause agent identifies the most likely failure family. The action planner proposes safe responses. When LLM is configured, this tier uses model reasoning." />
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
                          <MetricCard label="Records" value={macroResult.records.length} color="var(--rh-purple)" />
                          <MetricCard label="Time" value={`${macroResult.elapsed_ms}ms`} color="var(--rh-teal)" />
                          <MetricCard label="Runtime" value={macroResult.runtime} color="var(--rh-purple)" detail={macroResult.decision_type} />
                        </div>
                        {macroResult.records.map(r => (
                          <div key={r.classification_id} onClick={() => openDetail(`${r.agent_name}`, { tier: 'macro', taxonomy: r.taxonomy, class_name: r.class_name, severity: r.severity, confidence: r.confidence, rationale: r.rationale, decision_type: macroResult.decision_type, runtime: macroResult.runtime }, 'agent')}
                            style={{ padding: '8px 10px', background: 'var(--surface-2)', borderRadius: 6, marginBottom: 4, cursor: 'pointer' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                              <span style={{ fontFamily: 'Red Hat Mono, monospace', color: 'var(--rh-purple)', minWidth: 130 }}>{r.agent_name}</span>
                              <span style={{ color: 'var(--text-dim)' }}>{r.taxonomy}/{r.class_name}</span>
                              <span style={{ marginLeft: 'auto', color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>{(r.confidence * 100).toFixed(0)}%</span>
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>{r.rationale.slice(0, 120)}...</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </StepCard>
                )}

                {/* Summary */}
                {macroStatus === 'done' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 12 }}>
                    <MetricCard label="Total" value={classifications.length} />
                    <MetricCard label="Nano" value={nanoResult?.records.length || 0} color="var(--rh-blue)" />
                    <MetricCard label="Micro" value={microResult?.records.length || 0} color="var(--rh-green)" />
                    <MetricCard label="Macro" value={macroResult?.records.length || 0} color="var(--rh-purple)" />
                  </div>
                )}
              </div>
            )}
            {currentAct === 'reward' && (() => {
              const highFindings = loopResult ? loopResult.classifications.filter(c => c.confidence >= 0.7 && (c.severity === 'high' || c.severity === 'critical')) : [];
              const tiers = loopResult ? { nano: loopResult.classifications.filter(c => c.agent_tier === 'nano').length, micro: loopResult.classifications.filter(c => c.agent_tier === 'micro').length, macro: loopResult.classifications.filter(c => c.agent_tier === 'macro').length } : null;
              return (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  The cascade found convergent signals across multiple modalities. Now the system
                  decides what to do — and proves it's safe before proposing anything.
                </p>
                {evidence.length === 0 && <StepCard num={1} title="Ingest evidence first" status={ingestStatus} onRun={doIngest} buttonLabel="Ingest" />}
                {evidence.length > 0 && !baseline && <StepCard num={2} title="Build baseline first" status={baselineStatus} onRun={doBaseline} buttonLabel="Build baseline" />}
                <StepCard num={6} title="Decide → Act → Verify → Learn" status={loopStatus} onRun={baseline ? doLoop : undefined} buttonLabel="Run agent loop">
                  {loopResult && (
                    <div>
                      {/* Decision chain — WHY this action */}
                      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: 'var(--rh-blue)' }}>Decision Chain</div>
                      <div style={{ padding: 14, background: 'var(--surface-2)', borderRadius: 8, marginBottom: 16, border: '1px solid var(--border)' }}>
                        <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '0 0 10px', lineHeight: 1.7 }}>
                          {highFindings.length} high-confidence findings across {tiers ? `${tiers.nano} nano + ${tiers.micro} micro + ${tiers.macro} macro` : ''} classifications:
                        </p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 12 }}>
                          {highFindings.slice(0, 6).map(c => (
                            <div key={c.classification_id} onClick={() => openDetail(c.agent_name, { tier: c.agent_tier, taxonomy: c.taxonomy, class_name: c.class_name, severity: c.severity, confidence: c.confidence, rationale: c.rationale, decision_type: c.agent_tier === 'nano' ? 'Deterministic' : c.agent_tier === 'micro' ? 'Rule-backed' : 'Template', runtime: 'CPU' }, 'agent')}
                              style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', background: 'var(--surface-1)', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}>
                              <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.severity === 'critical' ? 'var(--rh-red)' : 'var(--rh-orange)', flexShrink: 0 }} />
                              <span style={{ fontFamily: 'Red Hat Mono, monospace', color: 'var(--text-secondary)', minWidth: 110 }}>{c.agent_name}</span>
                              <span style={{ color: 'var(--text-dim)' }}>{c.class_name}</span>
                              <span style={{ color: 'var(--text-dim)', marginLeft: 'auto' }}>{c.rationale.slice(0, 60)}</span>
                            </div>
                          ))}
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--text-dim)', borderTop: '1px solid var(--border)', paddingTop: 10, lineHeight: 1.6 }}>
                          Multiple modalities converged on <strong style={{ color: 'var(--text-secondary)' }}>quality/bearing failure</strong>:
                          vibration drift, thermal increase, log errors, image defect, audio anomaly.
                          This cross-modal agreement triggers the action planner.
                        </div>
                      </div>

                      {/* Action — WHAT it proposes */}
                      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: 'var(--rh-orange)' }}>Proposed Action</div>
                      {loopResult.actions.map(a => (
                        <div key={a.action_id} onClick={() => openDetail(`Action: ${a.action_type}`, { action_type: a.action_type, status: a.status, requires_human_approval: a.requires_human_approval, created_by_agent: a.created_by_agent, ...a.payload }, 'action')}
                          style={{ padding: 14, background: 'var(--surface-2)', borderRadius: 8, marginBottom: 12, cursor: 'pointer', border: '1px solid var(--border)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                            <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--rh-orange)' }} />
                            <div style={{ flex: 1 }}>
                              <div style={{ fontSize: 16, fontWeight: 700 }}>{a.action_type.toUpperCase()}</div>
                            </div>
                            <span style={{ padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700, background: 'var(--rh-green-dim)', color: 'var(--rh-green)' }}>NON-DESTRUCTIVE</span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 8 }}>
                            {String(a.payload.rationale || a.payload.reason || 'Action proposed based on classification cascade')}
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                            <div style={{ padding: 8, background: 'var(--surface-1)', borderRadius: 6, textAlign: 'center' }}>
                              <div style={{ fontSize: 9, color: 'var(--text-disabled)' }}>STATUS</div>
                              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--rh-blue)' }}>{a.status}</div>
                            </div>
                            <div style={{ padding: 8, background: 'var(--surface-1)', borderRadius: 6, textAlign: 'center' }}>
                              <div style={{ fontSize: 9, color: 'var(--text-disabled)' }}>APPROVAL</div>
                              <div style={{ fontSize: 13, fontWeight: 700, color: a.requires_human_approval ? 'var(--rh-yellow)' : 'var(--rh-green)' }}>
                                {a.requires_human_approval ? 'Human required' : 'Auto'}
                              </div>
                            </div>
                            <div style={{ padding: 8, background: 'var(--surface-1)', borderRadius: 6, textAlign: 'center' }}>
                              <div style={{ fontSize: 9, color: 'var(--text-disabled)' }}>PROPOSED BY</div>
                              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)' }}>{a.created_by_agent}</div>
                            </div>
                          </div>
                        </div>
                      ))}

                      <FlowDescription text="The system will NOT restart services, scale infrastructure, or quarantine resources without explicit human approval. Only non-destructive actions (notify, observe, create ticket) are proposed automatically. This is a governance constraint, not a limitation." />

                      {/* Verification — HOW it checks */}
                      <div style={{ fontSize: 13, fontWeight: 700, marginTop: 8, marginBottom: 8, color: 'var(--rh-green)' }}>Verification Plan</div>
                      {loopResult.verifications.map(v => (
                        <div key={v.verification_id} onClick={() => openDetail(`Verification: ${v.verification_type}`, { verification_type: v.verification_type, status: v.status, confidence: v.confidence, expected_outcome: v.expected_outcome }, 'action')}
                          style={{ padding: 14, background: 'var(--surface-2)', borderRadius: 8, marginBottom: 8, cursor: 'pointer', border: '1px solid var(--border)' }}>
                          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{v.verification_type.replace(/_/g, ' ')}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 8, lineHeight: 1.6 }}>
                            After the action is taken, the system will check whether metrics return to baseline.
                            This verification runs automatically to confirm the action had the desired effect.
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
                            Expected: {Object.entries(v.expected_outcome).slice(0, 3).map(([k, val]) => `${k}: ${typeof val === 'number' ? (val as number).toFixed(1) : String(val)}`).join(' · ')}
                            {Object.keys(v.expected_outcome).length > 3 && ` · +${Object.keys(v.expected_outcome).length - 3} more`}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </StepCard>
              </div>
              );
            })()}
            {currentAct === 'return' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>The system captures what it learned — not as silent changes, but as <strong>proposals</strong> that require human review before activation.</p>
                <FlowDescription text="Learning proposals never apply silently. Each captures a concrete before/after delta (e.g., lower the vibration z-score warning from 2.0σ to 1.8σ). The operator decides whether to accept, reject, or modify." />

                {loopResult?.learning_proposals.map(p => (
                  <div key={p.proposal_id}
                    onClick={() => openDetail(`Proposal: ${p.proposal_type}`, {
                      proposal_type: p.proposal_type, status: p.status, confidence: p.confidence,
                      rationale: p.rationale, before: p.before, after: p.after,
                    }, 'learning')}
                    style={{ padding: 14, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, marginBottom: 8, cursor: 'pointer' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, background: 'var(--rh-purple-dim)', color: 'var(--rh-purple)' }}>{p.proposal_type}</span>
                      <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'Red Hat Mono, monospace' }}>{(p.confidence * 100).toFixed(0)}% confidence</span>
                      <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-disabled)' }}>Click for before/after</span>
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>{p.rationale}</p>
                    {p.before && Object.keys(p.before).length > 0 && (
                      <div style={{ marginTop: 8, display: 'flex', gap: 12, fontSize: 11 }}>
                        <div style={{ flex: 1, padding: 8, background: 'var(--surface-2)', borderRadius: 6 }}>
                          <div style={{ fontSize: 9, color: 'var(--text-disabled)', marginBottom: 4 }}>BEFORE</div>
                          {Object.entries(p.before).slice(0, 3).map(([k, v]) => (
                            <div key={k} style={{ color: 'var(--text-dim)', fontFamily: 'Red Hat Mono, monospace' }}>
                              {k}: {typeof v === 'object' ? '...' : String(v)}
                            </div>
                          ))}
                        </div>
                        <div style={{ flex: 1, padding: 8, background: 'var(--rh-orange-dim)', borderRadius: 6 }}>
                          <div style={{ fontSize: 9, color: 'var(--rh-orange)', marginBottom: 4 }}>AFTER (proposed)</div>
                          {Object.entries(p.after).slice(0, 3).map(([k, v]) => (
                            <div key={k} style={{ color: 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace' }}>
                              {k}: {typeof v === 'object' ? '...' : String(v)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {/* Journey summary */}
                {loopResult && (
                  <div style={{ marginTop: 24 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Pipeline Summary</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
                      <MetricCard label="Evidence" value={evidence.length} color="var(--rh-blue)" />
                      <MetricCard label="Classifications" value={classifications.length} color="var(--rh-teal)" />
                      <MetricCard label="Actions" value={loopResult.actions.length} color="var(--rh-orange)" detail="non-destructive" />
                      <MetricCard label="Verifications" value={loopResult.verifications.length} color="var(--rh-green)" detail="pending" />
                      <MetricCard label="Learning" value={loopResult.learning_proposals.length} color="var(--rh-purple)" detail="awaiting review" />
                    </div>
                  </div>
                )}

                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
                  style={{ marginTop: 24, padding: 20, background: 'var(--surface-1)', border: '1px solid var(--rh-red)40', borderRadius: 10, textAlign: 'center' }}>
                  <p style={{ fontSize: 15, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.8 }}>
                    The system studied signals, classified reality, proposed safe action,
                    and captured what should change. The cycle continues.
                  </p>
                </motion.div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 32px', borderTop: '1px solid var(--border)', background: 'var(--surface-1)' }}>
        <button onClick={() => { if (actIndex > 0) setActIndex(actIndex - 1); else { setMode('slides'); setSlide(SLIDES.length - 1); } }}
          style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-dim)', padding: '6px 16px', borderRadius: 6, fontSize: 13 }}>
          ← Back
        </button>
        <span style={{ fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>{actIndex + 1} / {manualActs.length}</span>
        {meta.next ? (
          <button onClick={() => setActIndex(Math.min(manualActs.length - 1, actIndex + 1))}
            style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '6px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600 }}>
            {meta.next}
          </button>
        ) : (
          <button onClick={() => { setMode('auto'); startAuto(); }}
            style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '6px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600 }}>
            Run at Scale →
          </button>
        )}
      </div>
    </div>
  );
}
