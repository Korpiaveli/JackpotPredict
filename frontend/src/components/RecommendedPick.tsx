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
      className={`rounded-xl p-4 border-2 ${
        shouldGuess
          ? 'bg-gradient-to-r from-green-500/10 to-transparent border-green-500'
          : 'bg-gray-800/50 border-gray-700'
      }`}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Main recommendation row */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Target icon */}
          <span className="text-2xl flex-shrink-0">
            {shouldGuess ? '✅' : '🎯'}
          </span>

          {/* Answer */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xl font-bold text-white uppercase truncate">
                {answer}
              </span>
              <span className={`text-lg font-mono ${getConfidenceColor()}`}>
                ({Math.round(confidence * 100)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={onCopy}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition-colors"
            title="Copy to clipboard"
          >
            Copy
          </button>
          {shouldGuess && (
            <span className="px-3 py-1.5 bg-green-500 text-white rounded-lg text-sm font-bold animate-pulse">
              GUESS!
            </span>
          )}
        </div>
      </div>

      {/* Key insight */}
      {keyInsight && keyInsight !== 'No insight' && (
        <div className="mt-2 text-sm text-gray-400 italic pl-10">
          "{keyInsight}"
        </div>
      )}

      {/* Agreement badge */}
      <div className="mt-2 flex items-center gap-2 pl-10">
        <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getAgreementColor()}`}>
          {agentsAgreed} agent{agentsAgreed !== 1 ? 's' : ''} agree
        </span>
        <span className="text-xs text-gray-500">
          {agreementStrength} agreement
        </span>
      </div>
    </motion.div>
  )
}
