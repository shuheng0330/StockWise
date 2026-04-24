export function buildAnalysisNavigationTargets(
  analysisId: string | undefined,
  itemId?: string | number
) {
  const hasItem = itemId !== undefined && itemId !== null && String(itemId).trim() !== '';

  return {
    analysisHref: analysisId ? `/dashboard/${analysisId}` : undefined,
    recordsHref: analysisId ? `/records/${analysisId}` : undefined,
    simulationHref: analysisId && hasItem ? `/simulation/${analysisId}/${itemId}` : undefined,
    explanationHref: analysisId && hasItem ? `/explanation/${analysisId}/${itemId}` : undefined,
    exportHref: analysisId ? `/export/${analysisId}` : undefined,
  };
}
