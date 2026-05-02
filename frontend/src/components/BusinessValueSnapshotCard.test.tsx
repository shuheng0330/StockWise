import { renderToStaticMarkup } from 'react-dom/server';

import { BusinessValueSnapshotCard } from './BusinessValueSnapshotCard';

describe('BusinessValueSnapshotCard', () => {
  it('renders estimated opportunity, plan, and value-to-price copy without claiming realized savings', () => {
    const html = renderToStaticMarkup(
      <BusinessValueSnapshotCard
        snapshot={{
          monthlyWasteAvoided: 40,
          monthlyStockoutLossAvoided: 80,
          monthlyOpportunityValue: 120,
          monthlyTimeSavedHours: 1,
          suggestedPlan: {
            name: 'Starter',
            monthlyPrice: 39,
            rationale: 'Best fit for a small catalogue with measurable inventory exposure.',
          },
          valueToCostRatio: 3.1,
          assumptions: [
            'Uses current analysis results as a monthly opportunity estimate.',
            'Assumes four inventory review cycles per month.',
          ],
        }}
      />
    );

    expect(html).toContain('Business Value Snapshot');
    expect(html).toContain('Estimated opportunity');
    expect(html).toContain('RM120.00');
    expect(html).toContain('Starter');
    expect(html).toContain('3.1x');
    expect(html).toContain('3.1x</p>');
    expect(html).toContain('Value-to-price ratio');
    expect(html).not.toContain('guaranteed');
    expect(html).not.toContain('actual savings');
  });
});
