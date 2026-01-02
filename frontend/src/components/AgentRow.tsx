import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { AgentName, AgentPrediction } from '../types/api'
import { AGENT_INFO } from '../types/api'

interface AgentRowProps {
  agents: Record<AgentName, AgentPrediction | null>
  winningAnswer: string
}

const AGENT_ORDER: AgentName[] = ['lateral', 'wordsmith', 'popculture', 'literal', 'wildcard']

export default function AgentRow({ agents, winningAnswer }: AgentRowProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const agentCount = Object.values(agents).filter(Boolean).length
  const agreementCount = Object.values(agents).filter(
    (pred) => pred?.answer?.toLowerCase() === winningAnswer?.toLowerCase()
  ).length

  return (
    <div className="bg-gray-800/20 rounded-lg border border-gray-700/30 overflow-hidden">
      {/* Collapsed header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-700/20 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <span>👥</span>
          <span>Agent Details</span>
          <span className="text-xs text-gray-500">
            ({agentCount}/5 responded, {agreementCount} agree)
          </span>
        </div>
        <span className={`text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {/* Expandable content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="grid grid-cols-5 gap-2 p-2 pt-0">
              {AGENT_ORDER.map((agentName, idx) => {
                const pred = agents[agentName]
                const info = AGENT_INFO[agentName]
                const isWinner = pred?.answer?.toLowerCase() === winningAnswer?.toLowerCase()

                const getConfColor = (conf: number) => {
                  if (conf >= 0.75) return 'text-green-400'
                  if (conf >= 0.50) return 'text-yellow-400'
                  return 'text-red-400'
                }

                return (
                  <motion.div
                    key={agentName}
                    className={`rounded-lg p-2 text-center ${
                      isWinner
                        ? 'bg-green-500/10 border border-green-500/30'
                        : 'bg-gray-800/50 border border-gray-700/50'
                    }`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.03 }}
                  >
                    {/* Agent header */}
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <span className="text-sm">{info.emoji}</span>
                      <span className="text-xs font-medium text-gray-400">{info.label}</span>
                    </div>

                    {pred ? (
                      <>
                        {/* Answer */}
                        <div
                          className={`text-base font-bold truncate ${isWinner ? 'text-green-400' : 'text-white'}`}
                          title={pred.answer}
                        >
                          {pred.answer.length > 12 ? pred.answer.slice(0, 10) + '...' : pred.answer}
                        </div>

                        {/* Confidence */}
                        <div className={`text-sm font-mono ${getConfColor(pred.confidence)}`}>
                          {Math.round(pred.confidence * 100)}%
                        </div>

                        {/* Reasoning */}
                        <div
                          className="text-sm text-gray-500 truncate mt-0.5"
                          title={pred.reasoning}
                        >
                          {pred.reasoning.length > 15 ? pred.reasoning.slice(0, 12) + '...' : pred.reasoning}
                        </div>
                      </>
                    ) : (
                      <div className="text-sm text-gray-600 py-2">
                        No response
                      </div>
                    )}
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
