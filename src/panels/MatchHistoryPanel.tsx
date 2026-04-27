import { useState, useEffect } from 'react'
import { api, type Squad, type HistoricalMatch } from '../api/client'

interface Props {
  selectedSquad: Squad | null
  season: number
  onReplayMatch: (match: HistoricalMatch) => void
  activeReplayMatchId: string | null
}

export function MatchHistoryPanel({ selectedSquad, season, onReplayMatch, activeReplayMatchId }: Props) {
  const [matches, setMatches] = useState<HistoricalMatch[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedSquad) {
      setMatches([])
      return
    }
    setLoading(true)
    setError(null)

    api
      .get<{ matches: HistoricalMatch[]; error?: string }>(
        `/matches/list?team=${encodeURIComponent(selectedSquad.name)}&season=${season}&limit=15`
      )
      .then(res => {
        if (res.data.error) setError(res.data.error)
        setMatches(res.data.matches)
      })
      .catch(() => setError('Could not load match history'))
      .finally(() => setLoading(false))
  }, [selectedSquad, season])

  return (
    <div className="panel" data-testid="match-history-panel">
      <h2>Historical Replay</h2>
      <div className="panel-content">
        {!selectedSquad && (
          <p className="hint">Select a squad (step 1) to browse past matches.</p>
        )}

        {selectedSquad && loading && <p className="hint">Loading matches…</p>}

        {error && <p className="error-msg">⚠️ {error}</p>}

        {!loading && !error && matches.length === 0 && selectedSquad && (
          <p className="hint">No matches found for {selectedSquad.name} in {season}.</p>
        )}

        {matches.length > 0 && (
          <div className="match-history-list">
            <p className="field-label">
              {selectedSquad?.name} — {season} season ({matches.length} matches)
            </p>
            {matches.map(m => (
              <div
                key={m.match_id}
                className={`match-row ${activeReplayMatchId === m.match_id ? 'active' : ''}`}
                onClick={() => onReplayMatch(m)}
                title="Click to load this match for optimization"
              >
                <div className="match-row-left">
                  <span className={`result-dot ${m.result}`} />
                  <div>
                    <span className="match-opponent">vs {m.opponent}</span>
                    <span className="match-meta">{m.date} · {m.city}</span>
                  </div>
                </div>
                <span className={`match-result-badge ${m.result}`}>
                  {m.result === 'won' ? 'W' : 'L'}
                </span>
              </div>
            ))}
          </div>
        )}

        {activeReplayMatchId && (
          <div className="replay-notice">
            Replay mode active — opponent, venue & season pre-filled from selected match.
            Run optimization (step 4) to see the optimal XI.
          </div>
        )}
      </div>
    </div>
  )
}
