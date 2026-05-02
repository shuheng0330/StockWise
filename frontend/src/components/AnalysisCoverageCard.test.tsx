import { renderToStaticMarkup } from 'react-dom/server';

import { AnalysisCoverageCard } from './AnalysisCoverageCard';

describe('AnalysisCoverageCard', () => {
  it('shows that multiple uploaded rows are collapsed into current item snapshots', () => {
    const html = renderToStaticMarkup(
      <AnalysisCoverageCard
        rowCount={30}
        itemCount={10}
        dateRange={{ start: '2025-08-17', end: '2025-09-17' }}
      />
    );

    expect(html).toContain('30');
    expect(html).toContain('Source observations');
    expect(html).toContain('10');
    expect(html).toContain('Current item snapshots');
    expect(html).toContain('2025-08-17');
    expect(html).toContain('2025-09-17');
    expect(html).toContain('latest row for each item');
  });
});
