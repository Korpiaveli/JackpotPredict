export type EntityCategory = 'person' | 'place' | 'thing'

export interface Prediction {
  rank: number
  answer: string
  confidence: number
  category: EntityCategory
  reasoning: string
}

export interface GuessRecommendation {
  should_guess: boolean
  confidence_threshold: number
  rationale: string
}

export interface PredictionResponse {
  session_id: string
  clue_number: number
  predictions: Prediction[]
  guess_recommendation: GuessRecommendation
  elapsed_time: number
  clue_history: string[]
  category_probabilities: Record<EntityCategory, number>
}

export interface ClueRequest {
  clue_text: string
  session_id?: string
}

export interface ResetResponse {
  session_id: string
  message: string
}

export interface ValidationResponse {
  is_valid: boolean
  canonical_spelling?: string
  error_type?: string
  suggestion?: string
  fuzzy_matches: string[]
}

export interface HealthResponse {
  status: string
  version: string
  entity_count: number
  active_sessions: number
  uptime_seconds: number
}
