import { motion } from 'framer-motion'
import type { OracleGuess } from '../types/api'
import { getConfidenceStyle, getConfidencePercent } from '../utils/confidence'

interface SecondaryPicksProps {
  picks: OracleGuess[]
  onCopy: (text: string) => void
}

/**
 * Oracle's #2 and #3 predictions displayed as smaller tappable cards.
 * Only renders if there are 2+ guesses from Oracle.
 */
export default function SecondaryPicks({ picks, onCopy }: SecondaryPicksProps) {
  if (!picks || picks.length < 1) return null

  return (
    <div className="mt-4 flex gap-3">
      {picks.slice(0, 2).map((pick, index) => (
        <SecondaryCard
          key={pick.answer}
          pick={pick}
          rank={index + 2}
          onCopy={() => onCopy(pick.answer)}
        />
      ))}
    </div>
  )
}

interface SecondaryCardProps {
  pick: OracleGuess
  rank: number
  onCopy: () => void
}

function SecondaryCard({ pick, rank, onCopy }: SecondaryCardProps) {
  const confidenceStyle = getConfidenceStyle(pick.confidence)
  const confidencePercent = getConfidencePercent(pick.confidence)

  return (
    <motion.button
      onClick={onCopy}
      className="group flex-1 rounded-xl border border-gray-700 bg-gray-800/50 p-4 text-left transition-colors hover:border-gray-600"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.1 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Header: Rank and Confidence */}
      <div className="mb-2 flex items-center justify-between">
        <span className="rounded bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-300">
          #{rank}
        </span>
        <span className={`rounded-full px-3 py-1 font-mono text-sm font-bold ${confidenceStyle.bg} text-white`}>
          {confidencePercent}%
        </span>
      </div>

      {/* Answer */}
      <div className="mb-2 text-lg font-bold uppercase text-gray-100">
        {pick.answer}
      </div>

      {/* Explanation - Full text, no truncation */}
      {pick.explanation && (
        <div className="rounded-lg border border-gray-700/50 bg-gray-900/50 px-3 py-2">
          <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-gray-500">
            Reasoning
          </div>
          <div className="text-xs leading-relaxed text-gray-400">
            {pick.explanation}
          </div>
        </div>
      )}

      {/* Copy hint on hover */}
      <div className="mt-2 text-xs text-primary opacity-0 transition-opacity group-hover:opacity-100">
        Tap to copy
      </div>
    </motion.button>
  )
}
