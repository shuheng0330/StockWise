import axios, { AxiosInstance } from 'axios';
import {
  AnalysisResponse,
  ChatRequest,
  ChatResponse,
  ExplanationRequest,
  ExplanationResponse,
  ManualItemInput,
  SimulationRequest,
  SimulationResponse,
} from '@/types';
import { supabase } from '@/lib/supabase';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

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

  async uploadCsv(file: File): Promise<AnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await this.client.post('/api/v1/analyses', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async createManualAnalysis(items: ManualItemInput[]): Promise<AnalysisResponse> {
    const response = await this.client.post('/api/v1/manual-analyses', { items });
    return response.data;
  }

  async getAnalysis(analysisId: string): Promise<AnalysisResponse> {
    const response = await this.client.get(`/api/v1/analyses/${analysisId}`);
    return response.data;
  }

  async getLatestAnalysis(): Promise<AnalysisResponse> {
    const response = await this.client.get('/api/v1/analyses/latest');
    return response.data;
  }

  async getRecords(analysisId: string): Promise<any> {
    const response = await this.client.get(`/api/v1/analyses/${analysisId}/records`);
    return response.data;
  }

  async updateRecord(analysisId: string, itemId: string | number, data: Partial<ManualItemInput>): Promise<any> {
    const response = await this.client.patch(
      `/api/v1/analyses/${analysisId}/items/${itemId}`,
      data
    );
    return response.data;
  }

  async deleteRecord(analysisId: string, itemId: string | number): Promise<void> {
    await this.client.delete(`/api/v1/analyses/${analysisId}/items/${itemId}`);
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

  async getExplanation(
    analysisId: string,
    itemId: string | number,
    request?: ExplanationRequest
  ): Promise<ExplanationResponse> {
    const response = await this.client.post(
      `/api/v1/analyses/${analysisId}/items/${itemId}/explanation`,
      request || {}
    );
    return response.data;
  }

  async getAiChat(
    analysisId: string,
    request: ChatRequest
  ): Promise<ChatResponse> {
    const response = await this.client.post(
      `/api/v1/analyses/${analysisId}/ai-chat`,
      request
    );
    return response.data;
  }
}

export const apiClient = new ApiClient();
