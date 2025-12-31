import { motion } from 'framer-motion'

interface ResponseTimerProps {
  responseTime: number | null // in seconds
  isLoading: boolean
}

/**
 * Displays response time with color-coded visual indicator.
 * Green: <3s, Yellow: 3-5s, Red: >5s
 */
export default function ResponseTimer({ responseTime, isLoading }: ResponseTimerProps) {
  if (isLoading) {
    return (
      <motion.div
        className="flex items-center gap-1.5 rounded-full bg-gray-800 px-3 py-1.5"
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      >
        <div className="h-2 w-2 rounded-full bg-blue-500" />
        <span className="font-mono text-xs text-gray-400">...</span>
      </motion.div>
    )
  }

  if (responseTime === null) return null

  const getColorClasses = () => {
    if (responseTime < 3)
      return {
        dot: 'bg-green-500',
        text: 'text-green-400',
        bg: 'bg-green-900/30 border-green-500/30',
      }
    if (responseTime < 5)
      return {
        dot: 'bg-yellow-500',
        text: 'text-yellow-400',
        bg: 'bg-yellow-900/30 border-yellow-500/30',
      }
    return {
      dot: 'bg-red-500',
      text: 'text-red-400',
      bg: 'bg-red-900/30 border-red-500/30',
    }
  }

  const colors = getColorClasses()

  return (
    <motion.div
      className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 ${colors.bg}`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      title={`Response time: ${responseTime.toFixed(2)} seconds`}
    >
      <div className={`h-2 w-2 rounded-full ${colors.dot}`} />
      <span className={`font-mono text-xs font-medium ${colors.text}`}>
        {responseTime.toFixed(1)}s
      </span>
    </motion.div>
  )
}
