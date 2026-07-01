import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, BaselineProfile, BaselineBuildJob } from '../api/client';

const STATUS_COLORS: Record<string, string> = {
  draft: '#F0AB00', active: '#3E8635', archived: '#6A6E73',
  pending: '#0071C5', running: '#F0AB00', complete: '#3E8635',
  failed: '#C9190B', cancelled: '#6A6E73',
};

export default function BaselineCompiler() {
  const qc = useQueryClient();
  const { data: jobs = [] } = useQuery({ queryKey: ['baseline-jobs'], queryFn: api.baseline.listJobs });
  const { data: profiles = [] } = useQuery({ queryKey: ['baseline-profiles'], queryFn: api.baseline.listProfiles });

  const createJob = useMutation({
    mutationFn: () => api.baseline.createJob({ scope: { scope_type: 'site', scope_id: 'factory-line-01' } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['baseline-jobs'] }),
  });

  const activate = useMutation({
    mutationFn: (id: string) => api.baseline.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['baseline-profiles'] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Baseline Compiler</h1>
        <button
          onClick={() => createJob.mutate()}
          className="bg-[#0071C5] hover:bg-[#004B95] text-white px-4 py-2 rounded text-sm font-medium transition"
        >
          New Baseline Job
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Jobs */}
        <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
          <h2 className="text-sm font-medium text-[#6A6E73] mb-3">Build Jobs</h2>
          {jobs.length === 0 ? (
            <p className="text-[#6A6E73] text-sm">No jobs yet</p>
          ) : (
            <div className="space-y-2">
              {jobs.map((j: BaselineBuildJob) => (
                <div key={j.job_id} className="bg-[#212121] rounded p-3 border border-[#333]">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-[#a0a0a0]">{j.job_id.slice(0, 8)}</span>
                    <span className="text-xs px-2 py-0.5 rounded" style={{
                      backgroundColor: (STATUS_COLORS[j.status] || '#444') + '22',
                      color: STATUS_COLORS[j.status] || '#444',
                    }}>{j.status}</span>
                  </div>
                  {j.error && <p className="text-xs text-[#C9190B] mt-1">{j.error}</p>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Profiles */}
        <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
          <h2 className="text-sm font-medium text-[#6A6E73] mb-3">Profiles</h2>
          {profiles.length === 0 ? (
            <p className="text-[#6A6E73] text-sm">No profiles yet</p>
          ) : (
            <div className="space-y-2">
              {profiles.map((p: BaselineProfile) => (
                <div key={p.baseline_id} className="bg-[#212121] rounded p-3 border border-[#333]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{p.scope_type}/{p.scope_id}</span>
                    <span className="text-xs px-2 py-0.5 rounded" style={{
                      backgroundColor: (STATUS_COLORS[p.status] || '#444') + '22',
                      color: STATUS_COLORS[p.status] || '#444',
                    }}>{p.status}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-[#a0a0a0]">
                    <span>Modality: {p.modality}</span>
                    <span>Version: {p.profile_version}</span>
                    <span>Confidence: {(p.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-xs">
                    <span className="text-[#6A6E73]">
                      {Object.keys(p.thresholds).length} threshold groups
                    </span>
                    <span className="text-[#6A6E73]">
                      {Object.keys(p.normal_ranges).length} range groups
                    </span>
                  </div>
                  {p.status === 'draft' && (
                    <button
                      onClick={() => activate.mutate(p.baseline_id)}
                      className="mt-2 text-xs bg-[#3E8635] hover:bg-[#2C6B27] text-white px-3 py-1 rounded transition"
                    >
                      Activate
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
