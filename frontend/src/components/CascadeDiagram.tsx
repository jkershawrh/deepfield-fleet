import { motion, AnimatePresence } from 'motion/react';
import type { ClassificationRecord } from '../api/client';

interface Props {
  records: ClassificationRecord[];
  activeStage?: 'nano' | 'micro' | 'macro' | 'all' | null;
}

const TIER_META: Record<string, { color: string; label: string; y: number }> = {
  nano:  { color: '#0066cc', label: 'Nanoagents', y: 40 },
  micro: { color: '#63993d', label: 'Microagents', y: 140 },
  macro: { color: '#5e40be', label: 'Macroagents', y: 240 },
};

const SEV_COLORS: Record<string, string> = {
  critical: '#ee0000', high: '#f0561d', medium: '#ffcc17', low: '#0066cc', info: '#707070',
};

export function CascadeDiagram({ records, activeStage }: Props) {
  return (
    <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, padding: 20, marginBottom: 16 }}>
      <svg viewBox="0 0 700 310" style={{ width: '100%', height: 'auto' }}>
        {/* Flow arrows */}
        <motion.line x1="350" y1="70" x2="350" y2="120" stroke="var(--border)" strokeWidth="2" strokeDasharray="4 4"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.5, duration: 0.5 }} />
        <motion.line x1="350" y1="170" x2="350" y2="220" stroke="var(--border)" strokeWidth="2" strokeDasharray="4 4"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 1.0, duration: 0.5 }} />

        {Object.entries(TIER_META).map(([tier, meta]) => {
          const tierRecords = records.filter(r => r.agent_tier === tier);
          const isActive = activeStage === tier || activeStage === 'all';
          const isVisible = isActive || tierRecords.length > 0;

          return (
            <g key={tier}>
              {/* Tier box */}
              <motion.rect
                x="60" y={meta.y} width="580" height="60" rx="8"
                fill={isVisible ? meta.color + '15' : 'var(--surface-2)'}
                stroke={isActive ? meta.color : 'var(--border)'}
                strokeWidth={isActive ? 2 : 1}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                transition={{ delay: tier === 'nano' ? 0.2 : tier === 'micro' ? 0.7 : 1.2 }}
              />
              <motion.text
                x="80" y={meta.y + 20} fill={meta.color} fontSize="12" fontWeight="700"
                fontFamily="Red Hat Display, sans-serif"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                transition={{ delay: tier === 'nano' ? 0.3 : tier === 'micro' ? 0.8 : 1.3 }}
              >
                {meta.label} ({tierRecords.length})
              </motion.text>

              {/* Agent pills */}
              <AnimatePresence>
                {tierRecords.slice(0, 6).map((r, i) => {
                  const agents = [...new Set(tierRecords.map(r => r.agent_name))];
                  const agent = agents[i];
                  if (!agent || i >= agents.length) return null;
                  const agentRecords = tierRecords.filter(r => r.agent_name === agent);
                  const topSev = agentRecords.reduce((s, r) => {
                    const rank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };
                    return (rank[r.severity] || 0) > (rank[s] || 0) ? r.severity : s;
                  }, 'info');

                  return (
                    <motion.g key={agent}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + i * 0.08 }}
                    >
                      <rect
                        x={80 + i * 90} y={meta.y + 30} width={82} height={22} rx="4"
                        fill={SEV_COLORS[topSev] + '25'} stroke={SEV_COLORS[topSev]} strokeWidth="1"
                      />
                      <text
                        x={80 + i * 90 + 41} y={meta.y + 45}
                        textAnchor="middle" fontSize="9" fill="var(--text-secondary)"
                        fontFamily="Red Hat Mono, monospace"
                      >
                        {agent.length > 12 ? agent.slice(0, 11) + '…' : agent}
                      </text>
                    </motion.g>
                  );
                })}
              </AnimatePresence>
            </g>
          );
        })}

        {/* Escalation pulse */}
        {activeStage && activeStage !== 'all' && (
          <motion.circle
            r="4" fill={TIER_META[activeStage]?.color || '#fff'}
            animate={{ cy: [TIER_META[activeStage]?.y || 40, (TIER_META[activeStage]?.y || 40) + 30], opacity: [1, 0.3] }}
            transition={{ repeat: Infinity, duration: 1 }}
            cx="350"
          />
        )}
      </svg>
    </div>
  );
}
