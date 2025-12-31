import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import type { AgentName, AgentPrediction, OracleSynthesis, CulturalMatch } from '../types/api'
import AgentConsensus from './AgentConsensus'

interface InsightsPanelProps {
  oracle: OracleSynthesis | null
  agents: Record<AgentName, AgentPrediction | null>
  culturalMatches?: CulturalMatch[]
  clueHistory: string[]
  winningAnswer: string
}

/**
 * Collapsible details section for progressive disclosure.
 * Contains agent consensus, clue history, and cultural matches.
 */
export default function InsightsPanel({
  oracle,
  agents,
  culturalMatches,
  clueHistory,
  winningAnswer,
}: InsightsPanelProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="mt-4">
      {/* Expand/Collapse Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between rounded-lg bg-gray-800/30 px-4 py-3 transition-colors hover:bg-gray-800/50"
      >
        <span className="flex items-center gap-2 text-sm text-gray-400">
          <span>Details</span>
          {oracle?.key_theme && (
            <span className="rounded bg-indigo-900/50 px-2 py-0.5 text-xs text-indigo-300">
              {oracle.key_theme.length > 30
                ? oracle.key_theme.slice(0, 30) + '...'
                : oracle.key_theme}
            </span>
          )}
        </span>
        <motion.span
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-gray-500"
        >
          ▼
        </motion.span>
      </button>

      {/* Collapsible Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-4 pt-4">
              {/* Agent Consensus */}
              <AgentConsensus
                agents={agents}
                winningAnswer={winningAnswer}
                culturalMatches={culturalMatches}
              />

              {/* Oracle Analysis */}
              {oracle && (
                <div className="space-y-2">
                  {oracle.key_theme && (
                    <div className="rounded-lg border border-indigo-500/30 bg-indigo-900/20 p-3">
                      <div className="mb-1 text-xs font-medium uppercase text-indigo-400">
                        Theme
                      </div>
                      <div className="text-sm text-gray-300">{oracle.key_theme}</div>
                    </div>
                  )}

                  {oracle.blind_spot && (
                    <div className="rounded-lg border border-amber-500/30 bg-amber-900/20 p-3">
                      <div className="mb-1 text-xs font-medium uppercase text-amber-400">
                        Blind Spot
                      </div>
                      <div className="text-sm text-gray-300">{oracle.blind_spot}</div>
                    </div>
                  )}
                </div>
              )}

              {/* Clue History */}
              {clueHistory.length > 0 && (
                <div>
                  <div className="mb-2 text-xs uppercase tracking-wide text-gray-500">
                    Clue History
                  </div>
                  <div className="space-y-1.5">
                    {clueHistory.map((clue, index) => (
                      <motion.div
                        key={index}
                        className="flex items-start gap-2 text-sm"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-gray-700 text-xs text-gray-400">
                          {index + 1}
                        </span>
                        <span className="text-gray-400">{clue}</span>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
