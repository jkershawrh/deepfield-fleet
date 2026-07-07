import { useMemo, useCallback } from 'react';
import { ReactFlow, Background, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { AgentTierNode } from './nodes/AgentTierNode';
import { EvidenceEdge } from './edges/EvidenceEdge';
import type { ClassificationRecord } from '../api/client';

const nodeTypes = { agentTier: AgentTierNode };
const edgeTypes = { evidence: EvidenceEdge };

const TIER_CONFIG = {
  nano:  { color: '#0066cc', label: 'Nanoagents (7)', x: 90, y: 0 },
  micro: { color: '#63993d', label: 'Microagents (5)', x: 90, y: 160 },
  macro: { color: '#5e40be', label: 'Macroagents (5)', x: 90, y: 320 },
};

const SEV_RANK: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };

interface Props {
  records: ClassificationRecord[];
  activeStage?: 'nano' | 'micro' | 'macro' | 'all' | null;
  onAgentClick?: (agentName: string, tier: string) => void;
}

export function AgentCascadeFlow({ records, activeStage, onAgentClick }: Props) {
  const { nodes, edges } = useMemo(() => {
    const tierRecords = (tier: string) => records.filter(r => r.agent_tier === tier);

    const agentsForTier = (tier: string) => {
      const recs = tierRecords(tier);
      const names = [...new Set(recs.map(r => r.agent_name))];
      return names.map(name => {
        const agentRecs = recs.filter(r => r.agent_name === name);
        const topSev = agentRecs.reduce((s, r) =>
          (SEV_RANK[r.severity] || 0) > (SEV_RANK[s] || 0) ? r.severity : s, 'info');
        return { name, severity: topSev, count: agentRecs.length };
      });
    };

    const nodes: Node[] = Object.entries(TIER_CONFIG).map(([tier, cfg]) => ({
      id: tier,
      type: 'agentTier',
      position: { x: cfg.x, y: cfg.y },
      data: {
        label: cfg.label,
        color: cfg.color,
        tier,
        agents: agentsForTier(tier),
        recordCount: tierRecords(tier).length,
        isActive: activeStage === tier || activeStage === 'all',
        onAgentClick,
      },
      draggable: false,
    }));

    const nanoCount = tierRecords('nano').length;
    const microCount = tierRecords('micro').length;

    const edges: Edge[] = [
      {
        id: 'nano-micro',
        source: 'nano',
        target: 'micro',
        type: 'evidence',
        data: {
          count: microCount,
          color: TIER_CONFIG.micro.color,
          animated: (activeStage === 'micro' || activeStage === 'all') && microCount > 0,
        },
      },
      {
        id: 'micro-macro',
        source: 'micro',
        target: 'macro',
        type: 'evidence',
        data: {
          count: tierRecords('macro').length,
          color: TIER_CONFIG.macro.color,
          animated: (activeStage === 'macro' || activeStage === 'all') && tierRecords('macro').length > 0,
        },
      },
    ];

    if (nanoCount > 0 && microCount === 0) {
      edges[0].data = { ...edges[0].data, count: 0, animated: false };
    }

    return { nodes, edges };
  }, [records, activeStage, onAgentClick]);

  const onInit = useCallback((instance: { fitView: () => void }) => {
    instance.fitView();
  }, []);

  return (
    <div style={{
      background: 'var(--surface-1)',
      border: '1px solid var(--border)',
      borderRadius: 10,
      marginBottom: 16,
      height: 440,
    }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onInit={onInit}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        panOnDrag={true}
        zoomOnScroll={true}
        minZoom={0.5}
        maxZoom={1.5}
        style={{ background: 'transparent' }}
      >
        <Background color="var(--border)" gap={20} size={1} />
      </ReactFlow>
    </div>
  );
}
