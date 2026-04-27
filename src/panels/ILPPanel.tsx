import { useState } from 'react'
import { api, type Squad, type FormationBias, type SimulationResponse } from '../api/client'
import { trackXIConfirmed } from '../analytics/events'

interface Props {
  squad: Squad | null
  opponent: Squad | null
  venue: string
  formationBias: FormationBias
  simulationResult: SimulationResponse | null
  onSimulationComplete: (result: SimulationResponse, id: string) => void
}

const ROLE_ICON: Record<string, string> = {
  batsman: '🏏',
  bowler: '🎳',
  all_rounder: '⚡',
  wicket_keeper: '🧤',
}

export function ILPPanel({ squad, opponent, venue, formationBias, simulationResult, onSimulationComplete }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canRun = !!(squad && opponent && venue)

  const runOptimization = async () => {
    if (!squad || !opponent || !venue) return
    setLoading(true)
    setError(null)

    try {
      const payload = {
        team: {
          team_id: squad.id,
          name: squad.name,
          squad: squad.players,
        },
        match_context: {
          match_id: `${squad.id}_vs_${opponent.id}_${Date.now()}`,
          venue,
          opponent_team: opponent.name,
          season: 2024,
          is_home: false,
        },
        formation_bias: formationBias,
        must_include: [],
        must_exclude: [],
      }

      const res = await api.post<SimulationResponse>('/simulation/start', payload)
      onSimulationComplete(res.data, res.data.simulation_id)
      trackXIConfirmed(res.data.optimization.selected_xi.map(p => p.player_id))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'API unavailable — running offline demo'
      setError(msg)
      // Offline demo mode: build a deterministic XI from squad
      const sorted = [...squad.players]
        .sort((a, b) => (b.expected_runs + b.expected_wickets) - (a.expected_runs + a.expected_wickets))
      const xi = sorted.slice(0, 11)
      const fakeResult: SimulationResponse = {
        simulation_id: `demo-${Date.now()}`,
        optimization: {
          selected_xi: xi,
          commentary_steps: [],
          objective_value: xi.reduce((s, p) => s + p.expected_runs, 0),
          baseline_value: xi.reduce((s, p) => s + p.expected_runs * 0.9, 0),
          improvement_pct: 10,
        },
        simulation: {
          match_id: 'demo',
          team_xi: xi,
          opponent_xi: opponent.players.slice(0, 11),
          win_probability: { win_probability: 0.62, confidence_interval: [0.55, 0.69], calibration_applied: false, sample_size: 10000 },
          venue_analysis: { batting_weight: 1.0, bowling_weight: 1.0 },
          key_threats: [],
        },
        narrative: { summary: 'Offline demo mode — ILP solver not available.' },
      }
      onSimulationComplete(fakeResult, fakeResult.simulation_id)
      trackXIConfirmed(xi.map(p => p.player_id))
    } finally {
      setLoading(false)
    }
  }

  const xi = simulationResult?.optimization.selected_xi

  return (
    <div className="panel" data-testid="ilp-panel">
      <h2>4. ILP Optimization</h2>
      <div className="panel-content">
        {!canRun && <p className="hint">Complete steps 1–3 to unlock optimization.</p>}

        <button
          onClick={runOptimization}
          disabled={!canRun || loading}
          className="primary-btn"
          data-testid="optimize-button"
        >
          {loading ? '⏳ Optimizing...' : '🚀 Run ILP Optimization'}
        </button>

        {error && <p className="error-msg">⚠️ {error} (demo mode active)</p>}

        {simulationResult && (
          <div className="ilp-results" data-testid="ilp-results">
            <div className="improvement-badge">
              +{simulationResult.optimization.improvement_pct.toFixed(1)}% vs baseline
            </div>
            <p className="xi-header">Selected XI:</p>
            <div className="xi-list">
              {xi?.map((p, i) => (
                <div key={p.player_id} className="xi-player">
                  <span className="xi-num">{i + 1}</span>
                  <span className="role-icon">{ROLE_ICON[p.role]}</span>
                  <span className="player-name">{p.name}</span>
                  {p.is_overseas && <span className="badge overseas">OS</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
