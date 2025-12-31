import { AnimatePresence, motion } from 'framer-motion'

interface CopyToastProps {
  text: string | null
  show: boolean
}

/**
 * Global copy feedback notification.
 * Fixed position at bottom-center, auto-dismisses.
 */
export default function CopyToast({ text, show }: CopyToastProps) {
  return (
    <AnimatePresence>
      {show && text && (
        <motion.div
          className="fixed bottom-20 left-1/2 z-50 flex items-center gap-2 rounded-lg bg-green-500 px-4 py-2 text-sm font-medium text-white shadow-lg"
          initial={{ opacity: 0, y: 20, x: '-50%' }}
          animate={{ opacity: 1, y: 0, x: '-50%' }}
          exit={{ opacity: 0, y: 20, x: '-50%' }}
          transition={{ duration: 0.2 }}
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
          <span>Copied: {text}</span>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
