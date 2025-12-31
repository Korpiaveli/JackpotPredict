/**
 * Shared confidence color utility for consistent styling across all components.
 * Eliminates the 3 different implementations that existed before.
 */

export type ConfidenceLevel = 'high' | 'medium' | 'low'

/**
 * Determine confidence level from a confidence value.
 * Handles both 0-1 and 0-100 scales automatically.
 */
export function getConfidenceLevel(confidence: number): ConfidenceLevel {
  // Normalize to 0-1 if passed as percentage (0-100)
  const normalized = confidence > 1 ? confidence / 100 : confidence

  if (normalized >= 0.75) return 'high'
  if (normalized >= 0.5) return 'medium'
  return 'low'
}

/**
 * Confidence color mappings for Tailwind classes and hex values.
 */
export const CONFIDENCE_COLORS = {
  high: {
    text: 'text-green-400',
    bg: 'bg-green-500',
    bgSubtle: 'bg-green-500/20',
    border: 'border-green-500',
    hex: '#22c55e',
  },
  medium: {
    text: 'text-yellow-400',
    bg: 'bg-yellow-500',
    bgSubtle: 'bg-yellow-500/20',
    border: 'border-yellow-500',
    hex: '#eab308',
  },
  low: {
    text: 'text-red-400',
    bg: 'bg-red-500',
    bgSubtle: 'bg-red-500/20',
    border: 'border-red-500',
    hex: '#ef4444',
  },
} as const

/**
 * Get the appropriate color style for a confidence value.
 */
export function getConfidenceStyle(confidence: number) {
  return CONFIDENCE_COLORS[getConfidenceLevel(confidence)]
}

/**
 * Get confidence as a display percentage (always 0-100).
 */
export function getConfidencePercent(confidence: number): number {
  return confidence > 1 ? Math.round(confidence) : Math.round(confidence * 100)
}
