import React, { useState } from 'react';
import { motion } from 'motion/react';

type CellStatus = 'pass' | 'warn' | 'fail';
interface CellData { status: CellStatus; score?: number }
type MatrixData = Record<string, Record<string, CellData>>;
interface TestMatrixCompactProps {
  data?: MatrixData;
}

const CAPABILITIES = [
  'Multi-Cluster Placement', 'Canary Rollout', 'Blue-Green Rollout',
  'Rolling Update', 'Tenant Isolation', 'Quota Enforcement',
  'KV Cache Transfer', 'Standalone Ledger Integrity', 'Auto-Scaling',
  'SLO Gate Validation', 'Fleet Routing', 'Model Hot-Swap',
] as const;

const TEST_TYPES = ['Unit', 'Integration', 'E2E', 'Chaos', 'Performance', 'Security'] as const;

const STATUS_COLORS: Record<CellStatus, string> = {
  pass: '#63993d',
  warn: '#ffcc17',
  fail: '#ee0000',
};

// Default data is illustrative. Live evidence must be supplied by a caller.
function buildDefaultData(): MatrixData {
  const data: MatrixData = {};
  CAPABILITIES.forEach((cap) => {
    data[cap] = {};
    TEST_TYPES.forEach((tt) => {
      data[cap][tt] = { status: 'warn' };
    });
  });
  return data;
}

export function TestMatrixCompact({ data }: TestMatrixCompactProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const hasExternalData = Boolean(data && Object.keys(data).length > 0);
  const matrix = hasExternalData ? data! : buildDefaultData();

  const capabilities = Object.keys(matrix);
  const testTypes = capabilities.length > 0 ? Object.keys(matrix[capabilities[0]]) : [];

  // Tally
  let pass = 0, warn = 0, fail = 0;
  for (const cap of capabilities) {
    for (const tt of testTypes) {
      const s = matrix[cap]?.[tt]?.status;
      if (s === 'pass') pass++;
      else if (s === 'warn') warn++;
      else if (s === 'fail') fail++;
    }
  }
  const total = pass + warn + fail;
  const allGreen = warn === 0 && fail === 0;
  const summary = !hasExternalData
    ? `${total} Illustrative Cells, Evidence Required`
    : allGreen
    ? `${total} Tests: All Green`
    : `${pass} Pass / ${warn} Warn / ${fail} Fail`;

  if (capabilities.length === 0) {
    return (
      <div style={{ color: '#aaa', padding: 16, fontFamily: 'monospace', fontSize: 13 }}>
        No test data available.
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      style={{
        background: 'var(--surface-1, #1f1f1f)',
        border: '1px solid var(--border, #383838)',
        borderRadius: 8,
        padding: 16,
        fontFamily: "'Inter', system-ui, sans-serif",
        color: '#e0e0e0',
        width: 'fit-content',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <span style={{ fontSize: 13, fontWeight: 600, letterSpacing: 0.3 }}>Test Matrix</span>
        <span style={{
          fontSize: 11,
          padding: '2px 8px',
          borderRadius: 4,
          background: allGreen ? 'rgba(99,153,61,0.18)' : 'rgba(240,86,29,0.15)',
          color: allGreen ? '#63993d' : '#f0561d',
          fontWeight: 500,
        }}>
          {summary}
        </span>
      </div>

      {/* Grid */}
      <table style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ width: 140 }} />
            {testTypes.map((tt) => (
              <th key={tt} style={{
                fontSize: 10,
                fontWeight: 500,
                color: '#888',
                textAlign: 'center',
                padding: '0 2px 6px',
                width: 28,
                letterSpacing: 0.2,
              }}>
                {tt.slice(0, 4)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {capabilities.map((cap, ri) => (
            <tr key={cap}>
              <td style={{
                fontSize: 11,
                color: '#aaa',
                paddingRight: 10,
                paddingBottom: 2,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: 140,
              }}>
                {cap}
              </td>
              {testTypes.map((tt, ci) => {
                const cell = matrix[cap]?.[tt];
                if (!cell) return <td key={tt} />;
                const cellKey = `${ri}-${ci}`;
                const isHovered = hovered === cellKey;
                return (
                  <td key={tt} style={{ padding: 1 }}>
                    <div
                      title={`${cap} / ${tt}: ${cell.status}${cell.score != null ? ` (${cell.score}%)` : ''}`}
                      onMouseEnter={() => setHovered(cellKey)}
                      onMouseLeave={() => setHovered(null)}
                      style={{
                        width: 24,
                        height: 24,
                        borderRadius: 3,
                        background: STATUS_COLORS[cell.status],
                        opacity: isHovered ? 1 : 0.82,
                        transform: isHovered ? 'scale(1.15)' : 'scale(1)',
                        transition: 'opacity 0.15s, transform 0.15s',
                        cursor: 'default',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 9,
                        fontWeight: 600,
                        color: cell.status === 'warn' ? '#333' : '#fff',
                      }}
                    >
                      {isHovered && cell.score != null ? cell.score : ''}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
}

export default TestMatrixCompact;
