import { useEffect, useState } from 'react'
import { SquadPanel } from './panels/SquadPanel'
import { OpponentPanel } from './panels/OpponentPanel'
import { VenuePanel } from './panels/VenuePanel'
import { ILPPanel } from './panels/ILPPanel'
import { MonteCarloPanel } from './panels/MonteCarloPanel'
import { CommentaryPanel } from './panels/CommentaryPanel'
import { HistoryPanel } from './panels/HistoryPanel'
import { trackPageView } from './analytics/events'
import {
  type Squad,
  type FormationBias,
  type SimulationResponse,
  type AppMode,
  IPL_SEASONS,
} from './api/client'
import './App.css'

function App() {
  const [mode, setMode] = useState<AppMode>('upcoming')
  const [selectedSquad, setSelectedSquad] = useState<Squad | null>(null)
  const [selectedOpponent, setSelectedOpponent] = useState<Squad | null>(null)
  const [selectedVenue, setSelectedVenue] = useState<string>('')
  const [season, setSeason] = useState<number>(IPL_SEASONS[1]) // default 2023
  const [formationBias, setFormationBias] = useState<FormationBias>('balanced')
  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null)
  const [simulationId, setSimulationId] = useState<string | null>(null)

  useEffect(() => {
    trackPageView('main-dashboard')
  }, [])

  const switchMode = (next: AppMode) => {
    if (next === mode) return
    setMode(next)
    setSelectedVenue('')
    setSimulationResult(null)
    setSimulationId(null)
  }

  const isHistorical = mode === 'historical'
  const venueLabel = isHistorical ? '3 Venue & Season' : '3 Venue'

  return (
    <div className="app">
      <header className="app-header">
        <h1>🏏 IPL Captain Simulator</h1>
        <p>Optimize your XI selection with AI-powered ILP + Monte Carlo analytics</p>
        {simulationId && (
          <div className="session-badge">Session: {simulationId.slice(0, 8)}…</div>
        )}
      </header>

      <main className="app-main">
        <div className="mode-toggle" data-testid="mode-toggle">
          <button
            className={`mode-btn ${mode === 'upcoming' ? 'active' : ''}`}
            onClick={() => switchMode('upcoming')}
            data-testid="mode-upcoming"
          >
            Upcoming Match
          </button>
          <button
            className={`mode-btn ${mode === 'historical' ? 'active' : ''}`}
            onClick={() => switchMode('historical')}
            data-testid="mode-historical"
          >
            Historical Replay
          </button>
        </div>

        <div className="workflow-steps">
          <span className={selectedSquad ? 'step done' : 'step'}>1 Squad</span>
          <span className="arrow">→</span>
          <span className={selectedOpponent ? 'step done' : 'step'}>2 Opponent</span>
          <span className="arrow">→</span>
          <span className={selectedVenue ? 'step done' : 'step'}>{venueLabel}</span>
          <span className="arrow">→</span>
          <span className={simulationResult ? 'step done' : 'step'}>4 Optimize</span>
          <span className="arrow">→</span>
          <span className={simulationResult ? 'step done' : 'step'}>5 Simulate</span>
        </div>

        <div className="panel-grid">
          <SquadPanel
            selectedSquad={selectedSquad}
            onSquadSelect={setSelectedSquad}
          />
          <OpponentPanel
            mySquadId={selectedSquad?.id ?? null}
            selectedOpponent={selectedOpponent}
            onOpponentSelect={setSelectedOpponent}
          />
          <VenuePanel
            mode={mode}
            squadId={selectedSquad?.id ?? null}
            opponentId={selectedOpponent?.id ?? null}
            selectedVenue={selectedVenue}
            formationBias={formationBias}
            season={season}
            onVenueSelect={setSelectedVenue}
            onFormationChange={setFormationBias}
            onSeasonChange={setSeason}
          />
          {isHistorical && (
            <HistoryPanel
              squadId={selectedSquad?.id ?? null}
              opponentId={selectedOpponent?.id ?? null}
              season={season}
              selectedVenue={selectedVenue}
              onVenueSelect={setSelectedVenue}
            />
          )}
          <ILPPanel
            squad={selectedSquad}
            opponent={selectedOpponent}
            venue={selectedVenue}
            formationBias={formationBias}
            season={season}
            simulationResult={simulationResult}
            onSimulationComplete={(result, id) => {
              setSimulationResult(result)
              setSimulationId(id)
            }}
          />
          <MonteCarloPanel
            simulationResult={simulationResult}
            venue={selectedVenue}
          />
          <CommentaryPanel
            simulationResult={simulationResult}
          />
        </div>
      </main>
    </div>
  )
}

export default App
