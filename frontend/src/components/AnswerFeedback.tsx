import { useState } from 'react'
import { motion } from 'framer-motion'
import type { EntityCategory } from '../types/api'

interface AnswerFeedbackProps {
  sessionId: string
  clues: string[]
  topPrediction?: string
  onSubmit: (correctAnswer: string, category: EntityCategory, solvedAtClue?: number, keyInsight?: string) => void
  onSkip: () => void
  isLoading: boolean
}

export default function AnswerFeedback({
  sessionId,
  clues,
  topPrediction,
  onSubmit,
  onSkip,
  isLoading
}: AnswerFeedbackProps) {
  const [correctAnswer, setCorrectAnswer] = useState('')
  const [category, setCategory] = useState<EntityCategory>('thing')
  const [solvedAtClue, setSolvedAtClue] = useState<number | undefined>()
  const [keyInsight, setKeyInsight] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!correctAnswer.trim()) return
    onSubmit(correctAnswer.trim(), category, solvedAtClue, keyInsight.trim() || undefined)
  }

  return (
    <motion.div
      className="clue-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
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
            {isLoading ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </div>
      </form>

      {/* Session ID for reference */}
      <div className="mt-4 pt-4 border-t border-gray-800 text-xs text-gray-600 text-center">
        Session: {sessionId.slice(0, 8)}...
      </div>
    </motion.div>
  )
}
