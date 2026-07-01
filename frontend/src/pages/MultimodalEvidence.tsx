import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api, EvidenceArtifact } from '../api/client';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const MODALITY_COLORS: Record<string, string> = {
  metric: '#0071C5', log: '#3E8635', document: '#8F4700',
  image: '#6753AC', audio: '#C9190B', event: '#F0AB00',
  text: '#009596', trace: '#EE0000', video: '#A30000',
  human_note: '#6A6E73', unknown: '#444',
};

const SEV_COLORS: Record<string, string> = {
  public: '#3E8635', internal: '#0071C5', confidential: '#F0AB00', restricted: '#C9190B',
};

export default function MultimodalEvidence() {
  const [filter, setFilter] = useState<string>('');
  const { data: evidence = [], isLoading, error } = useQuery({
    queryKey: ['evidence', filter],
    queryFn: () => api.evidence.list(filter || undefined),
  });

  const modalityCounts = evidence.reduce((acc, e) => {
    acc[e.modality] = (acc[e.modality] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  const pieData = Object.entries(modalityCounts).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Evidence Artifacts</h1>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="bg-[#212121] border border-[#444] rounded px-3 py-1.5 text-sm"
        >
          <option value="">All modalities</option>
          {['metric', 'log', 'document', 'image', 'audio', 'event', 'text'].map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-[#6A6E73]">Loading evidence...</p>}
      {error && <p className="text-[#C9190B]">Error: {(error as Error).message}</p>}

      {evidence.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-[#1a1a1a] rounded-lg border border-[#333] overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#333] text-[#6A6E73] text-left">
                    <th className="px-4 py-3">Modality</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Sensitivity</th>
                    <th className="px-4 py-3">Features</th>
                  </tr>
                </thead>
                <tbody>
                  {evidence.map(e => (
                    <tr key={e.evidence_id} className="border-b border-[#222] hover:bg-[#212121]">
                      <td className="px-4 py-3">
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                              style={{ backgroundColor: MODALITY_COLORS[e.modality] + '22', color: MODALITY_COLORS[e.modality] }}>
                          {e.modality}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[#a0a0a0]">{e.artifact_type}</td>
                      <td className="px-4 py-3 text-[#a0a0a0]">{e.source}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs" style={{ color: SEV_COLORS[e.sensitivity] }}>{e.sensitivity}</span>
                      </td>
                      <td className="px-4 py-3 text-[#6A6E73] text-xs font-mono">
                        {Object.keys(e.features).length} keys
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
            <h3 className="text-sm font-medium text-[#6A6E73] mb-3">Modality Distribution</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name }) => name}>
                  {pieData.map(d => (
                    <Cell key={d.name} fill={MODALITY_COLORS[d.name] || '#444'} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#212121', border: '1px solid #444' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-1 text-xs text-[#a0a0a0]">
              <p>Total: {evidence.length} artifacts</p>
              <p>Modalities: {Object.keys(modalityCounts).length}</p>
            </div>
          </div>
        </div>
      )}

      {!isLoading && evidence.length === 0 && (
        <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-8 text-center text-[#6A6E73]">
          No evidence artifacts yet. Run a fixture ingestion or submit evidence via the API.
        </div>
      )}
    </div>
  );
}
