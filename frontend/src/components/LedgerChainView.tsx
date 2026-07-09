import { motion } from 'motion/react';

interface ChainData {
  type: string;
  valid: boolean;
  entries: number;
  latestHash?: string;
}

interface LedgerChainViewProps {
  chains?: ChainData[];
}

const DEFAULT_CHAINS: ChainData[] = [
  { type: 'placement', valid: true, entries: 847, latestHash: 'a3f8c2d1' },
  { type: 'scaling', valid: true, entries: 1203, latestHash: '7b2e9f4a' },
  { type: 'routing', valid: true, entries: 562, latestHash: 'd4c1a8e3' },
  { type: 'lifecycle', valid: true, entries: 234, latestHash: 'f9e2b7c6' },
  { type: 'tenant', valid: true, entries: 189, latestHash: '2a7d5e8b' },
];

const CHAIN_COLORS: Record<string, string> = {
  placement: 'var(--rh-blue)',
  scaling: 'var(--rh-purple)',
  routing: 'var(--rh-teal)',
  lifecycle: 'var(--rh-orange)',
  tenant: 'var(--rh-green)',
};

const FLOW_STEPS = [
  { label: 'Prediction', hash: 'a3f8c2d1...' },
  { label: 'Action', hash: '7b2e9f4a...' },
  { label: 'Outcome', hash: 'd4c1a8e3...' },
];

function ChainCard({ chain, index }: { chain: ChainData; index: number }) {
  const color = CHAIN_COLORS[chain.type] ?? 'var(--rh-blue)';
  const hash = chain.latestHash ? chain.latestHash.slice(0, 8) : '--------';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, type: 'spring', stiffness: 400, damping: 25 }}
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--border)',
        borderRadius: 10,
        padding: '14px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        minWidth: 220,
      }}
    >
      <span
        style={{
          background: color,
          color: '#fff',
          fontSize: 11,
          fontWeight: 700,
          padding: '3px 10px',
          borderRadius: 6,
          textTransform: 'uppercase',
          letterSpacing: 0.5,
          whiteSpace: 'nowrap',
        }}
      >
        {chain.type}
      </span>
      <span style={{ fontSize: 16, lineHeight: 1 }}>
        {chain.valid ? '✓' : '✗'}
      </span>
      <span style={{ fontSize: 13, color: 'var(--text-dim, #aaa)', whiteSpace: 'nowrap' }}>
        {chain.entries.toLocaleString()} entries
      </span>
      <span
        style={{
          fontSize: 11,
          fontFamily: 'monospace',
          color: 'var(--text-disabled, #666)',
          marginLeft: 'auto',
        }}
      >
        {hash}
      </span>
    </motion.div>
  );
}

function FlowDiagram() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.5 }}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 0,
        marginTop: 28,
        padding: '20px 0',
      }}
    >
      {FLOW_STEPS.map((step, i) => (
        <div key={step.label} style={{ display: 'flex', alignItems: 'center' }}>
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.6 + i * 0.15, type: 'spring', stiffness: 300, damping: 20 }}
            style={{
              background: 'var(--surface-2)',
              border: '1px solid var(--border)',
              borderRadius: 10,
              padding: '14px 22px',
              textAlign: 'center',
              minWidth: 120,
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>{step.label}</div>
            <div style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--rh-teal)', marginTop: 6 }}>
              SHA {step.hash}
            </div>
          </motion.div>
          {i < FLOW_STEPS.length - 1 && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.7 + i * 0.15 }}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                padding: '0 10px',
                color: 'var(--text-dim, #aaa)',
              }}
            >
              <span style={{ fontSize: 20, lineHeight: 1 }}>{'→'}</span>
              <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'var(--text-disabled, #666)', marginTop: 2 }}>
                linked
              </span>
            </motion.div>
          )}
        </div>
      ))}
    </motion.div>
  );
}

export function LedgerChainView({ chains }: LedgerChainViewProps) {
  const data = chains && chains.length > 0 ? chains : DEFAULT_CHAINS;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-dim, #aaa)', marginBottom: 14, letterSpacing: 0.5 }}>
        ARE LEDGER CHAINS
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: 10,
        }}
      >
        {data.map((chain, i) => (
          <ChainCard key={chain.type} chain={chain} index={i} />
        ))}
      </div>
      <FlowDiagram />
    </div>
  );
}

export default LedgerChainView;
