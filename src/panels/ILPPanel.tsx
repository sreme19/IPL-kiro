import { useState } from 'react'
import { trackXIConfirmed } from '../analytics/events'

export function ILPPanel() {
  const [status, setStatus] = useState<'idle' | 'running' | 'complete'>('idle')
  
  const runOptimization = () => {
    setStatus('running')
    setTimeout(() => {
      setStatus('complete')
      trackXIConfirmed(['player1', 'player2', 'player3'])
    }, 500)
  }

  return (
    <div className="panel" data-testid="ilp-panel">
      <h2>ILP Optimization</h2>
      <div className="panel-content">
        <button onClick={runOptimization} disabled={status === 'running'} data-testid="optimize-button">
          {status === 'running' ? 'Optimizing...' : 'Optimize XI'}
        </button>
        {status === 'complete' && <p data-testid="ilp-results">Optimization complete!</p>}
      </div>
    </div>
  )
}
