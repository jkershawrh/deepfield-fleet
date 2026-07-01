import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, AgentAction, VerificationRecord, LearningProposal } from '../api/client';

const STATUS_COLORS: Record<string, string> = {
  proposed: '#0071C5', approved: '#3E8635', executing: '#F0AB00',
  executed: '#3E8635', failed: '#C9190B', rejected: '#6A6E73',
  pending: '#0071C5', passed: '#3E8635', inconclusive: '#F0AB00',
  accepted: '#3E8635',
};

const LOOP_STEPS = [
  { label: 'Signals', icon: '📡' },
  { label: 'Decide', icon: '🧠' },
  { label: 'Act', icon: '⚡' },
  { label: 'Verify', icon: '✓' },
  { label: 'Learn', icon: '📚' },
];

export default function AgentLoop() {
  const qc = useQueryClient();
  const { data: actions = [] } = useQuery({ queryKey: ['actions'], queryFn: () => api.agentLoop.listActions() });
  const { data: verifications = [] } = useQuery({ queryKey: ['verifications'], queryFn: api.agentLoop.listVerifications });
  const { data: proposals = [] } = useQuery({ queryKey: ['proposals'], queryFn: () => api.agentLoop.listProposals() });

  const approve = useMutation({
    mutationFn: (id: string) => api.agentLoop.approveAction(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['actions'] }),
  });
  const execute = useMutation({
    mutationFn: (id: string) => api.agentLoop.executeAction(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['actions'] }),
  });
  const acceptProposal = useMutation({
    mutationFn: (id: string) => api.agentLoop.acceptProposal(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['proposals'] }),
  });
  const rejectProposal = useMutation({
    mutationFn: (id: string) => api.agentLoop.rejectProposal(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['proposals'] }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Agent Loop</h1>

      {/* Loop Visualization */}
      <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
        <div className="flex items-center justify-between px-8">
          {LOOP_STEPS.map((step, i) => (
            <div key={step.label} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-full bg-[#212121] border-2 border-[#0071C5] flex items-center justify-center text-xl">
                  {step.icon}
                </div>
                <span className="text-xs text-[#a0a0a0] mt-1">{step.label}</span>
              </div>
              {i < LOOP_STEPS.length - 1 && (
                <div className="w-16 h-0.5 bg-[#333] mx-2 mt-[-16px]" />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Actions */}
        <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
          <h2 className="text-sm font-medium text-[#6A6E73] mb-3">Actions ({actions.length})</h2>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {actions.map((a: AgentAction) => (
              <div key={a.action_id} className="bg-[#212121] rounded p-3 border border-[#333]">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{a.action_type}</span>
                  <span className="text-xs px-2 py-0.5 rounded" style={{
                    backgroundColor: (STATUS_COLORS[a.status] || '#444') + '22',
                    color: STATUS_COLORS[a.status],
                  }}>{a.status}</span>
                </div>
                <p className="text-xs text-[#6A6E73]">by {a.created_by_agent}</p>
                {a.requires_human_approval && a.status === 'proposed' && (
                  <div className="mt-2 flex gap-2">
                    <button onClick={() => approve.mutate(a.action_id)}
                      className="text-xs bg-[#3E8635] hover:bg-[#2C6B27] text-white px-2 py-1 rounded">
                      Approve
                    </button>
                  </div>
                )}
                {a.status === 'approved' && (
                  <button onClick={() => execute.mutate(a.action_id)}
                    className="mt-2 text-xs bg-[#0071C5] hover:bg-[#004B95] text-white px-2 py-1 rounded">
                    Execute
                  </button>
                )}
              </div>
            ))}
            {actions.length === 0 && <p className="text-[#6A6E73] text-xs">No actions</p>}
          </div>
        </div>

        {/* Verifications */}
        <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
          <h2 className="text-sm font-medium text-[#6A6E73] mb-3">Verifications ({verifications.length})</h2>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {verifications.map((v: VerificationRecord) => (
              <div key={v.verification_id} className="bg-[#212121] rounded p-3 border border-[#333]">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{v.verification_type}</span>
                  <span className="text-xs px-2 py-0.5 rounded" style={{
                    backgroundColor: (STATUS_COLORS[v.status] || '#444') + '22',
                    color: STATUS_COLORS[v.status],
                  }}>{v.status}</span>
                </div>
                <p className="text-xs text-[#6A6E73]">Confidence: {(v.confidence * 100).toFixed(0)}%</p>
              </div>
            ))}
            {verifications.length === 0 && <p className="text-[#6A6E73] text-xs">No verifications</p>}
          </div>
        </div>

        {/* Learning Proposals */}
        <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
          <h2 className="text-sm font-medium text-[#6A6E73] mb-3">Learning Proposals ({proposals.length})</h2>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {proposals.map((p: LearningProposal) => (
              <div key={p.proposal_id} className="bg-[#212121] rounded p-3 border border-[#333]">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{p.proposal_type}</span>
                  <span className="text-xs px-2 py-0.5 rounded" style={{
                    backgroundColor: (STATUS_COLORS[p.status] || '#444') + '22',
                    color: STATUS_COLORS[p.status],
                  }}>{p.status}</span>
                </div>
                <p className="text-xs text-[#a0a0a0] mt-1">{p.rationale}</p>
                <p className="text-xs text-[#6A6E73]">Confidence: {(p.confidence * 100).toFixed(0)}%</p>
                {p.status === 'proposed' && (
                  <div className="mt-2 flex gap-2">
                    <button onClick={() => acceptProposal.mutate(p.proposal_id)}
                      className="text-xs bg-[#3E8635] hover:bg-[#2C6B27] text-white px-2 py-1 rounded">
                      Accept
                    </button>
                    <button onClick={() => rejectProposal.mutate(p.proposal_id)}
                      className="text-xs bg-[#444] hover:bg-[#555] text-white px-2 py-1 rounded">
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
            {proposals.length === 0 && <p className="text-[#6A6E73] text-xs">No proposals</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
