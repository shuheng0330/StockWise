import { ChatMessage, ChatRequest, ChatSimulationContext } from '@/types';

export const AI_ADVISOR_STARTER_PROMPTS = [
  "What's the biggest risk in today's plan?",
  'Why is dairy risky this week?',
  'Which items can I delay to save cash?',
];

// Backward-compatible alias for older imports.
export const AI_Advisor_STARTER_PROMPTS = AI_ADVISOR_STARTER_PROMPTS;
// Backward-compatible alias for older Copilot naming.
export const AI_COPILOT_STARTER_PROMPTS = AI_ADVISOR_STARTER_PROMPTS;

export function buildInitialAdvisorRequest(
  prompt: string,
  simulationContext?: ChatSimulationContext
): ChatRequest {
  return {
    message: prompt,
    recent_messages: [],
    ...(simulationContext ? { simulation_context: simulationContext } : {}),
  };
}

export function buildNextAdvisorRequest(
  message: string,
  recentMessages: ChatMessage[],
  simulationContext?: ChatSimulationContext
): ChatRequest {
  return {
    message,
    recent_messages: recentMessages.slice(-4),
    ...(simulationContext ? { simulation_context: simulationContext } : {}),
  };
}
