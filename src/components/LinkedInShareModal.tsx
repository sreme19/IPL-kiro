import { useState } from 'react'
import { type SimulationResponse } from '../api/client'
import { trackResultShared } from '../analytics/events'

interface Props {
  result: SimulationResponse
  teamName: string
  opponentName: string
  venue: string
  season: number
  onClose: () => void
}

function generatePost(
  result: SimulationResponse,
  teamName: string,
  opponentName: string,
  venue: string,
  season: number
): string {
  const { optimization, simulation } = result
  const wp = (simulation.win_probability.win_probability * 100).toFixed(1)
  const ciLo = (simulation.win_probability.confidence_interval[0] * 100).toFixed(1)
  const ciHi = (simulation.win_probability.confidence_interval[1] * 100).toFixed(1)
  const improvement = optimization.improvement_pct.toFixed(1)
  const xi = optimization.selected_xi.map(p => p.name).join(', ')
  const overseas = optimization.selected_xi.filter(p => p.is_overseas).length
  const topThreat = simulation.key_threats[0]

  const ciWidth = (simulation.win_probability.confidence_interval[1] - simulation.win_probability.confidence_interval[0]) * 100

  let insight = ''
  if (ciWidth > 15) {
    insight = `The wide ${ciWidth.toFixed(0)}pp confidence interval (${ciLo}–${ciHi}%) tells the real story: this match is genuinely unpredictable. Small selection changes can swing win probability by double digits — exactly the kind of edge ILP captures.`
  } else if (parseFloat(improvement) > 12) {
    insight = `The ${improvement}% ILP gain over a naive selection isn't cosmetic. It compounds — across a 14-match season that gap translates to roughly 1–2 additional wins. Cricket selection is an optimisation problem whether teams acknowledge it or not.`
  } else if (topThreat) {
    insight = `The threat graph flagged ${topThreat.batter} vs ${topThreat.bowler} as the key matchup (threat score ${topThreat.threat_score?.toFixed(2) ?? 'high'}). The ILP penalised players who lose that edge — selection isn't just about form, it's about matchup geometry.`
  } else {
    insight = `Optimal team selection is a constrained combinatorial problem with 11 binary variables and 4 hard constraints. A greedy pick almost always leaves value on the table — the solver finds it.`
  }

  return `🏏 I ran an AI-powered IPL XI optimisation for ${teamName} vs ${opponentName} at ${venue} (IPL ${season}).

📊 RESULTS
• Optimal XI: ${xi}
• Overseas slots used: ${overseas}/4
• Win probability: ${wp}% (95% CI: ${ciLo}–${ciHi}%)
• ILP objective improvement over baseline: +${improvement}%

🔢 HOW IT WORKS — THE MATH
The engine solves an Integer Linear Programme:

  max  Σᵢ ( α·E[runs]ᵢ + β·E[wickets]ᵢ − γ·CI_penaltyᵢ − δ·threatᵢ ) · xᵢ
  s.t. Σ xᵢ = 11,  Σ xᵢ(WK) ≥ 1,  Σ xᵢ(bowl) ≥ 4,  Σ xᵢ(OS) ≤ 4,  xᵢ ∈ {0,1}

Once the XI is fixed, 10,000 T20 innings are simulated via a Poisson/Bernoulli MDP. Win probability is the fraction of rollouts where the selected team outscores the opponent, with Platt-scaling calibration applied from historical results.

💡 THE INSIGHT
${insight}

🛠 ABOUT THE PROJECT
IPL Captain Simulator combines Integer Linear Programming (PuLP/CBC), Monte Carlo simulation, a bipartite threat graph (NetworkX), and optional Claude AI commentary to pick and analyse IPL XIs. The backend is FastAPI on AWS Lambda; the frontend is React + Vite.

GitHub → https://github.com/your-repo/ipl-captain-simulator  ← swap in your link

Built with #Python #React #OperationsResearch #CricketAnalytics #AI
`
}

export function LinkedInShareModal({ result, teamName, opponentName, venue, season, onClose }: Props) {
  const [copied, setCopied] = useState(false)
  const post = generatePost(result, teamName, opponentName, venue, season)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(post)
    setCopied(true)
    trackResultShared('linkedin')
    setTimeout(() => setCopied(false), 2500)
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Share to LinkedIn</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <p className="modal-hint">
          Copy the post below, then paste it directly into LinkedIn.
        </p>

        <textarea
          className="share-textarea"
          readOnly
          value={post}
          rows={22}
        />

        <div className="modal-actions">
          <button className="copy-btn" onClick={handleCopy}>
            {copied ? '✅ Copied!' : '📋 Copy post'}
          </button>
          <a
            className="linkedin-btn"
            href="https://www.linkedin.com/post/new"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => trackResultShared('linkedin_open')}
          >
            Open LinkedIn ↗
          </a>
        </div>
      </div>
    </div>
  )
}
