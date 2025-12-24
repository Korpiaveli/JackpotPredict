import { motion } from 'framer-motion'
import type { PredictionSnapshot } from '../store/puzzleStore'

interface ConfidenceTrendProps {
  predictions: PredictionSnapshot[]
}

// Color based on confidence level
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.75) return '#22c55e'  // green-500
  if (confidence >= 0.50) return '#eab308'  // yellow-500
  return '#ef4444'  // red-500
}

// Agreement badge
function getAgreementBadge(strength: string): { color: string; label: string } {
  switch (strength) {
    case 'strong': return { color: 'bg-green-500', label: 'S' }
    case 'moderate': return { color: 'bg-yellow-500', label: 'M' }
    case 'weak': return { color: 'bg-orange-500', label: 'W' }
    default: return { color: 'bg-gray-500', label: '-' }
  }
}

export default function ConfidenceTrend({ predictions }: ConfidenceTrendProps) {
  if (predictions.length === 0) {
    return null
  }

  // Calculate max height for scaling (100% = 80px)
  const maxHeight = 60

  return (
    <motion.div
      className="bg-gray-800/30 rounded-lg p-3 border border-gray-700"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
        Confidence Trend
      </div>

      {/* Bar chart container */}
      <div className="flex items-end gap-2 h-20">
        {[1, 2, 3, 4, 5].map((clueNum) => {
          const pred = predictions.find(p => p.clueNumber === clueNum)

          if (!pred) {
            // Empty slot for future clues
            return (
              <div key={clueNum} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full h-16 flex items-end">
                  <div className="w-full h-2 bg-gray-700/50 rounded-t" />
                </div>
                <span className="text-xs text-gray-600">{clueNum}</span>
              </div>
            )
          }

          const agentHeight = pred.recommendedConfidence * maxHeight
          const oracleHeight = pred.oracleConfidence ? pred.oracleConfidence * maxHeight : 0
          const badge = getAgreementBadge(pred.agreementStrength)

          return (
            <div key={clueNum} className="flex-1 flex flex-col items-center gap-1">
              {/* Bars container */}
              <div className="w-full h-16 flex items-end gap-0.5">
                {/* Agent bar */}
                <motion.div
                  className="flex-1 rounded-t relative group"
                  style={{
                    height: agentHeight,
                    backgroundColor: getConfidenceColor(pred.recommendedConfidence),
                  }}
                  initial={{ height: 0 }}
                  animate={{ height: agentHeight }}
                  transition={{ duration: 0.3, delay: clueNum * 0.1 }}
                  title={`Agents: ${pred.recommendedPick} (${Math.round(pred.recommendedConfidence * 100)}%)`}
                >
                  {/* Tooltip on hover */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 text-xs text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 pointer-events-none">
                    {pred.recommendedPick}
                  </div>
                </motion.div>

                {/* Oracle bar */}
                {oracleHeight > 0 && (
                  <motion.div
                    className="flex-1 rounded-t relative group"
                    style={{
                      height: oracleHeight,
                      backgroundColor: '#a855f7',  // purple-500
                    }}
                    initial={{ height: 0 }}
                    animate={{ height: oracleHeight }}
                    transition={{ duration: 0.3, delay: clueNum * 0.1 + 0.1 }}
                    title={`Oracle: ${pred.oracleTopPick} (${Math.round(pred.oracleConfidence! * 100)}%)`}
                  >
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 text-xs text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 pointer-events-none">
                      {pred.oracleTopPick}
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Clue number with agreement badge */}
              <div className="flex items-center gap-1">
                <span className="text-xs text-gray-400">{clueNum}</span>
                <span className={`w-3 h-3 ${badge.color} rounded-full text-[8px] text-white flex items-center justify-center font-bold`}>
                  {badge.label}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-2 text-[10px] text-gray-500">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-green-500 rounded" />
          <span>Agents</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-purple-500 rounded" />
          <span>Oracle</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-green-500 rounded-full text-[8px] text-white flex items-center justify-center font-bold">S</span>
          <span>Strong</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 bg-yellow-500 rounded-full text-[8px] text-white flex items-center justify-center font-bold">M</span>
          <span>Moderate</span>
        </div>
      </div>
    </motion.div>
  )
}
