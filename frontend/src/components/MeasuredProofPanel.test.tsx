import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { MeasuredProofPanel } from './MeasuredProofPanel';

const passingReport = {
  generated_at: '2026-07-05T00:00:00Z',
  profile: 'enterprise-signal-volume',
  iterations: 5,
  hardware: { cpu_model: 'Intel Xeon 6', target: 'Intel Xeon 6 lab, local fallback' },
  totals: {
    evidence_count: 1800,
    classification_count: 3200,
    evidence_sent_to_llm_or_media_model: 0,
  },
  runtime: { p50_elapsed_ms: 12.3, p95_elapsed_ms: 18.4 },
  compression: {
    cpu_pre_expensive_percent: 100,
    threshold_percent: 98,
    meets_98_cpu_claim: true,
  },
};

function mockFetch(payloads: unknown[]) {
  const responses = payloads.map(payload => Promise.resolve({
    json: () => Promise.resolve(payload),
  } as Response));
  vi.stubGlobal('fetch', vi.fn(() => responses.shift() || responses[responses.length - 1]));
}

describe('MeasuredProofPanel', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('shows the no-report state', async () => {
    mockFetch([{ status: 'missing', message: 'No benchmark report found' }]);

    render(<MeasuredProofPanel />);

    expect(await screen.findByText('Benchmark required')).toBeInTheDocument();
    expect(screen.getByText(/Run benchmark to verify CPU compression/)).toBeInTheDocument();
  });

  it('shows measured passing proof from latest report', async () => {
    mockFetch([{ status: 'ok', report: passingReport }]);

    render(<MeasuredProofPanel />);

    expect(await screen.findByText('100.00% CPU pre-expensive')).toBeInTheDocument();
    expect(screen.getByText(/98% target met/)).toBeInTheDocument();
  });

  it('runs a benchmark from the empty state', async () => {
    mockFetch([
      { status: 'missing', message: 'No benchmark report found' },
      { status: 'ok', report: passingReport },
    ]);

    render(<MeasuredProofPanel />);

    fireEvent.click(await screen.findByText('Run benchmark'));

    expect(await screen.findByText('100.00% CPU pre-expensive')).toBeInTheDocument();
  });
});
