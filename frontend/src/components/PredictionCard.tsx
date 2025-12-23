import { useState } from 'react'
import { motion } from 'framer-motion'
import type { Prediction } from '../types/api'

interface PredictionCardProps {
  prediction: Prediction
  index: number
}

const MEDALS = ['🥇', '🥈', '🥉']
const RANK_LABELS = ['1ST', '2ND', '3RD']

export default function PredictionCard({ prediction, index }: PredictionCardProps) {
  const [copied, setCopied] = useState(false)

  const confidencePercent = (prediction.confidence * 100).toFixed(1)

  const getConfidenceColor = () => {
    const conf = prediction.confidence
    if (conf >= 0.75) return 'bg-primary'
    if (conf >= 0.5) return 'bg-warning'
    return 'bg-danger'
  }

  const getConfidenceTextColor = () => {
    const conf = prediction.confidence
    if (conf >= 0.75) return 'text-primary'
    if (conf >= 0.5) return 'text-warning'
    return 'text-danger'
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(prediction.answer)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <motion.div
      className="prediction-card relative overflow-hidden"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
      whileHover={{ scale: 1.02 }}
    >
      {/* Rank Badge */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <span className="text-4xl">{MEDALS[index]}</span>
        <span className="text-sm text-gray-500 uppercase font-bold">{RANK_LABELS[index]}</span>
      </div>

      {/* Answer */}
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-4xl font-mono font-bold text-white uppercase">
          {prediction.answer}
        </h2>
        <button
          onClick={copyToClipboard}
          className="px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded text-xs transition-colors"
          title="Copy answer"
        >
          {copied ? '✓ Copied' : '📋 Copy'}
        </button>
      </div>

      {/* Category */}
      <div className="flex items-center gap-2 mb-3">
        <span className="px-3 py-1 bg-gray-800 rounded-full text-xs uppercase tracking-wide text-gray-300">
          {prediction.category}
        </span>
      </div>

      {/* Confidence Bar */}
      <div className="mb-3">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-400">Confidence</span>
          <span className={`text-lg font-bold font-mono ${getConfidenceTextColor()}`}>
            {confidencePercent}%
          </span>
        </div>
        <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
          <motion.div
            className={`h-full ${getConfidenceColor()} rounded-full`}
            initial={{ width: 0 }}
            animate={{ width: `${prediction.confidence * 100}%` }}
            transition={{ duration: 0.8, delay: index * 0.1 + 0.2 }}
          />
        </div>
      </div>

      {/* Reasoning */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <p className="text-sm text-gray-400 leading-relaxed">
          <span className="text-gray-500 font-bold">Why: </span>
          {prediction.reasoning}
        </p>
      </div>

      {/* Glowing effect for top prediction */}
      {index === 0 && prediction.confidence > 0.75 && (
        <div className="absolute inset-0 bg-primary/5 pointer-events-none rounded-xl" />
      )}
    </motion.div>
  )
}
