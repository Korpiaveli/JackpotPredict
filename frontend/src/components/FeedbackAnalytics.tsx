import { motion } from 'framer-motion'
import type { AnalyticsResponse } from '../types/api'

interface FeedbackAnalyticsProps {
  analytics: AnalyticsResponse
}

export default function FeedbackAnalytics({ analytics }: FeedbackAnalyticsProps) {
  const {
    total_games,
    category_breakdown,
    avg_solve_clue,
    early_solves,
    late_solves,
    insights_provided,
    insights_percentage,
    recent_answers
  } = analytics

  // Calculate category percentages for the bar
  const categoryColors: Record<string, string> = {
    thing: 'bg-blue-500',
    person: 'bg-green-500',
    place: 'bg-purple-500'
  }

  const categoryEmojis: Record<string, string> = {
    thing: '',
    person: '',
    place: ''
  }

  return (
    <motion.div
      className="clue-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-bold text-white">Feedback Analytics</h3>
        <span className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-400">
          {total_games} games
        </span>
      </div>

      {/* Overall Stats Grid */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-gray-800/50 p-3 text-center">
          <div className="text-2xl font-bold text-primary">{avg_solve_clue}</div>
          <div className="text-xs text-gray-500">Avg Solve Clue</div>
        </div>
        <div className="rounded-lg bg-gray-800/50 p-3 text-center">
          <div className="text-2xl font-bold text-green-400">{early_solves}</div>
          <div className="text-xs text-gray-500">Early (1-2)</div>
        </div>
        <div className="rounded-lg bg-gray-800/50 p-3 text-center">
          <div className="text-2xl font-bold text-orange-400">{late_solves}</div>
          <div className="text-xs text-gray-500">Late (4-5)</div>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="mb-4">
        <div className="mb-2 text-xs uppercase tracking-wide text-gray-500">
          Category Distribution
        </div>
        <div className="flex h-3 overflow-hidden rounded-full bg-gray-800">
          {Object.entries(category_breakdown).map(([cat, stats]) => {
            const percentage = (stats.total / total_games) * 100
            return (
              <div
                key={cat}
                className={`${categoryColors[cat] || 'bg-gray-600'} transition-all`}
                style={{ width: `${percentage}%` }}
                title={`${cat}: ${stats.total} (${percentage.toFixed(0)}%)`}
              />
            )
          })}
        </div>
        <div className="mt-2 flex justify-between text-xs">
          {Object.entries(category_breakdown).map(([cat, stats]) => (
            <div key={cat} className="flex items-center gap-1">
              <span className={`h-2 w-2 rounded-full ${categoryColors[cat] || 'bg-gray-600'}`} />
              <span className="capitalize text-gray-400">
                {categoryEmojis[cat]} {cat}: {stats.total}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Category Details */}
      <div className="mb-4 space-y-2">
        <div className="text-xs uppercase tracking-wide text-gray-500">
          Performance by Category
        </div>
        {Object.entries(category_breakdown).map(([cat, stats]) => (
          <div
            key={cat}
            className="flex items-center justify-between rounded-lg bg-gray-800/30 px-3 py-2"
          >
            <span className="capitalize text-gray-300">
              {categoryEmojis[cat]} {cat}
            </span>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-400">
                Avg: <span className="font-mono text-white">{stats.avg_solve_clue}</span>
              </span>
              <span className="text-gray-400">
                Insights: <span className="font-mono text-green-400">{stats.insights_provided}</span>
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Insights Progress */}
      <div className="mb-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs uppercase tracking-wide text-gray-500">
            Key Insights Provided
          </span>
          <span className="text-sm font-bold text-green-400">
            {insights_percentage}%
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-gray-800">
          <motion.div
            className="h-full bg-green-500"
            initial={{ width: 0 }}
            animate={{ width: `${insights_percentage}%` }}
            transition={{ duration: 0.5, delay: 0.2 }}
          />
        </div>
        <div className="mt-1 text-xs text-gray-500">
          {insights_provided} of {total_games} games have insights
        </div>
      </div>

      {/* Recent Answers */}
      {recent_answers.length > 0 && (
        <div>
          <div className="mb-2 text-xs uppercase tracking-wide text-gray-500">
            Recent Answers
          </div>
          <div className="flex flex-wrap gap-1.5">
            {recent_answers.map((answer, idx) => (
              <span
                key={idx}
                className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300"
              >
                {answer}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
