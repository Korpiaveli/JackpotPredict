import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { usePuzzleStore } from '../store/puzzleStore'
import type { EntityCategory, ThinkerStatus } from '../types/api'

export function useSubmitClue() {
  const { sessionId, setPrediction, setLoading, setError } = usePuzzleStore()

  return useMutation({
    mutationFn: ({ clueText, theme }: { clueText: string; theme?: string }) => {
      setLoading(true)
      setError(null)
      return api.submitClue({
        clue_text: clueText,
        session_id: sessionId || undefined,
        theme: theme || undefined
      })
    },
    onSuccess: (data) => {
      setPrediction(data)
      setLoading(false)
    },
    onError: (error: Error) => {
      setError(error.message)
      setLoading(false)
    },
  })
}

export function useResetPuzzle() {
  const { sessionId, reset: resetStore } = usePuzzleStore()

  return useMutation({
    mutationFn: () => api.reset(sessionId || undefined),
    onSuccess: (data) => {
      resetStore()
      usePuzzleStore.getState().setSessionId(data.session_id)
    },
  })
}

export function useValidateAnswer() {
  return useMutation({
    mutationFn: (answer: string) => api.validate(answer),
  })
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000, // Refetch every 30 seconds
  })
}

export function useSubmitFeedback() {
  const { sessionId, clueHistory } = usePuzzleStore()

  return useMutation({
    mutationFn: ({
      correctAnswer,
      category,
      solvedAtClue,
      keyInsight
    }: {
      correctAnswer: string
      category: EntityCategory
      solvedAtClue?: number
      keyInsight?: string
    }) => {
      if (!sessionId) throw new Error('No active session')
      return api.submitFeedback({
        session_id: sessionId,
        correct_answer: correctAnswer,
        category,
        clues: clueHistory,
        solved_at_clue: solvedAtClue,
        key_insight: keyInsight
      })
    }
  })
}

export function useThinkerStatus(sessionId: string | null, clueNumber: number | null) {
  return useQuery<ThinkerStatus>({
    queryKey: ['thinker-status', sessionId, clueNumber],
    queryFn: () => {
      if (!sessionId || !clueNumber) {
        return { pending: false, completed: false, insight: null }
      }
      return api.getThinkerStatus(sessionId, clueNumber)
    },
    refetchInterval: (query) => {
      const data = query.state.data
      if (data?.completed || !sessionId || !clueNumber) {
        return false
      }
      return 1000
    },
    enabled: !!sessionId && !!clueNumber,
    staleTime: 0,
  })
}
