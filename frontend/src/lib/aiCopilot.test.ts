import {
  AI_COPILOT_STARTER_PROMPTS,
  buildInitialCopilotRequest,
  buildNextCopilotRequest,
} from './aiCopilot';

describe('ai copilot helpers', () => {
  it('exposes the starter prompts shown in the dashboard panel', () => {
    expect(AI_COPILOT_STARTER_PROMPTS).toContain('What should I buy today?');
    expect(AI_COPILOT_STARTER_PROMPTS).toContain('Why is dairy risky this week?');
  });

  it('builds an initial simulation-aware request from dashboard handoff state', () => {
    expect(
      buildInitialCopilotRequest('What changed after my simulation?', {
        item_id: 10,
        simulated_order_qty: 12,
      })
    ).toEqual({
      message: 'What changed after my simulation?',
      recent_messages: [],
      simulation_context: { item_id: 10, simulated_order_qty: 12 },
    });
  });

  it('builds the next request from short local history', () => {
    expect(
      buildNextCopilotRequest('Which items can I delay to save cash?', [
        { role: 'user', content: 'What should I buy today?' },
        { role: 'assistant', content: 'Buy urgent items first.' },
      ])
    ).toEqual({
      message: 'Which items can I delay to save cash?',
      recent_messages: [
        { role: 'user', content: 'What should I buy today?' },
        { role: 'assistant', content: 'Buy urgent items first.' },
      ],
    });
  });
});
