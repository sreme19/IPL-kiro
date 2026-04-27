import { VENUES, type FormationBias } from '../api/client'

interface Props {
  selectedVenue: string
  formationBias: FormationBias
  onVenueSelect: (venue: string) => void
  onFormationChange: (bias: FormationBias) => void
}

const TYPE_LABEL: Record<string, string> = {
  batting_friendly: '🏏 Batting-friendly',
  spin_friendly: '🎵 Spin-friendly',
  balanced: '⚖️ Balanced',
}

export function VenuePanel({ selectedVenue, formationBias, onVenueSelect, onFormationChange }: Props) {
  const venue = VENUES.find(v => v.name === selectedVenue)

  return (
    <div className="panel" data-testid="venue-panel">
      <h2>3. Venue & Formation</h2>
      <div className="panel-content">
        <label className="field-label">Match Venue</label>
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
