import { motion } from 'framer-motion'
import type { AgreementStrength } from '../types/api'

interface RecommendedPickProps {
  answer: string
  confidence: number
  keyInsight: string
  agreementStrength: AgreementStrength
  agentsAgreed: number
  shouldGuess: boolean
  onCopy: () => void
}

export default function RecommendedPick({
  answer,
  confidence,
  keyInsight,
  agreementStrength,
  agentsAgreed,
  shouldGuess,
  onCopy
}: RecommendedPickProps) {
  // Confidence color
  const getConfidenceColor = () => {
    if (confidence >= 0.75) return 'text-green-400'
    if (confidence >= 0.50) return 'text-yellow-400'
    return 'text-red-400'
  }

  // Agreement badge color
  const getAgreementColor = () => {
    switch (agreementStrength) {
      case 'strong': return 'bg-green-500/20 text-green-400 border-green-500/50'
      case 'moderate': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50'
      case 'weak': return 'bg-orange-500/20 text-orange-400 border-orange-500/50'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/50'
    }
  }

  return (
    <motion.div
      className={`rounded-lg p-2.5 border ${
        shouldGuess
          ? 'bg-gradient-to-r from-green-500/10 to-transparent border-green-500/50'
          : 'bg-gray-800/30 border-gray-700/50'
      }`}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Compact row layout */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {/* Icon */}
          <span className="text-lg flex-shrink-0">📊</span>

          {/* Label & Answer */}
          <span className="text-xs text-gray-500 flex-shrink-0">Voting:</span>
          <span className="text-lg font-bold text-white truncate">{answer}</span>
          <span className={`text-sm font-mono ${getConfidenceColor()}`}>
            {Math.round(confidence * 100)}%
          </span>

          {/* Agreement */}
          <span className={`px-1.5 py-0.5 text-xs font-medium rounded border ${getAgreementColor()}`}>
            {agentsAgreed}/5
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <button
            onClick={onCopy}
            className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs font-medium transition-colors"
            title="Copy to clipboard"
          >
            📋
          </button>
          {shouldGuess && (
            <span className="px-2 py-1 bg-green-500 text-white rounded text-xs font-bold">
              GUESS!
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}
