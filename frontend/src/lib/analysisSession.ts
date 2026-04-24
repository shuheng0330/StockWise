export const LATEST_ANALYSIS_ID_KEY = 'stockwise-latest-analysis-id';
export const ANALYSIS_HISTORY_KEY = 'stockwise-analysis-history';
export const ANALYSIS_HISTORY_MAX = 50;

export interface AnalysisHistoryEntry {
  analysisId: string;
  createdAt: string;
  label?: string;
  source?: 'manual' | 'upload' | 'unknown';
}

type AnalysisIdListener = (analysisId: string | null) => void;
type AnalysisHistoryListener = (history: AnalysisHistoryEntry[]) => void;

const listeners = new Set<AnalysisIdListener>();
const historyListeners = new Set<AnalysisHistoryListener>();

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

function notifyHistory(history: AnalysisHistoryEntry[]) {
  historyListeners.forEach((listener) => listener(history));
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

export function clearLatestAnalysisId() {
  getStorage()?.removeItem(LATEST_ANALYSIS_ID_KEY);
  notifyLatestAnalysisId(null);
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

export function getAnalysisHistory(): AnalysisHistoryEntry[] {
  const raw = getStorage()?.getItem(ANALYSIS_HISTORY_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (entry): entry is AnalysisHistoryEntry =>
          entry &&
          typeof entry === 'object' &&
          typeof entry.analysisId === 'string' &&
          typeof entry.createdAt === 'string'
      )
      .slice(0, ANALYSIS_HISTORY_MAX);
  } catch {
    return [];
  }
}

export function recordAnalysisInHistory(entry: {
  analysisId: string | null | undefined;
  label?: string;
  source?: AnalysisHistoryEntry['source'];
}): AnalysisHistoryEntry[] {
  const normalizedId = normalizeAnalysisId(entry.analysisId);
  if (!normalizedId) return getAnalysisHistory();

  const storage = getStorage();
  if (!storage) return getAnalysisHistory();

  const current = getAnalysisHistory().filter((item) => item.analysisId !== normalizedId);
  const next: AnalysisHistoryEntry[] = [
    {
      analysisId: normalizedId,
      createdAt: new Date().toISOString(),
      label: entry.label,
      source: entry.source ?? 'unknown',
    },
    ...current,
  ].slice(0, ANALYSIS_HISTORY_MAX);

  storage.setItem(ANALYSIS_HISTORY_KEY, JSON.stringify(next));
  notifyHistory(next);
  return next;
}

export function removeAnalysisFromHistory(analysisId: string): AnalysisHistoryEntry[] {
  const storage = getStorage();
  const next = getAnalysisHistory().filter((item) => item.analysisId !== analysisId);
  if (storage) {
    storage.setItem(ANALYSIS_HISTORY_KEY, JSON.stringify(next));
  }
  notifyHistory(next);
  return next;
}

export function clearAnalysisHistory(): void {
  getStorage()?.removeItem(ANALYSIS_HISTORY_KEY);
  notifyHistory([]);
}

export function subscribeToAnalysisHistory(listener: AnalysisHistoryListener) {
  historyListeners.add(listener);

  return () => {
    historyListeners.delete(listener);
  };
}
