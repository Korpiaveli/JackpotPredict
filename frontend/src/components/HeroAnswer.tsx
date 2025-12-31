import { motion } from 'framer-motion'
import { getConfidenceStyle, getConfidencePercent } from '../utils/confidence'

interface HeroAnswerProps {
  answer: string
  confidence: number
  shouldGuess: boolean
  trapWarning?: string | null
  keyInsight?: string
  onCopy: () => void
  isCopied: boolean
}

/**
 * Primary answer display - THE single most important element on screen.
 * Massive, tappable, unmistakable.
 */
export default function HeroAnswer({
  answer,
  confidence,
  shouldGuess,
  trapWarning,
  keyInsight,
  onCopy,
  isCopied,
}: HeroAnswerProps) {
  const confidenceStyle = getConfidenceStyle(confidence)
  const confidencePercent = getConfidencePercent(confidence)

  return (
    <motion.div
      className={`relative w-full cursor-pointer overflow-hidden rounded-2xl border-2 p-6 transition-colors md:p-8 ${
        shouldGuess
          ? 'border-green-500 bg-gradient-to-br from-green-900/40 via-green-800/20 to-transparent'
          : 'border-purple-500/50 bg-gradient-to-br from-purple-900/30 via-gray-900 to-transparent'
      } ${isCopied ? 'border-green-400' : ''}`}
      initial={{ opacity: 0, scale: 0.95, y: -20 }}
      animate={{
        opacity: 1,
        scale: 1,
        y: 0,
        boxShadow: shouldGuess
          ? [
              '0 0 0 0 rgba(34, 197, 94, 0.4)',
              '0 0 30px 10px rgba(34, 197, 94, 0.15)',
              '0 0 0 0 rgba(34, 197, 94, 0.4)',
            ]
          : 'none',
      }}
      transition={{
        duration: 0.25,
        ease: [0.25, 0.46, 0.45, 0.94],
        boxShadow: shouldGuess
          ? { duration: 2, repeat: Infinity, ease: 'easeInOut' }
          : undefined,
      }}
      onClick={onCopy}
      whileTap={{ scale: 0.98 }}
    >
      {/* GUESS NOW Badge */}
      {shouldGuess && (
        <motion.div
          className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-green-500 px-6 py-1.5 text-sm font-bold uppercase text-white shadow-lg"
          animate={{
            scale: [1, 1.05, 1],
          }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          GUESS NOW
        </motion.div>
      )}

      {/* Confidence Badge - Top Right */}
      <div
        className={`absolute right-4 top-4 rounded-full px-4 py-2 font-mono text-xl font-bold md:text-2xl ${confidenceStyle.bg} text-white`}
      >
        {confidencePercent}%
      </div>

      {/* Oracle Label */}
      <div className="mb-2 text-xs uppercase tracking-wide text-purple-400">
        Oracle Prediction
      </div>

      {/* THE ANSWER */}
      <div className="select-all text-center">
        <motion.h1
          className="text-4xl font-bold uppercase leading-tight tracking-tight text-white md:text-5xl lg:text-6xl"
          key={answer}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {answer}
        </motion.h1>
      </div>

      {/* Key Insight / Reasoning */}
      {keyInsight && keyInsight !== 'No insight' && (
        <div className="mt-4 rounded-lg border border-purple-500/20 bg-purple-900/20 px-4 py-3">
          <div className="mb-1 text-xs font-medium uppercase text-purple-400">
            Why this answer?
          </div>
          <div className="text-sm leading-relaxed text-gray-300">
            {keyInsight}
          </div>
        </div>
      )}

      {/* Tap to Copy Hint */}
      <div className="mt-4 text-center text-xs text-gray-500">
        {isCopied ? (
          <span className="text-green-400">Copied!</span>
        ) : (
          <span>Tap anywhere to copy</span>
        )}
      </div>

      {/* Trap Warning */}
      {trapWarning && (
        <motion.div
          className="mt-4 rounded-lg border border-red-500/50 bg-red-900/30 px-4 py-2"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={{ delay: 0.2 }}
        >
          <span className="text-sm font-bold text-red-400">TRAP DETECTED: </span>
          <span className="text-sm text-red-200">{trapWarning}</span>
        </motion.div>
      )}
    </motion.div>
  )
}
