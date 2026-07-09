import React from 'react';
import { motion } from 'motion/react';

type StageStatus = 'idle' | 'active' | 'done' | 'error';

interface Stage {
  label: string;
  status: StageStatus;
  detail?: string;
}

interface IntentFlowProps {
  stages: Stage[];
  intentType?: string;
  model?: string;
  confidence?: number;
}

const statusColors: Record<StageStatus, string> = {
  idle: '#6a6a6a',
  active: 'var(--rh-blue)',
  done: 'var(--rh-green)',
  error: '#ee0000',
};

const Arrow: React.FC = () => (
  <svg width="32" height="20" viewBox="0 0 32 20" style={{ flexShrink: 0 }}>
    <line x1="0" y1="10" x2="24" y2="10" stroke="var(--border)" strokeWidth="2" />
    <polygon points="24,4 32,10 24,16" fill="var(--border)" />
  </svg>
);

const StatusDot: React.FC<{ status: StageStatus }> = ({ status }) => {
  const base: React.CSSProperties = {
    width: 8,
    height: 8,
    borderRadius: '50%',
    backgroundColor: statusColors[status],
    display: 'inline-block',
    flexShrink: 0,
  };

  if (status === 'active') {
    return (
      <motion.span
        style={base}
        animate={{ opacity: [1, 0.3, 1] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
      />
    );
  }

  return <span style={base} />;
};

const Placeholder: React.FC = () => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px 16px',
      color: '#6a6a6a',
      fontSize: 14,
      fontStyle: 'italic',
    }}
  >
    No intent data available
  </div>
);

export function IntentFlow({ stages, intentType, model, confidence }: IntentFlowProps) {
  if (!stages || stages.length === 0) {
    return <Placeholder />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Metadata row */}
      {(intentType || model || confidence !== undefined) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          {intentType && (
            <span
              style={{
                background: 'var(--rh-purple)',
                color: '#fff',
                fontSize: 11,
                fontWeight: 600,
                padding: '2px 10px',
                borderRadius: 999,
                letterSpacing: 0.3,
                textTransform: 'uppercase',
              }}
            >
              {intentType}
            </span>
          )}
          {model && (
            <span style={{ color: '#ccc', fontSize: 13 }}>
              {model}
            </span>
          )}
          {confidence !== undefined && (
            <span
              style={{
                color: confidence >= 0.8 ? 'var(--rh-green)' : confidence >= 0.5 ? 'var(--rh-orange)' : '#ee0000',
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {Math.round(confidence * 100)}%
            </span>
          )}
        </div>
      )}

      {/* Flow row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 0,
          overflowX: 'auto',
          padding: '4px 0',
        }}
      >
        {stages.map((stage, i) => (
          <React.Fragment key={stage.label + i}>
            {i > 0 && <Arrow />}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.35, ease: 'easeOut' }}
              style={{
                background: 'var(--surface-2)',
                border: `1px solid ${stage.status === 'active' ? 'var(--rh-blue)' : 'var(--border)'}`,
                borderRadius: 10,
                padding: '10px 16px',
                minWidth: 110,
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                flexShrink: 0,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <StatusDot status={stage.status} />
                <span style={{ color: '#e0e0e0', fontSize: 14, fontWeight: 500 }}>
                  {stage.label}
                </span>
              </div>
              {stage.detail && (
                <span style={{ color: '#888', fontSize: 11, paddingLeft: 16 }}>
                  {stage.detail}
                </span>
              )}
            </motion.div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

export default IntentFlow;
