export type EntityCategory = 'person' | 'place' | 'thing'

export type SemanticMatch = 'strong' | 'medium' | 'weak'

export type AgentName = 'lateral' | 'wordsmith' | 'popculture' | 'literal' | 'wildcard'

export type AgreementStrength = 'strong' | 'moderate' | 'weak' | 'none'

// Agent prediction from MoA architecture
export interface AgentPrediction {
  answer: string
  confidence: number
  reasoning: string
}

// Vote breakdown for an answer
export interface VoteBreakdown {
  answer: string
  total_votes: number
  agents: AgentName[]
}

// Voting result from weighted voting
export interface VotingResult {
  recommended_pick: string
  key_insight: string
  agreement_strength: AgreementStrength
  vote_breakdown: VoteBreakdown[]
}

// Oracle (Claude 3.5 Sonnet) meta-synthesizer
export interface OracleGuess {
  answer: string
  confidence: number  // 0-100
  explanation: string
}

export interface OracleSynthesis {
  top_3: OracleGuess[]
  key_theme: string
  blind_spot: string
  latency_ms: number
  misdirection_detected?: string  // MOA v3: What trap is the clue writer setting?
}

// MOA v3: Cultural reference detected in clues
export type CulturalMatchSource = 'quote' | 'pattern' | 'historical'

export interface CulturalMatch {
  keyword: string
  answer: string
  source: CulturalMatchSource
  confidence: number  // 0.0-1.0
}

// Legacy prediction format (kept for backwards compatibility)
export interface Prediction {
  rank: number
  answer: string
  confidence: number
  category: EntityCategory
  reasoning: string
  semantic_match?: SemanticMatch
}

export interface GuessRecommendation {
  should_guess: boolean
  confidence_threshold: number
  rationale: string
}

// MoA-compatible prediction response
export interface PredictionResponse {
  session_id: string
  clue_number: number

  // 5-Agent MoA predictions
  agents: Record<AgentName, AgentPrediction | null>
  voting: VotingResult | null
  recommended_pick: string
  key_insight: string
  agreement_strength: AgreementStrength
  agents_responded: number
  agreements: AgentName[]

  // Oracle meta-synthesis (Claude 3.5 Sonnet)
  oracle: OracleSynthesis | null

  // Legacy fields (deprecated)
  predictions: Prediction[]
  gemini_predictions?: Prediction[]
  openai_predictions?: Prediction[]

  guess_recommendation: GuessRecommendation
  elapsed_time: number
  clue_history: string[]
  category_probabilities: Record<EntityCategory, number>

  // MOA v3: Cultural context fields
  cultural_matches?: CulturalMatch[]
  clue_strategy?: string
}

// Agent info for UI display
export const AGENT_INFO: Record<AgentName, { emoji: string; label: string; description: string }> = {
  lateral: { emoji: '', label: 'Lateral', description: 'Multi-hop associations' },
  wordsmith: { emoji: '', label: 'Words', description: 'Puns & wordplay' },
  popculture: { emoji: '', label: 'Pop', description: 'Netflix/trending' },
  literal: { emoji: '', label: 'Lit', description: 'Trap detection' },
  wildcard: { emoji: '', label: 'Wild', description: 'Creative leaps' },
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

export interface FeedbackRequest {
  session_id: string
  correct_answer: string
  category: EntityCategory
  clues: string[]
  solved_at_clue?: number
  key_insight?: string
}

export interface FeedbackResponse {
  success: boolean
  message: string
}

// Category statistics for analytics
export interface CategoryStats {
  total: number
  avg_solve_clue: number
  insights_provided: number
}

// Analytics response from /api/analytics
export interface AnalyticsResponse {
  total_games: number
  category_breakdown: Record<string, CategoryStats>
  avg_solve_clue: number
  early_solves: number
  late_solves: number
  insights_provided: number
  insights_percentage: number
  recent_answers: string[]
}
