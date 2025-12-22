import { create } from 'zustand'
import type { PredictionResponse } from '../types/api'

interface PuzzleState {
  sessionId: string | null
  clueHistory: string[]
  latestPrediction: PredictionResponse | null
  isLoading: boolean
  error: string | null

  // Actions
  setSessionId: (id: string) => void
  addClue: (clue: string) => void
  setPrediction: (prediction: PredictionResponse) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
}

export const usePuzzleStore = create<PuzzleState>((set) => ({
  sessionId: null,
  clueHistory: [],
  latestPrediction: null,
  isLoading: false,
  error: null,

  setSessionId: (id) => set({ sessionId: id }),

  addClue: (clue) =>
    set((state) => ({
      clueHistory: [...state.clueHistory, clue],
    })),

  setPrediction: (prediction) =>
    set({
      latestPrediction: prediction,
      sessionId: prediction.session_id,
      clueHistory: prediction.clue_history,
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  reset: () =>
    set({
      sessionId: null,
      clueHistory: [],
      latestPrediction: null,
      isLoading: false,
      error: null,
    }),
}))
