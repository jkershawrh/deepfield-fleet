import { useState, useEffect } from 'react';
import { motion } from 'motion/react';

export function Header() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    fetch('/health').then(r => r.json()).then(() => setHealthy(true)).catch(() => setHealthy(false));
  }, []);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '12px 32px', borderBottom: '1px solid var(--border)', background: 'var(--surface-1)',
      position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 18, fontWeight: 800, fontFamily: 'Red Hat Display, sans-serif' }}>
          DeepField<span style={{ color: 'var(--rh-red)' }}> Multimodal</span>
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <motion.div
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 2 }}
          style={{
            width: 8, height: 8, borderRadius: '50%',
            background: healthy === null ? 'var(--text-disabled)' : healthy ? 'var(--rh-green)' : 'var(--rh-red)',
          }}
        />
        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
          {healthy === null ? 'Connecting...' : healthy ? 'Backend connected' : 'Backend offline'}
        </span>
      </div>
    </div>
  );
}
