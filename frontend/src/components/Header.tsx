import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { useDemoStore } from '../stores/useDemoStore';

export function Header() {
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const { mode, setMode } = useDemoStore();

  useEffect(() => {
    fetch('/health').then(r => r.json()).then(() => setHealthy(true)).catch(() => setHealthy(false));
  }, []);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '14px 32px', borderBottom: '1px solid var(--border)', background: 'var(--surface-1)',
      position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <img src="/logos/redhat.svg" alt="Red Hat" style={{ height: 20 }} />
        <span style={{ color: 'var(--text-disabled)', fontSize: 22, fontWeight: 300 }}>&times;</span>
        <img src="/logos/intel.png" alt="Intel" style={{ height: 20 }} />
      </div>
      <span style={{ fontSize: 18, fontWeight: 700, fontFamily: 'Red Hat Display, sans-serif', letterSpacing: -0.5 }}>
        fleet-llm-d<span style={{ color: 'var(--rh-red)' }}> Fleet Orchestration</span>
      </span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {mode !== 'dashboard' && (
          <button
            onClick={() => setMode('dashboard')}
            style={{
              background: 'none', border: '1px solid var(--border)', color: 'var(--text-dim)',
              padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
              fontFamily: 'Red Hat Text, sans-serif', fontWeight: 600,
              transition: 'border-color 0.2s, color 0.2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--rh-red)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-dim)'; }}
          >
            Dashboard
          </button>
        )}
        <motion.div
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 2 }}
          style={{
            width: 8, height: 8, borderRadius: '50%',
            background: healthy === null ? 'var(--text-disabled)' : healthy ? 'var(--rh-green)' : 'var(--rh-red)',
          }}
        />
        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
          {healthy === null ? 'Connecting...' : healthy ? 'Connected' : 'Offline'}
        </span>
      </div>
    </div>
  );
}
