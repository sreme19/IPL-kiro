import { useState } from 'react'
import { trackSimulationStarted } from '../analytics/events'

export function SquadPanel() {
  const [selectedSquad, setSelectedSquad] = useState<string>('')
  
  const squads = [
    { id: 'csk', name: 'Chennai Super Kings', players: 16 },
    { id: 'mi', name: 'Mumbai Indians', players: 16 },
    { id: 'rcb', name: 'Royal Challengers Bangalore', players: 16 },
    { id: 'kkr', name: 'Kolkata Knight Riders', players: 16 }
  ]
  
  const handleSquadSelect = (squadId: string) => {
    setSelectedSquad(squadId)
    trackSimulationStarted(squadId, squadId)
  }

  return (
    <div className="panel" data-testid="squad-panel">
      <h2>Squad Selection</h2>
      <div className="panel-content">
        <select 
          value={selectedSquad} 
          onChange={(e) => handleSquadSelect(e.target.value)}
          data-testid="squad-select"
        >
          <option value="">Select your squad</option>
          {squads.map(squad => (
            <option key={squad.id} value={squad.id}>
              {squad.name} ({squad.players} players)
            </option>
          ))}
        </select>
        
        {selectedSquad && (
          <div className="selection-info" data-testid="squad-info">
            Selected: {squads.find(s => s.id === selectedSquad)?.name}
          </div>
        )}
      </div>
    </div>
  )
}
