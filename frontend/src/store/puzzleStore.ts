import { create } from 'zustand'
import type { PredictionResponse } from '../types/api'

// Simplified prediction snapshot for trend tracking
export interface PredictionSnapshot {
  clueNumber: number
  recommendedPick: string
  recommendedConfidence: number
  oracleTopPick: string | null
  oracleConfidence: number | null
  agreementStrength: string
}

interface PuzzleState {
  sessionId: string | null
  clueHistory: string[]
  latestPrediction: PredictionResponse | null
  predictionHistory: PredictionSnapshot[]  // Track all predictions for trend viz
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
  setPrediction: (prediction: PredictionResponse) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void

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

      return {
        latestPrediction: prediction,
        sessionId: prediction.session_id,
        clueHistory: prediction.clue_history,
        predictionHistory: [...state.predictionHistory, snapshot],
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
      isLoading: false,
      error: null,
      timerKey: 0,
      gameStarted: false,
      responseTimes: [],
      puzzleComplete: false,
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
