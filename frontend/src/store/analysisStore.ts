import { create } from 'zustand';
import { AnalysisResponse, InventoryItem, FilterOptions } from '@/types';

interface AnalysisStore {
  currentAnalysis: AnalysisResponse | null;
  setCurrentAnalysis: (analysis: AnalysisResponse | null) => void;
  currentItem: InventoryItem | null;
  setCurrentItem: (item: InventoryItem | null) => void;
  filterOptions: FilterOptions;
  setFilterOptions: (options: Partial<FilterOptions>) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  currentAnalysis: null,
  setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
  currentItem: null,
  setCurrentItem: (item) => set({ currentItem: item }),
  filterOptions: {
    search: '',
    actions: [],
    categories: [],
  },
  setFilterOptions: (options) =>
    set((state) => ({
      filterOptions: { ...state.filterOptions, ...options },
    })),
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),
  error: null,
  setError: (error) => set({ error }),
}));
