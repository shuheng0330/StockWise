import { renderToStaticMarkup } from 'react-dom/server';

import { TradeoffVerdictCard } from './ItemSimulation';

describe('TradeoffVerdictCard', () => {
  it('renders a compact AI verdict below the simulation result', () => {
    const html = renderToStaticMarkup(
      <TradeoffVerdictCard
        verdict={{
          source: 'mock',
          verdict: 'Cash-heavy but safe',
          reason: 'This reduces urgency but commits cash and raises waste exposure.',
          confidence_note: 'Based on simulated metrics.',
          safety_status: 'validated',
        }}
        isLoading={false}
        error=""
        onRetry={() => undefined}
      />
    );

    expect(html).toContain('AI Trade-off Verdict');
    expect(html).toContain('Cash-heavy but safe');
    expect(html).toContain('This reduces urgency');
    expect(html).toContain('mock');
  });
});
