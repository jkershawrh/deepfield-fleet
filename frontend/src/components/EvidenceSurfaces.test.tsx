import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { LedgerChainView } from './LedgerChainView';
import { TestMatrixCompact } from './TestMatrixCompact';

describe('evidence surfaces', () => {
  afterEach(cleanup);

  it('does not fabricate ledger chains when no external evidence is supplied', () => {
    render(<LedgerChainView />);

    expect(screen.getByText(/No live immutable-ledger evidence is attached/)).toBeInTheDocument();
    expect(screen.queryByText(/847 entries/)).not.toBeInTheDocument();
  });

  it('marks the default capability matrix as illustrative', () => {
    render(<TestMatrixCompact />);

    expect(screen.getByText(/Illustrative Cells, Evidence Required/)).toBeInTheDocument();
    expect(screen.queryByText(/All Green/)).not.toBeInTheDocument();
  });
});
