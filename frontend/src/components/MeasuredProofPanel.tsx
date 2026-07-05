import { useEffect, useState } from 'react';
import { motion } from 'motion/react';

interface BenchmarkReport {
  generated_at: string;
  profile: string;
  iterations: number;
  hardware: { cpu_model: string; target: string };
  totals: {
    evidence_count: number;
    classification_count: number;
    evidence_sent_to_llm_or_media_model: number;
  };
  runtime: { p50_elapsed_ms: number; p95_elapsed_ms: number };
  compression: {
    cpu_pre_expensive_percent: number;
    threshold_percent: number;
    meets_98_cpu_claim: boolean;
  };
}

interface LatestResponse {
  status: 'ok' | 'missing';
  message?: string;
  report?: BenchmarkReport;
}

interface RunResponse {
  status: 'ok';
  report: BenchmarkReport;
}

interface MeasuredProofPanelProps {
  compact?: boolean;
}

export function MeasuredProofPanel({ compact = false }: MeasuredProofPanelProps) {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [status, setStatus] = useState<'loading' | 'missing' | 'ok' | 'running' | 'error'>('loading');

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/v1/benchmark/latest', { signal: controller.signal })
      .then(r => r.json())
      .then((data: LatestResponse) => {
        if (data.status === 'ok' && data.report) {
          setReport(data.report);
          setStatus('ok');
        } else {
          setStatus('missing');
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus('error');
      });
    return () => controller.abort();
  }, []);

  const runBenchmark = async () => {
    setStatus('running');
    try {
      const res = await fetch('/api/v1/benchmark/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: 'enterprise-signal-volume',
          iterations: 5,
          save: true,
          include_project_tests: false,
        }),
      });
      const data = await res.json() as RunResponse;
      setReport(data.report);
      setStatus('ok');
    } catch {
      setStatus('error');
    }
  };

  const percent = report?.compression.cpu_pre_expensive_percent;
  const meetsClaim = Boolean(report?.compression.meets_98_cpu_claim);
  const color = meetsClaim ? 'var(--rh-green)' : report ? 'var(--rh-orange)' : 'var(--rh-blue)';

  return (
    <motion.div
      onClick={(event) => event.stopPropagation()}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      aria-busy={status === 'running'}
      style={{
        background: 'var(--surface-1)',
        border: `1px solid ${meetsClaim ? 'var(--rh-green)40' : 'var(--border)'}`,
        borderRadius: 8,
        padding: compact ? 12 : 16,
        marginBottom: compact ? 0 : 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div style={{ fontSize: 10, color, fontFamily: 'Red Hat Mono, monospace', fontWeight: 700, letterSpacing: 1 }}>
            MEASURED PROOF
          </div>
          <div style={{ fontSize: compact ? 18 : 24, fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'Red Hat Display, sans-serif', marginTop: 2 }}>
            {report ? `${percent?.toFixed(2)}% CPU pre-expensive` : 'Benchmark required'}
          </div>
        </div>
        <button
          onClick={runBenchmark}
          disabled={status === 'running'}
          style={{
            background: status === 'running' ? 'var(--surface-2)' : 'var(--rh-red)',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            padding: compact ? '6px 10px' : '8px 14px',
            fontSize: 12,
            fontWeight: 700,
            whiteSpace: 'nowrap',
            opacity: status === 'running' ? 0.7 : 1,
          }}
        >
          {status === 'running' ? 'Running...' : report ? 'Re-run' : 'Run benchmark'}
        </button>
      </div>

      {report ? (
        <div style={{ marginTop: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr 1fr' : 'repeat(4, 1fr)', gap: 8 }}>
            <Stat label="Evidence" value={String(report.totals.evidence_count)} />
            <Stat label="Expensive" value={String(report.totals.evidence_sent_to_llm_or_media_model)} color={color} />
            <Stat label="p50" value={`${report.runtime.p50_elapsed_ms}ms`} />
            <Stat label="p95" value={`${report.runtime.p95_elapsed_ms}ms`} />
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 10, lineHeight: 1.5 }}>
            {meetsClaim ? '98% target met' : 'Measured below 98% target'} on {report.hardware.cpu_model || report.hardware.target}.
          </div>
        </div>
      ) : (
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 8, lineHeight: 1.5 }}>
          {status === 'loading'
            ? 'Loading latest benchmark report...'
            : status === 'error'
              ? 'Benchmark report unavailable.'
              : 'Run benchmark to verify CPU compression before showing an exact percentage.'}
        </div>
      )}
    </motion.div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ padding: 8, background: 'var(--surface-2)', borderRadius: 6, textAlign: 'center' }}>
      <div style={{ fontSize: 9, color: 'var(--text-disabled)', fontFamily: 'Red Hat Mono, monospace' }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 800, color: color || 'var(--text-secondary)', fontFamily: 'Red Hat Display, sans-serif' }}>{value}</div>
    </div>
  );
}
