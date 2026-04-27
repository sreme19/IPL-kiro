import { useEffect, useState } from 'react'
import {
  VENUES,
  IPL_SEASONS,
  fetchHistoricalMatches,
  type FormationBias,
  type AppMode,
} from '../api/client'

interface Props {
  mode: AppMode
  squadId: string | null
  opponentId: string | null
  selectedVenue: string
  formationBias: FormationBias
  season: number
  onVenueSelect: (venue: string) => void
  onFormationChange: (bias: FormationBias) => void
  onSeasonChange: (season: number) => void
}

const TYPE_LABEL: Record<string, string> = {
  batting_friendly: '🏏 Batting-friendly',
  spin_friendly: '🎵 Spin-friendly',
  balanced: '⚖️ Balanced',
}

export function VenuePanel({
  mode,
  squadId,
  opponentId,
  selectedVenue,
  formationBias,
  season,
  onVenueSelect,
  onFormationChange,
  onSeasonChange,
}: Props) {
  const venue = VENUES.find(v => v.name === selectedVenue)
  const isHistorical = mode === 'historical'

  const [historicalVenues, setHistoricalVenues] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    if (!isHistorical) {
      setHistoricalVenues([])
      setLoadError(false)
      return
    }
    if (!squadId || !opponentId) {
      setHistoricalVenues([])
      setLoadError(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setLoadError(false)
    fetchHistoricalMatches(squadId, opponentId, season)
      .then(data => {
        if (cancelled) return
        setHistoricalVenues(data.venues)
        if (selectedVenue && !data.venues.includes(selectedVenue)) {
          onVenueSelect('')
        }
      })
      .catch(() => {
        if (cancelled) return
        setHistoricalVenues([])
        setLoadError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [isHistorical, squadId, opponentId, season, selectedVenue, onVenueSelect])

  const venueOptions = isHistorical
    ? VENUES.filter(v => historicalVenues.includes(v.name))
    : VENUES

  const showEmptyVenueState =
    isHistorical && !loading && !loadError && squadId && opponentId && historicalVenues.length === 0

  return (
    <div className="panel" data-testid="venue-panel">
      <h2>{isHistorical ? '3. Venue & Season' : '3. Venue & Formation'}</h2>
      <div className="panel-content">
        {isHistorical && (
          <>
            <label className="field-label">Season (Historical)</label>
            <select
              value={season}
              onChange={e => onSeasonChange(Number(e.target.value))}
              data-testid="season-select"
            >
              {IPL_SEASONS.map(s => (
                <option key={s} value={s}>IPL {s}</option>
              ))}
            </select>
          </>
        )}

        <label className="field-label" style={{ marginTop: isHistorical ? '0.75rem' : 0 }}>
          Match Venue
        </label>
        <select
          value={selectedVenue}
          onChange={e => onVenueSelect(e.target.value)}
          disabled={isHistorical && (!squadId || !opponentId)}
          data-testid="venue-select"
        >
          <option value="">— Select venue —</option>
          {venueOptions.map(v => (
            <option key={v.name} value={v.name}>{v.name}, {v.city}</option>
          ))}
        </select>

        {isHistorical && loading && (
          <p className="hint" data-testid="venue-loading">Loading historical venues…</p>
        )}
        {isHistorical && loadError && (
          <p className="hint warning" data-testid="venue-load-error">
            Could not load historical venues
          </p>
        )}
        {showEmptyVenueState && (
          <p className="hint" data-testid="venue-empty">
            No matches found for this combination
          </p>
        )}

        {venue && (
          <div className="venue-info">
            <span className="venue-type-badge">{TYPE_LABEL[venue.type]}</span>
          </div>
        )}

        <label className="field-label" style={{ marginTop: '1rem' }}>Formation Bias</label>
        <div className="formation-pills">
          {(['batting', 'balanced', 'bowling'] as FormationBias[]).map(b => (
            <button
              key={b}
              className={`pill ${formationBias === b ? 'active' : ''}`}
              onClick={() => onFormationChange(b)}
            >
              {b === 'batting' ? '🏏 Batting' : b === 'bowling' ? '🎳 Bowling' : '⚖️ Balanced'}
            </button>
          ))}
        </div>

        <div className="formation-weights">
          <span>α (batting) = {formationBias === 'batting' ? '0.65' : formationBias === 'bowling' ? '0.35' : '0.55'}</span>
          <span>β (bowling) = {formationBias === 'batting' ? '0.35' : formationBias === 'bowling' ? '0.65' : '0.45'}</span>
        </div>
      </div>
    </div>
  )
}
