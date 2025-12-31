import { useState, useCallback } from 'react'

interface UseCopyToClipboardReturn {
  copy: (text: string) => Promise<boolean>
  copiedText: string | null
  isCopied: boolean
}

/**
 * Unified copy-to-clipboard hook with feedback.
 * Provides haptic feedback on mobile and auto-resets after timeout.
 */
export function useCopyToClipboard(resetDelay = 2000): UseCopyToClipboardReturn {
  const [copiedText, setCopiedText] = useState<string | null>(null)

  const copy = useCallback(
    async (text: string): Promise<boolean> => {
      if (!text) return false

      try {
        await navigator.clipboard.writeText(text)
        setCopiedText(text)

        // Haptic feedback on mobile (if available)
        if ('vibrate' in navigator) {
          navigator.vibrate(50)
        }

        // Reset after delay
        setTimeout(() => setCopiedText(null), resetDelay)
        return true
      } catch (err) {
        console.error('Failed to copy:', err)
        return false
      }
    },
    [resetDelay]
  )

  return {
    copy,
    copiedText,
    isCopied: copiedText !== null,
  }
}
