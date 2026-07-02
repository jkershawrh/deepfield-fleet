import { motion } from 'motion/react';

interface Props {
  progress: number;
  title: string;
  subtitle: string;
}

export function StepProgress({ progress, title, subtitle }: Props) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 6 }}>
        <div>
          <span style={{ fontSize: 15, fontWeight: 700 }}>{title}</span>
          <span style={{ fontSize: 12, color: 'var(--text-dim)', marginLeft: 8 }}>{subtitle}</span>
        </div>
        <span style={{ fontSize: 12, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
          {progress}%
        </span>
      </div>
      <div style={{ height: 4, background: 'var(--surface-2)', borderRadius: 2, overflow: 'hidden' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
          style={{ height: '100%', background: progress >= 100 ? 'var(--rh-green)' : 'var(--rh-red)', borderRadius: 2 }}
        />
      </div>
    </div>
  );
}
