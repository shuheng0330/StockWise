import { SimulationResponse } from '@/types';

export async function runSimulationAndStore(
  simulatedOrderQty: number,
  simulate: (qty: number) => Promise<SimulationResponse>,
  storeResult: (result: SimulationResponse) => void
): Promise<SimulationResponse> {
  const result = await simulate(simulatedOrderQty);
  storeResult(result);
  return result;
}

export function buildSimulatedExplanationHref(
  analysisId: string | string[] | undefined,
  itemId: string | string[] | undefined,
  simulatedOrderQty: number
): string {
  const normalizedAnalysisId = Array.isArray(analysisId) ? analysisId[0] : analysisId;
  const normalizedItemId = Array.isArray(itemId) ? itemId[0] : itemId;

  return `/explanation/${normalizedAnalysisId}/${normalizedItemId}?simulated=${simulatedOrderQty}`;
}

export function buildSimulatedChatHref(
  analysisId: string | string[] | undefined,
  itemId: string | string[] | undefined,
  simulatedOrderQty: number
): string {
  const normalizedAnalysisId = Array.isArray(analysisId) ? analysisId[0] : analysisId;
  const normalizedItemId = Array.isArray(itemId) ? itemId[0] : itemId;
  const prompt = encodeURIComponent('What changed after my simulation?');

  return `/dashboard/${normalizedAnalysisId}?chatItemId=${normalizedItemId}&simulated=${simulatedOrderQty}&chatPrompt=${prompt}`;
}
