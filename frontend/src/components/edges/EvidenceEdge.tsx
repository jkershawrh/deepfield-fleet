import { memo } from 'react';
import { BaseEdge, getBezierPath } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';

interface EvidenceEdgeData {
  count: number;
  color: string;
  animated: boolean;
}

function EvidenceEdgeInner(props: EdgeProps & { data?: EvidenceEdgeData }) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data } = props;
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  const count = data?.count ?? 0;
  const color = data?.color ?? 'var(--border)';
  const animated = data?.animated ?? false;

  return (
    <>
      <BaseEdge
        {...props}
        path={edgePath}
        style={{ stroke: color + '40', strokeWidth: 2, strokeDasharray: '6 4' }}
      />
      {animated && count > 0 && (
        <>
          <circle r="3" fill={color}>
            <animateMotion dur="1.5s" repeatCount="indefinite" path={edgePath} />
          </circle>
          <circle r="3" fill={color} opacity="0.5">
            <animateMotion dur="1.5s" repeatCount="indefinite" path={edgePath} begin="0.75s" />
          </circle>
        </>
      )}
      {count > 0 && (
        <g transform={`translate(${labelX}, ${labelY})`}>
          <rect x="-16" y="-10" width="32" height="20" rx="4" fill="var(--surface-1)" stroke={color + '60'} strokeWidth="1" />
          <text textAnchor="middle" dominantBaseline="central" fontSize="10" fontWeight="700" fill={color} fontFamily="Red Hat Mono, monospace">
            {count}
          </text>
        </g>
      )}
    </>
  );
}

export const EvidenceEdge = memo(EvidenceEdgeInner);
