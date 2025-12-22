import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface CountdownTimerProps {
  initialSeconds?: number
  onComplete?: () => void
  isActive?: boolean
}

export default function CountdownTimer({
  initialSeconds = 20,
  onComplete,
  isActive = true
}: CountdownTimerProps) {
  const [seconds, setSeconds] = useState(initialSeconds)

  useEffect(() => {
    if (!isActive) return

    if (seconds === 0) {
      onComplete?.()
      return
    }

    const interval = setInterval(() => {
      setSeconds((prev) => Math.max(0, prev - 1))
    }, 1000)

    return () => clearInterval(interval)
  }, [seconds, isActive, onComplete])

  // Reset when initialSeconds changes
  useEffect(() => {
    setSeconds(initialSeconds)
  }, [initialSeconds])

  // Color based on remaining time
  const getColor = () => {
    if (seconds >= 15) return 'text-success' // Green
    if (seconds >= 8) return 'text-warning'  // Yellow
    return 'text-danger'  // Red
  }

  const getBgColor = () => {
    if (seconds >= 15) return 'from-success/20' // Green
    if (seconds >= 8) return 'from-warning/20'  // Yellow
    return 'from-danger/20'  // Red
  }

  return (
    <motion.div
      className={`relative flex flex-col items-center justify-center p-8 rounded-2xl bg-gradient-to-br ${getBgColor()} to-transparent border-2 ${
        seconds <= 7 ? 'border-danger' : seconds <= 14 ? 'border-warning' : 'border-success'
      } transition-all duration-500`}
      animate={{
        scale: seconds <= 5 ? [1, 1.05, 1] : 1,
      }}
      transition={{
        duration: 1,
        repeat: seconds <= 5 ? Infinity : 0,
      }}
    >
      <div className="text-sm uppercase tracking-wider text-gray-400 mb-2">
        Time Remaining
      </div>
      <motion.div
        className={`text-8xl font-mono font-bold ${getColor()} transition-colors duration-500`}
        key={seconds} // Force re-render for animation
        initial={{ scale: 1.2, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {seconds}s
      </motion.div>
      {seconds <= 5 && seconds > 0 && (
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
