import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Header } from './components/Header';
import { StepCard } from './components/StepCard';
import { MetricCard } from './components/MetricCard';
import { StepProgress } from './components/StepProgress';
import { DetailModal, KeyValueTable, ComparisonTable } from './components/DetailModal';
import { FlowDescription } from './components/FlowDescription';
import { InfraPanel } from './components/InfraPanel';
import { FleetPipelineFlow } from './components/FleetPipelineFlow';
import { CostComparison } from './components/CostComparison';
import { SLOGauge } from './components/SLOGauge';
import { IntentFlow } from './components/IntentFlow';
import { FleetArchitectureFlow } from './components/FleetArchitectureFlow';
import { ReplicaTimeline } from './components/ReplicaTimeline';
import { LedgerChainView } from './components/LedgerChainView';
import { TestMatrixCompact } from './components/TestMatrixCompact';
import { api } from './api/client';
import type { ApiCall } from './api/client';
import { useDemoStore } from './stores/useDemoStore';
import { useDataStore } from './stores/useDataStore';
import type { DemoState } from './stores/useDataStore';

/*
 * fleet-llm-d — Fleet-Level Inference Orchestration
 *
 * Hero's Journey through the platform:
 * - Slides: 7 slides introducing the problem and solution
 * - Manual: 8 acts walking through fleet operations step by step
 * - Auto: SSE-driven walkthrough via backend _run_demo()
 */

const STEP_TO_ACT: Record<string, number> = {
  cost: 0, event_profile: 1, fleet_deploy: 2, platform: 3,
  forecast: 4, blast_radius: 4, intent: 5, proof: 6, ledger: 6,
  fleet_return: 7,
  ordinary: 0, call: 1, threshold: 2,
  ordeal_nano: 3, ordeal_micro: 4, ordeal_macro: 5,
  reward: 6, return: 7,
  scale_10: 8, scale_50: 9, stress: 10, recovery: 11, claim: 12,
};

const ACT_LABELS = [
  'Cost', 'Event', 'Deploy', 'CRDs', 'Predict', 'Intent',
  'Proof', 'Return', '10x', '50x', 'Stress', 'Recovery', 'Claim',
];

export default function App() {
  const { mode, setMode, slide, setSlide, actIndex, setActIndex,
    costStatus, eventProfileStatus, fleetNanoStatus, forecastStatus,
    blastRadiusStatus, intentStatus, ledgerStatus,
    setStepStatus, detail, openDetail, closeDetail } = useDemoStore();

  const { demoState, setDemoState, classifications,
    fleetHealth, setFleetHealth, sloForecast, setSLOForecast,
    blastRadius, setBlastRadius, intentResponse, setIntentResponse,
    setCostComparison, ledgerChains, setLedgerChains,
    addApiCall } = useDataStore();

  const eventSourceRef = useRef<EventSource | null>(null);
  const [eventProfiles, setEventProfiles] = useState<
    Array<{ name: string; expected_users: number; pre_warm_minutes: number; models: string[] }>
  >([]);

  const detailOpen = detail.open;
  const detailTitle = detail.title;
  const detailContent = detail.content;
  const detailType = detail.type;

  /* eslint-disable @typescript-eslint/no-unused-vars */

  /* SSE connection for auto mode */
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
  }, [mode, setDemoState, setActIndex]);

  /* Auto mode controls */
  const startAuto = useCallback(async () => {
    await fetch('/api/v1/demo/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    setMode('auto');
  }, [setMode]);
  const pauseAuto = useCallback(async () => { await fetch('/api/v1/demo/pause', { method: 'POST' }); }, []);
  const resumeAuto = useCallback(async () => { await fetch('/api/v1/demo/resume', { method: 'POST' }); }, []);
  const stopAuto = useCallback(async () => {
    await fetch('/api/v1/demo/stop', { method: 'POST' });
    setDemoState({ status: 'stopped' });
  }, [setDemoState]);

  /* Manual fleet callbacks */
  const doCost = useCallback(async () => {
    setStepStatus('cost', 'running');
    const call = await api.fleetCost();
    addApiCall(call as ApiCall<unknown>);
    setCostComparison(call.response.data);
    setStepStatus('cost', 'done');
  }, [setStepStatus, addApiCall, setCostComparison]);

  const doEventProfile = useCallback(async () => {
    setStepStatus('eventProfile', 'running');
    const call = await api.fleetEventProfiles();
    addApiCall(call as ApiCall<unknown>);
    setEventProfiles(call.response.data.profiles);
    setStepStatus('eventProfile', 'done');
  }, [setStepStatus, addApiCall]);

  const doFleetHealth = useCallback(async () => {
    setStepStatus('fleetNano', 'running');
    const call = await api.fleetHealth();
    addApiCall(call as ApiCall<unknown>);
    setFleetHealth(call.response.data);
    setStepStatus('fleetNano', 'done');
  }, [setStepStatus, addApiCall, setFleetHealth]);

  const doForecast = useCallback(async () => {
    setStepStatus('forecast', 'running');
    const call = await api.fleetForecast();
    addApiCall(call as ApiCall<unknown>);
    setSLOForecast(call.response.data);
    setStepStatus('forecast', 'done');
  }, [setStepStatus, addApiCall, setSLOForecast]);

  const doBlastRadius = useCallback(async () => {
    setStepStatus('blastRadius', 'running');
    const call = await api.fleetBlastRadius();
    addApiCall(call as ApiCall<unknown>);
    setBlastRadius(call.response.data);
    setStepStatus('blastRadius', 'done');
  }, [setStepStatus, addApiCall, setBlastRadius]);

  const doIntent = useCallback(async () => {
    setStepStatus('intent', 'running');
    const call = await api.fleetEmitIntent({
      intent_type: 'pre_warm',
      model: 'granite-3.3-8b-instruct',
      target_replicas: 4,
      confidence: 0.87,
      justification: 'SLO breach predicted in 22 minutes based on P95 latency trend at +80ms/min.',
    });
    addApiCall(call as ApiCall<unknown>);
    setIntentResponse(call.response.data);
    setStepStatus('intent', 'done');
  }, [setStepStatus, addApiCall, setIntentResponse]);

  const doLedger = useCallback(async () => {
    setStepStatus('ledger', 'running');
    const call = await api.fleetVerifyChain();
    addApiCall(call as ApiCall<unknown>);
    setLedgerChains(call.response.data);
    setStepStatus('ledger', 'done');
  }, [setStepStatus, addApiCall, setLedgerChains]);

  /* ───────────────────────── SLIDES ───────────────────────── */

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
          fleet-llm-d
        </motion.h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ fontSize: 20, color: 'var(--text-dim)', marginTop: 24 }}>
          Fleet-Level Inference Orchestration
        </motion.p>
      </div>
    ),
    // 1: The Problem
    () => (
      <div style={{ textAlign: 'center', maxWidth: 700 }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 32, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.4 }}>
          GPU inference: <span style={{ color: 'var(--rh-red)' }}>$32/hr.</span>
          <br />Scarce. Single-cluster. Static scaling.
          <br />No governance. No audit trail.
        </motion.p>
      </div>
    ),
    // 2: The Platform
    () => (
      <div style={{ textAlign: 'center', maxWidth: 700 }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.4 }}>
          7 CRDs. 31 endpoints. Multi-cluster.
          <br />Multi-tenant. SLO-gated rollouts.
          <br />Cost optimization. ARE Ledger compliance.
        </motion.p>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 32 }}>
          {[
            { num: '7', label: 'CRDs', sub: 'Kubernetes-native' },
            { num: '31', label: 'REST Endpoints', sub: 'Full fleet API' },
            { num: '5', label: 'CPU Models', sub: 'Granite family' },
          ].map(s => (
            <div key={s.label} style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, textAlign: 'center' }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--rh-red)', fontFamily: 'Red Hat Display, sans-serif' }}>{s.num}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{s.label}</div>
              <div style={{ fontSize: 11, color: 'var(--text-disabled)', marginTop: 2 }}>{s.sub}</div>
            </div>
          ))}
        </motion.div>
      </div>
    ),
    // 3: CPU + Intel — the 53x number
    () => (
      <div style={{ textAlign: 'center' }}>
        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15 }}>
          <div style={{ fontSize: 120, fontWeight: 800, color: 'var(--rh-red)', fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1 }}>
            53x
          </div>
        </motion.div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          style={{ fontSize: 22, color: 'var(--text-dim)', marginTop: 16, lineHeight: 1.5 }}>
          cheaper than GPU inference.
          <br />Intel Xeon 6 Granite Rapids. 256 cores. AMX.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ fontSize: 16, color: 'var(--text-disabled)', marginTop: 24 }}>
          OVMS C++ with INT8 quantization. $0.60/hr vs $32/hr H100.
        </motion.p>
      </div>
    ),
    // 4: The Brain — deepfield-fleet
    () => (
      <div style={{ maxWidth: 700 }}>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          style={{ fontSize: 14, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 2, textAlign: 'center', marginBottom: 24 }}>
          THE PREDICTIVE LAYER
        </motion.p>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.4, textAlign: 'center', marginBottom: 24 }}>
          deepfield-fleet: predictive intelligence.
        </motion.p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[
            { label: 'SLO Forecasting', desc: 'Linear regression on P95 latency. Predicts breach 22 min ahead.', color: 'var(--rh-blue)', delay: 0.3 },
            { label: 'Event Pre-Warming', desc: 'Learns event profiles. Scales before the surge, not after.', color: 'var(--rh-green)', delay: 0.4 },
            { label: 'Intent-Driven Scaling', desc: 'Emits PreWarmIntent with confidence + justification. Policy-gated.', color: 'var(--rh-orange)', delay: 0.5 },
            { label: 'A/B Provable', desc: 'Ledger records every prediction vs outcome. Proof, not opinion.', color: 'var(--rh-purple)', delay: 0.6 },
          ].map(t => (
            <motion.div key={t.label} initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: t.delay }}
              style={{ padding: 14, background: 'var(--surface-1)', border: `1px solid ${t.color}40`, borderLeft: `4px solid ${t.color}`, borderRadius: '0 10px 10px 0' }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: t.color }}>{t.label}</div>
              <div style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>{t.desc}</div>
            </motion.div>
          ))}
        </div>
      </div>
    ),
    // 5: The Proof
    () => (
      <div style={{ textAlign: 'center', maxWidth: 700 }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, marginBottom: 32 }}>
          Measured. Tested. Auditable.
        </motion.p>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          {[
            { num: '360', label: 'Tests Passing', color: 'var(--rh-green)' },
            { num: '12', label: 'Test Suites', color: 'var(--rh-blue)' },
            { num: '5', label: 'CPU Models', color: 'var(--rh-teal)' },
            { num: '< 5s', label: 'P95 Latency', color: 'var(--rh-orange)' },
            { num: '1 → 4', label: 'HPA Scale', color: 'var(--rh-purple)' },
            { num: '0', label: 'Downtime', color: 'var(--rh-red)' },
          ].map(s => (
            <div key={s.label} style={{ padding: 16, background: 'var(--surface-1)', border: `1px solid ${s.color}30`, borderRadius: 10, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: s.color, fontFamily: 'Red Hat Display, sans-serif' }}>{s.num}</div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </motion.div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
          style={{ fontSize: 14, color: 'var(--text-disabled)', marginTop: 24 }}>
          Every decision recorded in the ARE Immutable Ledger.
        </motion.p>
      </div>
    ),
    // 6: CTA
    () => (
      <div style={{ textAlign: 'center' }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 36, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, marginBottom: 16 }}>
          Let me show you the fleet.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          style={{ fontSize: 16, color: 'var(--text-dim)', marginBottom: 40, lineHeight: 1.6 }}>
          Walk through each layer of the orchestration platform.
          <br />Then run it at scale.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          <button onClick={() => setMode('manual')}
            style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '16px 48px', borderRadius: 10, fontSize: 18, fontWeight: 700, cursor: 'pointer' }}>
            Next
          </button>
        </motion.div>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ marginTop: 32, fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
          Go control plane · Rust data plane · Intel Xeon 6 · $0.60/hr
        </motion.div>
      </div>
    ),
  ];

  /* ───────────────────────── SLIDES MODE ───────────────────────── */

  if (mode === 'slides') {
    const isLastSlide = slide === SLIDES.length - 1;
    return (
      <div
        onClick={() => { if (!isLastSlide) setSlide(s => s + 1); }}
        style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-dark)', cursor: isLastSlide ? 'default' : 'pointer' }}
      >
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
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 48px' }}>
          <AnimatePresence mode="wait">
            <motion.div key={slide} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.4, ease: 'easeOut' }}>
              {SLIDES[slide]()}
            </motion.div>
          </AnimatePresence>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 32px' }}>
          <button onClick={(e) => { e.stopPropagation(); if (slide > 0) setSlide(s => s - 1); }}
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

  /* ───────────────────────── AUTO MODE ───────────────────────── */

  if (mode === 'auto') {
    const isRunning = demoState.status === 'running' || demoState.status === 'starting';
    const isPaused = demoState.status === 'paused';
    const isComplete = demoState.status === 'completed';

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
          <InfraPanel />

          {(isRunning || isPaused) && demoState.step_title && (
            <StepProgress progress={demoState.step_progress || 0} title={demoState.step_title} subtitle={demoState.step_subtitle || ''} />
          )}

          <AnimatePresence mode="wait">
            {demoState.narrative && (
              <motion.div key={demoState.narrative.slice(0, 30)}
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, marginBottom: 12, fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7, fontStyle: 'italic' }}>
                {demoState.narrative}
              </motion.div>
            )}
          </AnimatePresence>

          {demoState.flow_description && <FlowDescription text={demoState.flow_description} alwaysOpen />}

          {isRunning && demoState.live_agent && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, padding: '8px 12px', background: 'var(--surface-2)', borderRadius: 8, border: '1px solid var(--border)' }}>
              <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1 }}
                style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--rh-green)' }} />
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

          {demoState.inference_stats && demoState.inference_stats.total_calls > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12, padding: '8px 14px', background: 'var(--surface-2)', borderRadius: 8, border: '1px solid var(--border)', fontSize: 11 }}>
              <span style={{ color: 'var(--rh-green)', fontWeight: 700 }}>INFERENCE</span>
              <span style={{ color: 'var(--text-dim)' }}>Calls: <strong style={{ color: 'var(--text-secondary)' }}>{demoState.inference_stats.total_calls}</strong></span>
              <span style={{ color: 'var(--text-dim)' }}>Tokens: <strong style={{ color: 'var(--text-secondary)' }}>{demoState.inference_stats.total_tokens_out}</strong></span>
              <span style={{ color: 'var(--text-dim)' }}>Latency: <strong style={{ color: 'var(--rh-orange)' }}>{demoState.inference_stats.avg_latency_ms}ms</strong></span>
              <span style={{ color: 'var(--text-dim)' }}>Tok/s: <strong style={{ color: 'var(--rh-blue)' }}>{demoState.inference_stats.avg_tokens_per_sec}</strong></span>
              {demoState.inference_stats.errors > 0 && <span style={{ color: 'var(--rh-red)' }}>Errors: {demoState.inference_stats.errors}</span>}
            </motion.div>
          )}

          {demoState.inference_mode && (
            <div style={{ fontSize: 10, color: 'var(--text-disabled)', marginBottom: 8, fontFamily: 'Red Hat Mono, monospace', textAlign: 'center' }}>
              Inference mode: {demoState.inference_mode === 'llm' ? 'Live LLM via LiteLLM' : 'Simulated (rule-backed) — set LITELLM_API_BASE for live inference'}
            </div>
          )}

          {demoState.scale_metrics && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
              <MetricCard label="Clusters" value={String((demoState.scale_metrics as Record<string, unknown>).clusters || '—')} color="var(--rh-blue)" />
              <MetricCard label="Models" value={String((demoState.scale_metrics as Record<string, unknown>).models || '—')} color="var(--rh-teal)" />
              <MetricCard label="Replicas" value={String((demoState.scale_metrics as Record<string, unknown>).replicas || '—')} color="var(--rh-green)" />
              <MetricCard label="Latency" value={`${(demoState.scale_metrics as Record<string, unknown>).elapsed_ms || '—'}ms`} color="var(--rh-orange)" />
            </div>
          )}

          {demoState.cumulative && ((demoState.step_id || '').startsWith('scale') || (demoState.step_id || '') === 'stress' || (demoState.step_id || '') === 'recovery') ? (
            <div style={{ fontSize: 11, color: 'var(--text-disabled)', marginBottom: 12, fontFamily: 'Red Hat Mono, monospace', display: 'flex', gap: 16, justifyContent: 'center' }}>
              <span>Total replicas: {String((demoState.cumulative as Record<string, unknown>).total_replicas || 0)}</span>
              <span>Total requests: {String((demoState.cumulative as Record<string, unknown>).total_requests || 0)}</span>
              <span>Clusters active: {String((demoState.cumulative as Record<string, unknown>).clusters_active || 0)}</span>
            </div>
          ) : null}

          {/* Fleet Pipeline Flow — live animated prediction→action→outcome→learn */}
          <FleetPipelineFlow
            stepId={demoState.step_id}
            sloGauge={demoState.slo_gauge}
            blastRadius={demoState.blast_radius}
            intentFlow={demoState.intent_flow}
            ledgerChains={demoState.ledger_chains}
            replicaEvents={demoState.replica_events}
            funnel={demoState.funnel}
            agentEvents={demoState.agent_events}
            costData={demoState.cost_data}
          />

          {/* Contextual detail panels — fade in at relevant steps */}
          <AnimatePresence>
            {demoState.cost_data && (
              <motion.div key="cost" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <CostComparison animate />
              </motion.div>
            )}
          </AnimatePresence>
          <AnimatePresence>
            {demoState.slo_gauge && (
              <motion.div key="slo" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <SLOGauge
                  currentMs={(demoState.slo_gauge as Record<string, number>).current_p95 || 800}
                  forecastMs={(demoState.slo_gauge as Record<string, number>).forecast_p95 || 800}
                  targetMs={(demoState.slo_gauge as Record<string, number>).slo_target || 5000}
                  breachInMinutes={(demoState.slo_gauge as Record<string, number>).minutes_to_breach}
                />
              </motion.div>
            )}
          </AnimatePresence>
          <AnimatePresence>
            {demoState.replica_events && demoState.replica_events.length > 0 && (
              <motion.div key="replicas" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <ReplicaTimeline events={demoState.replica_events} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* The Claim — fleet metrics + use cases */}
          {isComplete && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginBottom: 24 }}>
                <img src="/logos/redhat.svg" alt="Red Hat" style={{ height: 24 }} />
                <span style={{ color: 'var(--text-disabled)', fontSize: 24, fontWeight: 300 }}>&times;</span>
                <img src="/logos/intel.png" alt="Intel" style={{ height: 24 }} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
                {[
                  { value: '53x', label: 'Cost Savings', color: 'var(--rh-red)' },
                  { value: '360', label: 'Tests Passing', color: 'var(--rh-green)' },
                  { value: '5', label: 'CPU Models', color: 'var(--rh-blue)' },
                  { value: '< 5s', label: 'P95 SLO', color: 'var(--rh-orange)' },
                ].map(s => (
                  <div key={s.label} style={{ padding: 20, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, textAlign: 'center' }}>
                    <div style={{ fontSize: 36, fontWeight: 800, color: s.color, fontFamily: 'Red Hat Display, sans-serif' }}>{s.value}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>{s.label}</div>
                  </div>
                ))}
              </div>

              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
                style={{ padding: 24, background: 'var(--surface-1)', border: '1px solid var(--rh-red)40', borderRadius: 10, textAlign: 'center', marginBottom: 24 }}>
                <p style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', margin: 0, fontFamily: 'Red Hat Display, sans-serif' }}>
                  Fleet-level inference orchestration. Proven.
                </p>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 12, lineHeight: 1.8 }}>
                  Multi-cluster. Multi-tenant. SLO-gated. Cost-optimized.
                  CPU inference at $0.60/hr vs $32/hr GPU.
                  Every decision recorded in the ARE Immutable Ledger.
                </p>
              </motion.div>

              {demoState.flow_description && <FlowDescription text={demoState.flow_description} alwaysOpen />}

              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
                style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 24 }}>
                <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--rh-green)30', borderRadius: 10 }}>
                  <div style={{ fontSize: 10, color: 'var(--rh-green)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>ECONOMICS</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--rh-green)', fontFamily: 'Red Hat Display, sans-serif' }}>53x</div>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>
                    $0.60/hr Intel Xeon 6 vs $32/hr H100 GPU. OVMS C++ with INT8. Same Granite models, 53x cheaper.
                  </div>
                </div>
                <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--rh-blue)30', borderRadius: 10 }}>
                  <div style={{ fontSize: 10, color: 'var(--rh-blue)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>COMPLIANCE</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--rh-blue)', fontFamily: 'Red Hat Display, sans-serif' }}>ARE</div>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>
                    ARE Immutable Ledger. 5 chains verified. Every placement, scaling, and routing decision cryptographically recorded.
                  </div>
                </div>
                <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--rh-purple)30', borderRadius: 10 }}>
                  <div style={{ fontSize: 10, color: 'var(--rh-purple)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>INTELLIGENCE</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--rh-purple)', fontFamily: 'Red Hat Display, sans-serif' }}>Predict</div>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>
                    deepfield-fleet predicts, not reacts. SLO forecasting, event pre-warming, intent-driven scaling. A/B provable in the ledger.
                  </div>
                </div>
              </motion.div>

              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
                <div style={{ fontSize: 14, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 2, textAlign: 'center', marginBottom: 16 }}>
                  BEYOND GPU INFERENCE
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  {[
                    { title: 'Edge Inference', color: 'var(--rh-blue)',
                      desc: 'CPU inference at the edge. No GPU required. Low-latency serving on standard infrastructure. Granite models on Intel hardware at every location.' },
                    { title: 'Sovereign Cloud', color: 'var(--rh-green)',
                      desc: 'Data-sovereign inference within geographic boundaries. No model or data egress. ARE Ledger provides compliance proof for regulators.' },
                    { title: 'Multi-Tenant SaaS', color: 'var(--rh-purple)',
                      desc: 'Per-tenant quotas, priorities, and chargeback. TenantProfile CRD enforces isolation. Fair scheduling across shared GPU/CPU pools.' },
                    { title: 'Event-Driven Pre-Warming', color: 'var(--rh-orange)',
                      desc: 'Learn event profiles from history. Pre-warm replicas before conferences, launches, and campaigns. Zero downtime during demand surges.' },
                  ].map(uc => (
                    <motion.div key={uc.title} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                      style={{ padding: 16, background: 'var(--surface-1)', border: `1px solid ${uc.color}30`, borderRadius: 10 }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: uc.color, marginBottom: 8 }}>{uc.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-dim)', lineHeight: 1.6 }}>{uc.desc}</div>
                    </motion.div>
                  ))}
                </div>

                <div style={{ marginTop: 24, padding: 16, background: 'var(--surface-1)', borderRadius: 10, border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, textAlign: 'center', marginBottom: 12 }}>
                    INTEGRATION READY
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8 }}>
                    {['OpenShift', 'llm-d', 'OVMS', 'Prometheus', 'Grafana', 'Intel AMX', 'ARE Ledger', 'Helm'].map(name => (
                      <span key={name} style={{
                        padding: '4px 10px', borderRadius: 6, fontSize: 10,
                        background: 'var(--surface-2)', border: '1px solid var(--border)',
                        color: 'var(--text-dim)', fontFamily: 'Red Hat Mono, monospace',
                      }}>{name}</span>
                    ))}
                  </div>
                </div>

                <div style={{ textAlign: 'center', marginTop: 16, padding: 16, background: 'var(--surface-1)', borderRadius: 10, border: '1px solid var(--rh-red)40' }}>
                  <p style={{ fontSize: 15, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.7 }}>
                    Go control plane. Rust data plane. Intel Xeon 6.
                    <br />Fleet-level inference orchestration for the enterprise.
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-disabled)', marginTop: 12, fontFamily: 'Red Hat Mono, monospace' }}>
                    $0.60/hr CPU · 53x cheaper · 360 tests · ARE Ledger compliance
                  </p>
                  <a href="https://github.com/jkershawrh/fleet-llm-d" target="_blank" rel="noopener noreferrer"
                    style={{ display: 'inline-block', marginTop: 16, background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '10px 28px', borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: 'pointer', textDecoration: 'none' }}>
                    View on GitHub →
                  </a>
                </div>
              </motion.div>
            </motion.div>
          )}
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

        <DetailModal open={detailOpen} title={detailTitle} onClose={closeDetail}>
          {detailContent && detailType === 'agent' && (
            <div>
              <div style={{ fontSize: 12, color: 'var(--rh-teal)', marginBottom: 12, fontWeight: 700 }}>
                {String(detailContent.decision_type)} · {String(detailContent.runtime)}
              </div>
              <KeyValueTable data={{
                Tier: detailContent.tier, Taxonomy: detailContent.taxonomy,
                Classification: detailContent.class_name, Severity: detailContent.severity,
                Confidence: `${Number(detailContent.confidence) * 100}%`,
              }} label="Classification" />
              <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 6, marginBottom: 12, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
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
          {detailContent && detailType === 'intent' && (
            <KeyValueTable data={detailContent} label="Intent Details" />
          )}
          {detailContent && detailType === 'ledger' && (
            <KeyValueTable data={detailContent} label="Ledger Entry" />
          )}
          {detailContent && detailType === 'action' && (
            <KeyValueTable data={detailContent} label="Details" />
          )}
          {detailContent && !['agent', 'learning', 'action', 'intent', 'ledger'].includes(detailType) && (
            <KeyValueTable data={detailContent} />
          )}
        </DetailModal>
      </div>
    );
  }

  /* ───────────────────────── MANUAL MODE ───────────────────────── */

  const manualActs = ['cost', 'event', 'deploy', 'platform', 'predict', 'intent', 'proof', 'return'] as const;
  const manualMeta: Record<string, { title: string; subtitle: string; next: string }> = {
    cost:     { title: 'The Cost of Inference',  subtitle: 'Enterprise inference runs on GPU. There is another way.',          next: 'See the event →' },
    event:    { title: 'The Event Arrives',      subtitle: 'A surge is coming. The fleet prepares.',                           next: 'Deploy the fleet →' },
    deploy:   { title: 'The Fleet Deploys',      subtitle: 'OVMS C++ on Intel Xeon 6. Multi-cluster orchestration.',           next: 'See the CRDs →' },
    platform: { title: 'The Platform',           subtitle: 'Seven CRDs define the fleet\'s desired state.',                    next: 'Predict the SLO →' },
    predict:  { title: 'The Brain Predicts',     subtitle: 'SLO forecasting and blast radius scoping.',                        next: 'Emit the intent →' },
    intent:   { title: 'The Intent',             subtitle: 'Predictive intelligence drives pre-emptive action.',               next: 'See the proof →' },
    proof:    { title: 'The Proof',              subtitle: '360 tests. 12 suites. Every decision in the ledger.',              next: 'See the return →' },
    return:   { title: 'The Return',             subtitle: 'Auditable. Verifiable. Continuous.',                               next: '' },
  };
  const currentAct = manualActs[actIndex] || manualActs[0];
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

            {/* Act 0: The Cost of Inference */}
            {currentAct === 'cost' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  Enterprise inference runs on GPU. $32 per hour per H100. Scarce hardware.
                  Static scaling. No multi-tenant governance. No audit trail.
                </p>
                <CostComparison />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 16 }}>
                  <MetricCard label="GPU Cost" value="$32/hr" color="var(--rh-red)" detail="H100 instance" />
                  <MetricCard label="CPU Cost" value="$0.60/hr" color="var(--rh-green)" detail="Xeon 6 instance" />
                  <MetricCard label="Savings" value="53x" color="var(--rh-blue)" detail="Same models" />
                </div>
              </div>
            )}

            {/* Act 1: The Event Arrives */}
            {currentAct === 'event' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  Red Hat Summit Connect starts in 30 minutes. 200 concurrent users will need
                  inference across 5 Granite models. The fleet needs to prepare.
                </p>
                <StepCard num={1} title="Load Event Profile" status={eventProfileStatus} onRun={doEventProfile} buttonLabel="Load profile">
                  {eventProfiles.length > 0 && (() => {
                    const p = eventProfiles[0];
                    return (
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: 'var(--rh-blue)' }}>{p.name}</div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 8 }}>
                          <MetricCard label="Expected Users" value={p.expected_users} color="var(--rh-blue)" />
                          <MetricCard label="Pre-Warm" value={`${p.pre_warm_minutes} min`} color="var(--rh-orange)" />
                          <MetricCard label="Models" value={p.models.length} color="var(--rh-teal)" />
                          <MetricCard label="Burst RPS" value="6.7" color="var(--rh-red)" />
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {p.models.map(m => (
                            <span key={m} style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: 'var(--rh-teal)20', border: '1px solid var(--rh-teal)40', color: 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace' }}>{m}</span>
                          ))}
                        </div>
                      </div>
                    );
                  })()}
                </StepCard>
              </div>
            )}

            {/* Act 2: The Fleet Deploys */}
            {currentAct === 'deploy' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  fleet-llm-d manages clusters, models, tenants, and routing. OVMS C++ serves
                  Granite on Intel Xeon 6 with INT8 quantization via AMX.
                </p>
                <StepCard num={2} title="Check Fleet Health" status={fleetNanoStatus} onRun={doFleetHealth} buttonLabel="Check health">
                  {fleetHealth && (
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-disabled)', marginBottom: 8 }}>
                        Mode: <strong style={{ color: fleetHealth.mode === 'live' ? 'var(--rh-green)' : 'var(--text-dim)' }}>{fleetHealth.mode}</strong>
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6, color: 'var(--rh-blue)' }}>Clusters</div>
                      {fleetHealth.clusters.map(c => (
                        <div key={c.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', background: 'var(--surface-2)', borderRadius: 6, marginBottom: 4, fontSize: 12 }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.status === 'healthy' ? 'var(--rh-green)' : 'var(--rh-orange)', flexShrink: 0 }} />
                          <span style={{ fontFamily: 'Red Hat Mono, monospace', color: 'var(--text-secondary)' }}>{c.name}</span>
                          <span style={{ color: 'var(--text-dim)', marginLeft: 'auto' }}>{c.region}</span>
                        </div>
                      ))}
                      <div style={{ fontSize: 13, fontWeight: 700, marginTop: 10, marginBottom: 6, color: 'var(--rh-teal)' }}>Models</div>
                      {fleetHealth.models.map(m => (
                        <div key={m.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', background: 'var(--surface-2)', borderRadius: 6, marginBottom: 4, fontSize: 12 }}>
                          <span style={{ fontFamily: 'Red Hat Mono, monospace', color: 'var(--text-secondary)' }}>{m.name}</span>
                          <span style={{ color: 'var(--text-dim)', marginLeft: 'auto' }}>{m.runtime} · {m.replicas} replicas</span>
                        </div>
                      ))}
                    </div>
                  )}
                </StepCard>
                <div style={{ marginTop: 16 }}>
                  <FleetArchitectureFlow />
                </div>
              </div>
            )}

            {/* Act 3: The Platform — 7 CRDs */}
            {currentAct === 'platform' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  Seven CRDs define the fleet's desired state. The Go control plane watches for
                  changes and reconciles actual state continuously.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
                  {[
                    { name: 'FleetInferencePool', desc: 'Cluster inventory, model placement, GPU/CPU allocation', color: 'var(--rh-blue)' },
                    { name: 'PlacementPolicy', desc: 'Affinity, anti-affinity, topology constraints', color: 'var(--rh-green)' },
                    { name: 'FleetRoutingPolicy', desc: 'Cross-cluster traffic, load balancing, failover', color: 'var(--rh-teal)' },
                    { name: 'FleetScalingPolicy', desc: 'HPA triggers, SLO gates, min/max replicas', color: 'var(--rh-orange)' },
                    { name: 'TenantProfile', desc: 'Per-tenant quotas, priorities, rate limits, chargeback', color: 'var(--rh-purple)' },
                    { name: 'KVCacheTransferPolicy', desc: 'KV cache migration for session continuity', color: 'var(--rh-red)' },
                    { name: 'ModelLifecycle', desc: 'SLO-gated rollouts, canary, blue-green, rollback', color: 'var(--rh-yellow)' },
                  ].map(crd => (
                    <motion.div key={crd.name} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                      style={{ padding: 14, background: 'var(--surface-1)', border: `1px solid ${crd.color}40`, borderLeft: `4px solid ${crd.color}`, borderRadius: '0 10px 10px 0' }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: crd.color, fontFamily: 'Red Hat Mono, monospace' }}>{crd.name}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>{crd.desc}</div>
                    </motion.div>
                  ))}
                </div>
                <FlowDescription text="CRDs are the source of truth. The fleet controller watches for changes and reconciles: creating InferencePools, adjusting placement, updating routing rules, and enforcing tenant isolation. The Rust data plane picks up routing and scaling decisions in real time via gRPC." />
              </div>
            )}

            {/* Act 4: The Brain Predicts */}
            {currentAct === 'predict' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  The SLO forecaster runs linear regression on P95 latency. At +80ms/min,
                  P95 will breach the 5s SLO in 22 minutes. Time to act.
                </p>
                <StepCard num={3} title="Run SLO Forecast" status={forecastStatus} onRun={doForecast} buttonLabel="Run forecast">
                  {sloForecast && (
                    <div>
                      <SLOGauge
                        currentMs={sloForecast.current_p95_ms}
                        forecastMs={sloForecast.forecast_p95_ms}
                        targetMs={sloForecast.slo_target_ms}
                        breachInMinutes={sloForecast.breach_in_minutes ?? undefined}
                      />
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 12 }}>
                        <MetricCard label="Current P95" value={`${sloForecast.current_p95_ms}ms`} color="var(--rh-blue)" />
                        <MetricCard label="Forecast" value={`${sloForecast.forecast_p95_ms}ms`} color={sloForecast.status === 'breach_predicted' ? 'var(--rh-red)' : 'var(--rh-orange)'} />
                        <MetricCard label="SLO Target" value={`${sloForecast.slo_target_ms}ms`} color="var(--rh-green)" />
                        <MetricCard label="Confidence" value={`${(sloForecast.confidence * 100).toFixed(0)}%`} color="var(--rh-teal)" />
                      </div>
                    </div>
                  )}
                </StepCard>
                {forecastStatus === 'done' && (
                  <StepCard num={4} title="Scope Blast Radius" status={blastRadiusStatus} onRun={doBlastRadius} buttonLabel="Scope blast radius">
                    {blastRadius && (
                      <div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
                          <MetricCard label="Affected Models" value={blastRadius.affected_models} color="var(--rh-orange)" />
                          <MetricCard label="Est. Users" value={blastRadius.estimated_users} color="var(--rh-blue)" />
                          <MetricCard label="Severity" value={blastRadius.severity} color={blastRadius.severity === 'high' || blastRadius.severity === 'critical' ? 'var(--rh-red)' : 'var(--rh-orange)'} />
                        </div>
                        <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 6, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                          <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4, fontWeight: 600 }}>RATIONALE</div>
                          {blastRadius.rationale}
                        </div>
                        {blastRadius.requires_human_gate && (
                          <div style={{ marginTop: 8, padding: '6px 12px', background: 'var(--surface-2)', border: '1px solid var(--rh-orange)', borderRadius: 6, fontSize: 12, color: 'var(--rh-orange)', fontWeight: 600 }}>
                            Human gate required for this action
                          </div>
                        )}
                      </div>
                    )}
                  </StepCard>
                )}
              </div>
            )}

            {/* Act 5: The Intent */}
            {currentAct === 'intent' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  The predictive brain emits a PreWarmIntent to fleet-llm-d. The policy
                  evaluator checks confidence, replica limits, and human gates before executing.
                </p>
                <StepCard num={5} title="Emit PreWarm Intent" status={intentStatus} onRun={doIntent} buttonLabel="Emit intent">
                  {intentResponse && (
                    <div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
                        <MetricCard label="Status" value={intentResponse.status} color={intentResponse.status === 'executed' ? 'var(--rh-green)' : intentResponse.status === 'refused' ? 'var(--rh-red)' : 'var(--rh-orange)'} />
                        <MetricCard label="Intent ID" value={intentResponse.intent_id.slice(0, 8)} color="var(--rh-blue)" />
                        <MetricCard label="Ledger" value={intentResponse.ledger_entry_id ? 'Recorded' : 'Pending'} color="var(--rh-purple)" />
                      </div>
                      <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 6, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                        <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4, fontWeight: 600 }}>REASON</div>
                        {intentResponse.reason}
                      </div>
                    </div>
                  )}
                </StepCard>
                <div style={{ marginTop: 16 }}>
                  <IntentFlow
                    stages={[
                      { label: 'SLO Forecast', status: sloForecast ? 'done' : 'idle' },
                      { label: 'Blast Radius', status: blastRadius ? 'done' : 'idle' },
                      { label: 'Policy Check', status: intentResponse ? 'done' : intentStatus === 'running' ? 'active' : 'idle' },
                      { label: 'Execute', status: intentResponse ? (intentResponse.status === 'executed' ? 'done' : 'error') : 'idle' },
                      { label: 'Ledger Write', status: intentResponse?.ledger_entry_id ? 'done' : 'idle' },
                    ]}
                    intentType="pre_warm"
                    model="granite-3.3-8b-instruct"
                    confidence={0.87}
                  />
                </div>
                <FlowDescription text="The intent carries a confidence score, justification, and target replica count. The policy evaluator checks: Is confidence above threshold? Are we within the scaling window? Does this model have headroom? If all gates pass, the intent executes and the decision is recorded in the ARE Ledger." />
              </div>
            )}

            {/* Act 6: The Proof */}
            {currentAct === 'proof' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  360 tests across 12 suites. 5 CPU models. P95 under 5 seconds. HPA scales
                  1 to 4 replicas. Zero downtime. Every decision in the ledger.
                </p>
                <TestMatrixCompact />
                <StepCard num={6} title="Verify Ledger Chains" status={ledgerStatus} onRun={doLedger} buttonLabel="Verify chains">
                  {ledgerChains && <LedgerChainView chains={ledgerChains.chains} />}
                </StepCard>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 16 }}>
                  <MetricCard label="Tests" value="360" color="var(--rh-green)" />
                  <MetricCard label="Suites" value="12" color="var(--rh-blue)" />
                  <MetricCard label="P95" value="< 5s" color="var(--rh-orange)" />
                  <MetricCard label="Savings" value="53x" color="var(--rh-red)" />
                </div>
              </div>
            )}

            {/* Act 7: The Return */}
            {currentAct === 'return' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  Every prediction, action, and outcome is recorded in the ARE Ledger. The
                  chain is cryptographically verifiable. The cycle continues.
                </p>
                <ReplicaTimeline events={[
                  { time: 'T-30m', replicas: 1, trigger: 'Baseline' },
                  { time: 'T-22m', replicas: 2, trigger: 'SLO forecast' },
                  { time: 'T-10m', replicas: 3, trigger: 'Pre-warm intent' },
                  { time: 'T-0', replicas: 4, trigger: 'Event start' },
                  { time: 'T+60m', replicas: 2, trigger: 'Load decrease' },
                  { time: 'T+90m', replicas: 1, trigger: 'Cool-down' },
                ]} maxReplicas={4} />

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
                  <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--rh-red)30', borderRadius: 10 }}>
                    <div style={{ fontSize: 10, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>WITHOUT PREDICTION</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--rh-red)', fontFamily: 'Red Hat Display, sans-serif' }}>Reactive</div>
                    <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>SLO breach → scramble → scale → 2 min outage</div>
                  </div>
                  <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--rh-green)30', borderRadius: 10 }}>
                    <div style={{ fontSize: 10, color: 'var(--rh-green)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>WITH PREDICTION</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--rh-green)', fontFamily: 'Red Hat Display, sans-serif' }}>Proactive</div>
                    <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>Forecast → pre-warm → zero downtime → ledger proof</div>
                  </div>
                </div>

                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
                  style={{ marginTop: 16, padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Event Profile Learning</div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
                    After each event, the system compares predicted vs actual load. The event
                    profile updates: if we pre-warmed too many replicas, next time we warm fewer.
                    If we under-provisioned, next time we warm earlier. Continuous improvement,
                    recorded in the ledger.
                  </p>
                </motion.div>

                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
                  style={{ marginTop: 16, padding: 20, background: 'var(--surface-1)', border: '1px solid var(--rh-red)40', borderRadius: 10, textAlign: 'center' }}>
                  <p style={{ fontSize: 15, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.8 }}>
                    Predict. Act. Prove. Learn. The fleet orchestration cycle.
                  </p>
                </motion.div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Footer */}
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
