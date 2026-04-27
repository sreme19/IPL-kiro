import { type SimulationResponse } from '../api/client'

interface Props {
  simulationResult: SimulationResponse | null
  venue: string
}

function ProbBar({ value, label }: { value: number; label: string }) {
  const pct = Math.round(value * 100)
  const color = pct >= 60 ? '#16a34a' : pct >= 45 ? '#d97706' : '#dc2626'
  return (
    <div className="prob-bar-wrap">
      <div className="prob-bar-label">{label}</div>
      <div className="prob-bar-track">
        <div className="prob-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="prob-bar-value" style={{ color }}>{pct}%</div>
    </div>
  )
}

export function MonteCarloPanel({ simulationResult, venue }: Props) {
  const wp = simulationResult?.simulation.win_probability
  const venueAnalysis = simulationResult?.simulation.venue_analysis
  const threats = simulationResult?.simulation.key_threats ?? []

  return (
    <div className="panel" data-testid="monte-carlo-panel">
      <h2>5. Monte Carlo Simulation</h2>
      <div className="panel-content">
        {!simulationResult && <p className="hint">Run ILP optimization first.</p>}

        {wp && (
          <div data-testid="simulation-results">
            <div className="win-prob-circle" style={{ borderColor: wp.win_probability >= 0.5 ? '#16a34a' : '#dc2626' }}>
              <div className="win-prob-number">{(wp.win_probability * 100).toFixed(1)}%</div>
              <div className="win-prob-label">Win Probability</div>
            </div>

            <div className="ci-info">
              95% CI: [{(wp.confidence_interval[0] * 100).toFixed(1)}%, {(wp.confidence_interval[1] * 100).toFixed(1)}%]
              {wp.calibration_applied && <span className="badge calibrated">Calibrated</span>}
            </div>

            <div className="prob-bars">
              <ProbBar value={wp.win_probability} label="Win" />
              <ProbBar value={1 - wp.win_probability} label="Loss" />
            </div>

            <p className="sample-size">{wp.sample_size.toLocaleString()} rollouts · {venue || 'venue TBD'}</p>

            {venueAnalysis && (
              <div className="venue-weights">
                <span>Bat weight: {venueAnalysis.batting_weight?.toFixed(2) ?? '—'}</span>
                <span>Bowl weight: {venueAnalysis.bowling_weight?.toFixed(2) ?? '—'}</span>
              </div>
            )}

            {threats.length > 0 && (
              <div className="threats">
                <p className="threats-header">🔥 Key Threats</p>
                {threats.slice(0, 3).map((t, i) => (
                  <div key={i} className={`threat-row threat-${t.threat_level}`}>
                    <span>{t.batter} vs {t.bowler}</span>
                    <span className="threat-score">{(t.threat_score * 100).toFixed(0)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
