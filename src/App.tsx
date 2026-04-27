import { useEffect, useState } from 'react'
import { SquadPanel } from './panels/SquadPanel'
import { OpponentPanel } from './panels/OpponentPanel'
import { VenuePanel } from './panels/VenuePanel'
import { ILPPanel } from './panels/ILPPanel'
import { MonteCarloPanel } from './panels/MonteCarloPanel'
import { CommentaryPanel } from './panels/CommentaryPanel'
import { MatchHistoryPanel } from './panels/MatchHistoryPanel'
import { trackPageView } from './analytics/events'
import { SQUADS, type Squad, type FormationBias, type SimulationResponse, type HistoricalMatch } from './api/client'
import './App.css'

function App() {
  const [selectedSquad, setSelectedSquad] = useState<Squad | null>(null)
  const [selectedOpponent, setSelectedOpponent] = useState<Squad | null>(null)
  const [selectedVenue, setSelectedVenue] = useState<string>('')
  const [formationBias, setFormationBias] = useState<FormationBias>('balanced')
  const [selectedSeason, setSelectedSeason] = useState<number>(2024)
  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null)
  const [simulationId, setSimulationId] = useState<string | null>(null)
  const [replayMatch, setReplayMatch] = useState<HistoricalMatch | null>(null)
  const [mode, setMode] = useState<'upcoming' | 'historical'>('upcoming')

  useEffect(() => {
    trackPageView('main-dashboard')
  }, [])

  const handleReplayMatch = (match: HistoricalMatch) => {
    setReplayMatch(match)
    setSelectedSeason(match.season)
    setSelectedVenue(match.venue)
    // Pre-fill opponent if we have a matching squad
    const opponent = SQUADS.find(s => s.id === match.opponent_squad_id)
    if (opponent) setSelectedOpponent(opponent)
    // Clear any previous result
    setSimulationResult(null)
    setSimulationId(null)
  }

  const handleModeSwitch = (next: 'upcoming' | 'historical') => {
    setMode(next)
    if (next === 'upcoming') {
      setReplayMatch(null)
    }
  }

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
        <div className="mode-toggle">
          <button
            className={`mode-btn ${mode === 'upcoming' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('upcoming')}
          >
            Upcoming Match
          </button>
          <button
            className={`mode-btn ${mode === 'historical' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('historical')}
          >
            Historical Replay
          </button>
        </div>

        <div className="workflow-steps">
          <span className={selectedSquad ? 'step done' : 'step'}>1 Squad</span>
          <span className="arrow">→</span>
          <span className={selectedOpponent ? 'step done' : 'step'}>2 Opponent</span>
          <span className="arrow">→</span>
          <span className={selectedVenue ? 'step done' : 'step'}>3 Venue &amp; Season</span>
          <span className="arrow">→</span>
          <span className={simulationResult ? 'step done' : 'step'}>4 Optimize</span>
          <span className="arrow">→</span>
          <span className={simulationResult ? 'step done' : 'step'}>5 Simulate</span>
        </div>

        <div className="panel-grid">
          <SquadPanel
            selectedSquad={selectedSquad}
            onSquadSelect={squad => { setSelectedSquad(squad); setSimulationResult(null); setReplayMatch(null) }}
          />
          <OpponentPanel
            mySquadId={selectedSquad?.id ?? null}
            selectedOpponent={selectedOpponent}
            onOpponentSelect={setSelectedOpponent}
          />
          <VenuePanel
            selectedVenue={selectedVenue}
            formationBias={formationBias}
            selectedSeason={selectedSeason}
            mode={mode}
            teamName={selectedSquad?.name}
            opponentName={selectedOpponent?.name}
            onVenueSelect={setSelectedVenue}
            onFormationChange={setFormationBias}
            onSeasonChange={setSelectedSeason}
          />

          {mode === 'historical' && (
            <MatchHistoryPanel
              selectedSquad={selectedSquad}
              season={selectedSeason}
              onReplayMatch={handleReplayMatch}
              activeReplayMatchId={replayMatch?.match_id ?? null}
            />
          )}

          <ILPPanel
            squad={selectedSquad}
            opponent={selectedOpponent}
            venue={selectedVenue}
            formationBias={formationBias}
            season={selectedSeason}
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
            teamName={selectedSquad?.name ?? ''}
            opponentName={selectedOpponent?.name ?? ''}
            venue={selectedVenue}
            season={selectedSeason}
          />
        </div>
      </main>
    </div>
  )
}

export default App
