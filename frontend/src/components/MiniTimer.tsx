import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface MiniTimerProps {
  initialSeconds?: number
  isActive: boolean
  resetKey?: number
  showIdle?: boolean
}

/**
 * Compact circular timer for header placement.
 * 48x48px, color transitions based on time remaining.
 */
export default function MiniTimer({
  initialSeconds = 20,
  isActive,
  resetKey = 0,
  showIdle = false,
}: MiniTimerProps) {
  const [seconds, setSeconds] = useState(initialSeconds)

  // Reset timer when resetKey changes
  useEffect(() => {
    setSeconds(initialSeconds)
  }, [resetKey, initialSeconds])

  // Countdown logic
  useEffect(() => {
    if (!isActive || showIdle || seconds <= 0) return

    const interval = setInterval(() => {
      setSeconds((prev) => Math.max(0, prev - 1))
    }, 1000)

    return () => clearInterval(interval)
  }, [isActive, showIdle, seconds])

  // Color based on time remaining
  const getColorClasses = () => {
    if (showIdle) return 'border-primary text-primary'
    if (seconds >= 15) return 'border-green-500 text-green-400'
    if (seconds >= 8) return 'border-yellow-500 text-yellow-400'
    return 'border-red-500 text-red-400'
  }

  const isUrgent = seconds <= 5 && isActive && !showIdle

  return (
    <motion.div
      className={`flex h-12 w-12 items-center justify-center rounded-full border-2 font-mono text-lg font-bold transition-colors duration-300 ${getColorClasses()}`}
      animate={
        isUrgent
          ? {
              scale: [1, 1.1, 1],
              borderWidth: ['2px', '3px', '2px'],
            }
          : {}
      }
      transition={
        isUrgent
          ? {
              duration: 0.5,
              repeat: Infinity,
            }
          : {}
      }
    >
      {showIdle ? initialSeconds : seconds}
    </motion.div>
  )
}
