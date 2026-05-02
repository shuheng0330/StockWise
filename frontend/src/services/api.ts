import axios, { AxiosInstance } from 'axios';
import {
  AnalysisResponse,
  ChatRequest,
  ChatResponse,
  DecisionBriefResponse,
  ExplanationRequest,
  ExplanationResponse,
  ManualItemInput,
  RecordsResponse,
  SimulationRequest,
  SimulationResponse,
  TradeoffVerdictRequest,
  TradeoffVerdictResponse,
} from '@/types';
import { supabase } from '@/lib/supabase';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private analysisCache = new Map<string, AnalysisResponse>();
  private recordsCache = new Map<string, any>();

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use(async (config) => {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;

      if (token) {
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${token}`;
      }

      return config;
    });
  }

  private async cacheKey(analysisId: string): Promise<string> {
    const { data } = await supabase.auth.getSession();
    return `${data.session?.access_token || 'anonymous'}:${analysisId}`;
  }

  private async cacheAnalysis(response: AnalysisResponse): Promise<void> {
    this.analysisCache.set(await this.cacheKey(response.analysis_id), response);
  }

  private async clearAnalysisCaches(analysisId: string): Promise<void> {
    const key = await this.cacheKey(analysisId);
    this.analysisCache.delete(key);
    this.recordsCache.delete(key);
  }

  async uploadCsv(file: File, baseAnalysisId?: string | null): Promise<AnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (baseAnalysisId) {
      formData.append('base_analysis_id', baseAnalysisId);
    }
    const response = await this.client.post('/api/v1/analyses', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    await this.cacheAnalysis(response.data);
    return response.data;
  }

  async createManualAnalysis(items: ManualItemInput[], baseAnalysisId?: string | null): Promise<AnalysisResponse> {
    const response = await this.client.post('/api/v1/manual-analyses', {
      items,
      base_analysis_id: baseAnalysisId || null,
    });
    await this.cacheAnalysis(response.data);
    return response.data;
  }

  async getAnalysis(analysisId: string, options?: { refresh?: boolean }): Promise<AnalysisResponse> {
    const key = await this.cacheKey(analysisId);
    if (!options?.refresh && this.analysisCache.has(key)) {
      return this.analysisCache.get(key) as AnalysisResponse;
    }
    const response = await this.client.get(`/api/v1/analyses/${analysisId}`);
    this.analysisCache.set(key, response.data);
    return response.data;
  }

  async getLatestAnalysis(): Promise<AnalysisResponse> {
    const response = await this.client.get('/api/v1/analyses/latest');
    return response.data;
  }

  async getRecords(analysisId: string, options?: { refresh?: boolean }): Promise<RecordsResponse> {
    const key = await this.cacheKey(analysisId);
    if (!options?.refresh && this.recordsCache.has(key)) {
      return this.recordsCache.get(key);
    }
    const response = await this.client.get(`/api/v1/analyses/${analysisId}/records`);
    this.recordsCache.set(key, response.data);
    return response.data;
  }

  async updateRecord(analysisId: string, itemId: string | number, data: Partial<ManualItemInput>): Promise<any> {
    const response = await this.client.patch(
      `/api/v1/analyses/${analysisId}/items/${itemId}`,
      data
    );
    await this.clearAnalysisCaches(analysisId);
    return response.data;
  }

  async deleteRecord(analysisId: string, itemId: string | number): Promise<void> {
    await this.client.delete(`/api/v1/analyses/${analysisId}/items/${itemId}`);
    await this.clearAnalysisCaches(analysisId);
  }

  async simulate(
    analysisId: string,
    itemId: string | number,
    request: SimulationRequest
  ): Promise<SimulationResponse> {
    const response = await this.client.post(
      `/api/v1/analyses/${analysisId}/items/${itemId}/simulate`,
      request
    );
    return response.data;
  }

  async getTradeoffVerdict(
    analysisId: string,
    itemId: string | number,
    request: TradeoffVerdictRequest,
    options?: { refresh?: boolean }
  ): Promise<TradeoffVerdictResponse> {
    const response = await this.client.post(
      `/api/v1/analyses/${analysisId}/items/${itemId}/tradeoff-verdict`,
      request,
      { params: options?.refresh ? { refresh: true } : undefined }
    );
    return response.data;
  }

  async getExplanation(
    analysisId: string,
    itemId: string | number,
    request?: ExplanationRequest,
    options?: { refresh?: boolean }
  ): Promise<ExplanationResponse> {
    const response = await this.client.post(
      `/api/v1/analyses/${analysisId}/items/${itemId}/explanation`,
      request || {},
      { params: options?.refresh ? { refresh: true } : undefined }
    );
    return response.data;
  }

  async getAiChat(
    analysisId: string,
    request: ChatRequest,
    options?: { refresh?: boolean }
  ): Promise<ChatResponse> {
    const response = await this.client.post(
      `/api/v1/analyses/${analysisId}/ai-chat`,
      request,
      { params: options?.refresh ? { refresh: true } : undefined }
    );
    return response.data;
  }

  async getDecisionBrief(analysisId: string, options?: { refresh?: boolean }): Promise<DecisionBriefResponse> {
    const response = await this.client.get(
      `/api/v1/analyses/${analysisId}/decision-brief`,
      { params: options?.refresh ? { refresh: true } : undefined }
    );
    return response.data;
  }
}

export const apiClient = new ApiClient();
