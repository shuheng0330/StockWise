import { renderToStaticMarkup } from 'react-dom/server';

import { DecisionBriefResponse } from '@/types';
import { AIAdvisorPanel } from './AIAdvisorPanel';
import { AIDecisionBriefCard } from './AIDecisionBriefCard';
import { ExplanationDrawer } from './ExplanationDrawer';

const brief: DecisionBriefResponse = {
  source: 'fallback',
  safety_status: 'fallback_used',
  summary: 'Restock eggs first, buy less paneer, and delay rice.',
  buy_today: [
    { item_id: 2, item_name: 'Eggs', recommended_action: 'RESTOCK_NOW', reason: 'Shortage risk is highest.' },
  ],
  buy_less: [
    { item_id: 1, item_name: 'Paneer', recommended_action: 'BUY_LESS', reason: 'Waste risk is elevated.' },
  ],
  delay: [
    { item_id: 3, item_name: 'Rice', recommended_action: 'DELAY_PURCHASE', reason: 'Coverage is healthy.' },
  ],
  estimated_impact: {
    cash: 'Delay low-risk purchases to preserve cash.',
    waste: 'Buy less for high waste-risk items.',
    shortage: 'Restock urgent items first.',
  },
  top_tradeoffs: ['Restocking eggs uses cash but protects availability.'],
  recommended_order: ['Restock eggs', 'Buy less paneer', 'Delay rice'],
  confidence_note: 'Fallback brief generated from deterministic rules.',
  warning_flag: 'Review records before ordering.',
};

const fallbackExplanation = {
  source: 'fallback' as const,
  item_name: 'Paneer',
  recommended_action: 'BUY_LESS' as const,
  priority_level: 'MEDIUM' as const,
  short_reason: 'Paneer has high waste risk.',
  decision_explanation: 'Buy a smaller quantity.',
  tradeoff_summary: 'Lower waste risk with closer monitoring.',
  suggested_next_step: 'Review the order.',
  confidence_note: 'Fallback explanation generated from deterministic rules.',
  warning_flag: 'Review before ordering.',
};

describe('AIDecisionBriefCard', () => {
  it('renders a loading state independently from the dashboard', () => {
    const html = renderToStaticMarkup(
      <AIDecisionBriefCard analysisId="analysis-1" isLoading brief={null} error="" />
    );

    expect(html).toContain('AI Decision Brief');
    expect(html).toContain('Preparing decision brief');
  });

  it('renders fallback safety state and review records escalation', () => {
    const html = renderToStaticMarkup(
      <AIDecisionBriefCard analysisId="analysis-1" isLoading={false} brief={brief} error="" />
    );

    expect(html).toContain('fallback');
    expect(html).toContain('fallback used');
    expect(html).toContain('Review Records');
    expect(html).toContain('Restock eggs first');
  });

  it('renders a retry action for fallback briefs when available', () => {
    const html = renderToStaticMarkup(
      <AIDecisionBriefCard
        analysisId="analysis-1"
        isLoading={false}
        brief={brief}
        error=""
        onRetry={() => undefined}
        isRetrying={false}
      />
    );

    expect(html).toContain('Retry AI');
  });
});

describe('AIAdvisorPanel', () => {
  it('renders as an AI Advisor launcher instead of a full dashboard panel', () => {
    const html = renderToStaticMarkup(
      <AIAdvisorPanel analysisId="analysis-1" onSendMessage={async () => {
        throw new Error('not used');
      }} />
    );

    expect(html).toContain('AI Advisor');
    expect(html).toContain('Ask the AI Advisor');
    expect(html).not.toContain('AI Copilot');
    expect(html).not.toContain('Ask StockWise what to do next');
  });
});

describe('ExplanationDrawer', () => {
  it('renders a retry action for fallback explanations', () => {
    const html = renderToStaticMarkup(
      <ExplanationDrawer
        explanation={fallbackExplanation}
        onClose={() => undefined}
        onRetry={() => undefined}
      />
    );

    expect(html).toContain('Fallback explanation');
    expect(html).toContain('Retry AI');
  });
});
