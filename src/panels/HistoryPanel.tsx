import { useEffect, useState } from 'react'
import { fetchHistoricalMatches, type HistoricalMatch } from '../api/client'

interface Props {
  squadId: string | null
  opponentId: string | null
  season: number
  selectedVenue: string
  onVenueSelect: (venue: string) => void
}

export function HistoryPanel({
  squadId,
  opponentId,
  season,
  selectedVenue,
  onVenueSelect,
}: Props) {
  const [matches, setMatches] = useState<HistoricalMatch[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!squadId || !opponentId) {
      setMatches([])
      setError(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(false)
    fetchHistoricalMatches(squadId, opponentId, season)
      .then(data => {
        if (!cancelled) setMatches(data.matches)
      })
      .catch(() => {
        if (!cancelled) {
          setMatches([])
          setError(true)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [squadId, opponentId, season])

  return (
    <div className="panel" data-testid="history-panel">
      <h2>Historical Replay</h2>
      <div className="panel-content">
        {!squadId || !opponentId ? (
          <p className="hint">Select both teams to load match history.</p>
        ) : loading ? (
          <p className="hint">Loading match history…</p>
        ) : error ? (
          <p className="hint warning" data-testid="history-error">
            ⚠️ Could not load match history
          </p>
        ) : matches.length === 0 ? (
          <p className="hint" data-testid="history-empty">
            No matches found for this combination
          </p>
        ) : (
          <div className="history-list">
            {matches.map(m => {
              const isSelected = selectedVenue === m.venue
              return (
                <button
                  key={m.match_id}
                  className={`history-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => onVenueSelect(m.venue)}
                  data-testid={`history-card-${m.leg}`}
                >
                  <div className="history-row">
                    <span className="history-date">{m.date}</span>
                    <span className={`history-leg leg-${m.leg}`}>{m.leg.toUpperCase()}</span>
                  </div>
                  <div className="history-venue">{m.venue}, {m.city}</div>
                  <div className="history-score">
                    {m.host.toUpperCase()} {m.team1_score} vs {m.guest.toUpperCase()} {m.team2_score}
                  </div>
                  <div className="history-result">
                    🏆 {m.winner.toUpperCase()} won by {m.margin}
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
