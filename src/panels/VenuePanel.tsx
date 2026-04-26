import { useState } from 'react'

export function VenuePanel() {
  const [selectedVenue, setSelectedVenue] = useState<string>('')
  
  const venues = [
    { name: 'M. A. Chidambaram Stadium', city: 'Chennai', type: 'batting_friendly' },
    { name: 'Wankhede Stadium', city: 'Mumbai', type: 'balanced' },
    { name: 'Eden Gardens', city: 'Kolkata', type: 'spin_friendly' }
  ]

  return (
    <div className="panel" data-testid="venue-panel">
      <h2>Venue Selection</h2>
      <div className="panel-content">
        <select 
          value={selectedVenue} 
          onChange={(e) => setSelectedVenue(e.target.value)}
          data-testid="venue-select"
        >
          <option value="">Select venue</option>
          {venues.map(venue => (
            <option key={venue.name} value={venue.name}>
              {venue.city}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
