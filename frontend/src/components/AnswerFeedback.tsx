import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { EntityCategory } from '../types/api'
import type { RoundPrediction } from '../store/puzzleStore'
import PuzzleSummary from './PuzzleSummary'
import FeedbackAnalytics from './FeedbackAnalytics'
import { useAnalytics } from '../hooks/usePredictions'

interface AnswerFeedbackProps {
  sessionId: string
  clues: string[]
  roundHistory: RoundPrediction[]
  topPrediction?: string
  onSubmit: (correctAnswer: string, category: EntityCategory, solvedAtClue?: number, keyInsight?: string) => void
  onSkip: () => void
  isLoading: boolean
}

export default function AnswerFeedback({
  sessionId,
  clues,
  roundHistory,
  topPrediction,
  onSubmit,
  onSkip,
  isLoading
}: AnswerFeedbackProps) {
  const [correctAnswer, setCorrectAnswer] = useState('')
  const [category, setCategory] = useState<EntityCategory>('thing')
  const [solvedAtClue, setSolvedAtClue] = useState<number | undefined>()
  const [keyInsight, setKeyInsight] = useState('')
  const [showSummary, setShowSummary] = useState(false)
  const [submittedAnswer, setSubmittedAnswer] = useState('')
  const [showAnalytics, setShowAnalytics] = useState(false)

  const { data: analyticsData, refetch: refetchAnalytics } = useAnalytics()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!correctAnswer.trim()) return

    // Store the answer and show summary
    setSubmittedAnswer(correctAnswer.trim())
    setShowSummary(true)
  }

  const handleContinue = () => {
    // Actually submit and reset
    onSubmit(submittedAnswer, category, solvedAtClue, keyInsight.trim() || undefined)
  }

  return (
    <div className="space-y-4">
      <AnimatePresence mode="wait">
        {!showSummary ? (
          <motion.div
            key="feedback-form"
            className="clue-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <div className="text-center mb-6">
              <div className="text-4xl mb-2">🎯</div>
              <h3 className="text-xl font-bold text-white mb-1">Puzzle Complete!</h3>
              <p className="text-sm text-gray-400">
                Help improve predictions by sharing the correct answer
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Correct Answer */}
              <div>
                <label className="block text-xs text-gray-500 uppercase tracking-wide mb-2">
                  Correct Answer
                </label>
                <input
                  type="text"
                  value={correctAnswer}
                  onChange={(e) => setCorrectAnswer(e.target.value)}
                  placeholder={topPrediction ? `Was it "${topPrediction}"?` : 'Enter the correct answer...'}
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  autoFocus
                />
              </div>

              {/* Category */}
              <div>
                <label className="block text-xs text-gray-500 uppercase tracking-wide mb-2">
                  Category
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(['person', 'place', 'thing'] as EntityCategory[]).map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setCategory(cat)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                        category === cat
                          ? 'bg-primary text-white'
                          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              {/* Solved at Clue (Optional) */}
              <div>
                <label className="block text-xs text-gray-500 uppercase tracking-wide mb-2">
                  When did you know the answer? (Optional)
                </label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((clueNum) => (
                    <button
                      key={clueNum}
                      type="button"
                      onClick={() => setSolvedAtClue(solvedAtClue === clueNum ? undefined : clueNum)}
                      disabled={clueNum > clues.length}
                      className={`flex-1 px-3 py-2 rounded-lg text-sm font-mono transition-colors ${
                        solvedAtClue === clueNum
                          ? 'bg-success text-white'
                          : clueNum > clues.length
                          ? 'bg-gray-900 text-gray-600 cursor-not-allowed'
                          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                      }`}
                    >
                      #{clueNum}
                    </button>
                  ))}
                </div>
              </div>

              {/* Key Insight (Optional) */}
              <div>
                <label className="block text-xs text-gray-500 uppercase tracking-wide mb-2">
                  Key Insight (Optional)
                </label>
                <input
                  type="text"
                  value={keyInsight}
                  onChange={(e) => setKeyInsight(e.target.value)}
                  placeholder="e.g., 'hospitable' referred to Hilton Hotels"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-sm"
                />
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={onSkip}
                  disabled={isLoading}
                  className="flex-1 px-4 py-3 bg-gray-800 text-gray-400 rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Skip
                </button>
                <button
                  type="submit"
                  disabled={isLoading || !correctAnswer.trim()}
                  className="flex-1 px-4 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {isLoading ? 'Submitting...' : 'View Summary'}
                </button>
              </div>
            </form>

            {/* Session ID for reference */}
            <div className="mt-4 pt-4 border-t border-gray-800 text-xs text-gray-600 text-center">
              Session: {sessionId.slice(0, 8)}...
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="summary-view"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="space-y-4"
          >
            {/* Puzzle Summary */}
            <PuzzleSummary
              roundHistory={roundHistory}
              correctAnswer={submittedAnswer}
            />

            {/* Analytics Toggle */}
            <motion.button
              onClick={() => {
                setShowAnalytics(!showAnalytics)
                if (!showAnalytics) refetchAnalytics()
              }}
              className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-2 text-sm text-gray-400 transition-colors hover:bg-gray-700 hover:text-white"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
            >
              {showAnalytics ? 'Hide Analytics' : 'View Feedback Analytics'}
            </motion.button>

            {/* Analytics Panel */}
            <AnimatePresence>
              {showAnalytics && analyticsData && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <FeedbackAnalytics analytics={analyticsData} />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Continue Button */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="flex gap-3"
            >
              <button
                onClick={() => setShowSummary(false)}
                className="flex-1 px-4 py-3 bg-gray-800 text-gray-400 rounded-lg hover:bg-gray-700 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleContinue}
                disabled={isLoading}
                className="flex-1 px-4 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isLoading ? 'Submitting...' : 'New Puzzle'}
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
