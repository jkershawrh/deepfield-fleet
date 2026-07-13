import { useState } from 'react';
import { motion } from 'motion/react';
import LayerNav from './gcl/LayerNav';
import Layer0Hook from './gcl/layers/Layer0Hook';
import Layer1Evidence from './gcl/layers/Layer1Evidence';
import Layer2Lookahead from './gcl/layers/Layer2Lookahead';
import Layer3Floor from './gcl/layers/Layer3Floor';
import Close from './gcl/layers/Close';

interface GovernanceDeepDiveProps {
  onExit: () => void;
}

const LAYERS = [Layer0Hook, Layer1Evidence, Layer2Lookahead, Layer3Floor, Close] as const;

export default function GovernanceDeepDive({ onExit }: GovernanceDeepDiveProps) {
  const [activeLayer, setActiveLayer] = useState<0 | 1 | 2 | 3 | 4>(0);
  const ActiveComponent = LAYERS[activeLayer];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
        padding: 24,
        background: 'var(--surface-0)',
        minHeight: '100vh',
        color: 'var(--text-primary)',
      }}
    >
      {/* Navigation */}
      <LayerNav activeIndex={activeLayer} onSelect={setActiveLayer} />

      {/* Active layer content */}
      <div style={{ flex: 1 }}>
        <ActiveComponent />
      </div>

      {/* Footer with Exit */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '24px 0',
          borderTop: '1px solid var(--border)',
        }}
      >
        <button
          onClick={onExit}
          style={{
            background: 'var(--surface-2)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            padding: '10px 28px',
            borderRadius: 8,
            fontFamily: "'Red Hat Text', sans-serif",
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Exit
        </button>
      </div>
    </motion.div>
  );
}
