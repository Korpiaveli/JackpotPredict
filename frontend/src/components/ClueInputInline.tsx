import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

interface ClueInputInlineProps {
  onSubmit: (clue: string) => void
  clueNumber: number
  isLoading: boolean
  disabled?: boolean
}

/**
 * Simplified inline clue input.
 * Single row with input and submit button, always visible.
 */
export default function ClueInputInline({
  onSubmit,
  clueNumber,
  isLoading,
  disabled = false,
}: ClueInputInlineProps) {
  const [text, setText] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-focus when enabled
  useEffect(() => {
    if (!disabled && !isLoading && inputRef.current) {
      inputRef.current.focus()
    }
  }, [disabled, isLoading])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (text.trim() && !isLoading && !disabled) {
      onSubmit(text.trim())
      setText('')
    }
  }

  const isDisabled = disabled || isLoading || clueNumber > 5

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="flex items-center gap-2"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="relative flex-1">
        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            clueNumber > 5
              ? 'Puzzle complete!'
              : `Enter clue ${clueNumber}...`
          }
          disabled={isDisabled}
          maxLength={500}
          className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-base text-white placeholder:text-gray-600 focus:border-primary focus:outline-none disabled:opacity-50"
        />
        {/* Clue counter badge */}
        <span className="absolute right-3 top-1/2 -translate-y-1/2 font-mono text-xs text-gray-500">
          {clueNumber}/5
        </span>
      </div>

      <motion.button
        type="submit"
        disabled={!text.trim() || isDisabled}
        className="rounded-lg bg-primary px-6 py-3 font-bold text-background disabled:opacity-50"
        whileTap={{ scale: 0.95 }}
      >
        {isLoading ? (
          <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-background border-t-transparent" />
        ) : (
          'Go'
        )}
      </motion.button>
    </motion.form>
  )
}
