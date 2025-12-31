import { useMemo } from 'react'
import { motion } from 'framer-motion'
import type { RoundPrediction, FirstCorrectResult } from '../store/puzzleStore'
import { computeFirstCorrect } from '../store/puzzleStore'
import type { AgentName } from '../types/api'
import { AGENT_INFO } from '../types/api'

interface PuzzleSummaryProps {
  roundHistory: RoundPrediction[]
  correctAnswer: string
}

/**
 * PuzzleSummary - Post-game analysis showing when each agent first got the answer
 *
 * Features:
 * - "First Correct" section showing when each agent first guessed correctly
 * - Timeline of prediction evolution
 * - Agent performance summary
 */
export default function PuzzleSummary({
  roundHistory,
  correctAnswer
}: PuzzleSummaryProps) {
  // Compute which agents got the answer first
  const firstCorrectResults = useMemo(
    () => computeFirstCorrect(roundHistory, correctAnswer),
    [roundHistory, correctAnswer]
  )

  // Build a map for quick lookup
  const firstCorrectMap = useMemo(() => {
    const map = new Map<string, FirstCorrectResult>()
    for (const result of firstCorrectResults) {
      map.set(result.agentName, result)
    }
    return map
  }, [firstCorrectResults])

  // Track prediction evolution (how top pick changed over time)
  const predictionEvolution = useMemo(() => {
    return roundHistory.map((round) => ({
      clueNumber: round.clueNumber,
      oracleTop: round.oracleTop3[0]?.answer ?? null,
      recommended: round.recommendedPick
    }))
  }, [roundHistory])

  // All agents + oracle for display
  const allAgents: (AgentName | 'oracle')[] = [
    'lateral',
    'wordsmith',
    'popculture',
    'literal',
    'wildcard',
    'oracle'
  ]

  const getAgentLabel = (name: AgentName | 'oracle') => {
    if (name === 'oracle') return { emoji: '🔮', label: 'Oracle' }
    return AGENT_INFO[name]
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-xl border border-gray-800 bg-gray-900/50 overflow-hidden"
    >
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-800/30 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎯</span>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-white">
            Puzzle Summary
          </h3>
        </div>
        <p className="mt-1 text-sm text-primary font-medium">
          Answer: {correctAnswer}
        </p>
      </div>

      <div className="p-4 space-y-5">
        {/* First Correct Section */}
        <div>
          <h4 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-3">
            First Correct Predictions
          </h4>

          <div className="space-y-2">
            {allAgents.map((agentName) => {
              const result = firstCorrectMap.get(agentName)
              const { emoji, label } = getAgentLabel(agentName)

              return (
                <div
                  key={agentName}
                  className={`flex items-center justify-between rounded-lg px-3 py-2 ${
                    result
                      ? 'bg-green-900/20 border border-green-800/30'
                      : 'bg-gray-800/50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span>{emoji}</span>
                    <span className={`font-medium ${result ? 'text-green-400' : 'text-gray-500'}`}>
                      {label}
                    </span>
                  </div>

                  {result ? (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-green-400 font-medium">
                        Clue {result.clueNumber}
                      </span>
                      <span className="text-gray-500 text-xs">
                        ({result.confidence}%)
                      </span>
                    </div>
                  ) : (
                    <span className="text-gray-600 text-sm italic">
                      Never correct
                    </span>
                  )}
                </div>
              )
            })}
          </div>

          {/* Summary stat */}
          {firstCorrectResults.length > 0 && (
            <p className="mt-3 text-xs text-gray-500">
              {firstCorrectResults.length === 1 ? (
                <>
                  Only <span className="text-primary font-medium">
                    {getAgentLabel(firstCorrectResults[0].agentName).label}
                  </span> got it right (at clue {firstCorrectResults[0].clueNumber})
                </>
              ) : (
                <>
                  <span className="text-green-400 font-medium">
                    {getAgentLabel(firstCorrectResults[0].agentName).label}
                  </span> was first to get it right at clue {firstCorrectResults[0].clueNumber}
                </>
              )}
            </p>
          )}

          {firstCorrectResults.length === 0 && (
            <p className="mt-3 text-xs text-gray-500">
              No agent predicted the correct answer during this game.
            </p>
          )}
        </div>

        {/* Prediction Evolution */}
        {predictionEvolution.length > 1 && (
          <div>
            <h4 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-3">
              Prediction Evolution
            </h4>

            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-3 top-3 bottom-3 w-px bg-gray-700" />

              <div className="space-y-3">
                {predictionEvolution.map((round, idx) => {
                  const isCorrect = round.oracleTop?.toLowerCase() === correctAnswer.toLowerCase()
                  const isLast = idx === predictionEvolution.length - 1

                  return (
                    <div key={round.clueNumber} className="relative flex items-start gap-3 pl-1">
                      {/* Timeline dot */}
                      <div
                        className={`relative z-10 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-medium ${
                          isCorrect
                            ? 'bg-green-500 text-white'
                            : isLast
                            ? 'bg-primary text-white'
                            : 'bg-gray-700 text-gray-400'
                        }`}
                      >
                        {round.clueNumber}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 text-sm">
                          <span className="text-gray-500">Oracle:</span>
                          <span
                            className={`font-medium truncate ${
                              isCorrect ? 'text-green-400' : 'text-white'
                            }`}
                          >
                            {round.oracleTop ?? '—'}
                          </span>
                          {isCorrect && (
                            <span className="text-green-500 text-xs">✓</span>
                          )}
                        </div>
                        {round.recommended !== round.oracleTop && (
                          <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                            <span>Vote:</span>
                            <span className="text-gray-400">{round.recommended}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* Agent Performance Bars */}
        <div>
          <h4 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-3">
            Agent Accuracy
          </h4>

          <div className="space-y-2">
            {(['lateral', 'wordsmith', 'popculture', 'literal', 'wildcard'] as AgentName[]).map(
              (agentName) => {
                const info = AGENT_INFO[agentName]

                // Count how many rounds this agent got correct
                const correctCount = roundHistory.filter((round) => {
                  const pred = round.agents[agentName]
                  return (
                    pred && pred.answer.toLowerCase().trim() === correctAnswer.toLowerCase().trim()
                  )
                }).length

                const accuracy =
                  roundHistory.length > 0 ? (correctCount / roundHistory.length) * 100 : 0

                return (
                  <div key={agentName} className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 w-20 flex-shrink-0">
                      <span className="text-xs">{info.emoji}</span>
                      <span className="text-xs text-gray-400">{info.label}</span>
                    </div>

                    <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${accuracy}%` }}
                        transition={{ duration: 0.5, delay: 0.1 }}
                        className={`h-full rounded-full ${
                          accuracy > 50
                            ? 'bg-green-500'
                            : accuracy > 0
                            ? 'bg-yellow-500'
                            : 'bg-gray-700'
                        }`}
                      />
                    </div>

                    <span className="text-xs text-gray-500 w-16 text-right">
                      {correctCount}/{roundHistory.length}
                    </span>
                  </div>
                )
              }
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
