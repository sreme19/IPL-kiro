import { useEffect } from 'react'
import { SquadPanel } from './panels/SquadPanel'
import { OpponentPanel } from './panels/OpponentPanel'
import { VenuePanel } from './panels/VenuePanel'
import { ILPPanel } from './panels/ILPPanel'
import { MonteCarloPanel } from './panels/MonteCarloPanel'
import { CommentaryPanel } from './panels/CommentaryPanel'
import { trackPageView } from './analytics/events'
import './App.css'

function App() {
  useEffect(() => {
    trackPageView('main-dashboard')
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>IPL Captain Simulator</h1>
        <p>Optimize your XI selection with AI-powered analytics</p>
      </header>
      
      <main className="app-main">
        <div className="panel-grid">
          <SquadPanel />
          <OpponentPanel />
          <VenuePanel />
          <ILPPanel />
          <MonteCarloPanel />
          <CommentaryPanel />
        </div>
      </main>
    </div>
  )
}

export default App
