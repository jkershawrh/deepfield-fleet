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

const CHAIN_COLORS: Record<string, string> = {
  placement: 'var(--rh-blue)',
  scaling: 'var(--rh-purple)',
  routing: 'var(--rh-teal)',
  lifecycle: 'var(--rh-orange)',
  tenant: 'var(--rh-green)',
};

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

export function LedgerChainView({ chains }: LedgerChainViewProps) {
  const data = chains ?? [];

  if (data.length === 0) {
    return (
      <div style={{ padding: 16, color: 'var(--rh-orange)', fontSize: 13 }}>
        No live immutable-ledger evidence is attached. Verified receipts and entry
        lookups are required before a chain can be shown here.
      </div>
    );
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-dim, #aaa)', marginBottom: 14, letterSpacing: 0.5 }}>
        VERIFIED IMMUTABLE-LEDGER CHAINS
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
    </div>
  );
}

export default LedgerChainView;
