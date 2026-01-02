import { useState } from 'react'
import { motion } from 'framer-motion'
import type { ThinkerInsight as ThinkerInsightType } from '../types/api'

interface ThinkerInsightProps {
  insight: ThinkerInsightType | null
  isPending?: boolean
}

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
      className={`px-2 py-1 text-sm rounded transition-all ${
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

export default function ThinkerInsight({ insight, isPending }: ThinkerInsightProps) {
  if (isPending) {
    return (
      <motion.div
        className="bg-gradient-to-r from-emerald-900/40 to-teal-900/40 rounded-xl p-6 border-2 border-emerald-500/50 shadow-lg shadow-emerald-900/20"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center gap-4">
          <div className="text-4xl animate-pulse">🧠</div>
          <div>
            <div className="text-lg font-bold text-emerald-300">Deep Analysis</div>
            <div className="text-sm text-gray-400 animate-pulse flex items-center gap-2">
              <span className="inline-block w-2 h-2 bg-emerald-400 rounded-full animate-ping"></span>
              Analyzing patterns...
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  if (!insight) {
    return null
  }

  return (
    <motion.div
      className="bg-gradient-to-r from-emerald-900/40 to-teal-900/40 rounded-xl p-6 border-2 border-emerald-500/50 shadow-lg shadow-emerald-900/20"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-4xl">🧠</span>
          <div>
            <div className="text-lg font-bold text-emerald-300">Deep Analysis</div>
            <div className="text-xs text-gray-500">Gemini 2.5 Pro</div>
          </div>
        </div>
        {insight.latency_ms > 0 && (
          <div className="text-xs text-gray-500">
            {(insight.latency_ms / 1000).toFixed(1)}s
          </div>
        )}
      </div>

      {/* Primary Guess - LARGE */}
      <div className="bg-emerald-800/30 rounded-lg p-5 border border-emerald-400/40 mb-4">
        <div className="flex items-center justify-between mb-3 gap-3">
          <div className="flex items-baseline gap-4 min-w-0 flex-1">
            <span className="text-4xl font-bold text-white tracking-tight">{insight.top_guess}</span>
            <span className="text-2xl font-semibold text-emerald-300">{insight.confidence}%</span>
          </div>
          <CopyButton text={insight.top_guess} className="px-3 py-1.5" />
        </div>
        <p className="text-base text-gray-200 leading-relaxed">{insight.hypothesis_reasoning}</p>
      </div>

      {/* Patterns & Wordplay */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {insight.key_patterns.length > 0 && (
          <div className="bg-teal-900/30 rounded-lg p-3 border border-teal-600/30">
            <div className="text-sm font-medium text-teal-300 mb-2">🔍 Patterns</div>
            <div className="flex flex-wrap gap-2">
              {insight.key_patterns.map((pattern, i) => (
                <span key={i} className="px-2 py-1 bg-teal-800/50 rounded text-xs text-teal-200">
                  {pattern}
                </span>
              ))}
            </div>
          </div>
        )}
        {insight.wordplay_analysis && (
          <div className="bg-amber-900/30 rounded-lg p-3 border border-amber-600/30">
            <div className="text-sm font-medium text-amber-300 mb-2">💡 Wordplay</div>
            <p className="text-sm text-gray-300">{insight.wordplay_analysis}</p>
          </div>
        )}
      </div>

      {/* Narrative Arc */}
      {insight.narrative_arc && (
        <div className="bg-gray-800/40 rounded-lg p-3 border border-gray-600/30">
          <div className="text-sm font-medium text-gray-400 mb-1">📖 Narrative</div>
          <p className="text-sm text-gray-300">{insight.narrative_arc}</p>
        </div>
      )}

      {/* Alternative Guesses */}
      {insight.refined_guesses.length > 1 && (
        <div className="mt-4 pt-3 border-t border-gray-700/50">
          <div className="text-xs text-gray-500 mb-2">Alternative possibilities</div>
          <div className="flex gap-3">
            {insight.refined_guesses.slice(1).map((guess, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-gray-400">{guess.answer}</span>
                <span className="text-gray-600">{guess.confidence}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
