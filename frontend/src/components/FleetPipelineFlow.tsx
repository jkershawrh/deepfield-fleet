import { useMemo } from 'react';
import { ReactFlow, Handle, Position, BaseEdge, getBezierPath, type Node, type Edge, type NodeProps, type EdgeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { motion } from 'motion/react';
import dagre from 'dagre';

/* ── Types ─────────────────────────────────────────────────────────── */

interface FleetPipelineFlowProps {
  stepId?: string;
  sloGauge?: { current_p95?: number; forecast_p95?: number; slo_target?: number; minutes_to_breach?: number };
  blastRadius?: { affected_models?: number; affected_users?: number; severity_score?: number; requires_human_gate?: boolean };
  intentFlow?: { intent_type?: string; status?: string; current_phase?: string; model?: string; confidence?: number };
  ledgerChains?: Array<{ chain?: string; type?: string; entries?: number; status?: string; valid?: boolean }>;
  replicaEvents?: Array<{ time: string; replicas: number; trigger: string }>;
  funnel?: Record<string, number>;
  agentEvents?: Array<Record<string, unknown>>;
  costData?: { gpu_per_hour?: number; cpu_per_hour?: number; savings_factor?: number };
  learningProposals?: Array<{ type?: string; detail?: string }>;
}

type NodeState = 'idle' | 'active' | 'done';

interface StageNodeData { label: string; color: string; detail: string; state: NodeState; [key: string]: unknown }

/* ── Step → node state mapping ────────────────────────────────────── */

const ALL_IDLE: Record<string, NodeState> = { signal: 'idle', classify: 'idle', predict: 'idle', decide: 'idle', act: 'idle', verify: 'idle', learn: 'idle' };

const STEP_NODE_STATES: Record<string, Record<string, NodeState>> = {
  cost:         { ...ALL_IDLE, signal: 'active' },
  event:        { ...ALL_IDLE, signal: 'active' },
  fleet_deploy: { ...ALL_IDLE, signal: 'done' },
  platform:     { ...ALL_IDLE, signal: 'done' },
  forecast:     { signal: 'done', classify: 'active', predict: 'active', decide: 'idle', act: 'idle', verify: 'idle', learn: 'idle' },
  blast_radius: { signal: 'done', classify: 'done', predict: 'done', decide: 'active', act: 'idle', verify: 'idle', learn: 'idle' },
  intent:       { signal: 'done', classify: 'done', predict: 'done', decide: 'done', act: 'active', verify: 'idle', learn: 'idle' },
  proof:        { signal: 'done', classify: 'done', predict: 'done', decide: 'done', act: 'done', verify: 'active', learn: 'idle' },
  scale_10:     { signal: 'done', classify: 'active', predict: 'active', decide: 'active', act: 'active', verify: 'active', learn: 'idle' },
  scale_50:     { signal: 'done', classify: 'active', predict: 'active', decide: 'active', act: 'active', verify: 'active', learn: 'idle' },
  stress:       { signal: 'done', classify: 'active', predict: 'active', decide: 'active', act: 'active', verify: 'active', learn: 'idle' },
  recovery:     { signal: 'done', classify: 'done', predict: 'done', decide: 'done', act: 'done', verify: 'done', learn: 'active' },
  claim:        { signal: 'done', classify: 'done', predict: 'done', decide: 'done', act: 'done', verify: 'done', learn: 'done' },
};

/* ── Stage definitions ────────────────────────────────────────────── */

const STAGES = [
  { id: 'signal',   label: 'Signals',  color: 'var(--rh-teal)' },
  { id: 'classify', label: 'Classify', color: 'var(--rh-blue)' },
  { id: 'predict',  label: 'Predict',  color: 'var(--rh-green)' },
  { id: 'decide',   label: 'Decide',   color: 'var(--rh-orange)' },
  { id: 'act',      label: 'Act',      color: 'var(--rh-purple)' },
  { id: 'verify',   label: 'Verify',   color: 'var(--rh-red)' },
  { id: 'learn',    label: 'Learn',    color: 'var(--rh-yellow)' },
];

const IDLE_DETAILS: Record<string, string> = {
  signal: 'Awaiting metrics', classify: 'Fleet nanoagents', predict: 'SLO Forecaster',
  decide: 'Blast Radius', act: 'Intent Emission', verify: 'ARE Ledger', learn: 'Event Profiles',
};

function getDetail(id: string, state: NodeState, p: FleetPipelineFlowProps): string {
  if (state === 'idle') return IDLE_DETAILS[id];
  const { sloGauge: s, blastRadius: b, intentFlow: i, ledgerChains: l, funnel: f, agentEvents: a, learningProposals: lp } = p;
  switch (id) {
    case 'signal': { const n = f ? Object.values(f).reduce((a, b) => a + b, 0) : 0; return n ? `${n} signals | P95 ${s?.current_p95 ?? '?'}ms` : IDLE_DETAILS[id]; }
    case 'classify': return a?.length ? `${a.length} agents classified` : IDLE_DETAILS[id];
    case 'predict': return s?.current_p95 ? `P95: ${s.current_p95}→${s.forecast_p95 ?? '?'}ms${s.minutes_to_breach != null ? ` | Breach ${s.minutes_to_breach}min` : ''}` : IDLE_DETAILS[id];
    case 'decide': return b?.affected_users ? `${b.affected_users} users × ${b.affected_models ?? '?'} models | Score: ${b.severity_score ?? '?'}` : IDLE_DETAILS[id];
    case 'act': return i?.intent_type ? `${i.intent_type} — ${i.status ?? 'pending'}` : IDLE_DETAILS[id];
    case 'verify': { const v = l?.filter(c => c.valid !== false).length ?? 0; return l?.length ? `${v} chains verified` : IDLE_DETAILS[id]; }
    case 'learn': return lp?.length ? `${lp.length} proposals` : IDLE_DETAILS[id];
    default: return '';
  }
}

/* ── Custom node ──────────────────────────────────────────────────── */

const NODE_W = 140;
const NODE_H = 100;

const DOT: Record<NodeState, string> = { idle: 'var(--text-disabled)', active: 'var(--rh-blue)', done: 'var(--rh-green)' };

function PipelineStageNode({ data }: NodeProps<Node<StageNodeData>>) {
  const { label, color, detail, state } = data;
  const borderColor = state === 'idle' ? 'var(--border)' : color;
  const textColor = state === 'idle' ? 'var(--text-dim)' : 'var(--text-primary)';

  return (
    <div style={{
      width: NODE_W, height: NODE_H, background: 'var(--surface-1)', borderRadius: 10,
      border: `1.5px solid ${borderColor}`, padding: '10px 12px', position: 'relative',
      boxShadow: state === 'active' ? `0 0 12px ${color}40` : 'none',
      transition: 'border-color 0.3s, box-shadow 0.3s',
    }}>
      <Handle type="target" position={Position.Left} style={{ background: borderColor, width: 6, height: 6, border: 'none' }} />
      {/* Status dot */}
      <motion.div
        animate={state === 'active' ? { opacity: [1, 0.4, 1] } : { opacity: 1 }}
        transition={state === 'active' ? { duration: 1.2, repeat: Infinity } : {}}
        style={{ position: 'absolute', top: 10, left: 10, width: 8, height: 8, borderRadius: '50%', background: DOT[state] }}
      />
      {/* Done checkmark */}
      {state === 'done' && (
        <svg width="14" height="14" viewBox="0 0 14 14" style={{ position: 'absolute', top: 6, right: 6 }}>
          <circle cx="7" cy="7" r="6" fill="var(--rh-green)" opacity="0.9" />
          <path d="M4 7l2 2 4-4" stroke="#fff" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      <div style={{ fontWeight: 700, fontSize: 13, color: textColor, textAlign: 'center', marginTop: 10 }}>{label}</div>
      <div style={{ fontSize: 11, fontFamily: 'Red Hat Mono, monospace', color: 'var(--text-dim)', textAlign: 'center', marginTop: 6, lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {detail}
      </div>
      <Handle type="source" position={Position.Right} style={{ background: borderColor, width: 6, height: 6, border: 'none' }} />
    </div>
  );
}

/* ── Animated edge ────────────────────────────────────────────────── */

function PipelineEdge(props: EdgeProps & { data?: { animated?: boolean; color?: string } }) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data } = props;
  const [edgePath] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  const color = data?.color ?? 'var(--border)';
  const active = data?.animated ?? false;

  return (
    <>
      <BaseEdge {...props} path={edgePath} style={{ stroke: color + '50', strokeWidth: 2, strokeDasharray: '6 4', ...(active ? { animation: 'pipeline-dash 1s linear infinite' } : {}) }} />
      {active && (
        <circle r="3" fill={color} opacity="0.8">
          <animateMotion dur="1.8s" repeatCount="indefinite" path={edgePath} />
        </circle>
      )}
    </>
  );
}

const nodeTypes = { pipelineStage: PipelineStageNode };
const edgeTypes = { pipelineEdge: PipelineEdge };

/* ── Layout + build ───────────────────────────────────────────────── */

function buildGraph(props: FleetPipelineFlowProps): { nodes: Node<StageNodeData>[]; edges: Edge[] } {
  const states = STEP_NODE_STATES[props.stepId ?? ''] ?? ALL_IDLE;

  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', ranksep: 60, nodesep: 30 });
  g.setDefaultEdgeLabel(() => ({}));
  STAGES.forEach(s => g.setNode(s.id, { width: NODE_W, height: NODE_H }));
  for (let i = 0; i < STAGES.length - 1; i++) g.setEdge(STAGES[i].id, STAGES[i + 1].id);
  dagre.layout(g);

  const nodes: Node<StageNodeData>[] = STAGES.map(s => {
    const pos = g.node(s.id);
    const st = states[s.id] ?? 'idle';
    return { id: s.id, type: 'pipelineStage', position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 }, data: { label: s.label, color: s.color, state: st, detail: getDetail(s.id, st, props) } };
  });

  const edges: Edge[] = STAGES.slice(0, -1).map((s, i) => {
    const srcState = states[s.id] ?? 'idle';
    const active = srcState === 'active' || srcState === 'done';
    return { id: `e-${i}`, source: s.id, target: STAGES[i + 1].id, type: 'pipelineEdge', data: { animated: active, color: s.color } };
  });

  return { nodes, edges };
}

/* ── Keyframes (injected once) ────────────────────────────────────── */

const STYLE_ID = 'pipeline-dash-style';
if (typeof document !== 'undefined' && !document.getElementById(STYLE_ID)) {
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = '@keyframes pipeline-dash { to { stroke-dashoffset: -20; } }';
  document.head.appendChild(style);
}

/* ── Main component ───────────────────────────────────────────────── */

export function FleetPipelineFlow(props: FleetPipelineFlowProps) {
  const { nodes, edges } = useMemo(() => buildGraph(props), [props.stepId, props.sloGauge, props.blastRadius, props.intentFlow, props.ledgerChains, props.funnel, props.agentEvents, props.learningProposals, props.costData]);

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 160, background: 'var(--bg-dark)' }}>
      <ReactFlow
        nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false} nodesConnectable={false} zoomOnScroll={false} panOnScroll={false} panOnDrag={false}
        style={{ background: 'var(--bg-dark)' }}
      />
    </div>
  );
}

export default FleetPipelineFlow;
