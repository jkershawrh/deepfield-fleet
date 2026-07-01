import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api, ClassificationRecord } from '../api/client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const TIER_COLORS: Record<string, string> = {
  nano: '#0071C5', micro: '#3E8635', macro: '#6753AC', human: '#F0AB00',
};
const SEV_COLORS: Record<string, string> = {
  critical: '#C9190B', high: '#EE0000', medium: '#F0AB00', low: '#0071C5', info: '#6A6E73',
};

export default function ClassificationCascade() {
  const [tierFilter, setTierFilter] = useState('');
  const { data: records = [], isLoading } = useQuery({
    queryKey: ['classifications', tierFilter],
    queryFn: () => api.classification.listRecords(tierFilter || undefined),
  });

  const byTier = records.reduce((acc, r) => {
    acc[r.agent_tier] = (acc[r.agent_tier] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  const tierData = Object.entries(byTier).map(([tier, count]) => ({ tier, count }));

  const bySeverity = records.reduce((acc, r) => {
    acc[r.severity] = (acc[r.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  const sevData = Object.entries(bySeverity).map(([sev, count]) => ({ sev, count }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Classification Cascade</h1>
        <select
          value={tierFilter}
          onChange={e => setTierFilter(e.target.value)}
          className="bg-[#212121] border border-[#444] rounded px-3 py-1.5 text-sm"
        >
          <option value="">All tiers</option>
          <option value="nano">Nano</option>
          <option value="micro">Micro</option>
          <option value="macro">Macro</option>
        </select>
      </div>

      {isLoading && <p className="text-[#6A6E73]">Loading classifications...</p>}

      {records.length > 0 && (
        <>
          {/* Cascade Swimlanes */}
          <div className="grid grid-cols-3 gap-4">
            {['nano', 'micro', 'macro'].map(tier => {
              const tierRecords = records.filter(r => r.agent_tier === tier);
              return (
                <div key={tier} className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: TIER_COLORS[tier] }} />
                    <h3 className="text-sm font-medium uppercase">{tier}</h3>
                    <span className="text-xs text-[#6A6E73] ml-auto">{tierRecords.length}</span>
                  </div>
                  <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
                    {tierRecords.map(r => (
                      <div key={r.classification_id} className="bg-[#212121] rounded p-2 border border-[#333] text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{r.agent_name}</span>
                          <span style={{ color: SEV_COLORS[r.severity] }}>{r.severity}</span>
                        </div>
                        <div className="text-[#a0a0a0] mt-0.5">
                          {r.taxonomy}/{r.class_name}
                          <span className="ml-2 text-[#6A6E73]">{(r.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    ))}
                    {tierRecords.length === 0 && (
                      <p className="text-[#6A6E73] text-xs">No records</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
              <h3 className="text-sm font-medium text-[#6A6E73] mb-3">Records by Tier</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={tierData}>
                  <XAxis dataKey="tier" tick={{ fill: '#a0a0a0', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#6A6E73', fontSize: 11 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#212121', border: '1px solid #444' }} />
                  <Bar dataKey="count">
                    {tierData.map(d => <Cell key={d.tier} fill={TIER_COLORS[d.tier] || '#444'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-4">
              <h3 className="text-sm font-medium text-[#6A6E73] mb-3">Records by Severity</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={sevData}>
                  <XAxis dataKey="sev" tick={{ fill: '#a0a0a0', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#6A6E73', fontSize: 11 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#212121', border: '1px solid #444' }} />
                  <Bar dataKey="count">
                    {sevData.map(d => <Cell key={d.sev} fill={SEV_COLORS[d.sev] || '#444'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {!isLoading && records.length === 0 && (
        <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-8 text-center text-[#6A6E73]">
          No classification records yet. Run a classification cascade via the API.
        </div>
      )}
    </div>
  );
}
