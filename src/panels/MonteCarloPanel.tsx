import { useState } from 'react'
import { trackMatchCompleted } from '../analytics/events'

export function MonteCarloPanel() {
  const [status, setStatus] = useState<'idle' | 'running' | 'complete'>('idle')
  const [winProb, setWinProb] = useState<number>(0)
  
  const runSimulation = () => {
    setStatus('running')
    setTimeout(() => {
      const prob = Math.random() * 0.4 + 0.3
      setWinProb(prob)
      setStatus('complete')
      trackMatchCompleted('win', prob)
    }, 800)
  }

  return (
    <div className="panel" data-testid="monte-carlo-panel">
      <h2>Monte Carlo Simulation</h2>
      <div className="panel-content">
        <button onClick={runSimulation} disabled={status === 'running'} data-testid="simulate-button">
          {status === 'running' ? 'Simulating...' : 'Run Simulation'}
        </button>
        {status === 'complete' && (
          <p data-testid="simulation-results">Win Probability: {(winProb * 100).toFixed(1)}%</p>
        )}
      </div>
    </div>
  )
}
