import { ChatMessage, ChatRequest, ChatSimulationContext } from '@/types';

export const AI_COPILOT_STARTER_PROMPTS = [
  'What should I buy today?',
  'Why is dairy risky this week?',
  'Which items can I delay to save cash?',
];

export function buildInitialCopilotRequest(
  prompt: string,
  simulationContext?: ChatSimulationContext
): ChatRequest {
  return {
    message: prompt,
    recent_messages: [],
    ...(simulationContext ? { simulation_context: simulationContext } : {}),
  };
}

export function buildNextCopilotRequest(
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
