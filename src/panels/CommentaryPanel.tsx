import { useState } from 'react'
import { type SimulationResponse } from '../api/client'
import { LinkedInShareModal } from '../components/LinkedInShareModal'

interface Props {
  simulationResult: SimulationResponse | null
  teamName: string
  opponentName: string
  venue: string
  season: number
}

const INSIGHT_COLOR: Record<string, string> = {
  venue_encoding: '#3b82f6',
  bipartite_threat: '#ef4444',
  ilp_solution: '#8b5cf6',
  monte_carlo: '#16a34a',
}

const DEFAULT_STEPS = [
  { step_number: 1, title: 'Venue Encoding', description: 'Venue weights are computed using historical run-rate data, pitch type, and dew factor into an α-β weighted vector.', formula: 'w_venue = f(pitch, dew, boundary_size)', insight: 'Adjust formation based on pitch conditions', insight_type: 'venue_encoding' },
  { step_number: 2, title: 'Bipartite Threat Graph', description: 'A bipartite graph maps batters vs bowlers to compute dismissal-rate threat edges using historical head-to-head data.', formula: 'E(b,p) = Σ dismissal_rate × venue_multiplier', insight: 'High threat edges inform ILP exclusion penalties', insight_type: 'bipartite_threat' },
  { step_number: 3, title: 'ILP Optimisation', description: 'PuLP CBC solver maximizes team expected value subject to role, overseas, and formation constraints.', formula: 'max Σ(α·E[runs] + β·E[wkts] - γ·CI - δ·threat)·xᵢ', insight: 'Optimal XI selected respecting all cricket regulations', insight_type: 'ilp_solution' },
  { step_number: 4, title: 'Monte Carlo Win Probability', description: '10,000 vectorized T20 innings are simulated per Poisson/Bernoulli MDP with Platt-scaling calibration.', formula: 'P(win) = #{runs_team > runs_opp} / N', insight: '95% CI narrows with more calibration data', insight_type: 'monte_carlo' },
]

export function CommentaryPanel({ simulationResult, teamName, opponentName, venue, season }: Props) {
  const [activeStep, setActiveStep] = useState<number>(0)
  const [showShare, setShowShare] = useState(false)

  const steps = simulationResult?.optimization.commentary_steps.length
    ? simulationResult.optimization.commentary_steps
    : DEFAULT_STEPS

  const narrative = simulationResult?.narrative

  return (
    <div className="panel" data-testid="commentary-panel">
      <h2>6. AI Commentary</h2>
      <div className="panel-content">
        <div className="commentary-tabs" data-testid="commentary-steps">
          {steps.map((step, i) => (
            <button
              key={step.step_number}
              className={`tab-btn ${activeStep === i ? 'active' : ''}`}
              onClick={() => setActiveStep(i)}
              data-testid={`step-${i}`}
              style={activeStep === i ? { borderColor: INSIGHT_COLOR[step.insight_type] ?? '#1e3c72' } : {}}
            >
              Step {step.step_number}
            </button>
          ))}
        </div>

        {steps[activeStep] && (
          <div className="commentary-body">
            <div className="step-header" style={{ borderLeft: `4px solid ${INSIGHT_COLOR[steps[activeStep].insight_type] ?? '#1e3c72'}` }}>
              <h4>{steps[activeStep].title}</h4>
            </div>
            <code className="formula-block">{steps[activeStep].formula}</code>
            <p className="step-description">{steps[activeStep].description}</p>
            <div className="insight-box">
              <span className="insight-label">💡 Insight</span>
              <span>{steps[activeStep].insight}</span>
            </div>
          </div>
        )}

        {narrative?.summary && (
          <div className="narrative-box">
            <p className="narrative-label">🤖 Narrative</p>
            <p>{narrative.summary}</p>
          </div>
        )}

        <div className="commentary-footer">
          <span className="total-steps" data-testid="total-steps">{steps.length} commentary steps</span>
          {simulationResult && (
            <button className="share-btn" onClick={() => setShowShare(true)}>
              🔗 Share on LinkedIn
            </button>
          )}
        </div>
      </div>

      {showShare && simulationResult && (
        <LinkedInShareModal
          result={simulationResult}
          teamName={teamName}
          opponentName={opponentName}
          venue={venue}
          season={season}
          onClose={() => setShowShare(false)}
        />
      )}
    </div>
  )
}
