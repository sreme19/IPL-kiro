import { captureEvent } from './posthog'

// 6 required PostHog events for analytics

export function trackPageView(page: string) {
  captureEvent('page_view', { page })
}

export function trackSimulationStarted(squadId: string, opponentId: string) {
  captureEvent('simulation_started', { squad_id: squadId, opponent_id: opponentId })
}

export function trackXIConfirmed(playerIds: string[]) {
  captureEvent('xi_confirmed', { player_count: playerIds.length, players: playerIds })
}

export function trackMatchCompleted(result: string, winProbability: number) {
  captureEvent('match_completed', { result, win_probability: winProbability })
}

export function trackTournamentCompleted(position: number, totalPoints: number) {
  captureEvent('tournament_completed', { position, total_points: totalPoints })
}

export function trackResultShared(platform: string) {
  captureEvent('result_shared', { platform })
}

export function trackDonationClicked(amount: number) {
  captureEvent('donation_clicked', { amount })
}
