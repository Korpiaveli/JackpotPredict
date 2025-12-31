import type { ClueRequest, PredictionResponse, ResetResponse, ValidationResponse, HealthResponse, FeedbackRequest, FeedbackResponse, AnalyticsResponse } from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

class APIClient {
  private baseURL: string

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        error: 'UnknownError',
        message: 'An unexpected error occurred',
      }))
      throw new Error(error.message || `HTTP ${response.status}`)
    }

    return response.json()
  }

  async submitClue(request: ClueRequest): Promise<PredictionResponse> {
    return this.request<PredictionResponse>('/predict', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async reset(sessionId?: string): Promise<ResetResponse> {
    return this.request<ResetResponse>('/reset', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    })
  }

  async validate(answer: string): Promise<ValidationResponse> {
    return this.request<ValidationResponse>('/validate', {
      method: 'POST',
      body: JSON.stringify({ answer }),
    })
  }

  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health')
  }

  async submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
    return this.request<FeedbackResponse>('/feedback', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async repredict(clues: string[], sessionId?: string): Promise<PredictionResponse> {
    return this.request<PredictionResponse>('/repredict', {
      method: 'POST',
      body: JSON.stringify({ clues, session_id: sessionId }),
    })
  }

  async getAnalytics(): Promise<AnalyticsResponse> {
    return this.request<AnalyticsResponse>('/analytics')
  }
}

export const api = new APIClient()
