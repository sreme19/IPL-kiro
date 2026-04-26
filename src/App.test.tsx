import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders the main dashboard', () => {
    render(<App />)
    expect(screen.getByText('IPL Captain Simulator')).toBeDefined()
  })

  it('renders all 6 panels', () => {
    render(<App />)
    expect(screen.getByTestId('squad-panel')).toBeDefined()
    expect(screen.getByTestId('opponent-panel')).toBeDefined()
    expect(screen.getByTestId('venue-panel')).toBeDefined()
    expect(screen.getByTestId('ilp-panel')).toBeDefined()
    expect(screen.getByTestId('monte-carlo-panel')).toBeDefined()
    expect(screen.getByTestId('commentary-panel')).toBeDefined()
  })
})
