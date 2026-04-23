import { buildAnalysisNavigationTargets } from './navigationTargets';

describe('analysis navigation targets', () => {
  it('keeps item-specific simulation and explanation links on the current item', () => {
    expect(buildAnalysisNavigationTargets('analysis-1', 10)).toEqual({
      analysisHref: '/dashboard/analysis-1',
      recordsHref: '/records/analysis-1',
      simulationHref: '/simulation/analysis-1/10',
      explanationHref: '/explanation/analysis-1/10',
    });
  });

  it('does not point item-specific links back to the dashboard when no item is selected', () => {
    expect(buildAnalysisNavigationTargets('analysis-1')).toEqual({
      analysisHref: '/dashboard/analysis-1',
      recordsHref: '/records/analysis-1',
      simulationHref: undefined,
      explanationHref: undefined,
    });
  });
});
