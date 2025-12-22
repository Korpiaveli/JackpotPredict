import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { usePuzzleStore } from '../store/puzzleStore'

export function useSubmitClue() {
  const { sessionId, setPrediction, setLoading, setError } = usePuzzleStore()

  return useMutation({
    mutationFn: (clueText: string) => {
      setLoading(true)
      setError(null)
      return api.submitClue({ clue_text: clueText, session_id: sessionId || undefined })
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
