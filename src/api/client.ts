import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// ─── Types ────────────────────────────────────────────────────────────────────

export type PlayerRole = 'batsman' | 'bowler' | 'all_rounder' | 'wicket_keeper'
export type FormationBias = 'batting' | 'balanced' | 'bowling'

export interface Player {
  player_id: string
  name: string
  role: PlayerRole
  is_overseas: boolean
  expected_runs: number
  expected_wickets: number
  form_score: number
}

export interface Squad {
  id: string
  name: string
  players: Player[]
}

export interface CommentaryStep {
  step_number: number
  title: string
  formula: string
  description: string
  insight: string
  insight_type: string
  graph_data?: Record<string, unknown>
}

export interface WinProbability {
  win_probability: number
  confidence_interval: [number, number]
  calibration_applied: boolean
  sample_size: number
}

export interface SimulationResponse {
  simulation_id: string
  optimization: {
    selected_xi: Player[]
    commentary_steps: CommentaryStep[]
    objective_value: number
    baseline_value: number
    improvement_pct: number
  }
  simulation: {
    match_id: string
    team_xi: Player[]
    opponent_xi: Player[]
    win_probability: WinProbability
    venue_analysis: Record<string, number>
    key_threats: Array<{
      batter: string
      bowler: string
      threat_score: number
      threat_level: string
      runs_per_over: number
      dismissal_rate: number
    }>
  }
  narrative: Record<string, string>
}

export interface XIRecommendationResponse {
  match_id: string
  recommended_xi: Player[]
  commentary_steps: CommentaryStep[]
  objective_value: number
  baseline_value: number
  improvement_pct: number
  venue_analysis: Record<string, number>
  solve_time_ms: number
}

// ─── Static squad data (used when backend is unavailable) ─────────────────────

export const SQUADS: Squad[] = [
  {
    id: 'csk',
    name: 'Chennai Super Kings',
    players: [
      { player_id: 'csk_1', name: 'MS Dhoni', role: 'wicket_keeper', is_overseas: false, expected_runs: 1.4, expected_wickets: 0, form_score: 1.2 },
      { player_id: 'csk_2', name: 'Ruturaj Gaikwad', role: 'batsman', is_overseas: false, expected_runs: 1.6, expected_wickets: 0, form_score: 1.3 },
      { player_id: 'csk_3', name: 'Devon Conway', role: 'batsman', is_overseas: true, expected_runs: 1.5, expected_wickets: 0, form_score: 1.1 },
      { player_id: 'csk_4', name: 'Ajinkya Rahane', role: 'batsman', is_overseas: false, expected_runs: 1.3, expected_wickets: 0, form_score: 1.0 },
      { player_id: 'csk_5', name: 'Shivam Dube', role: 'all_rounder', is_overseas: false, expected_runs: 1.4, expected_wickets: 0.03, form_score: 1.1 },
      { player_id: 'csk_6', name: 'Ravindra Jadeja', role: 'all_rounder', is_overseas: false, expected_runs: 1.2, expected_wickets: 0.05, form_score: 1.2 },
      { player_id: 'csk_7', name: 'Moeen Ali', role: 'all_rounder', is_overseas: true, expected_runs: 1.3, expected_wickets: 0.04, form_score: 1.0 },
      { player_id: 'csk_8', name: 'Deepak Chahar', role: 'bowler', is_overseas: false, expected_runs: 0.5, expected_wickets: 0.07, form_score: 1.1 },
      { player_id: 'csk_9', name: 'Tushar Deshpande', role: 'bowler', is_overseas: false, expected_runs: 0.4, expected_wickets: 0.06, form_score: 1.0 },
      { player_id: 'csk_10', name: 'Matheesha Pathirana', role: 'bowler', is_overseas: true, expected_runs: 0.3, expected_wickets: 0.08, form_score: 1.3 },
      { player_id: 'csk_11', name: 'Maheesh Theekshana', role: 'bowler', is_overseas: true, expected_runs: 0.3, expected_wickets: 0.07, form_score: 1.1 },
      { player_id: 'csk_12', name: 'Rachin Ravindra', role: 'batsman', is_overseas: true, expected_runs: 1.4, expected_wickets: 0.02, form_score: 1.2 },
      { player_id: 'csk_13', name: 'Shardul Thakur', role: 'all_rounder', is_overseas: false, expected_runs: 1.0, expected_wickets: 0.05, form_score: 0.9 },
    ],
  },
  {
    id: 'mi',
    name: 'Mumbai Indians',
    players: [
      { player_id: 'mi_1', name: 'Rohit Sharma', role: 'batsman', is_overseas: false, expected_runs: 1.7, expected_wickets: 0, form_score: 1.2 },
      { player_id: 'mi_2', name: 'Ishan Kishan', role: 'wicket_keeper', is_overseas: false, expected_runs: 1.5, expected_wickets: 0, form_score: 1.1 },
      { player_id: 'mi_3', name: 'Suryakumar Yadav', role: 'batsman', is_overseas: false, expected_runs: 1.9, expected_wickets: 0, form_score: 1.5 },
      { player_id: 'mi_4', name: 'Tilak Varma', role: 'batsman', is_overseas: false, expected_runs: 1.5, expected_wickets: 0, form_score: 1.2 },
      { player_id: 'mi_5', name: 'Tim David', role: 'batsman', is_overseas: true, expected_runs: 1.7, expected_wickets: 0, form_score: 1.3 },
      { player_id: 'mi_6', name: 'Hardik Pandya', role: 'all_rounder', is_overseas: false, expected_runs: 1.4, expected_wickets: 0.05, form_score: 1.1 },
      { player_id: 'mi_7', name: 'Romario Shepherd', role: 'all_rounder', is_overseas: true, expected_runs: 1.2, expected_wickets: 0.04, form_score: 1.0 },
      { player_id: 'mi_8', name: 'Jasprit Bumrah', role: 'bowler', is_overseas: false, expected_runs: 0.4, expected_wickets: 0.10, form_score: 1.5 },
      { player_id: 'mi_9', name: 'Gerald Coetzee', role: 'bowler', is_overseas: true, expected_runs: 0.4, expected_wickets: 0.07, form_score: 1.1 },
      { player_id: 'mi_10', name: 'Piyush Chawla', role: 'bowler', is_overseas: false, expected_runs: 0.3, expected_wickets: 0.06, form_score: 0.9 },
      { player_id: 'mi_11', name: 'Nuwan Thushara', role: 'bowler', is_overseas: true, expected_runs: 0.3, expected_wickets: 0.07, form_score: 1.0 },
      { player_id: 'mi_12', name: 'Naman Dhir', role: 'all_rounder', is_overseas: false, expected_runs: 1.1, expected_wickets: 0.03, form_score: 1.0 },
    ],
  },
  {
    id: 'rcb',
    name: 'Royal Challengers Bangalore',
    players: [
      { player_id: 'rcb_1', name: 'Virat Kohli', role: 'batsman', is_overseas: false, expected_runs: 1.8, expected_wickets: 0, form_score: 1.4 },
      { player_id: 'rcb_2', name: 'Faf du Plessis', role: 'batsman', is_overseas: true, expected_runs: 1.6, expected_wickets: 0, form_score: 1.2 },
      { player_id: 'rcb_3', name: 'Glenn Maxwell', role: 'all_rounder', is_overseas: true, expected_runs: 1.8, expected_wickets: 0.04, form_score: 1.3 },
      { player_id: 'rcb_4', name: 'Rajat Patidar', role: 'batsman', is_overseas: false, expected_runs: 1.5, expected_wickets: 0, form_score: 1.1 },
      { player_id: 'rcb_5', name: 'Dinesh Karthik', role: 'wicket_keeper', is_overseas: false, expected_runs: 1.4, expected_wickets: 0, form_score: 1.0 },
      { player_id: 'rcb_6', name: 'Cameron Green', role: 'all_rounder', is_overseas: true, expected_runs: 1.5, expected_wickets: 0.04, form_score: 1.1 },
      { player_id: 'rcb_7', name: 'Mahipal Lomror', role: 'all_rounder', is_overseas: false, expected_runs: 1.2, expected_wickets: 0.03, form_score: 1.0 },
      { player_id: 'rcb_8', name: 'Mohammed Siraj', role: 'bowler', is_overseas: false, expected_runs: 0.4, expected_wickets: 0.08, form_score: 1.2 },
      { player_id: 'rcb_9', name: 'Josh Hazlewood', role: 'bowler', is_overseas: true, expected_runs: 0.3, expected_wickets: 0.09, form_score: 1.3 },
      { player_id: 'rcb_10', name: 'Yuzvendara Chahal', role: 'bowler', is_overseas: false, expected_runs: 0.3, expected_wickets: 0.07, form_score: 1.1 },
      { player_id: 'rcb_11', name: 'Reece Topley', role: 'bowler', is_overseas: true, expected_runs: 0.3, expected_wickets: 0.07, form_score: 1.0 },
      { player_id: 'rcb_12', name: 'Anuj Rawat', role: 'wicket_keeper', is_overseas: false, expected_runs: 1.2, expected_wickets: 0, form_score: 0.9 },
    ],
  },
  {
    id: 'kkr',
    name: 'Kolkata Knight Riders',
    players: [
      { player_id: 'kkr_1', name: 'Shreyas Iyer', role: 'batsman', is_overseas: false, expected_runs: 1.6, expected_wickets: 0, form_score: 1.2 },
      { player_id: 'kkr_2', name: 'Phil Salt', role: 'wicket_keeper', is_overseas: true, expected_runs: 1.7, expected_wickets: 0, form_score: 1.3 },
      { player_id: 'kkr_3', name: 'Venkatesh Iyer', role: 'all_rounder', is_overseas: false, expected_runs: 1.5, expected_wickets: 0.03, form_score: 1.1 },
      { player_id: 'kkr_4', name: 'Rinku Singh', role: 'batsman', is_overseas: false, expected_runs: 1.5, expected_wickets: 0, form_score: 1.3 },
      { player_id: 'kkr_5', name: 'Andre Russell', role: 'all_rounder', is_overseas: true, expected_runs: 1.8, expected_wickets: 0.06, form_score: 1.4 },
      { player_id: 'kkr_6', name: 'Sunil Narine', role: 'all_rounder', is_overseas: true, expected_runs: 1.4, expected_wickets: 0.06, form_score: 1.3 },
      { player_id: 'kkr_7', name: 'Nitish Rana', role: 'batsman', is_overseas: false, expected_runs: 1.3, expected_wickets: 0, form_score: 1.0 },
      { player_id: 'kkr_8', name: 'Mitchell Starc', role: 'bowler', is_overseas: true, expected_runs: 0.4, expected_wickets: 0.09, form_score: 1.2 },
      { player_id: 'kkr_9', name: 'Varun Chakravarthy', role: 'bowler', is_overseas: false, expected_runs: 0.3, expected_wickets: 0.07, form_score: 1.1 },
      { player_id: 'kkr_10', name: 'Harshit Rana', role: 'bowler', is_overseas: false, expected_runs: 0.4, expected_wickets: 0.07, form_score: 1.0 },
      { player_id: 'kkr_11', name: 'Suyash Sharma', role: 'bowler', is_overseas: false, expected_runs: 0.3, expected_wickets: 0.06, form_score: 0.9 },
      { player_id: 'kkr_12', name: 'Anukul Roy', role: 'all_rounder', is_overseas: false, expected_runs: 1.0, expected_wickets: 0.04, form_score: 0.9 },
    ],
  },
]

export const VENUES = [
  { name: 'M. A. Chidambaram Stadium', city: 'Chennai', type: 'spin_friendly' },
  { name: 'Wankhede Stadium', city: 'Mumbai', type: 'batting_friendly' },
  { name: 'Eden Gardens', city: 'Kolkata', type: 'balanced' },
  { name: 'M. Chinnaswamy Stadium', city: 'Bangalore', type: 'batting_friendly' },
  { name: 'Narendra Modi Stadium', city: 'Ahmedabad', type: 'balanced' },
  { name: 'Punjab Cricket Association Stadium', city: 'Mohali', type: 'batting_friendly' },
  { name: 'Rajiv Gandhi International Stadium', city: 'Hyderabad', type: 'batting_friendly' },
  { name: 'Sawai Mansingh Stadium', city: 'Jaipur', type: 'spin_friendly' },
]
