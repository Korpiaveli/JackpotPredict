import type { AgreementStrength } from '../types/api'

interface StatusBarProps {
  agentsResponded: number
  clueNumber: number
  elapsedTime: number
  agreementStrength: AgreementStrength
}

export default function StatusBar({
  agentsResponded,
  clueNumber,
  elapsedTime,
  agreementStrength
}: StatusBarProps) {
  return (
    <div className="flex items-center justify-between text-xs text-gray-400 px-1">
      <div className="flex items-center gap-3">
        {/* Agents responded */}
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
          {agentsResponded}/5 agents
        </span>

        {/* Agreement */}
        <span>
          {agreementStrength} agreement
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* Clue number */}
        <span>
          Clue {clueNumber}/5
        </span>

        {/* Processing time */}
        <span className="font-mono">
          {elapsedTime.toFixed(1)}s
        </span>
      </div>
    </div>
  )
}
