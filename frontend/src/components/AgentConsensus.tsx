import { motion } from 'framer-motion'
import type { AgentName, AgentPrediction, CulturalMatch } from '../types/api'
import { AGENT_INFO } from '../types/api'

interface AgentConsensusProps {
  agents: Record<AgentName, AgentPrediction | null>
  winningAnswer: string
  culturalMatches?: CulturalMatch[]
}

/**
 * Simplified agent display as horizontal scrollable pills.
 * Shows who agrees vs disagrees with the winning answer.
 */
export default function AgentConsensus({
  agents,
  winningAnswer,
  culturalMatches,
}: AgentConsensusProps) {
  const agentList = Object.entries(agents).filter(
    ([, pred]) => pred !== null
  ) as [AgentName, AgentPrediction][]

  const agreeing = agentList.filter(
    ([, pred]) => pred.answer.toLowerCase() === winningAnswer.toLowerCase()
  )
  const dissenting = agentList.filter(
    ([, pred]) => pred.answer.toLowerCase() !== winningAnswer.toLowerCase()
  )

  return (
    <div className="space-y-3">
      {/* Agent Agreement */}
      <div>
        <div className="mb-2 text-xs uppercase tracking-wide text-gray-500">
          Agent Consensus ({agreeing.length}/{agentList.length} agree)
        </div>

        <div className="flex flex-wrap gap-2">
          {agreeing.map(([name, pred]) => (
            <AgentPill key={name} name={name} pred={pred} agrees={true} />
          ))}
          {dissenting.map(([name, pred]) => (
            <AgentPill key={name} name={name} pred={pred} agrees={false} />
          ))}
        </div>
      </div>

      {/* Cultural References */}
      {culturalMatches && culturalMatches.length > 0 && (
        <div>
          <div className="mb-2 text-xs uppercase tracking-wide text-gray-500">
            Cultural References
          </div>
          <div className="flex flex-wrap gap-2">
            {culturalMatches.slice(0, 4).map((match) => (
              <CulturalPill key={match.keyword} match={match} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface AgentPillProps {
  name: AgentName
  pred: AgentPrediction
  agrees: boolean
}

function AgentPill({ name, pred, agrees }: AgentPillProps) {
  const info = AGENT_INFO[name]

  return (
    <motion.div
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs ${
        agrees
          ? 'border-green-500/50 bg-green-900/30 text-green-300'
          : 'border-gray-700 bg-gray-800/50 text-gray-400'
      }`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      title={pred.reasoning}
    >
      <span>{info.emoji}</span>
      <span className="font-medium">{info.label}</span>
      {!agrees && (
        <span className="text-gray-500">({pred.answer})</span>
      )}
    </motion.div>
  )
}

interface CulturalPillProps {
  match: CulturalMatch
}

function CulturalPill({ match }: CulturalPillProps) {
  const sourceColors: Record<string, string> = {
    quote: 'border-blue-500/50 bg-blue-900/30 text-blue-300',
    pattern: 'border-green-500/50 bg-green-900/30 text-green-300',
    historical: 'border-purple-500/50 bg-purple-900/30 text-purple-300',
  }

  return (
    <motion.div
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs ${
        sourceColors[match.source] || 'border-gray-700 bg-gray-800/50 text-gray-400'
      }`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      title={`${match.source}: ${match.keyword} → ${match.answer}`}
    >
      <span className="font-medium">{match.keyword}</span>
      <span className="opacity-60">→ {match.answer}</span>
    </motion.div>
  )
}
