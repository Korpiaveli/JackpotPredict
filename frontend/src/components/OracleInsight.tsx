import { motion } from 'framer-motion'
import type { OracleSynthesis } from '../types/api'

interface OracleInsightProps {
  oracle: OracleSynthesis | null
  isLoading?: boolean
}

export default function OracleInsight({ oracle, isLoading }: OracleInsightProps) {
  if (isLoading) {
    return (
      <motion.div
        className="bg-gradient-to-r from-purple-900/30 to-indigo-900/30 rounded-lg p-4 border border-purple-500/30"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center gap-3">
          <div className="text-2xl animate-pulse">🔮</div>
          <div>
            <div className="text-sm font-medium text-purple-300">The Oracle</div>
            <div className="text-xs text-gray-400 animate-pulse">Synthesizing predictions...</div>
          </div>
        </div>
      </motion.div>
    )
  }

  if (!oracle || !oracle.top_3 || oracle.top_3.length === 0) {
    return null
  }

  const [first, second, third] = oracle.top_3

  return (
    <motion.div
      className="bg-gradient-to-r from-purple-900/30 to-indigo-900/30 rounded-lg p-4 border border-purple-500/30"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🔮</span>
          <div>
            <div className="text-sm font-bold text-purple-300">The Oracle</div>
            <div className="text-xs text-gray-500">Claude 3.5 Sonnet Meta-Synthesis</div>
          </div>
        </div>
        {oracle.latency_ms > 0 && (
          <div className="text-xs text-gray-500">
            {(oracle.latency_ms / 1000).toFixed(1)}s
          </div>
        )}
      </div>

      {/* Top 3 Guesses */}
      <div className="grid grid-cols-3 gap-3 mb-3">
        {/* #1 - Primary guess */}
        {first && (
          <div className="bg-purple-800/30 rounded-lg p-3 border border-purple-400/30">
            <div className="flex items-baseline justify-between mb-1">
              <span className="text-lg font-bold text-white">{first.answer}</span>
              <span className="text-sm font-medium text-purple-300">{first.confidence}%</span>
            </div>
            <p className="text-xs text-gray-300 line-clamp-2">{first.explanation}</p>
          </div>
        )}

        {/* #2 - Secondary */}
        {second && (
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-600/30">
            <div className="flex items-baseline justify-between mb-1">
              <span className="text-sm font-medium text-gray-200">{second.answer}</span>
              <span className="text-xs text-gray-400">{second.confidence}%</span>
            </div>
            <p className="text-xs text-gray-400 line-clamp-2">{second.explanation}</p>
          </div>
        )}

        {/* #3 - Tertiary */}
        {third && (
          <div className="bg-gray-800/30 rounded-lg p-3 border border-gray-700/30">
            <div className="flex items-baseline justify-between mb-1">
              <span className="text-sm font-medium text-gray-300">{third.answer}</span>
              <span className="text-xs text-gray-500">{third.confidence}%</span>
            </div>
            <p className="text-xs text-gray-500 line-clamp-2">{third.explanation}</p>
          </div>
        )}
      </div>

      {/* Theme & Blind Spot */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="bg-indigo-900/20 rounded px-3 py-2">
          <span className="text-indigo-400 font-medium">Theme: </span>
          <span className="text-gray-300">{oracle.key_theme}</span>
        </div>
        <div className="bg-amber-900/20 rounded px-3 py-2">
          <span className="text-amber-400 font-medium">Blind Spot: </span>
          <span className="text-gray-300">{oracle.blind_spot}</span>
        </div>
      </div>
    </motion.div>
  )
}
