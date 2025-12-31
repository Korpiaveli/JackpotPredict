import { create } from 'zustand'
import type { PredictionResponse, AgentName, AgentPrediction, OracleGuess, VotingResult } from '../types/api'

// Simplified prediction snapshot for trend tracking
export interface PredictionSnapshot {
  clueNumber: number
  recommendedPick: string
  recommendedConfidence: number
  oracleTopPick: string | null
  oracleConfidence: number | null
  agreementStrength: string
}

// Full round prediction for history tracking
export interface RoundPrediction {
  clueNumber: number
  clueText: string
  agents: Record<AgentName, AgentPrediction | null>
  oracleTop3: OracleGuess[]
  votingResult: VotingResult | null
  recommendedPick: string
  timestamp: number
}

// First correct analysis for post-game summary
export interface FirstCorrectResult {
  agentName: AgentName | 'oracle'
  clueNumber: number
  confidence: number
}

export function computeFirstCorrect(
  roundHistory: RoundPrediction[],
  correctAnswer: string
): FirstCorrectResult[] {
  const results: FirstCorrectResult[] = []
  const normalizedAnswer = correctAnswer.toLowerCase().trim()

  // Track which agents/oracle we've already found first correct for
  const found = new Set<string>()

  for (const round of roundHistory) {
    // Check each agent
    for (const [agentName, pred] of Object.entries(round.agents)) {
      if (!pred || found.has(agentName)) continue
      if (pred.answer.toLowerCase().trim() === normalizedAnswer) {
        results.push({
          agentName: agentName as AgentName,
          clueNumber: round.clueNumber,
          confidence: pred.confidence
        })
        found.add(agentName)
      }
    }

    // Check Oracle top 3
    if (!found.has('oracle')) {
      for (const guess of round.oracleTop3) {
        if (guess.answer.toLowerCase().trim() === normalizedAnswer) {
          results.push({
            agentName: 'oracle',
            clueNumber: round.clueNumber,
            confidence: guess.confidence
          })
          found.add('oracle')
          break
        }
      }
    }
  }

  // Sort by clue number (earliest first)
  return results.sort((a, b) => a.clueNumber - b.clueNumber)
}

interface PuzzleState {
  sessionId: string | null
  clueHistory: string[]
  latestPrediction: PredictionResponse | null
  predictionHistory: PredictionSnapshot[]  // Track all predictions for trend viz
  roundHistory: RoundPrediction[]          // Full round history for post-game analysis
  isLoading: boolean
  error: string | null

  // Timer state
  timerKey: number              // Increment to force timer reset
  gameStarted: boolean          // Timer only runs after first clue
  responseTimes: number[]       // Track elapsed_time per clue

  // Puzzle completion state
  puzzleComplete: boolean       // True when puzzle is finished

  // Actions
  setSessionId: (id: string) => void
  addClue: (clue: string) => void
  updateClue: (index: number, newText: string) => void  // Edit a clue
  setPrediction: (prediction: PredictionResponse) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
  clearRoundHistory: () => void  // Clear history when re-predicting

  // Timer actions
  startGame: () => void
  resetTimer: () => void
  addResponseTime: (time: number) => void

  // Puzzle completion actions
  completePuzzle: () => void
}

export const usePuzzleStore = create<PuzzleState>((set) => ({
  sessionId: null,
  clueHistory: [],
  latestPrediction: null,
  predictionHistory: [],
  roundHistory: [],
  isLoading: false,
  error: null,

  // Timer state
  timerKey: 0,
  gameStarted: false,
  responseTimes: [],

  // Puzzle completion state
  puzzleComplete: false,

  setSessionId: (id) => set({ sessionId: id }),

  addClue: (clue) =>
    set((state) => ({
      clueHistory: [...state.clueHistory, clue],
    })),

  updateClue: (index, newText) =>
    set((state) => {
      const newClueHistory = [...state.clueHistory]
      newClueHistory[index] = newText
      return { clueHistory: newClueHistory }
    }),

  setPrediction: (prediction) =>
    set((state) => {
      // Create snapshot for trend tracking
      const topVoteScore = prediction.voting?.vote_breakdown?.[0]?.total_votes ?? 0
      const snapshot: PredictionSnapshot = {
        clueNumber: prediction.clue_number,
        recommendedPick: prediction.recommended_pick,
        recommendedConfidence: Math.min(topVoteScore / 2, 1),
        oracleTopPick: prediction.oracle?.top_3?.[0]?.answer ?? null,
        oracleConfidence: prediction.oracle?.top_3?.[0]?.confidence
          ? prediction.oracle.top_3[0].confidence / 100
          : null,
        agreementStrength: prediction.agreement_strength,
      }

      // Create full round prediction for history
      const roundPrediction: RoundPrediction = {
        clueNumber: prediction.clue_number,
        clueText: prediction.clue_history[prediction.clue_number - 1] || '',
        agents: prediction.agents as Record<AgentName, AgentPrediction | null>,
        oracleTop3: prediction.oracle?.top_3 || [],
        votingResult: prediction.voting,
        recommendedPick: prediction.recommended_pick,
        timestamp: Date.now()
      }

      return {
        latestPrediction: prediction,
        sessionId: prediction.session_id,
        clueHistory: prediction.clue_history,
        predictionHistory: [...state.predictionHistory, snapshot],
        roundHistory: [...state.roundHistory, roundPrediction],
      }
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  reset: () =>
    set({
      sessionId: null,
      clueHistory: [],
      latestPrediction: null,
      predictionHistory: [],
      roundHistory: [],
      isLoading: false,
      error: null,
      timerKey: 0,
      gameStarted: false,
      responseTimes: [],
      puzzleComplete: false,
    }),

  clearRoundHistory: () =>
    set({
      predictionHistory: [],
      roundHistory: [],
    }),

  // Timer actions
  startGame: () => set({ gameStarted: true }),

  resetTimer: () => set((state) => ({ timerKey: state.timerKey + 1 })),

  addResponseTime: (time) =>
    set((state) => ({
      responseTimes: [...state.responseTimes, time],
    })),

  // Puzzle completion actions
  completePuzzle: () => set({ puzzleComplete: true }),
}))
