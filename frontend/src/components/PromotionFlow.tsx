import { useMemo, useCallback } from 'react';
import { ReactFlow, Background, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

const RUBRIC_COLORS: Record<string, string> = {
  green: '#63993d',
  yellow: '#f0ab00',
  red: '#ee0000',
};

interface TierNodeData {
  label: string;
  tier: string;
  count: number;
  rubricStatus: string;
  threshold: string;
}

function TierNodeInner({ data }: NodeProps & { data: TierNodeData }) {
  const { label, count, rubricStatus, threshold } = data;
  const color = RUBRIC_COLORS[rubricStatus] || 'var(--border)';

  return (
    <div style={{
      background: color + '15',
      border: `2px solid ${color}`,
      borderRadius: 10,
      padding: '14px 20px',
      minWidth: 120,
      textAlign: 'center',
    }}>
      <Handle type="target" position={Position.Left} style={{ background: color, width: 6, height: 6, border: 'none' }} />
      <div style={{ fontSize: 13, fontWeight: 700, color, fontFamily: 'Red Hat Display, sans-serif' }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color, fontFamily: 'Red Hat Display, sans-serif', margin: '4px 0' }}>
        {count}
      </div>
      <div style={{ fontSize: 9, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>
        {threshold}
      </div>
      <Handle type="source" position={Position.Right} style={{ background: color, width: 6, height: 6, border: 'none' }} />
    </div>
  );
}

const TierNode = memo(TierNodeInner);
const nodeTypes = { tier: TierNode };

const TIERS = [
  { id: 'draft', label: 'Draft', threshold: 'Initial', x: 0 },
  { id: 'candidate', label: 'Candidate', threshold: '50 samples, 60%', x: 200 },
  { id: 'nano', label: 'Nano', threshold: '200 samples, 75%', x: 400 },
  { id: 'micro', label: 'Micro', threshold: '500 samples, 85%', x: 600 },
  { id: 'macro', label: 'Macro', threshold: '1000 samples, 85%+', x: 800 },
];

interface AgentSummary {
  tier: string;
  rubric_status: string;
}

interface Props {
  agents: AgentSummary[];
}

export function PromotionFlow({ agents }: Props) {
  const { nodes, edges } = useMemo(() => {
    const tierCounts: Record<string, number> = {};
    const tierStatus: Record<string, string> = {};

    for (const tier of TIERS) {
      const tierAgents = agents.filter(a => a.tier === tier.id);
      tierCounts[tier.id] = tierAgents.length;
      if (tierAgents.some(a => a.rubric_status === 'red')) tierStatus[tier.id] = 'red';
      else if (tierAgents.some(a => a.rubric_status === 'yellow')) tierStatus[tier.id] = 'yellow';
      else if (tierAgents.length > 0) tierStatus[tier.id] = 'green';
      else tierStatus[tier.id] = 'green';
    }

    const nodes: Node[] = TIERS.map((tier) => ({
      id: tier.id,
      type: 'tier',
      position: { x: tier.x, y: 40 },
      data: {
        label: tier.label,
        tier: tier.id,
        count: tierCounts[tier.id] || 0,
        rubricStatus: tierStatus[tier.id] || 'green',
        threshold: tier.threshold,
      },
      draggable: false,
    }));

    const edges: Edge[] = TIERS.slice(0, -1).map((tier, i) => ({
      id: `${tier.id}-${TIERS[i + 1].id}`,
      source: tier.id,
      target: TIERS[i + 1].id,
      style: { stroke: 'var(--border)', strokeWidth: 2, strokeDasharray: '6 4' },
      animated: false,
    }));

    return { nodes, edges };
  }, [agents]);

  const onInit = useCallback((instance: { fitView: () => void }) => {
    instance.fitView();
  }, []);

  return (
    <div style={{
      background: 'var(--surface-1)',
      border: '1px solid var(--border)',
      borderRadius: 10,
      padding: '8px 0',
      height: 180,
    }}>
      <div style={{ fontSize: 10, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1, textAlign: 'center', marginBottom: 4 }}>
        AGENT PROMOTION PIPELINE
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onInit={onInit}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        style={{ background: 'transparent' }}
      >
        <Background color="transparent" />
      </ReactFlow>
    </div>
  );
}
