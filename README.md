# 🏏 IPL Captain Simulator

An AI-powered IPL cricket team selection and match simulation platform. Combines **Integer Linear Programming (ILP)** for optimal XI selection with **Monte Carlo simulation** for win probability estimation — deployed serverlessly on AWS.

## 🌐 Live Demo

| Service | URL |
|---|---|
| **Frontend** | https://ipl-captain-simulator.netlify.app |
| **Backend API** | https://cwex9kiq9d.execute-api.us-west-2.amazonaws.com/staging/ |
| **Health check** | https://cwex9kiq9d.execute-api.us-west-2.amazonaws.com/staging/health |

---

## 🧠 How It Works

1. **Select** your IPL squad, opponent, venue, and formation bias
2. **ILP Optimizer** (PuLP CBC solver) picks the mathematically optimal XI by maximising expected runs + wickets while penalising opponent threat edges and confidence interval width
3. **Monte Carlo Engine** runs 10,000 vectorised T20 innings to compute win probability with a 95% confidence interval
4. **AI Commentary** explains each decision step — venue encoding → bipartite threat graph → ILP solution → MC result

---

## 🏗️ Technology Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| **React** | 18 | UI component framework |
| **TypeScript** | 5 | Type-safe JavaScript |
| **Vite** | 5 | Build tool and dev server |
| **Axios** | 1.x | HTTP client for API calls |
| **PostHog** | JS SDK | Product analytics (page views, events) |
| **Vitest** | 1.x | Unit testing framework |
| **Netlify** | — | Static hosting + global CDN |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.9 | Runtime |
| **FastAPI** | ≥0.104 | REST API framework with automatic OpenAPI docs |
| **Mangum** | ≥0.17 | ASGI adapter to run FastAPI on AWS Lambda |
| **Pydantic** | v2 | Request/response schema validation |
| **PuLP** | ≥2.7 | Integer Linear Programming (CBC solver) |
| **NumPy** | ≥1.24 | Vectorised Monte Carlo simulation (10k rollouts) |
| **NetworkX** | ≥3.2 | Max-flow DAG for tournament path computation |
| **Boto3** | ≥1.34 | AWS SDK — DynamoDB + S3 access |

### Infrastructure (AWS)
| Service | Resource | Purpose |
|---|---|---|
| **AWS Lambda** | `ipl-kiro-api-staging` | Serverless compute for FastAPI (512 MB, 30s timeout) |
| **API Gateway** | REST API | HTTPS endpoint + CORS for frontend |
| **DynamoDB** | `ipl-kiro-sessions-staging` | Per-user session state, form vectors, calibration log (7-day TTL) |
| **S3** | `ipl-kiro-data-staging-*` | Player tensor JSON, reference data |
| **CloudFormation** | `ipl-kiro-staging` | Infrastructure as Code via AWS SAM |
| **IAM** | Auto-generated role | Least-privilege Lambda execution role |

### DevOps & Tooling
| Tool | Purpose |
|---|---|
| **AWS SAM CLI** | Build, package, and deploy Lambda + infrastructure |
| **Netlify CLI** | Frontend deployment and CDN invalidation |
| **GitHub** | Source control (`sreme19/IPL-kiro`) |
| **GitHub Actions** | CI/CD pipeline (`.github/workflows/deploy.yml`) |

---

## 📁 Project Structure

```
kiro-packet/
├── api/                        # FastAPI backend (Python 3.9)
│   ├── main.py                 # App entrypoint + Mangum Lambda handler
│   ├── middleware/
│   │   └── error_reporter.py   # Auto-create Linear tickets on 5xx errors
│   ├── models/
│   │   ├── schemas.py          # Pydantic v2 request/response models
│   │   ├── ilp_solver.py       # PuLP CBC ILP optimizer — XI selection
│   │   ├── monte_carlo.py      # NumPy vectorised T20 MDP simulator
│   │   ├── session_store.py    # DynamoDB session state (TTL, EWM form)
│   │   ├── scout_agent.py      # S3 JSON tensor loader + form adjustment
│   │   ├── conditions_agent.py # Venue encoding + formation weights
│   │   ├── opponent_agent.py   # NetworkX bipartite threat graph
│   │   ├── narrative_agent.py  # Claude AI commentary (optional)
│   │   ├── tournament_graph.py # Max-flow DAG for tournament paths
│   │   └── commentary.py       # 4-step CommentaryStep generator
│   ├── routers/
│   │   ├── simulation.py       # POST /api/simulation/start
│   │   ├── match.py            # POST /api/match/recommend-xi, /simulate
│   │   ├── tournament.py       # GET  /api/tournament/path, /analysis
│   │   └── stats.py            # GET  /api/stats/community, /system
│   └── tests/
│       ├── test_ilp_constraints.py
│       ├── test_monte_carlo.py
│       └── test_commentary_schema.py
├── src/                        # React 18 + TypeScript frontend
│   ├── App.tsx                 # Root — shared state wired to all panels
│   ├── api/
│   │   └── client.ts           # Axios client + all TypeScript types + squad data
│   ├── panels/
│   │   ├── SquadPanel.tsx      # Step 1 — team/squad selector with player list
│   │   ├── OpponentPanel.tsx   # Step 2 — opponent selector with stats card
│   │   ├── VenuePanel.tsx      # Step 3 — venue + formation bias (α/β weights)
│   │   ├── ILPPanel.tsx        # Step 4 — ILP trigger, selected XI display
│   │   ├── MonteCarloPanel.tsx # Step 5 — win probability circle + CI bars
│   │   └── CommentaryPanel.tsx # Step 6 — tabbed 4-step AI commentary
│   └── analytics/
│       ├── posthog.ts          # PostHog init
│       └── events.ts           # Typed event helpers (6 tracked events)
├── scripts/
│   ├── build_data_pipeline.py  # ETL: Cricsheet JSON → player tensors
│   ├── build_reference_data.py # Reference data builder (venues, squads)
│   ├── check_gate.py           # CI quality gate
│   └── validate_ipl_data.py    # Raw data validation
├── data/                       # gitignored — loaded from S3 in production
│   ├── ipl_json_raw/           # Cricsheet ball-by-ball JSON
│   └── reference/
│       ├── team_name_map.json
│       ├── overseas_flags.json
│       ├── squad_pools.json
│       └── venue_geometry.json
├── lambda_package/             # gitignored — SAM build artifact
├── .github/workflows/
│   └── deploy.yml              # GitHub Actions CI/CD
├── template.yaml               # AWS SAM infrastructure (Lambda + API GW + DynamoDB + S3)
├── samconfig.toml              # SAM deploy config (staging + production)
├── netlify.toml                # Netlify build config + env vars
├── requirements.txt            # Python dependencies (no pandas/pyarrow for Lambda)
├── package.json                # Node.js dependencies
└── vite.config.ts              # Vite config with API proxy
```

---

## ⚙️ Core Algorithm Details

### ILP Optimizer (`api/models/ilp_solver.py`)

**Objective:**
```
max Σ ( α·E[runs_i] + β·E[wickets_i] - γ·CI_penalty_i - δ·threat_i ) · x_i
```

**Constraints:**
- `Σ x_i = 11` — exactly 11 players
- `Σ x_i (role=WK) ≥ 1` — at least 1 wicket-keeper
- `Σ x_i (role=bowler or all_rounder) ≥ 4` — bowling cover
- `Σ x_i (overseas=true) ≤ 4` — ICC overseas cap
- `x_i ∈ {0,1}` — binary selection

**Formation weights:**
| Bias | α (batting) | β (bowling) |
|---|---|---|
| `batting` | 0.65 | 0.35 |
| `balanced` | 0.55 | 0.45 |
| `bowling` | 0.35 | 0.65 |

**Solver:** PuLP CBC (open-source MILP), 5-second time limit

---

### Monte Carlo Simulator (`api/models/monte_carlo.py`)

- **10,000 vectorised T20 rollouts** per simulation using NumPy
- Each ball modelled as Poisson (runs) + Bernoulli (wicket)
- **95% confidence interval** via normal approximation: `p ± 1.96·√(p(1-p)/N)`
- **Platt scaling** calibration applied after ≥3 historical results
- In-memory LRU cache keyed on input hash to avoid re-computation

---

### Session Store (`api/models/session_store.py`)

- **DynamoDB** table with `session_id` (hash key) and 7-day TTL
- Per-session state: form vector, squad fatigue, calibration log
- **EWM form update:** `form_new = 0.4 · form_current + 0.6 · match_result`
- **Fatigue decay:** 10% per match played

---

### Tournament Graph (`api/models/tournament_graph.py`)

- Directed Acyclic Graph (DAG) modelling IPL playoff structure
- **Max-flow** algorithm (NetworkX) finds highest-probability qualification path
- Nodes: group matches → Qualifier 1 → Eliminator → Qualifier 2 → Final

---

## 🚀 Deployment

### AWS Backend (SAM)

```bash
# Prerequisites: AWS CLI configured, SAM CLI installed
pip install aws-sam-cli

# Build Lambda package
sam build

# Deploy to staging
sam deploy --config-env staging

# Deploy to production
sam deploy --config-env production
```

Outputs after deploy:
- `ApiUrl` — API Gateway HTTPS endpoint
- `SessionsTable` — DynamoDB table name
- `DataBucket` — S3 bucket name

### Frontend (Netlify)

```bash
# Prerequisites: Netlify CLI
npm install -g netlify-cli

# Build and deploy
npm run build
netlify deploy --prod --dir dist
```

Or set `VITE_API_URL` in `netlify.toml` and push — Netlify auto-builds on every commit.

---

## 🛠️ Local Development

### Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run FastAPI locally
cd api
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
# Install Node dependencies
npm install

# Start dev server (proxies /api to localhost:8000 by default)
npm run dev

# To proxy to the live AWS backend instead:
echo "VITE_API_URL=https://cwex9kiq9d.execute-api.us-west-2.amazonaws.com/staging" > .env.local
npm run dev
```

### Tests

```bash
# Frontend unit tests
npm test

# Backend tests
cd api
python -m pytest tests/ -v
```

---

## 📡 API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/simulation/start` | Start session → optimal XI + win probability |
| `GET` | `/api/simulation/{id}/status` | Poll session status |
| `POST` | `/api/simulation/{id}/confirm-xi` | Confirm or override AI XI |
| `POST` | `/api/match/recommend-xi` | Get recommended XI for a match |
| `POST` | `/api/match/simulate` | Run Monte Carlo match simulation |
| `POST` | `/api/match/result` | Record actual result for Platt calibration |
| `GET` | `/api/tournament/path?team=CSK` | Max-flow tournament qualification path |
| `GET` | `/api/tournament/analysis` | Full 10-team tournament analysis |
| `GET` | `/api/stats/community` | Community-wide usage statistics |
| `GET` | `/api/stats/system` | System health + Lambda metrics |

Interactive API docs (when running locally): http://localhost:8000/docs

---

## 🔐 Environment Variables

### Backend (Lambda / local)
| Variable | Description |
|---|---|
| `DYNAMODB_TABLE` | DynamoDB sessions table name (set by SAM) |
| `S3_BUCKET` | S3 data bucket name (set by SAM) |
| `ENVIRONMENT` | `staging` or `production` |
| `LOG_LEVEL` | Logging level (default: `INFO`) |
| `ANTHROPIC_API_KEY` | Claude API key for AI narrative (optional) |
| `POSTHOG_KEY` | PostHog server-side key (optional) |
| `LINEAR_API_KEY` | Linear API key for error ticket creation (optional) |

### Frontend (Vite build)
| Variable | Description |
|---|---|
| `VITE_API_URL` | Full AWS API Gateway base URL (leave empty to use local proxy) |

---

## 📝 Development Notes

- `lambda_package/` is a SAM build artifact — gitignored, regenerated by `sam build`
- `node_modules/` is gitignored — run `npm install` after cloning
- `data/` is gitignored — tensors are loaded from S3 in production; use fallback values locally
- `pandas` and `pyarrow` are intentionally excluded from `requirements.txt` — Lambda uses S3 JSON tensors instead of Parquet
- `anthropic` (Claude SDK) is an optional dependency — narrative falls back to static text if not installed or API key not set
- Platt calibration activates automatically after 3+ match results are recorded via `POST /api/match/result`
- The ILP Step 4 (Monte Carlo) commentary is seeded at 0.5 win probability on first run; updated after full simulation completes
