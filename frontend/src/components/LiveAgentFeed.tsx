import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';

interface AgentEvent {
  agent_name: string;
  modality: string;
  class_name: string;
  taxonomy: string;
  severity: string;
  confidence: number;
  tier: string;
  timestamp: string;
}

interface Props {
  events: AgentEvent[];
}

const TIER_COLORS: Record<string, string> = {
  nano: 'var(--rh-blue)', micro: 'var(--rh-green)', macro: 'var(--rh-purple)',
};

const SEV_COLORS: Record<string, string> = {
  critical: 'var(--rh-red)', high: 'var(--rh-orange)',
  medium: 'var(--rh-yellow)', low: 'var(--rh-blue)', info: 'var(--text-disabled)',
};

export function LiveAgentFeed({ events }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  return (
    <div style={{
      background: 'var(--surface-1)', border: '1px solid var(--border)',
      borderRadius: 10, padding: 16, marginBottom: 12,
    }}>
      <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 8, fontWeight: 600 }}>
        Agent Activity ({events.length} events)
      </div>
      <div ref={scrollRef} style={{ maxHeight: 240, overflowY: 'auto' }}>
        <AnimatePresence>
          {events.map((e, i) => (
            <motion.div
              key={`${e.agent_name}-${e.timestamp}-${i}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ type: 'spring', stiffness: 500, damping: 25 }}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '5px 8px', borderBottom: '1px solid var(--border)',
                fontSize: 11,
              }}
            >
              <span style={{
                padding: '1px 5px', borderRadius: 3, fontSize: 9, fontWeight: 700,
                background: (TIER_COLORS[e.tier] || 'var(--border)') + '25',
                color: TIER_COLORS[e.tier] || 'var(--text-dim)',
                fontFamily: 'Red Hat Mono, monospace', textTransform: 'uppercase',
              }}>{e.tier}</span>
              <span style={{ color: 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace', minWidth: 120 }}>
                {e.agent_name}
              </span>
              <span style={{ color: 'var(--text-dim)' }}>
                {e.taxonomy}/{e.class_name}
              </span>
              <span style={{
                marginLeft: 'auto', padding: '1px 4px', borderRadius: 3, fontSize: 9,
                background: (SEV_COLORS[e.severity] || 'var(--border)') + '20',
                color: SEV_COLORS[e.severity] || 'var(--text-dim)',
              }}>{e.severity}</span>
              <span style={{ color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace', fontSize: 10 }}>
                {(e.confidence * 100).toFixed(0)}%
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
        {events.length === 0 && (
          <div style={{ color: 'var(--text-disabled)', fontSize: 11, padding: 8 }}>
            Waiting for agent activity...
          </div>
        )}
      </div>
    </div>
  );
}
