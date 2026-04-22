import axios, { AxiosInstance } from 'axios';
import {
  AnalysisResponse,
  ExplanationRequest,
  ExplanationResponse,
  ManualItemInput,
  SimulationRequest,
  SimulationResponse,
} from '@/types';

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
    // Backend expects an object with `items: [...]` not a bare array
    const payload = { items };
    const response = await this.client.post('/api/v1/manual-analyses', payload);
    return response.data;
  }

  async getAnalysis(analysisId: string): Promise<AnalysisResponse> {
    const response = await this.client.get(`/api/v1/analyses/${analysisId}`);
    return response.data;
  }

  async getRecords(analysisId: string): Promise<any> {
    const response = await this.client.get(`/api/v1/analyses/${analysisId}/records`);
    return response.data;
  }

  async updateRecord(analysisId: string, itemId: string, data: Partial<ManualItemInput>): Promise<any> {
    const response = await this.client.patch(
      `/api/v1/analyses/${analysisId}/items/${itemId}`,
      data
    );
    return response.data;
  }

  async deleteRecord(analysisId: string, itemId: string): Promise<void> {
    await this.client.delete(`/api/v1/analyses/${analysisId}/items/${itemId}`);
  }

  async simulate(
    analysisId: string,
    itemId: string,
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
    itemId: string,
    request?: ExplanationRequest
  ): Promise<ExplanationResponse> {
    const response = await this.client.post(
      `/api/v1/analyses/${analysisId}/items/${itemId}/explanation`,
      request || {}
    );
    return response.data;
  }
}

export const apiClient = new ApiClient();
