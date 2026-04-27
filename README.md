# IPL Captain Simulator

An AI-powered IPL cricket team selection and match simulation platform. Combines Integer Linear Programming (ILP) for optimal XI selection with Monte Carlo simulation for win probability estimation.

---

## Architecture

```
kiro-packet/
├── api/                        # FastAPI backend (Python)
│   ├── main.py                 # App entrypoint + Mangum Lambda wrapper
│   ├── middleware/
│   │   └── error_reporter.py  # Auto-create Linear bug tickets on 5xx
│   ├── models/
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── ilp_solver.py       # PuLP ILP optimizer for XI selection
│   │   ├── monte_carlo.py      # 10k-rollout MDP win probability simulator
│   │   ├── session_store.py    # DynamoDB session state with TTL
│   │   ├── scout_agent.py      # Player tensor data loader (S3)
│   │   ├── conditions_agent.py # Venue encoding and formation weights
│   │   ├── opponent_agent.py   # Bipartite threat graph builder
│   │   ├── narrative_agent.py  # AI commentary narrative generator
│   │   ├── tournament_graph.py # Max-flow DAG for tournament paths
│   │   └── commentary.py       # CommentaryStep generator (4 steps)
│   ├── routers/
│   │   ├── simulation.py       # POST /api/simulation/start
│   │   ├── match.py            # POST /api/match/recommend-xi, /simulate
│   │   ├── tournament.py       # GET /api/tournament/path, /analysis
│   │   └── stats.py            # GET /api/stats/community, /system
│   └── tests/
│       ├── test_ilp_constraints.py
│       ├── test_monte_carlo.py
│       └── test_commentary_schema.py
├── src/                        # React + TypeScript frontend
│   ├── App.tsx                 # Root component with 6-panel layout
│   ├── panels/
│   │   ├── SquadPanel.tsx      # Team/squad selector
│   │   ├── OpponentPanel.tsx   # Opponent selector
│   │   ├── VenuePanel.tsx      # Venue selector
│   │   ├── ILPPanel.tsx        # ILP optimization trigger + results
│   │   ├── MonteCarloPanel.tsx # Win probability simulator
│   │   └── CommentaryPanel.tsx # AI commentary steps viewer
│   └── analytics/
│       ├── posthog.ts          # PostHog analytics client
│       └── events.ts           # Typed analytics event helpers
├── scripts/
│   ├── build_data_pipeline.py  # ETL pipeline for IPL ball-by-ball data
│   ├── build_reference_data.py # Reference data builder (venues, squads)
│   ├── check_gate.py           # CI quality gate checks
│   └── validate_ipl_data.py    # Data validation scripts
├── data/
│   ├── ipl_json_raw/           # Cricsheet JSON match data
│   └── reference/
│       ├── team_name_map.json
│       ├── overseas_flags.json
│       ├── squad_pools.json
│       └── venue_geometry.json
├── template.yaml               # AWS SAM infrastructure definition
├── samconfig.toml              # SAM deployment configuration
├── requirements.txt            # Python dependencies
├── package.json                # Node.js dependencies
└── vite.config.ts              # Vite frontend build config
```

---

## Infrastructure (AWS SAM)

| Resource | Description |
|---|---|
| `FastAPIFunction` | Lambda running FastAPI via Mangum |
| `ApiGatewayApi` | API Gateway with CORS enabled |
| `SessionsTable` | DynamoDB sessions table (7-day TTL) |
| `DataBucket` | S3 bucket for player tensor data |

### Deploy

```bash
# Build and deploy to staging
sam build
sam deploy --config-env staging

# Deploy to production
sam deploy --config-env production
```

---

## Backend

### Requirements

- Python 3.9+
- `pip install -r requirements.txt`

### Run locally

```bash
cd api
uvicorn main:app --reload --port 8000
```

### Key API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/simulation/start` | Start simulation session, returns optimal XI + win probability |
| `GET` | `/api/simulation/{id}/status` | Get session status |
| `POST` | `/api/simulation/{id}/confirm-xi` | Confirm or override AI XI |
| `POST` | `/api/match/recommend-xi` | Get AI-recommended XI for a match |
| `POST` | `/api/match/simulate` | Run Monte Carlo simulation |
| `POST` | `/api/match/result` | Record actual result for Platt calibration |
| `GET` | `/api/tournament/path?team=CSK` | Tournament max-flow path |
| `GET` | `/api/tournament/analysis` | Full tournament analysis |
| `GET` | `/api/stats/community` | Community-wide usage stats |
| `GET` | `/api/stats/system` | System health metrics |
| `GET` | `/health` | Health check |

### Core Models

**ILP Solver** (`api/models/ilp_solver.py`)
- Formulation: `max Σ(α·E[runs] + β·E[wkts] - γ·CI_penalty - δ·threat) · x_i`
- Constraints: exactly 11 players, ≥1 WK, ≥4 bowlers (incl. all-rounders), ≤4 overseas
- Formation biases: `batting (α=0.65, β=0.35)`, `balanced (α=0.55, β=0.45)`, `bowling (α=0.35, β=0.65)`
- Solver: PuLP CBC with 5-second time limit

**Monte Carlo Simulator** (`api/models/monte_carlo.py`)
- 10,000 vectorized T20 rollouts using NumPy
- 95% confidence interval via normal approximation
- Platt scaling calibration after ≥3 historical matches
- In-memory LRU cache keyed on input hash

**Session Store** (`api/models/session_store.py`)
- DynamoDB-backed per-user session: form vector, fatigue, calibration log
- EWM form update: `form = 0.4 * current + 0.6 * new`
- 10% fatigue decay per match played
- 7-day TTL with DynamoDB native expiry

---

## Frontend

### Requirements

- Node.js 18+
- `npm install`

### Run locally

```bash
npm run dev
```

### Build for production

```bash
npm run build
```

### Test

```bash
npm test
```

### Panel overview

| Panel | Description |
|---|---|
| `SquadPanel` | Select your IPL team/squad |
| `OpponentPanel` | Select opponent team |
| `VenuePanel` | Select match venue (affects formation weights) |
| `ILPPanel` | Trigger ILP optimization, view selected XI |
| `MonteCarloPanel` | Run win probability simulation |
| `CommentaryPanel` | View AI commentary steps (venue → threat → ILP → MC) |

---

## Data Pipeline

```bash
# Validate raw IPL JSON data
python scripts/validate_ipl_data.py

# Build reference data (venues, squad pools)
python scripts/build_reference_data.py

# Run full ETL pipeline
python scripts/build_data_pipeline.py

# Run CI quality gate
python scripts/check_gate.py
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `DYNAMODB_TABLE` | DynamoDB sessions table name |
| `S3_BUCKET` | S3 data bucket name |
| `POSTHOG_KEY` | PostHog analytics API key |
| `LINEAR_API_KEY` | Linear API key for error reporting (optional) |
| `ENVIRONMENT` | `staging` or `production` |
| `LOG_LEVEL` | Logging level (default: `INFO`) |

---

## Development Notes

- `lambda_package/` is a build artifact — do not commit it; it is regenerated by `sam build`
- `node_modules/` is gitignored — run `npm install` after cloning
- `data/` is gitignored — player tensors and match data are loaded from S3 in production
- The ILP commentary Step 4 (Monte Carlo) is initially seeded at 0.5 win probability and updated by the Monte Carlo agent after simulation
- Platt calibration activates after 3+ historical match results are recorded
