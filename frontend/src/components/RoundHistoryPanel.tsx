import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { RoundPrediction } from '../store/puzzleStore'
import type { AgentName } from '../types/api'
import { AGENT_INFO } from '../types/api'

interface RoundHistoryPanelProps {
  roundHistory: RoundPrediction[]
  isCollapsed?: boolean
}

/**
 * RoundHistoryPanel - Collapsible panel showing round-by-round predictions
 *
 * Displays all agent predictions and Oracle synthesis for each clue,
 * allowing users to review how predictions evolved across the game.
 */
export default function RoundHistoryPanel({
  roundHistory,
  isCollapsed: initialCollapsed = true
}: RoundHistoryPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(initialCollapsed)
  const [expandedRounds, setExpandedRounds] = useState<Set<number>>(new Set())

  if (roundHistory.length === 0) {
    return null
  }

  const toggleRound = (clueNumber: number) => {
    const newExpanded = new Set(expandedRounds)
    if (newExpanded.has(clueNumber)) {
      newExpanded.delete(clueNumber)
    } else {
      newExpanded.add(clueNumber)
    }
    setExpandedRounds(newExpanded)
  }

  const agentOrder: AgentName[] = ['lateral', 'wordsmith', 'popculture', 'literal', 'wildcard']

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 overflow-hidden">
      {/* Header - Always visible */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-gray-800/50"
      >
        <div className="flex items-center gap-2">
          <motion.span
            animate={{ rotate: isCollapsed ? 0 : 90 }}
            transition={{ duration: 0.2 }}
            className="text-gray-500"
          >
            ▶
          </motion.span>
          <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Round History
          </h3>
        </div>
        <span className="text-xs text-gray-600">
          {roundHistory.length} round{roundHistory.length !== 1 ? 's' : ''}
        </span>
      </button>

      {/* Content - Collapsible */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-2 px-4 pb-4">
              {roundHistory.map((round) => {
                const isExpanded = expandedRounds.has(round.clueNumber)

                return (
                  <div
                    key={round.clueNumber}
                    className="rounded-lg border border-gray-800 bg-gray-800/30"
                  >
                    {/* Round Header */}
                    <button
                      onClick={() => toggleRound(round.clueNumber)}
                      className="flex w-full items-start gap-3 p-3 text-left transition-colors hover:bg-gray-800/50"
                    >
                      {/* Clue Number Badge */}
                      <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-medium text-primary">
                        {round.clueNumber}
                      </span>

                      <div className="flex-1 min-w-0">
                        {/* Clue Text */}
                        <p className="text-sm text-gray-300 truncate">
                          {round.clueText}
                        </p>

                        {/* Quick Summary - Oracle Top Pick */}
                        <div className="mt-1 flex items-center gap-2 text-xs">
                          <span className="text-gray-500">Oracle:</span>
                          {round.oracleTop3.length > 0 ? (
                            <span className="font-medium text-amber-400">
                              {round.oracleTop3[0].answer}
                              <span className="ml-1 text-gray-500">
                                ({round.oracleTop3[0].confidence}%)
                              </span>
                            </span>
                          ) : (
                            <span className="text-gray-600">—</span>
                          )}
                        </div>
                      </div>

                      {/* Expand Indicator */}
                      <motion.span
                        animate={{ rotate: isExpanded ? 90 : 0 }}
                        transition={{ duration: 0.15 }}
                        className="flex-shrink-0 text-xs text-gray-600"
                      >
                        ▶
                      </motion.span>
                    </button>

                    {/* Expanded Details */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.15 }}
                          className="overflow-hidden border-t border-gray-800"
                        >
                          <div className="p-3 space-y-3">
                            {/* Oracle Top 3 */}
                            {round.oracleTop3.length > 0 && (
                              <div>
                                <h4 className="text-xs font-medium text-gray-500 mb-2">
                                  Oracle Top 3
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                  {round.oracleTop3.map((guess, idx) => (
                                    <div
                                      key={guess.answer}
                                      className={`rounded-lg px-3 py-1.5 text-sm ${
                                        idx === 0
                                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                          : 'bg-gray-800 text-gray-400'
                                      }`}
                                    >
                                      <span className="font-medium">{guess.answer}</span>
                                      <span className="ml-1.5 text-xs opacity-70">
                                        {guess.confidence}%
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Agent Predictions */}
                            <div>
                              <h4 className="text-xs font-medium text-gray-500 mb-2">
                                Agent Predictions
                              </h4>
                              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                                {agentOrder.map((agentName) => {
                                  const pred = round.agents[agentName]
                                  const info = AGENT_INFO[agentName]

                                  return (
                                    <div
                                      key={agentName}
                                      className="rounded-lg bg-gray-800/50 px-2.5 py-2 text-xs"
                                    >
                                      <div className="flex items-center gap-1.5 mb-1">
                                        <span>{info.emoji}</span>
                                        <span className="font-medium text-gray-400">
                                          {info.label}
                                        </span>
                                      </div>
                                      {pred ? (
                                        <div>
                                          <p className="font-medium text-white truncate">
                                            {pred.answer}
                                          </p>
                                          <p className="text-gray-500">
                                            {pred.confidence}% conf
                                          </p>
                                        </div>
                                      ) : (
                                        <p className="text-gray-600 italic">No response</p>
                                      )}
                                    </div>
                                  )
                                })}
                              </div>
                            </div>

                            {/* Voting Result */}
                            {round.votingResult && (
                              <div className="pt-2 border-t border-gray-800">
                                <div className="flex items-center gap-2 text-xs">
                                  <span className="text-gray-500">Recommended:</span>
                                  <span className="font-medium text-primary">
                                    {round.recommendedPick}
                                  </span>
                                  <span className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${
                                    round.votingResult.agreement_strength === 'strong'
                                      ? 'bg-green-900/50 text-green-400'
                                      : round.votingResult.agreement_strength === 'moderate'
                                      ? 'bg-yellow-900/50 text-yellow-400'
                                      : 'bg-gray-800 text-gray-500'
                                  }`}>
                                    {round.votingResult.agreement_strength}
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
