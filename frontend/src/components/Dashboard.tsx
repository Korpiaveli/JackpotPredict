import { motion, AnimatePresence } from 'framer-motion'
import CountdownTimer from './CountdownTimer'
import ClueInput from './ClueInput'
import AnswerFeedback from './AnswerFeedback'
import RecommendedPick from './RecommendedPick'
import AgentRow from './AgentRow'
import StatusBar from './StatusBar'
import OracleInsight from './OracleInsight'
import ConfidenceTrend from './ConfidenceTrend'
import { useSubmitClue, useResetPuzzle, useHealth, useSubmitFeedback } from '../hooks/usePredictions'
import { usePuzzleStore } from '../store/puzzleStore'
import type { EntityCategory, AgentName, AgentPrediction } from '../types/api'

export default function Dashboard() {
  const {
    latestPrediction,
    clueHistory,
    predictionHistory,
    isLoading,
    error,
    timerKey,
    gameStarted,
    puzzleComplete,
    startGame,
    resetTimer,
    addResponseTime,
    completePuzzle,
    reset: resetStore
  } = usePuzzleStore()
  const submitClueMutation = useSubmitClue()
  const resetMutation = useResetPuzzle()
  const submitFeedbackMutation = useSubmitFeedback()
  const { data: healthData } = useHealth()

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

      if (result?.clue_number >= 5) {
        completePuzzle()
      }
    } catch (err) {
      console.error('Failed to submit clue:', err)
    }
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

  const handleCopyAnswer = () => {
    if (latestPrediction?.recommended_pick) {
      navigator.clipboard.writeText(latestPrediction.recommended_pick)
    }
  }

  const currentClueNumber = (latestPrediction?.clue_number || 0) + 1
  const shouldGuess = latestPrediction?.guess_recommendation?.should_guess ?? false

  // Get agent predictions with proper typing
  const agentPredictions = (latestPrediction?.agents ?? {}) as Record<AgentName, AgentPrediction | null>

  // Count agents that agreed on the recommended pick
  const agentsAgreed = latestPrediction?.agreements?.length ?? 0

  // Calculate confidence from voting
  const topVoteScore = latestPrediction?.voting?.vote_breakdown?.[0]?.total_votes ?? 0
  const recommendedConfidence = Math.min(topVoteScore / 2, 1)

  return (
    <div className="min-h-screen bg-background text-white flex flex-col">
      {/* Compact Header */}
      <header className="border-b border-gray-800 px-4 py-2">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-primary">
              JackpotPredict
            </h1>
            <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
              v3.0 MoA
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* Timer (compact) */}
            <div className="flex items-center gap-2 text-sm">
              <CountdownTimer
                initialSeconds={20}
                isActive={gameStarted && !isLoading && !puzzleComplete}
                resetKey={timerKey}
                showIdle={!gameStarted}
              />
            </div>

            {/* Health indicator */}
            {healthData && (
              <div className="flex items-center gap-2 text-xs">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                <span className="text-gray-500">{healthData.entity_count.toLocaleString()} entities</span>
              </div>
            )}

            {/* Reset button */}
            <button
              onClick={handleReset}
              disabled={resetMutation.isPending}
              className="text-xs px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded transition-colors"
            >
              {resetMutation.isPending ? '...' : 'Reset'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content - Optimized for single screen */}
      <main className="flex-1 px-4 py-4 max-w-6xl mx-auto w-full overflow-auto">
        <div className="space-y-4">
          {/* Error Display */}
          <AnimatePresence>
            {error && (
              <motion.div
                className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <span className="text-red-400">Error: {error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Recommended Pick - Most prominent */}
          {latestPrediction && latestPrediction.recommended_pick && (
            <RecommendedPick
              answer={latestPrediction.recommended_pick}
              confidence={recommendedConfidence}
              keyInsight={latestPrediction.key_insight || ''}
              agreementStrength={latestPrediction.agreement_strength || 'none'}
              agentsAgreed={agentsAgreed}
              shouldGuess={shouldGuess}
              onCopy={handleCopyAnswer}
            />
          )}

          {/* Status Bar */}
          {latestPrediction && (
            <StatusBar
              agentsResponded={latestPrediction.agents_responded || 0}
              clueNumber={latestPrediction.clue_number}
              elapsedTime={latestPrediction.elapsed_time}
              agreementStrength={latestPrediction.agreement_strength || 'none'}
            />
          )}

          {/* Oracle Meta-Synthesis - Above agent predictions */}
          {latestPrediction && (
            <OracleInsight
              oracle={latestPrediction.oracle}
              isLoading={isLoading}
            />
          )}

          {/* Clue History and Confidence Trend - Side by side on larger screens */}
          {clueHistory.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {/* Clue History */}
              <div className="bg-gray-800/30 rounded-lg p-3">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                  Clue History
                </div>
                <div className="space-y-1">
                  {clueHistory.map((clue, index) => (
                    <div key={index} className="flex items-start gap-2 text-sm">
                      <span className="text-primary font-mono text-xs mt-0.5">
                        {index + 1}.
                      </span>
                      <span className={`text-gray-300 ${index === clueHistory.length - 1 ? 'font-medium' : ''}`}>
                        "{clue}"
                        {index === clueHistory.length - 1 && (
                          <span className="text-primary ml-1 text-xs">current</span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Confidence Trend */}
              {predictionHistory.length > 0 && (
                <ConfidenceTrend predictions={predictionHistory} />
              )}
            </div>
          )}

          {/* 5-Agent Row */}
          {latestPrediction && Object.keys(agentPredictions).length > 0 && (
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                Agent Predictions
              </div>
              <AgentRow
                agents={agentPredictions}
                winningAnswer={latestPrediction.recommended_pick || ''}
              />
            </div>
          )}

          {/* Clue Input - Always visible */}
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <ClueInput
              onSubmit={handleSubmitClue}
              clueNumber={currentClueNumber}
              previousClues={clueHistory}
              isLoading={isLoading}
              disabled={currentClueNumber > 5 || puzzleComplete}
            />
          </div>

          {/* Welcome Message */}
          {!latestPrediction && !puzzleComplete && (
            <motion.div
              className="text-center py-8"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <div className="text-4xl mb-3">🎯</div>
              <h2 className="text-xl font-bold mb-2">Ready to Predict!</h2>
              <p className="text-gray-400 text-sm max-w-md mx-auto">
                Enter the first clue to get predictions from 5 specialized AI agents.
              </p>
            </motion.div>
          )}

          {/* Feedback Form */}
          {puzzleComplete && latestPrediction && (
            <AnswerFeedback
              sessionId={latestPrediction.session_id}
              clues={clueHistory}
              topPrediction={latestPrediction.recommended_pick}
              onSubmit={handleSubmitFeedback}
              onSkip={handleSkipFeedback}
              isLoading={submitFeedbackMutation.isPending}
            />
          )}
        </div>
      </main>

      {/* Compact Footer */}
      <footer className="border-t border-gray-800 px-4 py-2 text-center text-xs text-gray-600">
        🔮 Oracle + 5 Agents: Lateral + Wordsmith + PopCulture + Literal + WildCard
      </footer>
    </div>
  )
}
