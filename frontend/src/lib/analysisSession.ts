export const LATEST_ANALYSIS_ID_KEY = 'stockwise-latest-analysis-id';

type AnalysisIdListener = (analysisId: string | null) => void;

const listeners = new Set<AnalysisIdListener>();

function getStorage(): Storage | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage;
    }

    if (typeof globalThis !== 'undefined' && 'localStorage' in globalThis) {
      return (globalThis as typeof globalThis & { localStorage: Storage }).localStorage;
    }
  } catch {
    return null;
  }

  return null;
}

function normalizeAnalysisId(analysisId: string | null | undefined): string | null {
  const normalized = analysisId?.trim();
  return normalized || null;
}

function notifyLatestAnalysisId(analysisId: string | null) {
  listeners.forEach((listener) => listener(analysisId));
}

export function getLatestAnalysisId(): string | null {
  const stored = getStorage()?.getItem(LATEST_ANALYSIS_ID_KEY);
  return normalizeAnalysisId(stored);
}

export function saveLatestAnalysisId(analysisId: string | null | undefined) {
  const normalized = normalizeAnalysisId(analysisId);
  if (!normalized) return;

  getStorage()?.setItem(LATEST_ANALYSIS_ID_KEY, normalized);
  notifyLatestAnalysisId(normalized);
}

export async function hydrateLatestAnalysisId(
  fetchLatestAnalysisId: () => Promise<string | null | undefined>
): Promise<string | null> {
  const stored = getLatestAnalysisId();
  if (stored) return stored;

  const latestAnalysisId = normalizeAnalysisId(await fetchLatestAnalysisId());
  if (latestAnalysisId) {
    saveLatestAnalysisId(latestAnalysisId);
  }
  return latestAnalysisId;
}

export function subscribeToLatestAnalysisId(listener: AnalysisIdListener) {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}
