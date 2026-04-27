import { useEffect, useState } from 'react'
import { SquadPanel } from './panels/SquadPanel'
import { OpponentPanel } from './panels/OpponentPanel'
import { VenuePanel } from './panels/VenuePanel'
import { ILPPanel } from './panels/ILPPanel'
import { MonteCarloPanel } from './panels/MonteCarloPanel'
import { CommentaryPanel } from './panels/CommentaryPanel'
import { trackPageView } from './analytics/events'
import { type Squad, type FormationBias, type SimulationResponse } from './api/client'
import './App.css'

function App() {
  const [selectedSquad, setSelectedSquad] = useState<Squad | null>(null)
  const [selectedOpponent, setSelectedOpponent] = useState<Squad | null>(null)
  const [selectedVenue, setSelectedVenue] = useState<string>('')
  const [formationBias, setFormationBias] = useState<FormationBias>('balanced')
  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null)
  const [simulationId, setSimulationId] = useState<string | null>(null)

  useEffect(() => {
    trackPageView('main-dashboard')
  }, [])

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
        <div className="workflow-steps">
          <span className={selectedSquad ? 'step done' : 'step'}>1 Squad</span>
          <span className="arrow">→</span>
          <span className={selectedOpponent ? 'step done' : 'step'}>2 Opponent</span>
          <span className="arrow">→</span>
          <span className={selectedVenue ? 'step done' : 'step'}>3 Venue</span>
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
            selectedVenue={selectedVenue}
            formationBias={formationBias}
            onVenueSelect={setSelectedVenue}
            onFormationChange={setFormationBias}
          />
          <ILPPanel
            squad={selectedSquad}
            opponent={selectedOpponent}
            venue={selectedVenue}
            formationBias={formationBias}
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
