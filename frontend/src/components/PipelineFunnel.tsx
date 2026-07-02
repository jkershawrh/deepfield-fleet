import { motion } from 'motion/react';

interface FunnelData {
  total_evidence?: number;
  nano_processed?: number;
  nano_escalated?: number;
  nano_retained?: number;
  micro_processed?: number;
  micro_escalated?: number;
  macro_processed?: number;
  actions_proposed?: number;
  verifications_created?: number;
  learning_proposals?: number;
}

interface Props {
  funnel: FunnelData;
}

const STAGES = [
  { key: 'total_evidence', label: 'Evidence', color: 'var(--rh-teal)' },
  { key: 'nano_processed', label: 'Nano', color: 'var(--rh-blue)' },
  { key: 'micro_processed', label: 'Micro', color: 'var(--rh-green)' },
  { key: 'macro_processed', label: 'Macro', color: 'var(--rh-purple)' },
  { key: 'actions_proposed', label: 'Actions', color: 'var(--rh-orange)' },
  { key: 'learning_proposals', label: 'Learning', color: 'var(--rh-red)' },
];

export function PipelineFunnel({ funnel }: Props) {
  const max = Math.max(1, ...STAGES.map(s => (funnel as Record<string, number>)[s.key] || 0));

  return (
    <div style={{
      background: 'var(--surface-1)', border: '1px solid var(--border)',
      borderRadius: 10, padding: 16, marginBottom: 12,
    }}>
      <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 12, fontWeight: 600 }}>
        Pipeline Funnel
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {STAGES.map(stage => {
          const value = (funnel as Record<string, number>)[stage.key] || 0;
          const width = (value / max) * 100;
          return (
            <div key={stage.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 70, textAlign: 'right', fontSize: 11, color: 'var(--text-dim)' }}>
                {stage.label}
              </div>
              <div style={{ flex: 1, height: 22, background: 'var(--surface-2)', borderRadius: 4, overflow: 'hidden' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${width}%` }}
                  transition={{ type: 'spring', stiffness: 200, damping: 20 }}
                  style={{
                    height: '100%', background: stage.color, borderRadius: 4,
                    display: 'flex', alignItems: 'center', paddingLeft: 8,
                    fontSize: 11, fontWeight: 700, color: '#fff',
                    fontFamily: 'Red Hat Mono, monospace', minWidth: value > 0 ? 28 : 0,
                  }}
                >
                  {value > 0 ? value : ''}
                </motion.div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
