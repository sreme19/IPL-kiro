# IPL Captain Simulator — Kiro Steering File
# Place at: .kiro/steering.md
# Kiro reads this before EVERY agent task. These rules are non-negotiable.

---

## CRITICAL: Staged gate system
This project has FIVE stages. Kiro must NOT proceed to a later stage until
the gate condition for the current stage is explicitly confirmed PASSED.

Stage gates are checked by running: python scripts/check_gate.py --stage N

| Stage | Name                  | Gate condition                                      |
|-------|-----------------------|-----------------------------------------------------|
| 0     | Data validation       | ipl_validation_summary.json → all_checks_pass: true |
| 1     | Data pipeline         | data/tensors/ contains Parquet files for all seasons|
| 2     | Backend core          | pytest api/tests/ → 0 failures                      |
| 3     | Frontend              | npm test → 0 failures, npm run type-check → clean   |
| 4     | Infrastructure        | sam validate → valid, CI green on main branch       |

If a gate is not passed, STOP. Report which check failed and what to fix.
Do not generate code for the next stage. Ask the user to resolve the gate first.

---

## Stack (non-negotiable)

Frontend:    React 18 + TypeScript + Tailwind CSS (utility-only) + Recharts + React DnD + html2canvas
Backend:     Python 3.11 + FastAPI + Mangum + PuLP + NumPy + SciPy + NetworkX + boto3 + Anthropic SDK
Data:        Cricsheet JSON → DuckDB (offline) → Parquet on S3 (runtime reads)
Infra:       AWS Lambda + API Gateway HTTP + S3 + DynamoDB + SQS + CloudWatch
Frontend CD: Vercel (auto-deploy from GitHub main)
Analytics:   PostHog JS (client-side)
Donations:   Ko-fi (0% fee, href only)
Issues:      Linear (Python SDK + MCP)

---

## Architecture rules

- NEVER run ONNX inference at request time. Read pre-computed S3 Parquet tensors only.
- Cache Monte Carlo results in Lambda memory: LRU(500) keyed on (xi_hash, venue_id, opponent_xi_hash).
- Cache Narrative Agent response keyed on match_id. One Claude call per match maximum.
- Lambda package ≤ 250 MB. Use Layers for: numpy+scipy, pulp, onnxruntime (if needed later).
- Lambda timeout 15 s. Monte Carlo must complete in ≤ 3 s. ILP solve ≤ 500 ms.
- No managed database at runtime. DynamoDB for session store + counters only. S3 for tensors.
- No authentication. Public anonymous tool.
- All Anthropic API calls go through FastAPI backend. Never call from frontend directly.
- All secrets in .env.local (frontend) and AWS SSM Parameter Store (backend). Never hardcode.

---

## Agent commentary system

Every ILP solve MUST produce a CommentaryStep[4] array returned alongside the XI:

  Step 1 — venue_encoding:   venue_vec values + implications for α/β weights
  Step 2 — bipartite_threat: graph_data for inline SVG + highest-threat matchup identified
  Step 3 — ilp_solution:     players in/out with reasons + objective_value vs baseline
  Step 4 — monte_carlo:      P(win), 95% CI, calibration note if Platt scaling active

CommentaryStep schema:
  { step_number, title, formula, description, insight, insight_type, graph_data? }

---

## Stateful agent memory tiers

  In-context:  SimulationContext Pydantic object (one Lambda invocation)
  Session:     DynamoDB key=simulation_id, TTL=7d
               Fields: form_vec{player_id→ewm}, calibration_log[(pred,actual)], squad_fatigue
  Episodic:    S3 JSON logs batched nightly (override_signals, xi_outcomes, tensor_bias_samples)
  Feedback:    Platt scaling activated after match 3 in session (fit on calibration_log)

---

## Eval harness (run nightly via GitHub Actions)

  eval_1_constraints:   pytest — every ILP hard constraint asserted. Blocker if fails.
  eval_2_ilp_lift:      ILP XI vs random XI on held-out 2015 season. Target ≥ 5pp lift.
  eval_3_brier:         brier_score_loss on 2014–2015 matches. Target ≤ 0.18.
  eval_4_narrative:     LLM-as-judge, 50 samples/week. Target mean score ≥ 4.0 / 5.
  eval_5_overrides:     Override alignment rate. Alert if >20% of overrides improve on ILP.

---

## Data reference files (in data/reference/)

  team_name_map.json      — franchise rename normalisation (e.g. "Delhi Daredevils" → "Delhi Capitals")
  venue_geometry.json     — 12 IPL venues with sq/straight boundary distances for Conditions Agent
  overseas_flags.json     — player_id → {overseas: bool, seasons: [int]} (sourced from Kaggle auction CSV)
  squad_pools.json        — team → season → [player_ids] for 25-man squad pool

These files must exist and be validated by Stage 0 before Stage 1 begins.

---

## Naming conventions

  React components:     PascalCase in src/components/
  API route handlers:   snake_case functions in api/routers/
  Pydantic models:      api/models/*.py
  TypeScript types:     generated from OpenAPI schema via `npm run generate-types`
  Test files:           api/tests/test_*.py and src/__tests__/*.test.tsx

---

## Testing rules

  Every ILP constraint has a pytest unit test asserting it is enforced.
  Monte Carlo output validated: P(win) ∈ [0,1], CI lower < CI upper.
  Frontend: React Testing Library for components, Playwright for E2E.
  Kiro hook: run `pytest api/tests/ -q` on every save to api/**/*.py
  Kiro hook: run `npm run type-check` on every save to src/**/*.tsx

---

## Cost guardrails

  DynamoDB counter `claude_spend_cents` incremented on every Narrative Agent call.
  If spend exceeds $20 (2000 cents) in current calendar month:
    → Return cached narrative response
    → Log CloudWatch metric: NarrativeBudgetExceeded
    → Continue simulation (never block user for cost reasons)
  Lambda p95 latency alarm: > 8s → SNS email
  Error rate alarm: > 2% → SNS email

---

## Linear issue tracking

  After every stage gate passes, create Linear tickets for the next stage via Python SDK.
  Epic per stage. Child issues per feature spec prompt task.
  Bug tickets auto-created by FastAPI exception middleware (5xx only).
  n8n workflow: CloudWatch alarm → SNS → n8n → Linear bug ticket.

---

## Do not

  - Add any database other than DynamoDB (counters + session) and S3 Parquet (tensors)
  - Use CSS-in-JS. Tailwind utility classes only.
  - Use any charting library other than Recharts.
  - Use unicode bullet characters (• ‣) — use LevelFormat.BULLET in docx, CSS list-style in HTML
  - Proceed to next stage without gate confirmation
  - Call Anthropic API from the frontend
  - Hardcode any secret, API key, or environment-specific URL
