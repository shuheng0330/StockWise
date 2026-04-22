import {
  getLatestAnalysisId,
  hydrateLatestAnalysisId,
  saveLatestAnalysisId,
  subscribeToLatestAnalysisId,
} from './analysisSession';

describe('analysis session storage', () => {
  const storage = new Map<string, string>();

  beforeEach(() => {
    storage.clear();
    Object.defineProperty(global, 'localStorage', {
      configurable: true,
      value: {
        getItem: jest.fn((key: string) => storage.get(key) ?? null),
        setItem: jest.fn((key: string, value: string) => storage.set(key, value)),
        removeItem: jest.fn((key: string) => storage.delete(key)),
        clear: jest.fn(() => storage.clear()),
      },
    });
  });

  it('persists the latest analysis id and notifies listeners', () => {
    const listener = jest.fn();
    const unsubscribe = subscribeToLatestAnalysisId(listener);

    expect(getLatestAnalysisId()).toBeNull();

    saveLatestAnalysisId('analysis-123');

    expect(getLatestAnalysisId()).toBe('analysis-123');
    expect(listener).toHaveBeenCalledWith('analysis-123');

    unsubscribe();
  });

  it('hydrates from a remote latest analysis lookup when browser storage is empty', async () => {
    const analysisId = await hydrateLatestAnalysisId(async () => 'analysis-from-db');

    expect(analysisId).toBe('analysis-from-db');
    expect(getLatestAnalysisId()).toBe('analysis-from-db');
  });
});
