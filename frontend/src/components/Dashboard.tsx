import { AnimatePresence, motion } from 'framer-motion'
import HeroAnswer from './HeroAnswer'
import SecondaryPicks from './SecondaryPicks'
import ClueHistory from './ClueHistory'
import InsightsPanel from './InsightsPanel'
import RoundHistoryPanel from './RoundHistoryPanel'
import MiniTimer from './MiniTimer'
import ResponseTimer from './ResponseTimer'
import CopyToast from './CopyToast'
import AnswerFeedback from './AnswerFeedback'
import { useCopyToClipboard } from '../hooks/useCopyToClipboard'
import { useSubmitClue, useResetPuzzle, useHealth, useSubmitFeedback, useRepredict } from '../hooks/usePredictions'
import { usePuzzleStore } from '../store/puzzleStore'
import type { EntityCategory, AgentName, AgentPrediction } from '../types/api'

export default function Dashboard() {
  const {
    latestPrediction,
    clueHistory,
    roundHistory,
    isLoading,
    error,
    timerKey,
    gameStarted,
    puzzleComplete,
    startGame,
    resetTimer,
    addResponseTime,
    completePuzzle,
    updateClue,
    clearRoundHistory,
    reset: resetStore
  } = usePuzzleStore()

  const submitClueMutation = useSubmitClue()
  const resetMutation = useResetPuzzle()
  const submitFeedbackMutation = useSubmitFeedback()
  const repredictMutation = useRepredict()
  const { data: healthData } = useHealth()
  const { copy, copiedText, isCopied } = useCopyToClipboard()

  const handleSubmitClue = async (clueText: string) => {
    try {
      if (!gameStarted) {
        startGame()
      }

      const result = await submitClueMutation.mutateAsync(clueText)

      if (result?.elapsed_time) {
        addResponseTime(result.elapsed_time)
      }

      resetTimer()
      // Don't auto-complete - let user see the 5th clue prediction first
    } catch (err) {
      console.error('Failed to submit clue:', err)
    }
  }

  const handleFinishPuzzle = () => {
    completePuzzle()
  }

  const handleReset = async () => {
    try {
      await resetMutation.mutateAsync()
      resetStore()
    } catch (err) {
      console.error('Failed to reset:', err)
    }
  }

  const handleSubmitFeedback = async (
    correctAnswer: string,
    category: EntityCategory,
    solvedAtClue?: number,
    keyInsight?: string
  ) => {
    try {
      await submitFeedbackMutation.mutateAsync({
        correctAnswer,
        category,
        solvedAtClue,
        keyInsight
      })
      await handleReset()
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }
  }

  const handleSkipFeedback = () => {
    handleReset()
  }

  const handleEditClue = async (index: number, newText: string) => {
    // Update the store with the edited clue
    updateClue(index, newText)

    // Get updated clue list
    const updatedClues = [...clueHistory]
    updatedClues[index] = newText

    // Clear round history since we're re-predicting
    clearRoundHistory()

    try {
      // Re-run predictions with corrected clues
      await repredictMutation.mutateAsync(updatedClues)
      resetTimer()
    } catch (err) {
      console.error('Failed to repredict:', err)
    }
  }

  // Derive display values
  const currentClueNumber = (latestPrediction?.clue_number || 0) + 1
  const shouldGuess = latestPrediction?.guess_recommendation?.should_guess ?? false

  // Oracle's primary answer (preferred) or fallback to voting recommended pick
  const oracle = latestPrediction?.oracle
  const primaryAnswer = oracle?.top_3?.[0]?.answer ?? latestPrediction?.recommended_pick
  const primaryConfidence = oracle?.top_3?.[0]?.confidence ?? 50
  const primaryInsight = oracle?.top_3?.[0]?.explanation ?? latestPrediction?.key_insight
  const trapWarning = oracle?.misdirection_detected

  // Agent predictions for InsightsPanel
  const agentPredictions = (latestPrediction?.agents ?? {}) as Record<AgentName, AgentPrediction | null>

  return (
    <div className="flex min-h-screen flex-col bg-background text-white">
      {/* Compact Header */}
      <header className="border-b border-gray-800 px-4 py-2">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold text-primary">JackpotPredict</h1>
            <span className="rounded bg-gray-800 px-2 py-0.5 text-xs text-gray-500">
              v4.0
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Mini Timer */}
            <MiniTimer
              initialSeconds={20}
              isActive={gameStarted && !isLoading && !puzzleComplete}
              resetKey={timerKey}
              showIdle={!gameStarted}
            />

            {/* Response Timer - shows API latency */}
            <ResponseTimer
              responseTime={latestPrediction?.elapsed_time ?? null}
              isLoading={isLoading}
            />

            {/* Health indicator */}
            {healthData && (
              <div className="hidden items-center gap-1.5 text-xs sm:flex">
                <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
                <span className="text-gray-500">
                  {healthData.entity_count.toLocaleString()}
                </span>
              </div>
            )}

            {/* Reset button */}
            <button
              onClick={handleReset}
              disabled={resetMutation.isPending}
              className="rounded bg-gray-800 px-3 py-1 text-xs transition-colors hover:bg-gray-700"
            >
              {resetMutation.isPending ? '...' : 'Reset'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content - Mobile-first, focused */}
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-4">
        <div className="space-y-4">
          {/* Error Display */}
          <AnimatePresence>
            {error && (
              <motion.div
                className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <span className="text-red-400">Error: {error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* HERO ANSWER - Primary Focus */}
          {primaryAnswer && !puzzleComplete && (
            <HeroAnswer
              answer={primaryAnswer}
              confidence={primaryConfidence}
              shouldGuess={shouldGuess}
              trapWarning={trapWarning}
              keyInsight={primaryInsight}
              onCopy={() => copy(primaryAnswer)}
              isCopied={copiedText === primaryAnswer}
            />
          )}

          {/* Secondary Picks - Oracle #2 and #3 */}
          {oracle?.top_3 && oracle.top_3.length > 1 && !puzzleComplete && (
            <SecondaryPicks
              picks={oracle.top_3.slice(1)}
              onCopy={copy}
            />
          )}

          {/* Clue History with Input - Always visible */}
          {!puzzleComplete && (
            <ClueHistory
              clues={clueHistory}
              currentClueNumber={currentClueNumber}
              isLoading={isLoading || repredictMutation.isPending}
              onSubmitClue={handleSubmitClue}
              onEditClue={handleEditClue}
              disabled={currentClueNumber > 5}
            />
          )}

          {/* Finish Puzzle Button - Shows after all 5 clues */}
          {currentClueNumber > 5 && !puzzleComplete && (
            <motion.button
              onClick={handleFinishPuzzle}
              className="w-full rounded-xl bg-gradient-to-r from-primary to-purple-600 px-6 py-4 text-lg font-semibold text-white shadow-lg transition-all hover:scale-[1.02] hover:shadow-xl"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              Finish Puzzle & Submit Feedback
            </motion.button>
          )}

          {/* Collapsible Details */}
          {latestPrediction && !puzzleComplete && (
            <InsightsPanel
              oracle={oracle ?? null}
              agents={agentPredictions}
              culturalMatches={latestPrediction.cultural_matches}
              clueHistory={clueHistory}
              winningAnswer={primaryAnswer || ''}
            />
          )}

          {/* Round-by-Round History */}
          {roundHistory.length > 0 && !puzzleComplete && (
            <RoundHistoryPanel roundHistory={roundHistory} />
          )}

          {/* Welcome State */}
          {!latestPrediction && !puzzleComplete && (
            <motion.div
              className="py-12 text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <div className="mb-4 text-5xl">🎯</div>
              <h2 className="mb-2 text-2xl font-bold">Ready to Predict</h2>
              <p className="mx-auto max-w-sm text-sm text-gray-400">
                Enter the first clue to get predictions from Oracle + 5 specialized AI agents.
              </p>
            </motion.div>
          )}

          {/* Feedback Form */}
          {puzzleComplete && latestPrediction && (
            <AnswerFeedback
              sessionId={latestPrediction.session_id}
              clues={clueHistory}
              roundHistory={roundHistory}
              topPrediction={primaryAnswer}
              onSubmit={handleSubmitFeedback}
              onSkip={handleSkipFeedback}
              isLoading={submitFeedbackMutation.isPending}
            />
          )}
        </div>
      </main>

      {/* Copy Toast */}
      <CopyToast text={copiedText} show={isCopied} />
    </div>
  )
}
