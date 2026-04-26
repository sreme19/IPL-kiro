// PostHog analytics - disabled for test environment
// import posthog from 'posthog-js'

// const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || 'test-key'
// const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://app.posthog.com'

export function initPostHog() {
  // Initialize PostHog analytics
  console.log('PostHog initialized (test mode)')
}

export function captureEvent(event: string, properties?: Record<string, unknown>) {
  // Capture analytics event
  console.log(`Event captured: ${event}`, properties)
}
