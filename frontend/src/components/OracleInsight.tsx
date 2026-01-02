import { useState } from 'react'
import { motion } from 'framer-motion'
import type { OracleSynthesis } from '../types/api'

interface OracleInsightProps {
  oracle: OracleSynthesis | null
  isLoading?: boolean
}

// Copy button component with feedback
function CopyButton({ text, className = '' }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <button
      onClick={handleCopy}
      className={`px-2 py-0.5 text-xs rounded transition-all ${
        copied
          ? 'bg-green-600 text-white'
          : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
      } ${className}`}
      title={`Copy "${text}"`}
    >
      {copied ? '✓' : '📋'}
    </button>
  )
}

export default function OracleInsight({ oracle, isLoading }: OracleInsightProps) {
  if (isLoading) {
    return (
      <motion.div
        className="bg-gradient-to-r from-purple-900/25 to-indigo-900/25 rounded-lg p-3 border border-purple-500/20"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center gap-2">
          <div className="text-xl animate-pulse">🔮</div>
          <div>
            <div className="text-sm font-medium text-purple-300">Oracle</div>
            <div className="text-xs text-gray-400 animate-pulse">Synthesizing...</div>
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
      className="bg-gradient-to-r from-purple-900/25 to-indigo-900/25 rounded-lg p-3 border border-purple-500/20"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔮</span>
          <div>
            <div className="text-sm font-medium text-purple-300">Oracle</div>
            <div className="text-xs text-gray-500">Claude Sonnet</div>
          </div>
        </div>
        {oracle.latency_ms > 0 && (
          <div className="text-xs text-gray-500">
            {(oracle.latency_ms / 1000).toFixed(1)}s
          </div>
        )}
      </div>

      {/* Top 3 Guesses - Compact horizontal layout */}
      <div className="flex gap-3 mb-2">
        {/* #1 - Primary guess */}
        {first && (
          <div className="bg-purple-800/30 rounded-lg p-2.5 border border-purple-400/30 flex-1">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-baseline gap-2 min-w-0 flex-1">
                <span className="text-xl font-bold text-white truncate">{first.answer}</span>
                <span className="text-sm font-medium text-purple-300 flex-shrink-0">{first.confidence}%</span>
              </div>
              <CopyButton text={first.answer} />
            </div>
            <p className="text-xs text-gray-300 line-clamp-2 mt-1">{first.explanation}</p>
          </div>
        )}

        {/* #2 - Secondary */}
        {second && (
          <div className="bg-gray-800/40 rounded-lg p-2.5 border border-gray-600/20 flex-1">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-baseline gap-2 min-w-0 flex-1">
                <span className="text-base font-medium text-gray-200 truncate">{second.answer}</span>
                <span className="text-xs text-gray-400 flex-shrink-0">{second.confidence}%</span>
              </div>
              <CopyButton text={second.answer} />
            </div>
            <p className="text-xs text-gray-400 line-clamp-2 mt-1">{second.explanation}</p>
          </div>
        )}

        {/* #3 - Tertiary */}
        {third && (
          <div className="bg-gray-800/20 rounded-lg p-2.5 border border-gray-700/20 flex-1">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-baseline gap-2 min-w-0 flex-1">
                <span className="text-base font-medium text-gray-300 truncate">{third.answer}</span>
                <span className="text-xs text-gray-500 flex-shrink-0">{third.confidence}%</span>
              </div>
              <CopyButton text={third.answer} />
            </div>
            <p className="text-xs text-gray-500 line-clamp-2 mt-1">{third.explanation}</p>
          </div>
        )}
      </div>

      {/* Theme & Blind Spot - Compact */}
      <div className="flex gap-3 text-xs">
        <div className="bg-indigo-900/15 rounded px-2 py-1.5 flex-1">
          <span className="text-indigo-400 font-medium">Theme: </span>
          <span className="text-gray-300">{oracle.key_theme}</span>
        </div>
        <div className="bg-amber-900/15 rounded px-2 py-1.5 flex-1">
          <span className="text-amber-400 font-medium">Blind Spot: </span>
          <span className="text-gray-300">{oracle.blind_spot}</span>
        </div>
      </div>
    </motion.div>
  )
}
