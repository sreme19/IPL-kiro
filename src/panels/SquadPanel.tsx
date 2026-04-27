import { SQUADS, type Squad } from '../api/client'
import { trackSimulationStarted } from '../analytics/events'

interface Props {
  selectedSquad: Squad | null
  onSquadSelect: (squad: Squad) => void
}

const ROLE_ICON: Record<string, string> = {
  batsman: '🏏',
  bowler: '🎳',
  all_rounder: '⚡',
  wicket_keeper: '🧤',
}

export function SquadPanel({ selectedSquad, onSquadSelect }: Props) {
  const handleSelect = (id: string) => {
    const squad = SQUADS.find(s => s.id === id)
    if (squad) {
      onSquadSelect(squad)
      trackSimulationStarted(squad.id, 'tbd')
    }
  }

  return (
    <div className="panel" data-testid="squad-panel">
      <h2>1. Squad Selection</h2>
      <div className="panel-content">
        <select
          value={selectedSquad?.id ?? ''}
          onChange={e => handleSelect(e.target.value)}
          data-testid="squad-select"
        >
          <option value="">— Select your team —</option>
          {SQUADS.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        {selectedSquad && (
          <div className="squad-list" data-testid="squad-info">
            <p className="squad-meta">{selectedSquad.players.length} players · {selectedSquad.players.filter(p => p.is_overseas).length} overseas</p>
            <div className="player-table">
              {selectedSquad.players.map(p => (
                <div key={p.player_id} className="player-row">
                  <span className="role-icon">{ROLE_ICON[p.role]}</span>
                  <span className="player-name">{p.name}</span>
                  {p.is_overseas && <span className="badge overseas">OS</span>}
                  <span className="form-badge" style={{ color: p.form_score >= 1.2 ? '#16a34a' : p.form_score >= 1.0 ? '#d97706' : '#dc2626' }}>
                    ★ {p.form_score.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
