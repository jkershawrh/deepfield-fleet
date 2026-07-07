import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { motion, AnimatePresence } from 'motion/react';

const SEV_COLORS: Record<string, string> = {
  critical: '#ee0000', high: '#f0561d', medium: '#ffcc17', low: '#0066cc', info: '#707070',
};

interface AgentTierData {
  label: string;
  color: string;
  tier: string;
  agents: Array<{ name: string; severity: string; count: number }>;
  recordCount: number;
  isActive: boolean;
  onAgentClick?: (agentName: string, tier: string) => void;
}

function AgentTierNodeInner({ data }: NodeProps & { data: AgentTierData }) {
  const { label, color, agents, recordCount, isActive, onAgentClick } = data;

  return (
    <div style={{
      background: isActive ? color + '15' : 'var(--surface-2)',
      border: `${isActive ? 2 : 1}px solid ${isActive ? color : 'var(--border)'}`,
      borderRadius: 10,
      padding: '12px 16px',
      minWidth: 520,
      transition: 'border-color 0.3s, background 0.3s',
    }}>
      <Handle type="target" position={Position.Top} style={{ background: color, width: 8, height: 8, border: 'none' }} />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: agents.length > 0 ? 10 : 0 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color, fontFamily: 'Red Hat Display, sans-serif' }}>
          {label}
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
          {recordCount} records
        </span>
      </div>

      <AnimatePresence>
        {agents.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {agents.slice(0, 7).map((agent, i) => (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.06, type: 'spring', stiffness: 400, damping: 25 }}
                onClick={(e) => { e.stopPropagation(); onAgentClick?.(agent.name, data.tier); }}
                style={{
                  padding: '3px 10px',
                  borderRadius: 5,
                  fontSize: 10,
                  fontFamily: 'Red Hat Mono, monospace',
                  background: (SEV_COLORS[agent.severity] || '#707070') + '20',
                  border: `1px solid ${SEV_COLORS[agent.severity] || '#707070'}50`,
                  color: 'var(--text-secondary)',
                  cursor: onAgentClick ? 'pointer' : 'default',
                }}
              >
                {agent.name.length > 14 ? agent.name.slice(0, 13) + '…' : agent.name}
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>

      <Handle type="source" position={Position.Bottom} style={{ background: color, width: 8, height: 8, border: 'none' }} />
    </div>
  );
}

export const AgentTierNode = memo(AgentTierNodeInner);
