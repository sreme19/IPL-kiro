import { SQUADS, type Squad } from '../api/client'

interface Props {
  mySquadId: string | null
  selectedOpponent: Squad | null
  onOpponentSelect: (squad: Squad) => void
}

const STRENGTH_COLOR: Record<string, string> = {
  csk: '#fbbf24',
  mi: '#3b82f6',
  rcb: '#ef4444',
  kkr: '#8b5cf6',
}

export function OpponentPanel({ mySquadId, selectedOpponent, onOpponentSelect }: Props) {
  const opponents = SQUADS.filter(s => s.id !== mySquadId)

  const handleSelect = (id: string) => {
    const squad = SQUADS.find(s => s.id === id)
    if (squad) onOpponentSelect(squad)
  }

  const avgForm = (squad: Squad) =>
    (squad.players.reduce((s, p) => s + p.form_score, 0) / squad.players.length).toFixed(2)

  return (
    <div className="panel" data-testid="opponent-panel">
      <h2>2. Opponent</h2>
      <div className="panel-content">
        {!mySquadId && <p className="hint">Select your squad first.</p>}
        <select
          value={selectedOpponent?.id ?? ''}
          onChange={e => handleSelect(e.target.value)}
          disabled={!mySquadId}
          data-testid="opponent-select"
        >
          <option value="">— Select opponent —</option>
          {opponents.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        {selectedOpponent && (
          <div className="opponent-card">
            <div className="team-color-bar" style={{ background: STRENGTH_COLOR[selectedOpponent.id] ?? '#6b7280' }} />
            <div className="opp-stats">
              <div className="stat-row"><span>Players</span><strong>{selectedOpponent.players.length}</strong></div>
              <div className="stat-row"><span>Overseas</span><strong>{selectedOpponent.players.filter(p => p.is_overseas).length}</strong></div>
              <div className="stat-row"><span>Avg Form</span><strong>{avgForm(selectedOpponent)}</strong></div>
              <div className="stat-row"><span>Top Batter</span><strong>{selectedOpponent.players.filter(p => p.role === 'batsman').sort((a, b) => b.expected_runs - a.expected_runs)[0]?.name ?? '—'}</strong></div>
              <div className="stat-row"><span>Top Bowler</span><strong>{selectedOpponent.players.filter(p => p.role === 'bowler').sort((a, b) => b.expected_wickets - a.expected_wickets)[0]?.name ?? '—'}</strong></div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
