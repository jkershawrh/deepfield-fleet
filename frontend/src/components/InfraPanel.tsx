import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';

interface AgentInfo {
  name: string;
  type: string;
  runtime: string;
  description: string;
}

interface InfraData {
  runtime: { python_version: string; platform: string; architecture: string; cpu_count: number; hostname: string };
  inference: {
    llm_connected: boolean; api_base: string; model_micro: string; model_macro: string;
    mode: string; nano_tier: string; micro_tier: string; macro_tier: string;
    stats: { total_calls: number; total_tokens_in: number; total_tokens_out: number; avg_latency_ms: number; avg_tokens_per_sec: number; errors: number } | null;
  };
  agents: {
    total: number; tiers: number;
    nano: { count: number; type: string; agents: AgentInfo[] };
    micro: { count: number; type: string; agents: AgentInfo[] };
    macro: { count: number; type: string; agents: AgentInfo[] };
  };
  pipeline: { flow: string; compression: string; safety: string };
  framework: { backend: string; frontend: string; database: string; container: string };
}

const TIER_COLORS: Record<string, string> = {
  nano: 'var(--rh-blue)', micro: 'var(--rh-green)', macro: 'var(--rh-purple)',
};

export function InfraPanel() {
  const [data, setData] = useState<InfraData | null>(null);
  const [open, setOpen] = useState(false);
  const [expandedTier, setExpandedTier] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/v1/demo/infrastructure').then(r => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data) return null;

  return (
    <div style={{ marginBottom: 16 }}>
      <button onClick={() => setOpen(!open)} style={{
        background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 8,
        padding: '10px 16px', width: '100%', cursor: 'pointer', textAlign: 'left',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 14 }}>&#9881;</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Infrastructure</span>
          <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
            {data.agents.total} agents · {data.inference.llm_connected ? `LLM: ${data.inference.model_micro}` : 'Rule-backed (no LLM)'}
          </span>
          {data.inference.llm_connected && (
            <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, background: 'var(--rh-green-dim)', color: 'var(--rh-green)', fontWeight: 700 }}>LIVE</span>
          )}
        </div>
        <span style={{ fontSize: 10, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
          {open ? '▼' : '▶'}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              background: 'var(--surface-1)', border: '1px solid var(--border)', borderTop: 'none',
              borderRadius: '0 0 8px 8px', padding: 16,
            }}>
              {/* Runtime */}
              <Section title="Runtime Environment">
                <Row label="Python" value={data.runtime.python_version} />
                <Row label="Platform" value={data.runtime.platform} />
                <Row label="Architecture" value={data.runtime.architecture} />
                <Row label="CPU Cores" value={String(data.runtime.cpu_count)} />
                <Row label="Host" value={data.runtime.hostname} />
              </Section>

              {/* Inference */}
              <Section title="Inference">
                <Row label="Mode" value={data.inference.mode} color={data.inference.llm_connected ? 'var(--rh-green)' : 'var(--rh-yellow)'} />
                <Row label="API Base" value={data.inference.api_base} />
                <Row label="Nano Tier" value={data.inference.nano_tier} />
                <Row label="Micro Tier" value={data.inference.micro_tier} />
                <Row label="Macro Tier" value={data.inference.macro_tier} />
                {data.inference.stats && data.inference.stats.total_calls > 0 && (
                  <div style={{ marginTop: 8, padding: 8, background: 'var(--surface-2)', borderRadius: 6 }}>
                    <div style={{ fontSize: 10, color: 'var(--text-disabled)', marginBottom: 4, fontWeight: 600 }}>LIVE INFERENCE STATS</div>
                    <Row label="Total Calls" value={String(data.inference.stats.total_calls)} color="var(--rh-blue)" />
                    <Row label="Tokens In" value={String(data.inference.stats.total_tokens_in)} />
                    <Row label="Tokens Out" value={String(data.inference.stats.total_tokens_out)} />
                    <Row label="Avg Latency" value={`${data.inference.stats.avg_latency_ms}ms`} color="var(--rh-orange)" />
                    <Row label="Avg Tok/s" value={String(data.inference.stats.avg_tokens_per_sec)} color="var(--rh-green)" />
                    <Row label="Errors" value={String(data.inference.stats.errors)} color={data.inference.stats.errors > 0 ? 'var(--rh-red)' : 'var(--rh-green)'} />
                  </div>
                )}
              </Section>

              {/* Agent tiers */}
              <Section title={`Agents (${data.agents.total} across ${data.agents.tiers} tiers)`}>
                {(['nano', 'micro', 'macro'] as const).map(tier => {
                  const tierData = data.agents[tier];
                  const isExpanded = expandedTier === tier;
                  return (
                    <div key={tier} style={{ marginBottom: 8 }}>
                      <div
                        onClick={() => setExpandedTier(isExpanded ? null : tier)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          padding: '6px 8px', background: 'var(--surface-2)', borderRadius: 6,
                          cursor: 'pointer',
                        }}
                      >
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: TIER_COLORS[tier] }} />
                        <span style={{ fontSize: 12, fontWeight: 700, color: TIER_COLORS[tier], textTransform: 'uppercase' }}>
                          {tier}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                          {tierData.count} agents · {tierData.type}
                        </span>
                        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
                          {isExpanded ? '▼' : '▶'}
                        </span>
                      </div>
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                          >
                            {tierData.agents.map(a => (
                              <div key={a.name} style={{
                                padding: '6px 8px 6px 24px', borderBottom: '1px solid var(--border)',
                                fontSize: 11,
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                  <span style={{ fontWeight: 700, color: 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace', minWidth: 140 }}>
                                    {a.name}
                                  </span>
                                  <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: TIER_COLORS[tier] + '20', color: TIER_COLORS[tier] }}>
                                    {a.runtime}
                                  </span>
                                </div>
                                <div style={{ color: 'var(--text-dim)', marginTop: 2 }}>{a.description}</div>
                              </div>
                            ))}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </Section>

              {/* Pipeline */}
              <Section title="Pipeline">
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace', padding: '4px 0', wordBreak: 'break-all' }}>
                  {data.pipeline.flow}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>{data.pipeline.compression}</div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>{data.pipeline.safety}</div>
              </Section>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}


function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', fontSize: 12, borderBottom: '1px solid var(--border)' }}>
      <span style={{ color: 'var(--text-dim)' }}>{label}</span>
      <span style={{ color: color || 'var(--text-secondary)', fontFamily: 'Red Hat Mono, monospace' }}>{value}</span>
    </div>
  );
}
