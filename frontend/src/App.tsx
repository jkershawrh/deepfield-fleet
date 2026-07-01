import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Header } from './components/Header';
import { StepCard } from './components/StepCard';
import { MetricCard } from './components/MetricCard';
import { CascadeDiagram } from './components/CascadeDiagram';
import { JsonViewer } from './components/JsonViewer';
import { api } from './api/client';
import type { EvidenceArtifact, ClassificationRecord, BaselineProfile, AgentAction, VerificationRecord, LearningProposal, LoopResult, ApiCall } from './api/client';

/*
 * Joseph Campbell's Hero's Journey — mapped to DeepField Multimodal
 *
 * Act 0: The Ordinary World     — "Everything is normal. The factory hums."
 * Act 1: The Call to Adventure  — "Signals arrive. Something is different."
 * Act 2: Crossing the Threshold — "Nanoagents detect what humans can't yet see."
 * Act 3: The Ordeal             — "Multi-modal evidence converges on the truth."
 * Act 4: The Reward             — "The system proposes what to do — safely."
 * Act 5: The Return             — "What was learned will protect the future."
 */

const ACTS = ['ordinary', 'call', 'threshold', 'ordeal', 'reward', 'return'] as const;
type Act = typeof ACTS[number];

const ACT_META: Record<Act, { title: string; subtitle: string; next: string }> = {
  ordinary:  { title: 'The Ordinary World',     subtitle: 'Everything is normal. The factory hums.',                  next: 'Begin the story →' },
  call:      { title: 'The Call to Adventure',   subtitle: 'Signals arrive. Something is different.',                 next: 'Cross the threshold →' },
  threshold: { title: 'Crossing the Threshold',  subtitle: 'Nanoagents detect what humans can\'t yet see.',           next: 'Face the ordeal →' },
  ordeal:    { title: 'The Ordeal',              subtitle: 'Multi-modal evidence converges on the truth.',            next: 'Claim the reward →' },
  reward:    { title: 'The Reward',              subtitle: 'The system proposes what to do — safely.',                next: 'Begin the return →' },
  return:    { title: 'The Return',              subtitle: 'What was learned will protect the future.',               next: '' },
};

const MODALITY_COLORS: Record<string, string> = {
  metric: 'var(--rh-blue)', log: 'var(--rh-green)', document: 'var(--rh-orange)',
  image: 'var(--rh-purple)', audio: 'var(--rh-red)', event: 'var(--rh-yellow)',
};

export default function App() {
  const [started, setStarted] = useState(false);
  const [actIndex, setActIndex] = useState(0);

  // Data state
  const [evidence, setEvidence] = useState<EvidenceArtifact[]>([]);
  const [baseline, setBaseline] = useState<BaselineProfile | null>(null);
  const [classifications, setClassifications] = useState<ClassificationRecord[]>([]);
  const [loopResult, setLoopResult] = useState<LoopResult | null>(null);

  // Step statuses
  const [ingestStatus, setIngestStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [baselineStatus, setBaselineStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [cascadeStatus, setCascadeStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [loopStatus, setLoopStatus] = useState<'idle' | 'running' | 'done'>('idle');

  // API call records
  const [apiCalls, setApiCalls] = useState<ApiCall<unknown>[]>([]);

  const addCall = (call: ApiCall<unknown>) => setApiCalls(prev => [...prev, call]);

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

  const currentAct = ACTS[actIndex];
  const meta = ACT_META[currentAct];

  // --- Hero screen ---
  if (!started) {
    return (
      <div
        onClick={() => setStarted(true)}
        style={{ height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', background: 'var(--bg-dark)' }}
      >
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', lineHeight: 1.2 }}>
              DeepField<span style={{ color: 'var(--rh-red)' }}> Multimodal</span>
            </div>
            <div style={{ fontSize: 18, color: 'var(--text-dim)', marginTop: 12, fontFamily: 'Red Hat Text, sans-serif' }}>
              Enterprise Signal Intelligence
            </div>
            <div style={{ fontSize: 14, color: 'var(--text-disabled)', marginTop: 24, fontFamily: 'Red Hat Mono, monospace' }}>
              Signals → Decide → Act → Verify → Learn
            </div>
          </div>
        </motion.div>
        <motion.div
          animate={{ opacity: [0.3, 0.8, 0.3] }}
          transition={{ repeat: Infinity, duration: 2.5 }}
          style={{ marginTop: 48, fontSize: 13, color: 'var(--text-dim)' }}
        >
          Click anywhere to begin
        </motion.div>
      </div>
    );
  }

  // --- Story acts ---
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />

      {/* Act indicator dots */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 6, padding: '12px 0', borderBottom: '1px solid var(--border)', background: 'var(--bg-dark)' }}>
        {ACTS.map((act, i) => (
          <div key={act}
            onClick={() => { if (i <= actIndex) setActIndex(i); }}
            style={{
              width: 8, height: 8, borderRadius: '50%', cursor: i <= actIndex ? 'pointer' : 'default',
              background: i === actIndex ? 'var(--rh-red)' : i < actIndex ? 'var(--rh-green)' : 'var(--border)',
              transition: 'background 0.3s',
            }}
          />
        ))}
      </div>

      {/* Act content */}
      <div style={{ flex: 1, maxWidth: 840, margin: '0 auto', padding: '32px 24px', width: '100%' }}>
        {/* Act header */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentAct}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.3 }}
          >
            <div style={{ marginBottom: 32 }}>
              <div style={{ fontSize: 12, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 800, marginBottom: 4 }}>
                ACT {actIndex + 1} OF {ACTS.length}
              </div>
              <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>{meta.title}</h2>
              <p style={{ fontSize: 16, color: 'var(--text-dim)', margin: 0 }}>{meta.subtitle}</p>
            </div>

            {/* Act-specific content */}
            {currentAct === 'ordinary' && <OrdinaryWorld />}
            {currentAct === 'call' && (
              <CallToAdventure evidence={evidence} status={ingestStatus} onIngest={doIngest} />
            )}
            {currentAct === 'threshold' && (
              <CrossingThreshold baseline={baseline} status={baselineStatus} onBuild={doBaseline} evidence={evidence} onIngest={doIngest} ingestStatus={ingestStatus} />
            )}
            {currentAct === 'ordeal' && (
              <TheOrdeal classifications={classifications} status={cascadeStatus} onCascade={doCascade} evidence={evidence} baseline={baseline} onIngest={doIngest} onBuild={doBaseline} ingestStatus={ingestStatus} baselineStatus={baselineStatus} />
            )}
            {currentAct === 'reward' && (
              <TheReward loopResult={loopResult} status={loopStatus} onLoop={doLoop} evidence={evidence} baseline={baseline} classifications={classifications} onIngest={doIngest} onBuild={doBaseline} onCascade={doCascade} ingestStatus={ingestStatus} baselineStatus={baselineStatus} cascadeStatus={cascadeStatus} />
            )}
            {currentAct === 'return' && (
              <TheReturn loopResult={loopResult} apiCalls={apiCalls} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Bottom navigation */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '14px 32px', borderTop: '1px solid var(--border)', background: 'var(--surface-1)',
      }}>
        <button
          onClick={() => setActIndex(Math.max(0, actIndex - 1))}
          disabled={actIndex === 0}
          style={{
            background: 'none', border: '1px solid var(--border)', color: 'var(--text-dim)',
            padding: '6px 16px', borderRadius: 6, fontSize: 13,
            opacity: actIndex === 0 ? 0.3 : 1,
          }}
        >
          ← Back
        </button>
        <span style={{ fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
          {actIndex + 1} / {ACTS.length}
        </span>
        {meta.next && (
          <button
            onClick={() => setActIndex(Math.min(ACTS.length - 1, actIndex + 1))}
            style={{
              background: 'var(--rh-red)', border: 'none', color: '#fff',
              padding: '6px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600,
            }}
          >
            {meta.next}
          </button>
        )}
        {!meta.next && <div />}
      </div>
    </div>
  );
}


// =========================================================================
// ACT COMPONENTS
// =========================================================================

function OrdinaryWorld() {
  return (
    <div>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15 }}>
        A factory production line hums with the rhythm of precision machinery.
        Bearings spin, temperatures hold steady, vibration sensors report flat lines.
        Every signal says the same thing: <em>normal</em>.
      </p>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15, marginTop: 16 }}>
        But beneath the surface, DeepField has been learning. It has studied
        weeks of historical data — vibration patterns, thermal profiles, maintenance
        logs, inspection reports. It has compiled a <strong>baseline</strong>: the shape of normal.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 24 }}>
        <MetricCard label="Vibration RMS" value="0.22" color="var(--rh-green)" detail="Within baseline" />
        <MetricCard label="Temperature" value="38.2°C" color="var(--rh-green)" detail="Stable" />
        <MetricCard label="Defect Rate" value="0.1%" color="var(--rh-green)" detail="Normal" />
      </div>

      <div style={{
        marginTop: 24, padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)',
        borderRadius: 10, fontSize: 13, color: 'var(--text-dim)', fontStyle: 'italic',
      }}>
        "The first job of enterprise AI is not generation. It is classifying reality
        well enough to know what should happen next."
      </div>
    </div>
  );
}


function CallToAdventure({ evidence, status, onIngest }: {
  evidence: EvidenceArtifact[]; status: string; onIngest: () => void;
}) {
  return (
    <div>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15 }}>
        Then the signals change. Vibration drifts upward. Temperature creeps.
        A maintenance log fills with warnings. An inspection camera captures
        something on the bearing surface. An operator writes a note about
        an unusual grinding noise.
      </p>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15, marginTop: 16 }}>
        The enterprise has called. Will the system answer?
      </p>

      <StepCard num={1} title="Ingest Multimodal Evidence" status={status as 'idle' | 'running' | 'done'} onRun={onIngest} buttonLabel="Ingest signals">
        {evidence.length > 0 && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
              <MetricCard label="Artifacts" value={evidence.length} color="var(--rh-blue)" />
              <MetricCard label="Modalities" value={new Set(evidence.map(e => e.modality)).size} color="var(--rh-teal)" />
              <MetricCard label="Sources" value={new Set(evidence.map(e => e.source)).size} color="var(--rh-orange)" />
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {evidence.map(e => (
                <motion.span
                  key={e.evidence_id}
                  initial={{ scale: 0 }} animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 20 }}
                  style={{
                    display: 'inline-block', padding: '4px 10px', borderRadius: 6, fontSize: 11,
                    background: (MODALITY_COLORS[e.modality] || 'var(--border)') + '20',
                    border: `1px solid ${MODALITY_COLORS[e.modality] || 'var(--border)'}40`,
                    color: 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace',
                  }}
                >
                  {e.modality}/{e.artifact_type}
                </motion.span>
              ))}
            </div>
            <JsonViewer label="Raw evidence response" data={evidence} />
          </div>
        )}
      </StepCard>
    </div>
  );
}


function CrossingThreshold({ baseline, status, onBuild, evidence, onIngest, ingestStatus }: {
  baseline: BaselineProfile | null; status: string; onBuild: () => void;
  evidence: EvidenceArtifact[]; onIngest: () => void; ingestStatus: string;
}) {
  return (
    <div>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15 }}>
        The hero cannot face the unknown without preparation. DeepField compiles
        everything it has learned into a <strong>baseline profile</strong> — the
        shape of normal, distilled into thresholds, ranges, and statistical signatures.
      </p>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15, marginTop: 16 }}>
        This baseline becomes the lens through which every new signal is judged.
        Deviations are measured. Confidence is quantified. The threshold between
        normal and abnormal is crossed.
      </p>

      {evidence.length === 0 && (
        <StepCard num={1} title="Ingest evidence first" status={ingestStatus as 'idle' | 'running' | 'done'} onRun={onIngest} buttonLabel="Ingest signals" />
      )}

      <StepCard num={2} title="Build Baseline Profile" status={status as 'idle' | 'running' | 'done'}
        onRun={evidence.length > 0 ? onBuild : undefined}
        buttonLabel="Compile baseline"
      >
        {baseline && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
              <MetricCard label="Confidence" value={`${(baseline.confidence * 100).toFixed(0)}%`} color="var(--rh-green)" />
              <MetricCard label="Scope" value={baseline.scope_id} color="var(--rh-blue)" />
              <MetricCard label="Threshold Groups" value={Object.keys(baseline.thresholds).length} color="var(--rh-orange)" />
              <MetricCard label="Range Groups" value={Object.keys(baseline.normal_ranges).length} color="var(--rh-teal)" />
            </div>
            <JsonViewer label="Baseline profile" data={baseline} />
          </div>
        )}
      </StepCard>
    </div>
  );
}


function TheOrdeal({ classifications, status, onCascade, evidence, baseline, onIngest, onBuild, ingestStatus, baselineStatus }: {
  classifications: ClassificationRecord[]; status: string; onCascade: () => void;
  evidence: EvidenceArtifact[]; baseline: BaselineProfile | null;
  onIngest: () => void; onBuild: () => void; ingestStatus: string; baselineStatus: string;
}) {
  const nano = classifications.filter(c => c.agent_tier === 'nano');
  const micro = classifications.filter(c => c.agent_tier === 'micro');
  const macro = classifications.filter(c => c.agent_tier === 'macro');
  const highConf = classifications.filter(c => c.confidence >= 0.7 && (c.severity === 'high' || c.severity === 'critical'));

  return (
    <div>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15 }}>
        Now comes the ordeal. The evidence flows through three tiers of increasingly
        sophisticated agents. <strong>Nanoagents</strong> — fast, deterministic, no
        LLM — detect the first signs of drift. <strong>Microagents</strong> classify
        the image, the audio, the text. <strong>Macroagents</strong> correlate across
        modalities and build the incident timeline.
      </p>

      {evidence.length === 0 && (
        <StepCard num={1} title="Ingest evidence first" status={ingestStatus as 'idle' | 'running' | 'done'} onRun={onIngest} buttonLabel="Ingest" />
      )}
      {evidence.length > 0 && !baseline && (
        <StepCard num={2} title="Build baseline first" status={baselineStatus as 'idle' | 'running' | 'done'} onRun={onBuild} buttonLabel="Build baseline" />
      )}

      <StepCard num={3} title="Run Classification Cascade" status={status as 'idle' | 'running' | 'done'}
        onRun={baseline ? onCascade : undefined}
        buttonLabel="Run cascade"
      >
        {classifications.length > 0 && (
          <div>
            <CascadeDiagram records={classifications} activeStage="all" />

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 16 }}>
              <MetricCard label="Total Records" value={classifications.length} color="var(--text-primary)" />
              <MetricCard label="Nano" value={nano.length} color="var(--rh-blue)" detail={`${new Set(nano.map(c => c.agent_name)).size} agents`} />
              <MetricCard label="Micro" value={micro.length} color="var(--rh-green)" detail={`${new Set(micro.map(c => c.agent_name)).size} agents`} />
              <MetricCard label="Macro" value={macro.length} color="var(--rh-purple)" detail={`${new Set(macro.map(c => c.agent_name)).size} agents`} />
            </div>

            {highConf.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 8, fontWeight: 600 }}>Key findings:</div>
                {highConf.slice(0, 5).map(c => (
                  <motion.div key={c.classification_id}
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12,
                      padding: '8px 12px', background: 'var(--surface-2)', borderRadius: 6,
                      marginBottom: 4, fontSize: 12,
                    }}
                  >
                    <span style={{
                      padding: '2px 6px', borderRadius: 4, fontSize: 10, fontWeight: 700,
                      background: c.severity === 'critical' ? 'var(--rh-red-dim)' : 'var(--rh-orange-dim)',
                      color: c.severity === 'critical' ? 'var(--rh-red)' : 'var(--rh-orange)',
                    }}>{c.severity}</span>
                    <span style={{ color: 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace' }}>
                      {c.agent_name}
                    </span>
                    <span style={{ color: 'var(--text-dim)' }}>{c.taxonomy}/{c.class_name}</span>
                    <span style={{ marginLeft: 'auto', color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
                      {(c.confidence * 100).toFixed(0)}%
                    </span>
                  </motion.div>
                ))}
              </div>
            )}
            <JsonViewer label="Full classification records" data={classifications} />
          </div>
        )}
      </StepCard>
    </div>
  );
}


function TheReward({ loopResult, status, onLoop, evidence, baseline, classifications, onIngest, onBuild, onCascade, ingestStatus, baselineStatus, cascadeStatus }: {
  loopResult: LoopResult | null; status: string; onLoop: () => void;
  evidence: EvidenceArtifact[]; baseline: BaselineProfile | null; classifications: ClassificationRecord[];
  onIngest: () => void; onBuild: () => void; onCascade: () => void;
  ingestStatus: string; baselineStatus: string; cascadeStatus: string;
}) {
  return (
    <div>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15 }}>
        The ordeal is survived. The truth is known. Now the hero claims the
        reward: <strong>a safe, governed action</strong>. DeepField does not act
        recklessly — it proposes, requires human approval, and never executes
        destructive operations automatically.
      </p>

      {evidence.length === 0 && (
        <StepCard num={1} title="Ingest evidence first" status={ingestStatus as 'idle' | 'running' | 'done'} onRun={onIngest} buttonLabel="Ingest" />
      )}
      {evidence.length > 0 && !baseline && (
        <StepCard num={2} title="Build baseline first" status={baselineStatus as 'idle' | 'running' | 'done'} onRun={onBuild} buttonLabel="Build baseline" />
      )}

      <StepCard num={4} title="Run Full Agent Loop" status={status as 'idle' | 'running' | 'done'}
        onRun={baseline ? onLoop : undefined}
        buttonLabel="Decide → Act → Verify → Learn"
      >
        {loopResult && (
          <div>
            {/* Actions */}
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>Actions Proposed</div>
            {loopResult.actions.map(a => (
              <motion.div key={a.action_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 14px', background: 'var(--surface-2)',
                  border: '1px solid var(--border)', borderRadius: 8, marginBottom: 8,
                }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--rh-blue)' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{a.action_type}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                    Status: {a.status} · {a.requires_human_approval ? 'Requires human approval' : 'Auto-approved'}
                  </div>
                </div>
                <span style={{
                  padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700,
                  background: 'var(--rh-green-dim)', color: 'var(--rh-green)',
                }}>SAFE</span>
              </motion.div>
            ))}

            {/* Verifications */}
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginTop: 16, marginBottom: 8 }}>Verification Checks</div>
            {loopResult.verifications.map(v => (
              <div key={v.verification_id} style={{
                padding: '8px 14px', background: 'var(--surface-2)',
                border: '1px solid var(--border)', borderRadius: 8, marginBottom: 8, fontSize: 12,
              }}>
                <span style={{ fontWeight: 600 }}>{v.verification_type}</span>
                <span style={{ color: 'var(--text-dim)', marginLeft: 8 }}>Status: {v.status}</span>
              </div>
            ))}

            <JsonViewer label="Full loop result" data={loopResult} />
          </div>
        )}
      </StepCard>
    </div>
  );
}


function TheReturn({ loopResult, apiCalls }: {
  loopResult: LoopResult | null; apiCalls: ApiCall<unknown>[];
}) {
  const proposals = loopResult?.learning_proposals || [];
  const totalCalls = apiCalls.length;
  const avgLatency = totalCalls > 0 ? Math.round(apiCalls.reduce((s, c) => s + c.elapsed, 0) / totalCalls) : 0;

  return (
    <div>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: 15 }}>
        The hero returns transformed. DeepField captures what was learned —
        not as silent changes, but as <strong>proposals</strong> that require
        human review. Thresholds to tighten. Patterns to remember. A system
        that grows wiser with every incident.
      </p>

      {proposals.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12 }}>Learning Proposals</div>
          {proposals.map(p => (
            <motion.div key={p.proposal_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              style={{
                padding: '14px 16px', background: 'var(--surface-1)',
                border: '1px solid var(--border)', borderRadius: 10, marginBottom: 8,
              }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{
                  padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700,
                  background: 'var(--rh-purple-dim)', color: 'var(--rh-purple)',
                }}>{p.proposal_type}</span>
                <span style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'Red Hat Mono, monospace' }}>
                  {(p.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>{p.rationale}</p>
            </motion.div>
          ))}
        </div>
      )}

      {/* Journey summary */}
      <div style={{ marginTop: 32 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12 }}>The Journey</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
          {[
            { icon: '📡', label: 'Signals', value: loopResult ? `${loopResult.classifications.length}` : '—' },
            { icon: '🧠', label: 'Decide', value: loopResult ? `${new Set(loopResult.classifications.map(c => c.agent_tier)).size} tiers` : '—' },
            { icon: '⚡', label: 'Act', value: loopResult ? `${loopResult.actions.length} safe` : '—' },
            { icon: '✓', label: 'Verify', value: loopResult ? `${loopResult.verifications.length} checks` : '—' },
            { icon: '📚', label: 'Learn', value: loopResult ? `${loopResult.learning_proposals.length} proposals` : '—' },
          ].map(s => (
            <motion.div key={s.label}
              initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              style={{
                textAlign: 'center', padding: 12, background: 'var(--surface-1)',
                border: '1px solid var(--border)', borderRadius: 10,
              }}>
              <div style={{ fontSize: 24 }}>{s.icon}</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>{s.label}</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>{s.value}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* API performance */}
      {totalCalls > 0 && (
        <div style={{ marginTop: 24, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <MetricCard label="API calls made" value={totalCalls} color="var(--rh-blue)" />
          <MetricCard label="Avg latency" value={`${avgLatency}ms`} color="var(--rh-teal)" />
        </div>
      )}

      {/* Closing */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
        style={{
          marginTop: 32, padding: 20, background: 'var(--surface-1)',
          border: '1px solid var(--rh-red)40', borderRadius: 10, textAlign: 'center',
        }}>
        <p style={{ fontSize: 15, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.8 }}>
          DeepField studied past enterprise signals, learned the shape of normal,
          classified new multimodal evidence, proposed safe action, verified the
          result, and captured what should be learned next.
        </p>
        <p style={{ fontSize: 13, color: 'var(--rh-red)', marginTop: 12, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif' }}>
          The hero returns. The cycle begins again.
        </p>
      </motion.div>
    </div>
  );
}
