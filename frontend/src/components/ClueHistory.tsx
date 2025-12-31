import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ClueHistoryProps {
  clues: string[]
  currentClueNumber: number
  isLoading: boolean
  onSubmitClue: (clue: string) => void
  onEditClue: (index: number, newText: string) => void
  disabled?: boolean
}

/**
 * ClueHistory - Always-visible clue list with inline editing
 *
 * Features:
 * - Shows all entered clues with numbers
 * - Edit button on each clue for typo correction
 * - Input field for next clue at bottom
 * - Visual indicator for edited clues
 */
export default function ClueHistory({
  clues,
  currentClueNumber,
  isLoading,
  onSubmitClue,
  onEditClue,
  disabled = false
}: ClueHistoryProps) {
  const [inputValue, setInputValue] = useState('')
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading || disabled) return
    onSubmitClue(inputValue.trim())
    setInputValue('')
  }

  const startEditing = (index: number) => {
    setEditingIndex(index)
    setEditValue(clues[index])
  }

  const cancelEditing = () => {
    setEditingIndex(null)
    setEditValue('')
  }

  const saveEdit = () => {
    if (editingIndex !== null && editValue.trim() !== clues[editingIndex]) {
      onEditClue(editingIndex, editValue.trim())
    }
    cancelEditing()
  }

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      saveEdit()
    } else if (e.key === 'Escape') {
      cancelEditing()
    }
  }

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500">
          Clues
        </h3>
        <span className="text-xs text-gray-600">
          {clues.length}/5
        </span>
      </div>

      {/* Clue List */}
      <div className="space-y-2">
        <AnimatePresence mode="popLayout">
          {clues.map((clue, index) => (
            <motion.div
              key={`clue-${index}`}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="group flex items-start gap-2"
            >
              {/* Clue Number */}
              <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gray-800 text-xs font-medium text-gray-400">
                {index + 1}
              </span>

              {/* Clue Content or Edit Input */}
              {editingIndex === index ? (
                <div className="flex flex-1 items-center gap-2">
                  <input
                    type="text"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={handleEditKeyDown}
                    className="flex-1 rounded-lg border border-primary bg-gray-800 px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary"
                    autoFocus
                  />
                  <button
                    onClick={saveEdit}
                    className="rounded px-2 py-1 text-xs text-green-400 hover:bg-green-900/30"
                    title="Save"
                  >
                    Save
                  </button>
                  <button
                    onClick={cancelEditing}
                    className="rounded px-2 py-1 text-xs text-gray-400 hover:bg-gray-700"
                    title="Cancel"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <>
                  <span className="flex-1 text-sm text-gray-300">{clue}</span>

                  {/* Edit Button - visible on hover */}
                  <button
                    onClick={() => startEditing(index)}
                    className="flex-shrink-0 rounded p-1 text-gray-600 opacity-0 transition-opacity hover:bg-gray-800 hover:text-gray-400 group-hover:opacity-100"
                    title="Edit clue"
                    disabled={isLoading}
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                </>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* New Clue Input */}
        {currentClueNumber <= 5 && !disabled && (
          <motion.form
            onSubmit={handleSubmit}
            className="flex items-center gap-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {/* Clue Number */}
            <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-dashed border-gray-700 text-xs font-medium text-gray-500">
              {currentClueNumber}
            </span>

            {/* Input */}
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={`Enter clue ${currentClueNumber}...`}
              disabled={isLoading || disabled}
              className="flex-1 rounded-lg border border-gray-700 bg-gray-800/50 px-3 py-2 text-sm text-white placeholder-gray-500 transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
            />

            {/* Submit Button */}
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading || disabled}
              className="flex-shrink-0 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                </span>
              ) : (
                'Submit'
              )}
            </button>
          </motion.form>
        )}

        {/* All clues submitted indicator */}
        {currentClueNumber > 5 && (
          <div className="flex items-center gap-2 pt-2 text-sm text-gray-500">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-900/30 text-green-400">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </span>
            <span>All 5 clues submitted</span>
          </div>
        )}
      </div>
    </div>
  )
}
