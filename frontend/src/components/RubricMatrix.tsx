import { motion } from 'motion/react';

interface AgentRow {
  agent_id: string;
  name: string;
  tier: string;
  rubric_status: string;
  samples_tested: number;
  accuracy: number;
  false_positive_rate: number;
  coverage: number;
  confidence_calibration: string;
  human_reviewed: boolean;
}

interface Props {
  matrix: {
    overall: string;
    total_agents: number;
    green: number;
    yellow: number;
    red: number;
    agents: AgentRow[];
  };
  onPromote?: (agentId: string) => void;
  onDemote?: (agentId: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  green: 'var(--rh-green)', yellow: 'var(--rh-yellow)', red: 'var(--rh-red)',
};

const TIER_COLORS: Record<string, string> = {
  draft: 'var(--text-disabled)', candidate: 'var(--rh-yellow)',
  nano: 'var(--rh-blue)', micro: 'var(--rh-green)', macro: 'var(--rh-purple)',
};

export function RubricMatrix({ matrix, onPromote, onDemote }: Props) {
  return (
    <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, padding: 16 }}>
      {/* Overall health */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 12, height: 12, borderRadius: '50%', background: STATUS_COLORS[matrix.overall] || 'var(--border)' }} />
          <span style={{ fontSize: 14, fontWeight: 700 }}>Agent Maturity</span>
        </div>
        <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-dim)' }}>
          <span><span style={{ color: 'var(--rh-green)' }}>{matrix.green}</span> promoted</span>
          <span><span style={{ color: 'var(--rh-yellow)' }}>{matrix.yellow}</span> candidate</span>
          <span><span style={{ color: 'var(--rh-red)' }}>{matrix.red}</span> draft</span>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 16, background: 'var(--surface-2)' }}>
        {matrix.green > 0 && (
          <motion.div initial={{ width: 0 }} animate={{ width: `${(matrix.green / matrix.total_agents) * 100}%` }}
            style={{ background: 'var(--rh-green)', height: '100%' }} />
        )}
        {matrix.yellow > 0 && (
          <motion.div initial={{ width: 0 }} animate={{ width: `${(matrix.yellow / matrix.total_agents) * 100}%` }}
            style={{ background: 'var(--rh-yellow)', height: '100%' }} />
        )}
        {matrix.red > 0 && (
          <motion.div initial={{ width: 0 }} animate={{ width: `${(matrix.red / matrix.total_agents) * 100}%` }}
            style={{ background: 'var(--rh-red)', height: '100%' }} />
        )}
      </div>

      {/* Header */}
      <div style={{ display: 'grid', gridTemplateColumns: '140px 70px 60px 60px 60px 60px 1fr', gap: 4, padding: '6px 8px', fontSize: 10, color: 'var(--text-disabled)', fontWeight: 600, borderBottom: '1px solid var(--border)' }}>
        <span>AGENT</span>
        <span>TIER</span>
        <span style={{ textAlign: 'right' }}>SAMPLES</span>
        <span style={{ textAlign: 'right' }}>ACCURACY</span>
        <span style={{ textAlign: 'right' }}>FP RATE</span>
        <span style={{ textAlign: 'right' }}>COVERAGE</span>
        <span style={{ textAlign: 'right' }}>STATUS</span>
      </div>

      {/* Rows */}
      {matrix.agents.map(a => (
        <motion.div key={a.agent_id}
          initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
          style={{
            display: 'grid', gridTemplateColumns: '140px 70px 60px 60px 60px 60px 1fr',
            gap: 4, padding: '8px 8px', fontSize: 12, borderBottom: '1px solid var(--border)',
            alignItems: 'center',
          }}>
          <span style={{ fontFamily: 'Red Hat Mono, monospace', color: 'var(--text-secondary)', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {a.name}
          </span>
          <span style={{ padding: '1px 6px', borderRadius: 3, fontSize: 9, fontWeight: 700, background: (TIER_COLORS[a.tier] || 'var(--border)') + '20', color: TIER_COLORS[a.tier], textTransform: 'uppercase', textAlign: 'center' }}>
            {a.tier}
          </span>
          <span style={{ textAlign: 'right', color: 'var(--text-dim)', fontFamily: 'Red Hat Mono, monospace', fontSize: 11 }}>
            {a.samples_tested}
          </span>
          <span style={{ textAlign: 'right', fontFamily: 'Red Hat Mono, monospace', fontSize: 11, color: a.accuracy >= 0.75 ? 'var(--rh-green)' : a.accuracy >= 0.6 ? 'var(--rh-yellow)' : 'var(--rh-red)' }}>
            {(a.accuracy * 100).toFixed(0)}%
          </span>
          <span style={{ textAlign: 'right', fontFamily: 'Red Hat Mono, monospace', fontSize: 11, color: a.false_positive_rate <= 0.1 ? 'var(--rh-green)' : a.false_positive_rate <= 0.2 ? 'var(--rh-yellow)' : 'var(--rh-red)' }}>
            {(a.false_positive_rate * 100).toFixed(0)}%
          </span>
          <span style={{ textAlign: 'right', fontFamily: 'Red Hat Mono, monospace', fontSize: 11, color: 'var(--text-dim)' }}>
            {(a.coverage * 100).toFixed(0)}%
          </span>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS[a.rubric_status] || 'var(--border)' }} />
            {a.tier === 'candidate' && onPromote && (
              <button onClick={() => onPromote(a.agent_id)}
                style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, border: 'none', background: 'var(--rh-green)', color: '#fff', cursor: 'pointer' }}>
                Promote
              </button>
            )}
            {(a.tier === 'nano' || a.tier === 'micro') && onDemote && (
              <button onClick={() => onDemote(a.agent_id)}
                style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, border: '1px solid var(--border)', background: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
                Demote
              </button>
            )}
          </div>
        </motion.div>
      ))}

      {matrix.agents.length === 0 && (
        <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-disabled)', fontSize: 12 }}>
          No agents registered. Connect a data source or apply a profile to create agents.
        </div>
      )}
    </div>
  );
}
