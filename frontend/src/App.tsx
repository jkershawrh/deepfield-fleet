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
import { FleetDashboard } from './components/FleetDashboard';
import GovernanceDeepDive from './components/GovernanceDeepDive';
import { api } from './api/client';
import type { ApiCall } from './api/client';
import { useDemoStore } from './stores/useDemoStore';
import { useDataStore } from './stores/useDataStore';
import type { DemoState } from './stores/useDataStore';

/*
 * fleet-llm-d: Battle-Ready Inference at Fleet Scale
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
          style={{ fontSize: 44, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.1, margin: '24px 0 0', maxWidth: 700 }}>
          Governed AI Inference Fleet Management
        </motion.h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ fontSize: 22, color: 'var(--text-dim)', marginTop: 24 }}>
          Observe. Govern. Act. Prove.
        </motion.p>
      </div>
    ),
    // 1: The Bottleneck
    () => (
      <div style={{ textAlign: 'center', maxWidth: 800 }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <p style={{ fontSize: 40, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, margin: 0 }}>
            Enterprise AI inference demand is growing <span style={{ color: 'var(--rh-red)' }}>10x per year.</span>
          </p>
          <p style={{ fontSize: 36, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, margin: 0, color: 'var(--text-secondary)' }}>
            73% of organizations report inference service degradation during peak traffic.
          </p>
          <p style={{ fontSize: 36, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, margin: 0, color: 'var(--text-secondary)' }}>
            Average cost of unplanned AI downtime: <span style={{ color: 'var(--rh-red)' }}>$300,000 per hour.</span>
          </p>
        </motion.div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          style={{ fontSize: 22, color: 'var(--text-dim)', marginTop: 32 }}>
          The bottleneck isn&apos;t compute. It&apos;s orchestration.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ fontSize: 12, color: 'var(--text-disabled)', marginTop: 24, fontFamily: 'Red Hat Mono, monospace' }}>
          Sources: Gartner 2025, IDC AI Infrastructure Survey, Forrester TEI Analysis
        </motion.p>
      </div>
    ),
    // 2: What is llm-d?
    () => (
      <div style={{ textAlign: 'center', maxWidth: 700 }}>
        <motion.h2 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 56, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', margin: '0 0 16px' }}>
          llm-d
        </motion.h2>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          style={{ fontSize: 20, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 32 }}>
          Open-source inference gateway for Kubernetes. Scalable model serving with intelligent
          routing, KV cache optimization, and prefix-aware scheduling. The foundation.
        </motion.p>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          style={{ display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'left' }}>
          {[
            'Scalable model serving on Kubernetes',
            'Intelligent request routing with KV cache affinity',
            'Open source, CNCF-aligned, community-driven',
          ].map((line, i) => (
            <div key={i} style={{ fontSize: 20, color: 'var(--text-dim)', paddingLeft: 16, borderLeft: '3px solid var(--rh-red)' }}>
              {line}
            </div>
          ))}
        </motion.div>
      </div>
    ),
    // 3: What is fleet-llm-d?
    () => (
      <div style={{ textAlign: 'center', maxWidth: 750 }}>
        <motion.h2 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 56, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', margin: '0 0 16px' }}>
          <span style={{ color: 'var(--rh-red)' }}>fleet-</span>llm-d
        </motion.h2>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          style={{ fontSize: 20, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 32 }}>
          Multi-cluster orchestration built on llm-d. Governs inference fleets across clusters,
          tenants, and regions. Designed for the burst, not just the baseline.
        </motion.p>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          style={{ display: 'flex', flexDirection: 'column', gap: 16, textAlign: 'left' }}>
          {[
            { bold: 'Multi-cluster placement', desc: "models where they're needed, when they're needed" },
            { bold: 'Multi-tenant governance', desc: 'quotas, budgets, fair scheduling per tenant' },
            { bold: 'SLO-gated rollouts', desc: 'auto-rollback if latency breaches threshold' },
            { bold: 'Load shedding', desc: 'graceful 503s with Retry-After, not cascading failures' },
          ].map((item, i) => (
            <div key={i} style={{ fontSize: 22, lineHeight: 1.4 }}>
              <strong style={{ color: 'var(--text-primary)' }}>{item.bold}</strong>
              <span style={{ color: 'var(--text-dim)' }}> - {item.desc}</span>
            </div>
          ))}
        </motion.div>
      </div>
    ),
    // 4: Battle-Ready
    () => (
      <div style={{ maxWidth: 800 }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 42, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.2, textAlign: 'center', marginBottom: 40 }}>
          When 200 users hit at once,
          <br />does your inference stack <span style={{ color: 'var(--rh-red)' }}>survive?</span>
        </motion.p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { industry: 'Telco edge', desc: '5G tower handoff spikes, 10,000 inference calls in 30 seconds', color: 'var(--rh-blue)' },
            { industry: 'Financial services', desc: 'market open, every trading desk needs risk models simultaneously', color: 'var(--rh-green)' },
            { industry: 'Healthcare', desc: 'clinical decision support during shift change, 40 providers querying at once', color: 'var(--rh-purple)' },
            { industry: 'Events', desc: 'Red Hat Summit Connect, 200 concurrent demo users, zero tolerance for failure', color: 'var(--rh-red)' },
          ].map((scenario, i) => (
            <motion.div key={scenario.industry} initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 + i * 0.15 }}
              style={{ padding: 20, background: 'var(--surface-1)', border: `1px solid ${scenario.color}40`, borderLeft: `4px solid ${scenario.color}`, borderRadius: '0 10px 10px 0' }}>
              <span style={{ fontSize: 22, fontWeight: 800, color: scenario.color }}>{scenario.industry}</span>
              <span style={{ fontSize: 20, color: 'var(--text-dim)', fontStyle: 'italic' }}>{' '}- {scenario.desc}</span>
            </motion.div>
          ))}
        </div>
      </div>
    ),
    // 5: The Ecosystem
    () => (
      <div style={{ textAlign: 'center', maxWidth: 800 }}>
        <motion.h2 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 42, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', margin: '0 0 32px' }}>
          The Ecosystem: Four Systems, One Pipeline
        </motion.h2>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0, flexWrap: 'wrap' }}>
          {[
            { name: 'deepfield-fleet', verb: 'Observe', color: 'var(--rh-blue)', desc: 'Predictive intelligence. SLO forecasting, event profiles, advisory evidence.' },
            { name: 'GCL', verb: 'Govern', color: 'var(--rh-purple)', desc: 'Constraint classification, falsification gate, signed DecisionPackages.' },
            { name: 'fleet-llm-d', verb: 'Act', color: 'var(--rh-red)', desc: 'Authorization, admission, multi-cluster actuation, load shedding.' },
            { name: 'ARE Ledger', verb: 'Prove', color: 'var(--rh-teal)', desc: 'Immutable receipts. Every committed action cryptographically anchored.' },
          ].map((sys, i) => (
            <div key={sys.name} style={{ display: 'flex', alignItems: 'center' }}>
              <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 + i * 0.15 }}
                style={{ padding: '16px 20px', background: 'var(--surface-1)', border: `1px solid ${sys.color}40`, borderRadius: 10, textAlign: 'center', width: 160 }}>
                <div style={{ fontSize: 10, color: sys.color, fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 6 }}>
                  {sys.verb.toUpperCase()}
                </div>
                <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'Red Hat Display, sans-serif', marginBottom: 6 }}>
                  {sys.name}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.5 }}>
                  {sys.desc}
                </div>
              </motion.div>
              {i < 3 && (
                <span style={{ fontSize: 18, color: 'var(--text-disabled)', margin: '0 6px', fontWeight: 300 }}>&rarr;</span>
              )}
            </div>
          ))}
        </motion.div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9 }}
          style={{ fontSize: 13, color: 'var(--text-disabled)', marginTop: 28, fontFamily: 'Red Hat Mono, monospace' }}>
          Each system owns one concern. No system bypasses its neighbors.
        </motion.p>
      </div>
    ),
    // 6: CTA
    () => (
      <div style={{ textAlign: 'center' }}>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          style={{ fontSize: 42, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.3, marginBottom: 16 }}>
          Let me show you what happens
          <br />when 200 users hit at once.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          <button onClick={() => setMode('manual')}
            style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '16px 48px', borderRadius: 10, fontSize: 20, fontWeight: 700, cursor: 'pointer' }}>
            Start the Demo &rarr;
          </button>
        </motion.div>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
          style={{ marginTop: 32, fontSize: 13, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
          Tested on Intel Xeon 6 &middot; Red Hat OpenShift &middot; Zero GPU required
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

  /* ───────────────────────── GOVERNANCE MODE ───────────────────────── */

  if (mode === 'governance') {
    return <GovernanceDeepDive onExit={() => setMode('manual')} />;
  }

  /* ───────────────────────── DASHBOARD MODE ───────────────────────── */

  if (mode === 'dashboard') {
    return <FleetDashboard onExit={() => setMode('slides')} />;
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
              Inference mode: {demoState.inference_mode === 'llm' ? 'Live LLM via LiteLLM' : 'Simulated (rule-backed). Set LITELLM_API_BASE for live inference'}
            </div>
          )}

          {demoState.scale_metrics && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
              <MetricCard label="Clusters" value={String((demoState.scale_metrics as Record<string, unknown>).clusters || '--')} color="var(--rh-blue)" />
              <MetricCard label="Models" value={String((demoState.scale_metrics as Record<string, unknown>).models || '--')} color="var(--rh-teal)" />
              <MetricCard label="Replicas" value={String((demoState.scale_metrics as Record<string, unknown>).replicas || '--')} color="var(--rh-green)" />
              <MetricCard label="Latency" value={`${(demoState.scale_metrics as Record<string, unknown>).elapsed_ms || '--'}ms`} color="var(--rh-orange)" />
            </div>
          )}

          {demoState.cumulative && ((demoState.step_id || '').startsWith('scale') || (demoState.step_id || '') === 'stress' || (demoState.step_id || '') === 'recovery') ? (
            <div style={{ fontSize: 11, color: 'var(--text-disabled)', marginBottom: 12, fontFamily: 'Red Hat Mono, monospace', display: 'flex', gap: 16, justifyContent: 'center' }}>
              <span>Total replicas: {String((demoState.cumulative as Record<string, unknown>).total_replicas || 0)}</span>
              <span>Total requests: {String((demoState.cumulative as Record<string, unknown>).total_requests || 0)}</span>
              <span>Clusters active: {String((demoState.cumulative as Record<string, unknown>).clusters_active || 0)}</span>
            </div>
          ) : null}

          {/* Fleet Pipeline Flow: live animated prediction, action, outcome, learn */}
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

          {/* Contextual detail panels: fade in at relevant steps */}
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

          {/* The Claim: fleet metrics + use cases */}
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
                  { value: '295', label: 'Backend Tests Passing', color: 'var(--rh-green)' },
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
                  Fleet ecosystem architecture. Contract-tested.
                </p>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 12, lineHeight: 1.8 }}>
                  DeepField produces advisory evidence, GCL synthesizes signed decisions, and
                  fleet owns authorization and operations. Live multi-cluster actuation and
                  standalone-ledger proof remain external promotion evidence.
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
                    Standalone immutable-ledger integration is proof-only. No chain is shown as verified without a live receipt and entry lookup.
                  </div>
                </div>
                <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--rh-purple)30', borderRadius: 10 }}>
                  <div style={{ fontSize: 10, color: 'var(--rh-purple)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>INTELLIGENCE</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--rh-purple)', fontFamily: 'Red Hat Display, sans-serif' }}>Predict</div>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>
                    deepfield-fleet produces observations, findings, forecasts, and advisory remediation proposals for GCL evaluation.
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
                      desc: 'Data-sovereign inference within geographic boundaries. Residency and ledger evidence require live fleet outcomes and independently verified receipts.' },
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
                    Historical cost fixture · 295 backend tests · external execution proof required
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
            {isRunning || isPaused ? `Step ${(demoState.current_step || 0) + 1} / ${demoState.total_steps || 13}${isPaused ? ' - PAUSED' : ''}` : demoState.status}
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

  const manualActs = ['baseline', 'event', 'fleet', 'predict', 'response', 'burst', 'proof', 'learning'] as const;
  const manualMeta: Record<string, { title: string; subtitle: string; next: string }> = {
    baseline: { title: 'The Baseline',    subtitle: 'The fleet is quiet. Everything is green.',                                   next: 'The event arrives →' },
    event:    { title: 'The Event',        subtitle: 'The burst is coming. Load the event profile.',                               next: 'See the fleet →' },
    fleet:    { title: 'The Fleet',        subtitle: 'How fleet-llm-d manages routing, scaling, and governance.',                  next: 'See the prediction →' },
    predict:  { title: 'The Prediction',   subtitle: 'The SLO forecaster sees latency climbing.',                                  next: 'See the response →' },
    response: { title: 'The Governance Gate', subtitle: 'Advisory evidence enters the Governed Cognitive Loop.',                      next: 'See the actuation →' },
    burst:    { title: 'The Actuation',    subtitle: 'fleet-llm-d admits, authorizes, and executes.',                              next: 'See the proof →' },
    proof:    { title: 'Evidence Boundary', subtitle: 'Synthetic walkthrough; live fleet and ledger proof remain external.',       next: 'See the learning →' },
    learning: { title: 'The Learning',     subtitle: 'The fleet gets smarter for next time.',                                      next: '' },
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

            {/* Act 0: The Baseline */}
            {currentAct === 'baseline' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 16 }}>
                  A fleet of 5 Granite models serving inference on Intel Xeon 6. Single replica per
                  model. P95 latency: 800ms. The fleet is quiet.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 16 }}>
                  <MetricCard label="P95 Latency" value="800ms" color="var(--rh-green)" detail="Under SLO" />
                  <MetricCard label="Replicas" value="5" color="var(--rh-blue)" detail="1 each" />
                  <MetricCard label="Queue Depth" value="0" color="var(--rh-teal)" detail="No backlog" />
                  <MetricCard label="Error Rate" value="0%" color="var(--rh-green)" detail="All healthy" />
                </div>
              </div>
            )}

            {/* Act 1: The Event */}
            {currentAct === 'event' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 16 }}>
                  Red Hat Summit Connect starts in 30 minutes. 200 concurrent users will need
                  inference. This is the moment that breaks most inference stacks.
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

            {/* Act 2: The Fleet */}
            {currentAct === 'fleet' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 16 }}>
                  fleet-llm-d sits between users and models. It manages routing, scaling, load
                  shedding, and tenant governance across the fleet.
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
                          <span style={{ color: 'var(--text-dim)', marginLeft: 'auto' }}>{m.runtime} &middot; {m.replicas} replicas</span>
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

            {/* Act 3: The Prediction */}
            {currentAct === 'predict' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 16 }}>
                  The SLO forecaster sees latency climbing. At the current rate, P95 will breach
                  the 5-second SLO in 22 minutes. 200 users across 5 models. Severity score: critical.
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
                        <MetricCard label="Current P95" value={`${Math.round(sloForecast.current_p95_ms).toLocaleString()}ms`} color="var(--rh-blue)" />
                        <MetricCard label="Forecast" value={`${Math.round(sloForecast.forecast_p95_ms).toLocaleString()}ms`} color={sloForecast.status === 'breach_predicted' ? 'var(--rh-red)' : 'var(--rh-orange)'} />
                        <MetricCard label="SLO Target" value={`${Math.round(sloForecast.slo_target_ms).toLocaleString()}ms`} color="var(--rh-green)" />
                        <MetricCard label="Confidence" value={`${Math.round(sloForecast.confidence * 100)}%`} color="var(--rh-teal)" />
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
                {/* Ecosystem context callout */}
                <div style={{
                  marginTop: 16, padding: '12px 16px', background: 'var(--rh-blue)08',
                  border: '1px solid var(--rh-blue)30', borderLeft: '3px solid var(--rh-blue)',
                  borderRadius: '0 8px 8px 0', fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.7,
                }}>
                  <span style={{ fontSize: 10, color: 'var(--rh-blue)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1 }}>
                    ECOSYSTEM BOUNDARY
                  </span>
                  <br />
                  Advisory evidence published as CloudEvents to the Governed Cognitive Loop. deepfield-fleet
                  observes and forecasts. It never executes.
                </div>
              </div>
            )}

            {/* Act 4: The Governance Gate */}
            {currentAct === 'response' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 16 }}>
                  Advisory evidence enters the Governed Cognitive Loop. Constraints classified.
                  Falsification gate applied. A signed DecisionPackage is emitted to fleet-llm-d.
                </p>

                {/* Governance flow visualization */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0, flexWrap: 'wrap', margin: '20px 0' }}>
                  {[
                    { label: 'Advisory CloudEvent', detail: 'from deepfield-fleet', color: 'var(--rh-blue)', status: sloForecast ? 'done' : 'idle' },
                    { label: 'Classify Constraints', detail: 'GCL constraint engine', color: 'var(--rh-purple)', status: blastRadius ? 'done' : 'idle' },
                    { label: 'Falsification Gate', detail: '7 deterministic checks', color: 'var(--rh-orange)', status: intentStatus === 'running' ? 'active' : intentResponse ? 'done' : 'idle' },
                    { label: 'Signed DecisionPackage', detail: 'cryptographic commitment', color: 'var(--rh-teal)', status: intentResponse ? 'done' : 'idle' },
                    { label: 'fleet-llm-d Admission', detail: 'authorization + execution', color: 'var(--rh-red)', status: 'idle' },
                  ].map((stage, i) => (
                    <div key={stage.label} style={{ display: 'flex', alignItems: 'center' }}>
                      <div style={{
                        padding: '10px 14px', background: 'var(--surface-1)',
                        border: `1px solid ${stage.status === 'done' ? stage.color : 'var(--border)'}`,
                        borderRadius: 8, textAlign: 'center', minWidth: 120, opacity: stage.status === 'idle' ? 0.6 : 1,
                      }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: stage.status === 'done' ? stage.color : 'var(--text-secondary)', marginBottom: 2 }}>
                          {stage.label}
                        </div>
                        <div style={{ fontSize: 9, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
                          {stage.detail}
                        </div>
                      </div>
                      {i < 4 && (
                        <span style={{ fontSize: 14, color: 'var(--text-disabled)', margin: '0 4px' }}>&rarr;</span>
                      )}
                    </div>
                  ))}
                </div>

                <StepCard num={5} title="Emit DecisionPackage" status={intentStatus} onRun={doIntent} buttonLabel="Run governance gate">
                  {intentResponse && (
                    <div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
                        <MetricCard label="Delivery" value={intentResponse.status} color={intentResponse.status === 'accepted' ? 'var(--rh-blue)' : intentResponse.status === 'rejected' ? 'var(--rh-red)' : 'var(--rh-orange)'} />
                        <MetricCard label="Correlation" value={intentResponse.intent_id.slice(0, 8)} color="var(--rh-blue)" />
                        <MetricCard label="Execution" value={intentResponse.execution_verified ? 'Verified' : 'Unverified'} color="var(--rh-orange)" />
                      </div>
                      <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 6, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                        <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4, fontWeight: 600 }}>DECISION REASON</div>
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
                      { label: 'Falsification Gate', status: intentResponse ? 'done' : intentStatus === 'running' ? 'active' : 'idle' },
                      { label: 'DecisionPackage Signed', status: intentResponse ? (intentResponse.status === 'accepted' ? 'done' : 'error') : 'idle' },
                      { label: 'fleet-llm-d Admission', status: 'idle' },
                    ]}
                    intentType="pre_warm"
                    model="granite-3.3-8b-instruct"
                    confidence={0.87}
                  />
                </div>

                <button
                  onClick={() => setMode('governance')}
                  style={{
                    marginTop: 16, background: 'none', border: '1px solid var(--rh-purple)',
                    color: 'var(--rh-purple)', padding: '8px 20px', borderRadius: 6, fontSize: 13,
                    fontWeight: 600, cursor: 'pointer', display: 'block', width: '100%',
                  }}>
                  Governance Deep Dive
                </button>
              </div>
            )}

            {/* Act 5: The Actuation */}
            {currentAct === 'burst' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 16 }}>
                  fleet-llm-d admits the DecisionPackage, checks authorization, and executes. Pre-warm
                  replicas scale. Load shedding activates under burst.
                </p>
                <div style={{ padding: 12, background: 'var(--surface-1)', border: '1px solid var(--rh-red)30', borderRadius: 8, marginBottom: 16, fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.7 }}>
                  <span style={{ color: 'var(--rh-red)', fontWeight: 700, fontSize: 10, fontFamily: 'Red Hat Mono, monospace', letterSpacing: 1 }}>AUTHORIZATION BOUNDARY</span>
                  <br />
                  fleet-llm-d owns the authorization decision. GCL produces a signed DecisionPackage,
                  but fleet-llm-d independently verifies the signature, checks policy, and decides
                  whether to execute. The governance layer advises; the fleet layer authorizes.
                </div>
                <ReplicaTimeline events={[
                  { time: 'T-30m', replicas: 1, trigger: 'Baseline' },
                  { time: 'T-22m', replicas: 2, trigger: 'SLO forecast' },
                  { time: 'T-10m', replicas: 3, trigger: 'DecisionPackage admitted' },
                  { time: 'T-0', replicas: 4, trigger: 'Event start, pre-warmed' },
                  { time: 'T+5m', replicas: 4, trigger: 'Load shedding active' },
                  { time: 'T+15m', replicas: 5, trigger: 'HPA scale-up' },
                ]} maxReplicas={5} />
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 16 }}>
                  <MetricCard label="Peak Users" value="200" color="var(--rh-red)" detail="Concurrent" />
                  <MetricCard label="503s Served" value="12" color="var(--rh-orange)" detail="With Retry-After" />
                  <MetricCard label="Cascading Failures" value="0" color="var(--rh-green)" detail="Load shedding active" />
                </div>
              </div>
            )}

            {/* Act 6: The Proof */}
            {currentAct === 'proof' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 16 }}>
                  This synthetic scenario illustrates an intended outcome. It does not prove a
                  fleet operation, a measured SLO, or a verified immutable-ledger receipt.
                </p>
                <TestMatrixCompact />
                <StepCard num={6} title="Check External Ledger Evidence" status={ledgerStatus} onRun={doLedger} buttonLabel="Check evidence">
                  {ledgerChains && <LedgerChainView chains={ledgerChains.chains} />}
                </StepCard>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 16 }}>
                  <MetricCard label="P95 Fixture" value="< 5s" color="var(--rh-orange)" detail="Not live evidence" />
                  <MetricCard label="Backend Tests" value="295" color="var(--rh-blue)" detail="3 skipped" />
                  <MetricCard label="Failure Fixture" value="0" color="var(--rh-orange)" detail="Not live evidence" />
                  <MetricCard label="Ledger Evidence" value="0 live chains" color="var(--rh-orange)" detail="External evidence required" />
                </div>
              </div>
            )}

            {/* Act 7: The Learning */}
            {currentAct === 'learning' && (
              <div>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 16 }}>
                  The event profile captures what actually happened vs what was predicted. Next
                  time, pre-warming starts earlier, replica targets are higher. The fleet learns
                  from every burst.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
                  <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--rh-red)30', borderRadius: 10 }}>
                    <div style={{ fontSize: 10, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>PREDICTED</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--rh-red)', fontFamily: 'Red Hat Display, sans-serif' }}>4 replicas</div>
                    <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>Pre-warm target based on event profile. Started 30 min early.</div>
                  </div>
                  <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--rh-green)30', borderRadius: 10 }}>
                    <div style={{ fontSize: 10, color: 'var(--rh-green)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>ACTUAL</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--rh-green)', fontFamily: 'Red Hat Display, sans-serif' }}>5 replicas needed</div>
                    <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>HPA scaled one additional. Next time, pre-warm to 5.</div>
                  </div>
                </div>

                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
                  style={{ marginTop: 16, padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Event Profile Update</div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
                    The event profile records the delta: predicted 4 replicas, needed 5. Pre-warm
                    window was 30 minutes, sufficient. Next Summit Connect event will pre-warm to
                    5 replicas. This is an advisory learning fixture; policy and authority cannot
                    be promoted automatically from it.
                  </p>
                </motion.div>

                <div style={{ marginTop: 16 }}>
                  <ReplicaTimeline events={[
                    { time: 'T-30m', replicas: 1, trigger: 'Baseline' },
                    { time: 'T-22m', replicas: 2, trigger: 'SLO forecast' },
                    { time: 'T-10m', replicas: 4, trigger: 'Pre-warm intent' },
                    { time: 'T-0', replicas: 4, trigger: 'Event start' },
                    { time: 'T+15m', replicas: 5, trigger: 'HPA scale-up' },
                    { time: 'T+60m', replicas: 2, trigger: 'Load decrease' },
                    { time: 'T+90m', replicas: 1, trigger: 'Cool-down' },
                  ]} maxReplicas={5} />
                </div>
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
