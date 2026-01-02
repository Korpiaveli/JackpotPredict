import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ClueInputProps {
  onSubmit: (clue: string, theme?: string) => void
  clueNumber: number
  previousClues: string[]
  isLoading: boolean
  disabled?: boolean
}

export default function ClueInput({
  onSubmit,
  clueNumber,
  previousClues,
  isLoading,
  disabled = false
}: ClueInputProps) {
  const [clueText, setClueText] = useState('')
  const [theme, setTheme] = useState('')
  const [showTheme, setShowTheme] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Auto-focus input when enabled
    if (!disabled && inputRef.current) {
      inputRef.current.focus()
    }
  }, [disabled])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (clueText.trim() && !isLoading) {
      onSubmit(clueText.trim(), theme.trim() || undefined)
      setClueText('')
    }
  }

  const isMaxClues = clueNumber > 5

  return (
    <div className="space-y-4">
      {/* Previous Clues History */}
      {previousClues.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm text-gray-500 uppercase tracking-wide">Previous Clues</h3>
          <div className="space-y-2">
            <AnimatePresence>
              {previousClues.map((clue, index) => (
                <motion.div
                  key={index}
                  className="clue-card flex items-center gap-3"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center text-sm font-bold">
                    {index + 1}
                  </span>
                  <p className="text-gray-300 text-sm">{clue}</p>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Theme/Sponsor Input (Optional, Collapsible) */}
      <div className="mb-4">
        <button
          type="button"
          onClick={() => setShowTheme(!showTheme)}
          className="text-sm text-gray-400 hover:text-primary transition-colors flex items-center gap-2"
        >
          <span className={`transform transition-transform ${showTheme ? 'rotate-90' : ''}`}>▶</span>
          {showTheme ? 'Hide' : 'Add'} Tonight's Theme/Sponsor (optional)
        </button>
        <AnimatePresence>
          {showTheme && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-2 overflow-hidden"
            >
              <input
                type="text"
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                placeholder="e.g., Stranger Things, Marvel, 80s Movies..."
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-base
                         focus:border-primary focus:outline-none transition-all duration-200
                         placeholder:text-gray-500"
                maxLength={200}
              />
              <p className="text-xs text-gray-500 mt-1">
                Hint: The answer may or may not relate to this theme
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label htmlFor="clue-input" className="block mb-2">
            <span className="text-primary text-xl font-bold uppercase tracking-wide">
              Clue {clueNumber} of 5
            </span>
            {isMaxClues && (
              <span className="ml-2 text-danger text-sm">(Maximum reached)</span>
            )}
          </label>
          <input
            ref={inputRef}
            id="clue-input"
            type="text"
            value={clueText}
            onChange={(e) => setClueText(e.target.value)}
            placeholder={
              isMaxClues
                ? 'Maximum clues reached'
                : 'Enter the clue from the game show...'
            }
            disabled={disabled || isLoading || isMaxClues}
            className="w-full px-6 py-4 bg-gray-900 border-2 border-gray-800 rounded-lg text-white text-xl
                     focus:border-primary focus:outline-none transition-all duration-200
                     disabled:opacity-50 disabled:cursor-not-allowed
                     placeholder:text-gray-600"
            maxLength={500}
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={!clueText.trim() || isLoading || disabled || isMaxClues}
            className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-background border-t-transparent rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                Submit Clue {clueNumber}
                <span>→</span>
              </>
            )}
          </button>
        </div>

        {/* Character count */}
        {clueText.length > 0 && (
          <div className="text-xs text-gray-500 text-right">
            {clueText.length} / 500 characters
          </div>
        )}

        {/* Keyboard hint */}
        {!isLoading && !disabled && !isMaxClues && (
          <div className="text-xs text-gray-600 text-center">
            Press <kbd className="px-2 py-1 bg-gray-800 rounded">Enter</kbd> to submit
          </div>
        )}
      </form>
    </div>
  )
}
