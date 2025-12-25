import { motion } from 'framer-motion'
import type { AgentName, AgentPrediction } from '../types/api'
import { AGENT_INFO } from '../types/api'

interface AgentRowProps {
  agents: Record<AgentName, AgentPrediction | null>
  winningAnswer: string
}

const AGENT_ORDER: AgentName[] = ['lateral', 'wordsmith', 'popculture', 'literal', 'wildcard']

export default function AgentRow({ agents, winningAnswer }: AgentRowProps) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {AGENT_ORDER.map((agentName, idx) => {
        const pred = agents[agentName]
        const info = AGENT_INFO[agentName]
        const isWinner = pred?.answer?.toLowerCase() === winningAnswer?.toLowerCase()

        // Confidence color
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
            transition={{ delay: idx * 0.05 }}
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
                  className={`text-sm font-bold truncate ${isWinner ? 'text-green-400' : 'text-white'}`}
                  title={pred.answer}
                >
                  {pred.answer.length > 12 ? pred.answer.slice(0, 10) + '...' : pred.answer}
                </div>

                {/* Confidence */}
                <div className={`text-xs font-mono ${getConfColor(pred.confidence)}`}>
                  {Math.round(pred.confidence * 100)}%
                </div>

                {/* Reasoning */}
                <div
                  className="text-xs text-gray-500 truncate mt-0.5"
                  title={pred.reasoning}
                >
                  {pred.reasoning.length > 15 ? pred.reasoning.slice(0, 12) + '...' : pred.reasoning}
                </div>
              </>
            ) : (
              <div className="text-xs text-gray-600 py-2">
                No response
              </div>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}
