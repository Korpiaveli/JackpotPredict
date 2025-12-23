import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface CountdownTimerProps {
  initialSeconds?: number
  onComplete?: () => void
  isActive?: boolean
  resetKey?: number        // Increment to trigger reset
  showIdle?: boolean       // Show "Ready" instead of countdown
}

export default function CountdownTimer({
  initialSeconds = 20,
  onComplete,
  isActive = true,
  resetKey = 0,
  showIdle = false
}: CountdownTimerProps) {
  const [seconds, setSeconds] = useState(initialSeconds)

  useEffect(() => {
    if (!isActive || showIdle) return

    if (seconds === 0) {
      onComplete?.()
      return
    }

    const interval = setInterval(() => {
      setSeconds((prev) => Math.max(0, prev - 1))
    }, 1000)

    return () => clearInterval(interval)
  }, [seconds, isActive, showIdle, onComplete])

  // Reset when resetKey changes (external reset trigger)
  useEffect(() => {
    setSeconds(initialSeconds)
  }, [resetKey, initialSeconds])

  // Color based on remaining time
  const getColor = () => {
    if (showIdle) return 'text-primary' // Blue for idle
    if (seconds >= 15) return 'text-success' // Green
    if (seconds >= 8) return 'text-warning'  // Yellow
    return 'text-danger'  // Red
  }

  const getBgColor = () => {
    if (showIdle) return 'from-primary/20' // Blue for idle
    if (seconds >= 15) return 'from-success/20' // Green
    if (seconds >= 8) return 'from-warning/20'  // Yellow
    return 'from-danger/20'  // Red
  }

  const getBorderColor = () => {
    if (showIdle) return 'border-primary'
    if (seconds <= 7) return 'border-danger'
    if (seconds <= 14) return 'border-warning'
    return 'border-success'
  }

  return (
    <motion.div
      className={`relative flex flex-col items-center justify-center p-8 rounded-2xl bg-gradient-to-br ${getBgColor()} to-transparent border-2 ${getBorderColor()} transition-all duration-500`}
      animate={{
        scale: !showIdle && seconds <= 5 ? [1, 1.05, 1] : 1,
      }}
      transition={{
        duration: 1,
        repeat: !showIdle && seconds <= 5 ? Infinity : 0,
      }}
    >
      <div className="text-sm uppercase tracking-wider text-gray-400 mb-2">
        {showIdle ? 'Status' : 'Time Remaining'}
      </div>
      <motion.div
        className={`text-8xl font-mono font-bold ${getColor()} transition-colors duration-500`}
        key={showIdle ? 'idle' : seconds} // Force re-render for animation
        initial={{ scale: 1.2, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {showIdle ? (
          <span className="text-5xl">READY</span>
        ) : (
          `${seconds}s`
        )}
      </motion.div>
      {showIdle && (
        <motion.div
          className="absolute -bottom-2 text-primary text-xs font-bold uppercase"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          Enter first clue
        </motion.div>
      )}
      {!showIdle && seconds <= 5 && seconds > 0 && (
        <motion.div
          className="absolute -bottom-2 text-danger text-xs font-bold uppercase"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          HURRY!
        </motion.div>
      )}
    </motion.div>
  )
}
