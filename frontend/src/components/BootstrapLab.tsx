import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { RubricMatrix } from './RubricMatrix';
import { FlowDescription } from './FlowDescription';
import { StepCard } from './StepCard';

interface Profile {
  id: string;
  name: string;
  domain: string;
  description: string;
}

interface Scenario {
  id: string;
  name: string;
  domain: string;
  description: string;
  signal_count: number;
  modalities: string[];
  profile?: string;
}

async function post(path: string, body?: unknown) {
  const res = await fetch(path, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

async function get(path: string) {
  const res = await fetch(path);
  return res.json();
}

export function BootstrapLab({ onExit }: { onExit: () => void }) {
  const [step, setStep] = useState(0);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null);
  const [connectType, setConnectType] = useState('scenario');

  const [connectStatus, setConnectStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [analyzeStatus, setAnalyzeStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [validateStatus, setValidateStatus] = useState<'idle' | 'running' | 'done'>('idle');

  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null);
  const [rubric, setRubric] = useState<Record<string, unknown> | null>(null);
  const [sourceConfig, setSourceConfig] = useState('');
  const [sourceType, setSourceType] = useState('file');
  const [hints, setHints] = useState('');
  const [error, setError] = useState('');

  const loadScenarios = useCallback(async () => {
    const data = await get('/api/v1/bootstrap/scenarios');
    setScenarios(data.scenarios || []);
  }, []);

  const loadScenario = useCallback(async (scenarioId: string) => {
    setConnectStatus('running');
    setError('');
    const data = await post(`/api/v1/bootstrap/scenarios/${scenarioId}/load`);
    if (data.status === 'scenario_loaded') {
      setConnectStatus('done');
      if (data.suggested_profile) {
        await post(`/api/v1/bootstrap/profiles/${data.suggested_profile}/apply`);
        const analysisData = await get('/api/v1/bootstrap/status');
        setAnalysis(analysisData.analysis || null);
        setAnalyzeStatus('done');
        setStep(2);
      } else {
        setStep(1);
      }
    } else {
      setError('Failed to load scenario');
      setConnectStatus('idle');
    }
  }, []);

  const loadProfiles = useCallback(async () => {
    const data = await get('/api/v1/bootstrap/profiles');
    setProfiles(data.profiles || []);
  }, []);

  const applyProfile = useCallback(async (profileId: string) => {
    setConnectStatus('running');
    setError('');
    const data = await post(`/api/v1/bootstrap/profiles/${profileId}/apply`);
    setAnalysis(data.analysis || null);
    setConnectStatus('done');
    setAnalyzeStatus('done');
    setStep(2);
  }, []);

  const connectSource = useCallback(async () => {
    setConnectStatus('running');
    setError('');
    try {
      const config = sourceType === 'file' ? { path: sourceConfig } : { endpoint: sourceConfig };
      await post('/api/v1/bootstrap/connect', { source_type: sourceType, config });
      setConnectStatus('done');
      setStep(1);
    } catch (e) {
      setError(String(e));
      setConnectStatus('idle');
    }
  }, [sourceType, sourceConfig]);

  const analyzeSource = useCallback(async () => {
    setAnalyzeStatus('running');
    setError('');
    const data = await post('/api/v1/bootstrap/analyze', { hints });
    if (data.status === 'error') {
      setError(data.error || 'Analysis failed');
      setAnalyzeStatus('idle');
    } else {
      setAnalysis(data.analysis || null);
      setAnalyzeStatus('done');
      setStep(2);
    }
  }, [hints]);

  const validate = useCallback(async () => {
    setValidateStatus('running');
    const data = await post('/api/v1/bootstrap/validate');
    setRubric(data);
    setValidateStatus('done');
    setStep(3);
  }, []);

  const promote = useCallback(async (agentId: string) => {
    await post(`/api/v1/bootstrap/promote/${agentId}`);
    const data = await get('/api/v1/bootstrap/rubric');
    setRubric(data);
  }, []);

  const demote = useCallback(async (agentId: string) => {
    await post(`/api/v1/bootstrap/demote/${agentId}`);
    const data = await get('/api/v1/bootstrap/rubric');
    setRubric(data);
  }, []);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 32px', borderBottom: '1px solid var(--border)', background: 'var(--surface-1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <img src="/logos/redhat.svg" alt="Red Hat" style={{ height: 20 }} />
          <span style={{ color: 'var(--text-disabled)', fontSize: 22, fontWeight: 300 }}>&times;</span>
          <img src="/logos/intel.png" alt="Intel" style={{ height: 20 }} />
        </div>
        <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif' }}>
          Bootstrap Lab
        </span>
        <button onClick={onExit} style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-dim)', padding: '4px 12px', borderRadius: 6, fontSize: 12 }}>
          ← Back to Demo
        </button>
      </div>

      {/* Steps indicator */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 24, padding: '16px 0', borderBottom: '1px solid var(--border)' }}>
        {['Configure', 'Analyze', 'Validate', 'Deploy'].map((label, i) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700,
              background: i < step ? 'var(--rh-green)' : i === step ? 'var(--rh-red)' : 'var(--border)',
              color: i <= step ? '#fff' : 'var(--text-disabled)',
            }}>
              {i < step ? '✓' : i + 1}
            </div>
            <span style={{ fontSize: 12, color: i === step ? 'var(--text-primary)' : 'var(--text-disabled)' }}>{label}</span>
          </div>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, maxWidth: 800, margin: '0 auto', padding: '24px', width: '100%' }}>
        <AnimatePresence mode="wait">
          <motion.div key={step} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>

            {/* Step 0: Configure */}
            {step === 0 && (
              <div>
                <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Configure Data Source</h2>
                <p style={{ color: 'var(--text-dim)', marginBottom: 24 }}>Pick a scenario that looks like your environment, or connect your own source.</p>

                <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
                  {[
                    { value: 'scenario', label: 'Pick a Scenario', desc: 'Synthetic data, no URL needed' },
                    { value: 'profile', label: 'Pre-built Profile', desc: 'Rules only, no data' },
                    { value: 'connect', label: 'Connect Source', desc: 'Your Prometheus / K8s' },
                  ].map(opt => (
                    <div key={opt.value}
                      onClick={() => { setConnectType(opt.value); if (opt.value === 'scenario') loadScenarios(); if (opt.value === 'profile') loadProfiles(); }}
                      style={{
                        flex: 1, padding: 16, borderRadius: 8, cursor: 'pointer', textAlign: 'center',
                        background: connectType === opt.value ? 'var(--rh-red)15' : 'var(--surface-2)',
                        border: `2px solid ${connectType === opt.value ? 'var(--rh-red)' : 'var(--border)'}`,
                      }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: connectType === opt.value ? 'var(--rh-red)' : 'var(--text-secondary)' }}>{opt.label}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>{opt.desc}</div>
                    </div>
                  ))}
                </div>

                {connectType === 'scenario' && (
                  <div>
                    <FlowDescription text="Each scenario contains realistic synthetic data for a specific domain. The system will load the data, analyze it, and build classification agents — just like it would with your real signals." alwaysOpen />
                    {scenarios.length === 0 && (
                      <button onClick={loadScenarios} style={{ background: 'var(--rh-blue)', border: 'none', color: '#fff', padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                        Load Scenarios
                      </button>
                    )}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
                      {scenarios.map(s => (
                        <div key={s.id}
                          onClick={() => loadScenario(s.id)}
                          style={{
                            padding: 14, borderRadius: 8, cursor: 'pointer',
                            background: 'var(--surface-2)', border: '1px solid var(--border)',
                          }}>
                          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{s.name}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>{s.description}</div>
                          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                            <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, background: 'var(--rh-blue-dim)', color: 'var(--rh-blue)' }}>{s.domain}</span>
                            <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, background: 'var(--surface-1)', color: 'var(--text-dim)' }}>{s.signal_count} signals</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {connectType === 'profile' && (
                  <div>
                    <FlowDescription text="Pre-built profiles ship with the engine. No data leaves the cluster. No LLM needed. Select a profile that matches your environment." alwaysOpen />
                    {profiles.length === 0 && (
                      <button onClick={loadProfiles} style={{ background: 'var(--rh-blue)', border: 'none', color: '#fff', padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                        Load Profiles
                      </button>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
                      {profiles.map(p => (
                        <div key={p.id}
                          onClick={() => { setSelectedProfile(p.id); applyProfile(p.id); }}
                          style={{
                            padding: 14, borderRadius: 8, cursor: 'pointer',
                            background: selectedProfile === p.id ? 'var(--rh-green)15' : 'var(--surface-2)',
                            border: `1px solid ${selectedProfile === p.id ? 'var(--rh-green)' : 'var(--border)'}`,
                          }}>
                          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{p.name}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>{p.description}</div>
                          <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, background: 'var(--rh-blue-dim)', color: 'var(--rh-blue)', marginTop: 6, display: 'inline-block' }}>{p.domain}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {connectType === 'connect' && (
                  <div>
                    <FlowDescription text="Connect to a live data source. The system will sample your data and use a frontier model (Qwen 235B or Claude) to analyze it and generate a classification config." alwaysOpen />
                    <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                      {['file', 'prometheus', 'kubernetes'].map(t => (
                        <button key={t} onClick={() => setSourceType(t)}
                          style={{
                            padding: '6px 14px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                            background: sourceType === t ? 'var(--rh-blue)' : 'var(--surface-2)',
                            border: `1px solid ${sourceType === t ? 'var(--rh-blue)' : 'var(--border)'}`,
                            color: sourceType === t ? '#fff' : 'var(--text-dim)',
                          }}>
                          {t}
                        </button>
                      ))}
                    </div>
                    <input
                      value={sourceConfig}
                      onChange={e => setSourceConfig(e.target.value)}
                      placeholder={sourceType === 'file' ? '/path/to/data.csv' : 'https://prometheus:9090'}
                      style={{ width: '100%', padding: '10px 14px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text-primary)', fontSize: 13, fontFamily: 'Red Hat Mono, monospace' }}
                    />
                    <button onClick={connectSource} disabled={!sourceConfig || connectStatus === 'running'}
                      style={{ marginTop: 12, background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', opacity: connectStatus === 'running' ? 0.5 : 1 }}>
                      {connectStatus === 'running' ? 'Connecting...' : 'Connect & Sample'}
                    </button>
                  </div>
                )}

                {error && <div style={{ marginTop: 12, padding: 10, background: 'var(--rh-red-dim)', borderRadius: 6, fontSize: 12, color: 'var(--rh-red)' }}>{error}</div>}
              </div>
            )}

            {/* Step 1: Analyze */}
            {step === 1 && (
              <div>
                <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Analyze Data</h2>
                <p style={{ color: 'var(--text-dim)', marginBottom: 16 }}>The system will analyze your data samples and propose a classification config.</p>
                <FlowDescription text="A frontier model (Qwen 235B or Claude Sonnet) examines your data samples and determines: what domain it belongs to, what features to track, what thresholds to set, and what nano rules to create. This is the one-time GPU call." alwaysOpen />
                <input
                  value={hints}
                  onChange={e => setHints(e.target.value)}
                  placeholder="Optional: describe your data (e.g., 'vibration sensors from factory bearings')"
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text-primary)', fontSize: 13, marginBottom: 12 }}
                />
                <button onClick={analyzeSource} disabled={analyzeStatus === 'running'}
                  style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', opacity: analyzeStatus === 'running' ? 0.5 : 1 }}>
                  {analyzeStatus === 'running' ? 'Analyzing with frontier model...' : 'Analyze'}
                </button>
                {error && <div style={{ marginTop: 12, padding: 10, background: 'var(--rh-red-dim)', borderRadius: 6, fontSize: 12, color: 'var(--rh-red)' }}>{error}</div>}
              </div>
            )}

            {/* Step 2: Validate */}
            {step === 2 && (
              <div>
                <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Validate Agents</h2>
                <p style={{ color: 'var(--text-dim)', marginBottom: 16 }}>Run the proposed agents against your data. Agents earn their tier through empirical validation.</p>

                {analysis && (
                  <div style={{ padding: 14, background: 'var(--surface-2)', borderRadius: 8, marginBottom: 16, fontSize: 12 }}>
                    <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                      <span><strong>Domain:</strong> {String(analysis.domain)}</span>
                      <span><strong>Modality:</strong> {String(analysis.modality)}</span>
                      <span><strong>Confidence:</strong> {String(Number(analysis.confidence || 0) * 100)}%</span>
                    </div>
                    <div style={{ color: 'var(--text-dim)' }}>{String(analysis.domain_description || '')}</div>
                  </div>
                )}

                <FlowDescription text="Agents start as drafts. The validation engine runs each agent against your sampled data and scores accuracy, false positive rate, and coverage against baseline-derived ground truth. Agents that pass the rubric thresholds get promoted." alwaysOpen />

                <button onClick={validate} disabled={validateStatus === 'running'}
                  style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', opacity: validateStatus === 'running' ? 0.5 : 1 }}>
                  {validateStatus === 'running' ? 'Validating...' : 'Run Validation'}
                </button>

                {rubric && (
                  <div style={{ marginTop: 16 }}>
                    <RubricMatrix matrix={rubric as any} onPromote={promote} onDemote={demote} />
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Deploy */}
            {step === 3 && (
              <div>
                <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Deploy</h2>
                <p style={{ color: 'var(--text-dim)', marginBottom: 16 }}>Only promoted agents (green) run in the active pipeline. Draft and candidate agents are excluded.</p>

                {rubric && <RubricMatrix matrix={rubric as any} onPromote={promote} onDemote={demote} />}

                <div style={{ marginTop: 20, textAlign: 'center' }}>
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
                    style={{ padding: 20, background: 'var(--surface-1)', border: '1px solid var(--rh-green)40', borderRadius: 10 }}>
                    <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--rh-green)', margin: 0 }}>
                      Pipeline Active
                    </p>
                    <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 8 }}>
                      {(rubric as any)?.green || 0} promoted agents running. Deterministic on CPU. Evidence-based promotion. Human approval gates.
                    </p>
                  </motion.div>
                </div>

                {/* What just happened + next steps */}
                <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
                  style={{ marginTop: 24 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>What you just did</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 20 }}>
                    <div style={{ padding: 12, background: 'var(--surface-1)', borderRadius: 8, textAlign: 'center', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--rh-blue)' }}>1</div>
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>Connected data</div>
                    </div>
                    <div style={{ padding: 12, background: 'var(--surface-1)', borderRadius: 8, textAlign: 'center', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--rh-teal)' }}>2</div>
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>Agents proposed</div>
                    </div>
                    <div style={{ padding: 12, background: 'var(--surface-1)', borderRadius: 8, textAlign: 'center', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--rh-orange)' }}>3</div>
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>Validated on data</div>
                    </div>
                    <div style={{ padding: 12, background: 'var(--surface-1)', borderRadius: 8, textAlign: 'center', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--rh-green)' }}>4</div>
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>Promoted & deployed</div>
                    </div>
                  </div>

                  <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>What's next</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
                    <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 8, border: '1px solid var(--border)', fontSize: 13, color: 'var(--text-secondary)' }}>
                      <strong style={{ color: 'var(--text-primary)' }}>Try another scenario</strong> — each domain generates different agents with different rules and taxonomies
                    </div>
                    <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 8, border: '1px solid var(--border)', fontSize: 13, color: 'var(--text-secondary)' }}>
                      <strong style={{ color: 'var(--text-primary)' }}>Connect your own Prometheus</strong> — same flow, real signals, 20 minutes to first classification
                    </div>
                    <div style={{ padding: 12, background: 'var(--surface-2)', borderRadius: 8, border: '1px solid var(--border)', fontSize: 13, color: 'var(--text-secondary)' }}>
                      <strong style={{ color: 'var(--text-primary)' }}>Run more validation rounds</strong> — agents accumulate samples and earn higher tiers over time
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                    <button onClick={() => { setStep(0); setAnalysis(null); setRubric(null); setConnectStatus('idle'); setAnalyzeStatus('idle'); setValidateStatus('idle'); }}
                      style={{ background: 'var(--rh-red)', border: 'none', color: '#fff', padding: '10px 24px', borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>
                      Try Another Scenario
                    </button>
                    <button onClick={onExit}
                      style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-dim)', padding: '10px 24px', borderRadius: 8, fontSize: 14, cursor: 'pointer' }}>
                      Back to Demo
                    </button>
                  </div>

                  <div style={{ marginTop: 24, padding: 16, background: 'var(--surface-1)', borderRadius: 10, border: '1px solid var(--rh-red)40', textAlign: 'center' }}>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.7 }}>
                      You just bootstrapped a classification engine in under 5 minutes.
                      <br />No ML training. No GPU. No data scientist.
                    </p>
                    <p style={{ fontSize: 12, color: 'var(--text-disabled)', marginTop: 8, fontFamily: 'Red Hat Mono, monospace' }}>
                      ~210 MB · Intel Xeon 6 · Red Hat OpenShift · Agents earn their tier
                    </p>
                  </div>
                </motion.div>
              </div>
            )}

          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
