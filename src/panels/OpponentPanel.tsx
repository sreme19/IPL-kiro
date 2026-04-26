import { useState } from 'react'

export function OpponentPanel() {
  const [selectedOpponent, setSelectedOpponent] = useState<string>('')
  
  const opponents = [
    { id: 'csk', name: 'Chennai Super Kings', strength: 'high' },
    { id: 'mi', name: 'Mumbai Indians', strength: 'high' },
    { id: 'rcb', name: 'Royal Challengers Bangalore', strength: 'medium' },
    { id: 'kkr', name: 'Kolkata Knight Riders', strength: 'medium' }
  ]

  return (
    <div className="panel" data-testid="opponent-panel">
      <h2>Opponent Selection</h2>
      <div className="panel-content">
        <select 
          value={selectedOpponent} 
          onChange={(e) => setSelectedOpponent(e.target.value)}
          data-testid="opponent-select"
        >
          <option value="">Select opponent</option>
          {opponents.map(opp => (
            <option key={opp.id} value={opp.id}>
              {opp.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
