import { useMemo } from 'react';
import {
  ReactFlow,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';

/* ── Types ─────────────────────────────────────────────────────────── */

interface FleetArchitectureFlowProps {
  animated?: boolean;
}

interface ArchNodeData {
  label: string;
  subtitle: string;
  description: string;
  color: string;
  [key: string]: unknown;
}

/* ── Node definitions ──────────────────────────────────────────────── */

const NODE_W = 260;
const NODE_H = 96;

const NODES_RAW: { id: string; data: ArchNodeData }[] = [
  {
    id: 'deepfield-fleet',
    data: {
      label: 'deepfield-fleet',
      subtitle: 'Advisory Producer',
      description: 'Observations • Findings • Forecasts',
      color: 'var(--rh-purple)',
    },
  },
  {
    id: 'governed-cognitive-loop',
    data: {
      label: 'governed-cognitive-loop',
      subtitle: 'Decision Synthesis',
      description: 'Candidates • Falsification • Signed DecisionPackage',
      color: 'var(--rh-red)',
    },
  },
  {
    id: 'fleet-controller',
    data: {
      label: 'fleet-controller',
      subtitle: 'Fleet Control Plane',
      description: 'Admission • Authorization • Durable Operations',
      color: 'var(--rh-blue)',
    },
  },
  {
    id: 'fleet-gateway',
    data: {
      label: 'fleet-gateway',
      subtitle: 'Rust Data Plane',
      description: 'Cross-Cluster Routing • Load Balancing',
      color: 'var(--rh-teal)',
    },
  },
  {
    id: 'inference-proxy',
    data: {
      label: 'inference-proxy',
      subtitle: 'Inference Proxy',
      description: 'OpenAI-Compatible • Load Shedding • SSE',
      color: 'var(--rh-orange)',
    },
  },
  {
    id: 'ovms',
    data: {
      label: 'ovms',
      subtitle: 'OVMS C++',
      description: 'INT8 on Intel Xeon 6 • AMX • $0.60/hr',
      color: 'var(--rh-green)',
    },
  },
  {
    id: 'immutable-ledger',
    data: {
      label: 'are-immutable-ledger',
      subtitle: 'Standalone Proof Service',
      description: 'Evidence Receipts • Chain Verification • No Grants',
      color: 'var(--rh-red)',
    },
  },
];

const EDGES_RAW: { source: string; target: string; label: string }[] = [
  { source: 'deepfield-fleet', target: 'governed-cognitive-loop', label: 'Advisory CloudEvents' },
  { source: 'governed-cognitive-loop', target: 'fleet-controller', label: 'Signed DecisionPackages' },
  { source: 'fleet-controller', target: 'fleet-gateway', label: 'Routing Policies' },
  { source: 'fleet-controller', target: 'inference-proxy', label: 'Backend Config' },
  { source: 'fleet-controller', target: 'immutable-ledger', label: 'Evidence Receipts' },
  { source: 'inference-proxy', target: 'ovms', label: 'Chat Completions' },
  { source: 'fleet-gateway', target: 'inference-proxy', label: 'Cross-Cluster Traffic' },
];

/* ── Dagre layout ──────────────────────────────────────────────────── */

function layoutGraph(): { nodes: Node<ArchNodeData>[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 60 });
  g.setDefaultEdgeLabel(() => ({}));

  NODES_RAW.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  EDGES_RAW.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);

  const nodes: Node<ArchNodeData>[] = NODES_RAW.map((n) => {
    const pos = g.node(n.id);
    return {
      id: n.id,
      type: 'archNode',
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      data: n.data,
    };
  });

  const edges: Edge[] = EDGES_RAW.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: true,
    style: { stroke: 'var(--border)', strokeWidth: 1.5 },
    labelStyle: { fill: '#aaa', fontSize: 11 },
    labelBgStyle: { fill: 'var(--surface-1)', fillOpacity: 0.9 },
  }));

  return { nodes, edges };
}

/* ── Custom node ───────────────────────────────────────────────────── */

function ArchNode({ data }: NodeProps<Node<ArchNodeData>>) {
  return (
    <div
      style={{
        background: 'var(--surface-2)',
        border: `1.5px solid ${data.color}`,
        borderRadius: 10,
        padding: '10px 16px',
        minWidth: NODE_W,
        textAlign: 'center',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: data.color }} />
      <div style={{ fontWeight: 600, fontSize: 14, color: data.color }}>{data.label}</div>
      <div style={{ fontSize: 12, color: '#ccc', marginTop: 2 }}>{data.subtitle}</div>
      <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{data.description}</div>
      <Handle type="source" position={Position.Bottom} style={{ background: data.color }} />
    </div>
  );
}

const nodeTypes = { archNode: ArchNode };

/* ── Main component ────────────────────────────────────────────────── */

export function FleetArchitectureFlow({ animated = true }: FleetArchitectureFlowProps) {
  const { nodes, edges } = useMemo(() => {
    const layout = layoutGraph();
    if (!animated) {
      layout.edges = layout.edges.map((e) => ({ ...e, animated: false }));
    }
    return layout;
  }, [animated]);

  if (!nodes.length) return null;

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 500, background: 'var(--bg-dark)' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        zoomOnScroll={false}
        panOnDrag={false}
        style={{ background: 'var(--bg-dark)' }}
      />
    </div>
  );
}

export default FleetArchitectureFlow;
