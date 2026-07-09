import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { MetricCard } from './MetricCard';
import { CostComparison } from './CostComparison';
import { LedgerChainView } from './LedgerChainView';
import { TestMatrixCompact } from './TestMatrixCompact';
import { Header } from './Header';
import { api } from '../api/client';
import { useDemoStore } from '../stores/useDemoStore';
import type { FleetHealthResponse, LedgerChainResponse } from '../api/client';

interface FleetDashboardProps {
  onExit: () => void;
}

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview' },
  { id: 'clusters', label: 'Clusters' },
  { id: 'models', label: 'Models' },
  { id: 'tenants', label: 'Tenants' },
  { id: 'rollouts', label: 'Rollouts' },
  { id: 'compliance', label: 'Compliance' },
  { id: 'matrix', label: 'Matrix' },
] as const;

const RECENT_EVENTS = [
  { text: 'PreWarm intent executed', color: 'var(--rh-green)', time: '2m ago' },
  { text: 'SLO forecast: safe', color: 'var(--rh-blue)', time: '5m ago' },
  { text: 'Cluster dev-cluster-1 registered', color: 'var(--rh-teal)', time: '12m ago' },
  { text: 'Canary rollout promoted to 100%', color: 'var(--rh-purple)', time: '18m ago' },
  { text: 'Ledger chain verified: placement', color: 'var(--rh-orange)', time: '24m ago' },
  { text: 'Tenant acme-corp quota updated', color: 'var(--rh-blue)', time: '31m ago' },
];

const MOCK_CLUSTERS = [
  { name: 'dev-cluster-1', region: 'us-east', status: 'healthy', hardware: 'Intel Xeon 6767P', cores: 256, amx: true },
  { name: 'prod-cluster-1', region: 'us-east', status: 'healthy', hardware: 'Intel Xeon 6', cores: 128, amx: true },
];

const MOCK_MODELS = [
  { name: 'granite-3.3-8b-instruct', runtime: 'ovms-cpp', quantization: 'INT8', replicas: 4, status: 'serving' },
  { name: 'granite-3.3-2b-instruct', runtime: 'ovms-cpp', quantization: 'INT8', replicas: 2, status: 'serving' },
  { name: 'granite-3.2-8b-instruct', runtime: 'ovms-cpp', quantization: 'INT8', replicas: 3, status: 'serving' },
  { name: 'granite-3.2-2b-instruct', runtime: 'ovms-cpp', quantization: 'INT8', replicas: 1, status: 'serving' },
  { name: 'granite-guardian-3.2-3b', runtime: 'ovms-cpp', quantization: 'INT8', replicas: 2, status: 'serving' },
];

const MOCK_TENANTS = [
  { name: 'acme-corp', tokensPerMin: 12000, concurrent: 50, budget: 5000, used: 62, status: 'active' },
  { name: 'globex-inc', tokensPerMin: 8000, concurrent: 30, budget: 3000, used: 45, status: 'active' },
  { name: 'initech-labs', tokensPerMin: 20000, concurrent: 100, budget: 10000, used: 78, status: 'warning' },
];

const RUBRIC_SCORES = [
  { label: 'Reliability', score: 92, color: 'var(--rh-green)' },
  { label: 'Performance', score: 84, color: 'var(--rh-blue)' },
  { label: 'Security', score: 95, color: 'var(--rh-teal)' },
  { label: 'Chaos Resilience', score: 74, color: 'var(--rh-orange)' },
  { label: 'Scalability', score: 86, color: 'var(--rh-purple)' },
  { label: 'Compliance', score: 97, color: 'var(--rh-red)' },
];

/* ─── Shared styles ─── */
const tableHeaderStyle: React.CSSProperties = {
  fontSize: 11, fontWeight: 700, color: 'var(--text-disabled)', textAlign: 'left',
  padding: '8px 12px', borderBottom: '1px solid var(--border)',
  fontFamily: 'Red Hat Mono, monospace', letterSpacing: 0.5, textTransform: 'uppercase',
};
const tableCellStyle: React.CSSProperties = {
  fontSize: 13, color: 'var(--text-secondary)', padding: '10px 12px',
  borderBottom: '1px solid var(--border)', fontFamily: 'Red Hat Text, sans-serif',
};

/* ─── Page renderers ─── */

function OverviewPage({ health }: { health: FleetHealthResponse | null }) {
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        <MetricCard label="Clusters" value={health?.clusters?.length ?? 2} color="var(--rh-blue)" />
        <MetricCard label="Models" value={health?.models?.length ?? 5} color="var(--rh-teal)" />
        <MetricCard label="Tests" value="360" color="var(--rh-green)" />
        <MetricCard label="Cost Savings" value="53x" color="var(--rh-red)" />
      </div>
      {health && (
        <div style={{ marginBottom: 24, padding: 14, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-dim)', marginBottom: 8 }}>Fleet Status</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: health.status === 'healthy' ? 'var(--rh-green)' : 'var(--rh-orange)' }} />
            <span style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 600 }}>{health.status}</span>
            <span style={{ fontSize: 12, color: 'var(--text-disabled)', marginLeft: 8 }}>Mode: {health.mode}</span>
          </div>
        </div>
      )}
      <div style={{ marginBottom: 24 }}>
        <CostComparison animate={false} />
      </div>
      <div style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-dim)', marginBottom: 12 }}>Recent Events</div>
        {RECENT_EVENTS.map((ev, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: i < RECENT_EVENTS.length - 1 ? '1px solid var(--border)' : 'none' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: ev.color, flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: 'var(--text-secondary)', flex: 1 }}>{ev.text}</span>
            <span style={{ fontSize: 11, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>{ev.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ClustersPage() {
  return (
    <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {['Name', 'Region', 'Status', 'Hardware', 'CPU Cores', 'AMX'].map(h => (
              <th key={h} style={tableHeaderStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MOCK_CLUSTERS.map(c => (
            <tr key={c.name}>
              <td style={{ ...tableCellStyle, fontFamily: 'Red Hat Mono, monospace', fontWeight: 600 }}>{c.name}</td>
              <td style={tableCellStyle}>{c.region}</td>
              <td style={tableCellStyle}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.status === 'healthy' ? 'var(--rh-green)' : 'var(--rh-orange)' }} />
                  {c.status}
                </span>
              </td>
              <td style={tableCellStyle}>{c.hardware}</td>
              <td style={{ ...tableCellStyle, fontFamily: 'Red Hat Mono, monospace' }}>{c.cores}</td>
              <td style={tableCellStyle}>
                <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, background: 'var(--rh-blue)20', color: 'var(--rh-blue)', fontWeight: 600 }}>
                  {c.amx ? 'Enabled' : 'Disabled'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ModelsPage() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
      {MOCK_MODELS.map(m => (
        <motion.div key={m.name} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          style={{ padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10 }}>
          <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'Red Hat Mono, monospace', color: 'var(--text-primary)', marginBottom: 10 }}>{m.name}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {[
              { label: m.runtime, bg: 'var(--rh-teal)' },
              { label: m.quantization, bg: 'var(--rh-blue)' },
              { label: `${m.replicas} replica${m.replicas > 1 ? 's' : ''}`, bg: 'var(--rh-purple)' },
              { label: m.status, bg: 'var(--rh-green)' },
            ].map(t => (
              <span key={t.label} style={{ padding: '2px 8px', borderRadius: 4, fontSize: 10, background: `${t.bg}20`, color: t.bg, fontWeight: 600, fontFamily: 'Red Hat Mono, monospace' }}>
                {t.label}
              </span>
            ))}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function TenantsPage() {
  return (
    <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {['Tenant', 'Tokens/min', 'Concurrent', 'Budget', 'Used', 'Status'].map(h => (
              <th key={h} style={tableHeaderStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MOCK_TENANTS.map(t => (
            <tr key={t.name}>
              <td style={{ ...tableCellStyle, fontFamily: 'Red Hat Mono, monospace', fontWeight: 600 }}>{t.name}</td>
              <td style={{ ...tableCellStyle, fontFamily: 'Red Hat Mono, monospace' }}>{t.tokensPerMin.toLocaleString()}</td>
              <td style={{ ...tableCellStyle, fontFamily: 'Red Hat Mono, monospace' }}>{t.concurrent}</td>
              <td style={{ ...tableCellStyle, fontFamily: 'Red Hat Mono, monospace' }}>${t.budget.toLocaleString()}</td>
              <td style={{ ...tableCellStyle, width: 160 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--surface-2)', overflow: 'hidden' }}>
                    <div style={{
                      width: `${t.used}%`, height: '100%', borderRadius: 3,
                      background: t.used > 75 ? 'var(--rh-orange)' : 'var(--rh-green)',
                    }} />
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'Red Hat Mono, monospace', minWidth: 32 }}>{t.used}%</span>
                </div>
              </td>
              <td style={tableCellStyle}>
                <span style={{
                  padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                  background: t.status === 'active' ? 'var(--rh-green)20' : 'var(--rh-orange)20',
                  color: t.status === 'active' ? 'var(--rh-green)' : 'var(--rh-orange)',
                }}>
                  {t.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RolloutsPage() {
  const [weight, setWeight] = useState(35);
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      style={{ padding: 24, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif' }}>granite-3.3-8b-instruct</div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>v2.1.0 -&gt; v2.2.0</div>
        </div>
        <span style={{ padding: '4px 12px', borderRadius: 6, fontSize: 11, background: 'var(--rh-purple)20', color: 'var(--rh-purple)', fontWeight: 700, fontFamily: 'Red Hat Mono, monospace' }}>
          CANARY
        </span>
      </div>
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-dim)', marginBottom: 6 }}>
          <span>Traffic weight</span>
          <span style={{ fontFamily: 'Red Hat Mono, monospace', color: 'var(--rh-purple)' }}>{weight}%</span>
        </div>
        <div style={{ height: 8, borderRadius: 4, background: 'var(--surface-2)', overflow: 'hidden' }}>
          <motion.div animate={{ width: `${weight}%` }} transition={{ type: 'spring', stiffness: 80 }}
            style={{ height: '100%', borderRadius: 4, background: 'var(--rh-purple)' }} />
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20, padding: '8px 12px', background: 'var(--surface-2)', borderRadius: 6 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--rh-green)' }} />
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>SLO gate: <strong style={{ color: 'var(--rh-green)' }}>passing</strong></span>
        <span style={{ fontSize: 11, color: 'var(--text-disabled)', marginLeft: 'auto' }}>P95 &lt; 5000ms</span>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={() => setWeight(100)}
          style={{ background: 'var(--rh-green)', border: 'none', color: '#fff', padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
          Promote
        </button>
        <button onClick={() => setWeight(0)}
          style={{ background: 'none', border: '1px solid var(--rh-red)', color: 'var(--rh-red)', padding: '8px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
          Rollback
        </button>
      </div>
    </motion.div>
  );
}

function CompliancePage() {
  const [chains, setChains] = useState<LedgerChainResponse | null>(null);
  const [verifying, setVerifying] = useState(false);

  const doVerify = useCallback(async () => {
    setVerifying(true);
    try {
      const call = await api.fleetVerifyChain();
      setChains(call.response.data);
    } catch { /* use defaults */ }
    setVerifying(false);
  }, []);

  return (
    <div>
      <LedgerChainView chains={chains?.chains} />
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
        <button onClick={doVerify} disabled={verifying}
          style={{
            background: verifying ? 'var(--surface-2)' : 'var(--rh-blue)', border: 'none', color: '#fff',
            padding: '10px 28px', borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: verifying ? 'default' : 'pointer',
          }}>
          {verifying ? 'Verifying...' : 'Verify All Chains'}
        </button>
      </div>
    </div>
  );
}

function MatrixPage() {
  return (
    <div>
      <TestMatrixCompact />
      <div style={{ marginTop: 24, padding: 16, background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-dim)', marginBottom: 16 }}>Rubric Scores</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {RUBRIC_SCORES.map(r => (
            <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 120, flexShrink: 0 }}>{r.label}</span>
              <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--surface-2)', overflow: 'hidden' }}>
                <motion.div initial={{ width: 0 }} animate={{ width: `${r.score}%` }}
                  transition={{ type: 'spring', stiffness: 60, damping: 14 }}
                  style={{ height: '100%', borderRadius: 4, background: r.color }} />
              </div>
              <span style={{ fontSize: 12, fontWeight: 700, color: r.color, fontFamily: 'Red Hat Mono, monospace', minWidth: 28, textAlign: 'right' }}>{r.score}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Main Dashboard ─── */

export function FleetDashboard({ onExit }: FleetDashboardProps) {
  const { dashPage, setDashPage } = useDemoStore();
  const [health, setHealth] = useState<FleetHealthResponse | null>(null);

  useEffect(() => {
    api.fleetHealth()
      .then(call => setHealth(call.response.data))
      .catch(() => { /* offline — use mock data via defaults */ });
  }, []);

  const PAGE_TITLES: Record<string, string> = {
    overview: 'Fleet Overview',
    clusters: 'Cluster Management',
    models: 'Model Inventory',
    tenants: 'Tenant Profiles',
    rollouts: 'Rollout Management',
    compliance: 'ARE Ledger Compliance',
    matrix: 'Test Matrix & Rubric',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar */}
        <nav style={{
          width: 160, flexShrink: 0, background: 'var(--surface-1)', borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '12px 0',
        }}>
          <div>
            {NAV_ITEMS.map(item => {
              const active = dashPage === item.id;
              return (
                <button key={item.id} onClick={() => setDashPage(item.id)}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left', background: 'none',
                    border: 'none', borderLeft: active ? '3px solid var(--rh-red)' : '3px solid transparent',
                    padding: '10px 16px', fontSize: 13, cursor: 'pointer',
                    color: active ? 'var(--text-primary)' : 'var(--text-dim)',
                    fontWeight: active ? 700 : 400,
                    fontFamily: 'Red Hat Text, sans-serif',
                    transition: 'color 0.15s, border-color 0.15s',
                  }}
                  onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = 'var(--text-secondary)'; }}
                  onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = 'var(--text-dim)'; }}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
          <button onClick={onExit}
            style={{
              display: 'block', width: '100%', textAlign: 'left', background: 'none',
              border: 'none', borderTop: '1px solid var(--border)', padding: '12px 16px',
              fontSize: 12, color: 'var(--text-dim)', cursor: 'pointer',
              fontFamily: 'Red Hat Text, sans-serif',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--rh-red)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-dim)'; }}
          >
            &larr; Back to Demo
          </button>
        </nav>

        {/* Content */}
        <main style={{ flex: 1, overflow: 'auto', padding: '28px 32px', background: 'var(--bg-dark)' }}>
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 11, color: 'var(--rh-red)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1.5, marginBottom: 4 }}>
                DASHBOARD
              </div>
              <h2 style={{ fontSize: 24, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif', margin: 0 }}>
                {PAGE_TITLES[dashPage] || 'Fleet Overview'}
              </h2>
            </div>
            <AnimatePresence mode="wait">
              <motion.div key={dashPage} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
                {dashPage === 'overview' && <OverviewPage health={health} />}
                {dashPage === 'clusters' && <ClustersPage />}
                {dashPage === 'models' && <ModelsPage />}
                {dashPage === 'tenants' && <TenantsPage />}
                {dashPage === 'rollouts' && <RolloutsPage />}
                {dashPage === 'compliance' && <CompliancePage />}
                {dashPage === 'matrix' && <MatrixPage />}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>

      {/* Footer */}
      <div style={{
        display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16,
        padding: '10px 32px', borderTop: '1px solid var(--border)', background: 'var(--surface-1)',
        fontSize: 11, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace',
      }}>
        <span>fleet-llm-d</span>
        <span style={{ color: 'var(--border)' }}>|</span>
        <span>Intel Xeon 6</span>
        <span style={{ color: 'var(--border)' }}>|</span>
        <span>Red Hat OpenShift AI</span>
      </div>
    </div>
  );
}

export default FleetDashboard;
