import { useEffect, useState } from 'react'
import { VENUES, IPL_SEASONS, type FormationBias, type HistoricalMatch, api } from '../api/client'

// Teams that only joined IPL after a certain season
const TEAM_DEBUT: Record<string, number> = {
  'Gujarat Titans': 2022,
  'Lucknow Super Giants': 2022,
  'Rising Pune Supergiant': 2016,
  'Gujarat Lions': 2016,
  'Pune Warriors': 2011,
  'Kochi Tuskers Kerala': 2011,
}

const CURRENT_YEAR = new Date().getFullYear()
// Upcoming mode: current season + 1 future season
const UPCOMING_SEASONS = IPL_SEASONS.filter(y => y >= CURRENT_YEAR - 1)

interface Props {
  selectedVenue: string
  formationBias: FormationBias
  selectedSeason: number
  mode: 'upcoming' | 'historical'
  teamName?: string
  opponentName?: string
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
  selectedVenue, formationBias, selectedSeason, mode,
  teamName, opponentName,
  onVenueSelect, onFormationChange, onSeasonChange,
}: Props) {
  const venue = VENUES.find(v => v.name === selectedVenue)
  const [fixtures, setFixtures] = useState<HistoricalMatch[]>([])
  const [loadingFixtures, setLoadingFixtures] = useState(false)
  const [selectedFixtureId, setSelectedFixtureId] = useState<string>('')

  // Compute available seasons based on mode + selected teams
  const availableSeasons = (() => {
    if (mode === 'upcoming') return UPCOMING_SEASONS

    // Historical: all seasons where both selected teams existed
    const teamDebut = teamName ? (TEAM_DEBUT[teamName] ?? 2008) : 2008
    const oppDebut = opponentName ? (TEAM_DEBUT[opponentName] ?? 2008) : 2008
    const earliest = Math.max(teamDebut, oppDebut)
    return [...IPL_SEASONS].filter(y => y <= CURRENT_YEAR && y >= earliest).reverse()
  })()

  // Clamp selected season into the available list whenever it changes
  useEffect(() => {
    if (!availableSeasons.includes(selectedSeason)) {
      onSeasonChange(availableSeasons[0])
    }
  }, [mode, teamName, opponentName]) // eslint-disable-line react-hooks/exhaustive-deps

  // In historical mode with both teams set, fetch actual match fixtures
  const showFixturePicker = mode === 'historical' && !!teamName && !!opponentName

  useEffect(() => {
    if (!showFixturePicker) {
      setFixtures([])
      setSelectedFixtureId('')
      return
    }

    let cancelled = false
    setLoadingFixtures(true)
    api
      .get('/matches/list', {
        params: { team: teamName, opponent: opponentName, season: selectedSeason, limit: 50 },
      })
      .then(res => {
        if (cancelled) return
        const list: HistoricalMatch[] = res.data.matches ?? []
        setFixtures(list)
        if (list.length > 0) {
          setSelectedFixtureId(list[0].match_id)
          onVenueSelect(list[0].venue)
        } else {
          setSelectedFixtureId('')
          onVenueSelect('')
        }
      })
      .catch(() => {
        if (!cancelled) setFixtures([])
      })
      .finally(() => {
        if (!cancelled) setLoadingFixtures(false)
      })

    return () => { cancelled = true }
  }, [showFixturePicker, teamName, opponentName, selectedSeason]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleFixtureChange = (matchId: string) => {
    setSelectedFixtureId(matchId)
    const match = fixtures.find(f => f.match_id === matchId)
    if (match) onVenueSelect(match.venue)
  }

  const seasonLabel = mode === 'upcoming' ? 'Season (upcoming)' : 'Season (historical)'

  return (
    <div className="panel" data-testid="venue-panel">
      <h2>3. Venue & Formation</h2>
      <div className="panel-content">
        <label className="field-label">{seasonLabel}</label>
        <select
          value={selectedSeason}
          onChange={e => onSeasonChange(Number(e.target.value))}
          data-testid="season-select"
        >
          {availableSeasons.map(y => (
            <option key={y} value={y}>IPL {y}</option>
          ))}
        </select>

        <label className="field-label" style={{ marginTop: '1rem' }}>Match Venue</label>

        {showFixturePicker ? (
          loadingFixtures ? (
            <div className="fixture-loading">Loading matches…</div>
          ) : fixtures.length > 0 ? (
            <select
              value={selectedFixtureId}
              onChange={e => handleFixtureChange(e.target.value)}
              data-testid="fixture-select"
            >
              {fixtures.map(f => (
                <option key={f.match_id} value={f.match_id}>
                  {f.date} — {f.venue} ({f.result === 'won' ? '✓ Won' : '✗ Lost'})
                </option>
              ))}
            </select>
          ) : (
            <div className="fixture-empty">No matches found for this combination</div>
          )
        ) : (
          <select
            value={selectedVenue}
            onChange={e => onVenueSelect(e.target.value)}
            data-testid="venue-select"
          >
            <option value="">— Select venue —</option>
            {VENUES.map(v => (
              <option key={v.name} value={v.name}>{v.name}, {v.city}</option>
            ))}
          </select>
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
