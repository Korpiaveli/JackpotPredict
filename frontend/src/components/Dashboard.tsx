import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import CountdownTimer from './CountdownTimer'
import PredictionCard from './PredictionCard'
import ClueInput from './ClueInput'
import { useSubmitClue, useResetPuzzle, useHealth } from '../hooks/usePredictions'
import { usePuzzleStore } from '../store/puzzleStore'

export default function Dashboard() {
  const { latestPrediction, clueHistory, isLoading, error } = usePuzzleStore()
  const submitClueMutation = useSubmitClue()
  const resetMutation = useResetPuzzle()
  const { data: healthData } = useHealth()

  const handleSubmitClue = async (clueText: string) => {
    try {
      await submitClueMutation.mutateAsync(clueText)
    } catch (err) {
      console.error('Failed to submit clue:', err)
    }
  }

  const handleReset = async () => {
    try {
      await resetMutation.mutateAsync()
    } catch (err) {
      console.error('Failed to reset:', err)
    }
  }

  const currentClueNumber = (latestPrediction?.clue_number || 0) + 1
  const shouldGuess = latestPrediction?.guess_recommendation?.should_guess
  const topPrediction = latestPrediction?.predictions?.[0]

  return (
    <div className="min-h-screen bg-background text-white p-6">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-primary mb-2">
              🎰 JackpotPredict
            </h1>
            <p className="text-gray-400">
              AI-Powered Trivia Answer Prediction Engine
            </p>
          </div>

          {/* Health Status */}
          {healthData && (
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
                <span className="text-gray-400">Online</span>
              </div>
              <div className="text-gray-500">
                {healthData.entity_count.toLocaleString()} entities
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Timer & Input */}
          <div className="lg:col-span-1 space-y-6">
            {/* Countdown Timer */}
            <CountdownTimer
              initialSeconds={20}
              isActive={!isLoading && currentClueNumber <= 5}
            />

            {/* Session Info */}
            {latestPrediction && (
              <div className="clue-card">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                  Session Info
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Clues Submitted:</span>
                    <span className="text-white font-bold">
                      {latestPrediction.clue_number} / 5
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Processing Time:</span>
                    <span className="text-white font-mono">
                      {latestPrediction.elapsed_time.toFixed(2)}s
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Category Probabilities */}
            {latestPrediction?.category_probabilities && (
              <div className="clue-card">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-3">
                  Category Analysis
                </div>
                <div className="space-y-3">
                  {Object.entries(latestPrediction.category_probabilities).map(([category, prob]) => (
                    <div key={category}>
                      <div className="flex justify-between mb-1 text-sm">
                        <span className="text-gray-400 capitalize">{category}</span>
                        <span className="text-white font-mono">{(prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-primary rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${prob * 100}%` }}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Reset Button */}
            <button
              onClick={handleReset}
              disabled={resetMutation.isPending}
              className="btn-secondary w-full"
            >
              {resetMutation.isPending ? 'Resetting...' : '🔄 New Puzzle'}
            </button>
          </div>

          {/* Right Column - Predictions & Input */}
          <div className="lg:col-span-2 space-y-6">
            {/* Guess Recommendation Banner */}
            <AnimatePresence>
              {shouldGuess && topPrediction && (
                <motion.div
                  className="bg-gradient-to-r from-success/20 to-transparent border-2 border-success rounded-xl p-6"
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="flex items-center gap-4">
                    <div className="text-4xl">✅</div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-success mb-1">
                        Recommendation: GUESS NOW!
                      </h3>
                      <p className="text-sm text-gray-300">
                        {latestPrediction.guess_recommendation.rationale}
                      </p>
                      <p className="text-sm text-gray-400 mt-2">
                        Top Answer: <span className="text-white font-bold">{topPrediction.answer}</span>
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error Display */}
            <AnimatePresence>
              {error && (
                <motion.div
                  className="bg-danger/20 border-2 border-danger rounded-xl p-4"
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">⚠️</span>
                    <div>
                      <h4 className="font-bold text-danger">Error</h4>
                      <p className="text-sm text-gray-300">{error}</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Predictions */}
            {latestPrediction && latestPrediction.predictions.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold text-white mb-4">
                  Top {latestPrediction.predictions.length} Predictions
                </h2>
                <div className="space-y-4">
                  {latestPrediction.predictions.map((prediction, index) => (
                    <PredictionCard
                      key={`${prediction.answer}-${index}`}
                      prediction={prediction}
                      index={index}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Clue Input */}
            <div className="clue-card">
              <ClueInput
                onSubmit={handleSubmitClue}
                clueNumber={currentClueNumber}
                previousClues={clueHistory}
                isLoading={isLoading}
                disabled={currentClueNumber > 5}
              />
            </div>

            {/* Welcome Message */}
            {!latestPrediction && (
              <motion.div
                className="text-center py-12"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <div className="text-6xl mb-4">🎯</div>
                <h2 className="text-2xl font-bold mb-2">Ready to Predict!</h2>
                <p className="text-gray-400 max-w-md mx-auto">
                  Enter the first clue from the game show above to start getting AI-powered predictions.
                  You'll get top 3 answers with confidence scores after each clue.
                </p>
              </motion.div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto mt-12 pt-6 border-t border-gray-800 text-center text-sm text-gray-500">
        <p>
          Powered by Bayesian inference + NLP polysemy detection • {' '}
          <a href="/api/docs" target="_blank" className="text-primary hover:underline">
            API Docs
          </a>
        </p>
      </footer>
    </div>
  )
}
