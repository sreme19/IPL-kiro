# IPL Captain Simulator — Kiro Spec Prompts
# ==========================================
# INSTRUCTIONS FOR KIRO:
#
# 1. Read .kiro/steering.md first (always).
# 2. Before starting any spec, run: python scripts/check_gate.py --stage N
#    where N is the stage you are about to implement.
# 3. If the gate fails, STOP and report what needs fixing.
# 4. Only proceed when the gate passes.
# 5. After completing a spec, run the gate check again to confirm.
#
# Stage order: 0 (data) → 1 (pipeline) → 2 (backend) → 3 (frontend) → 4 (infra)
# ==========================================


# ════════════════════════════════════════════════════════════════
# STAGE 0 — DATA VALIDATION
# Gate: python scripts/check_gate.py --stage 0
# ════════════════════════════════════════════════════════════════

STAGE_0_SPEC = """
Validate that all required data is available before building anything.

Run these commands in order and confirm each passes before proceeding:

STEP 1 — Install dependencies
  pip install requests duckdb pandas pyarrow

STEP 2 — Download and validate Cricsheet IPL data
  python scripts/validate_ipl_data.py

  This script:
  - Downloads ipl_male_json.zip from cricsheet.org/downloads/
  - Parses all match JSON files
  - Checks season coverage for 2008–2016 (≥14 matches each)
  - Checks field completeness (batter, bowler, venue, runs ≥99%)
  - Checks (batter, bowler, venue) tensor density
  - Writes data/ipl_validation_summary.json

  If any check fails, read the failure message and resolve before continuing.

STEP 3 — Build reference data files
  python scripts/build_reference_data.py --all

  This creates:
  - data/reference/team_name_map.json    (franchise rename mappings)
  - data/reference/venue_geometry.json  (12 IPL venues with boundary dimensions)
  - data/reference/overseas_flags.json  (known overseas players 2008–2016)
  - data/reference/squad_pools.json     (25-man squad template)

  ACTION REQUIRED for full overseas + squad coverage:
  1. Download from Kaggle: https://www.kaggle.com/datasets/nowke9/ipldata
     Files needed: Players.csv (has team, season, player_name, nationality)
  2. Re-run:
     python scripts/build_reference_data.py --overseas-flags --squad-pools --kaggle-csv Players.csv

STEP 4 — Confirm gate passes
  python scripts/check_gate.py --stage 0

  Expected output: "GATE 0 PASSED — safe to proceed to Stage 1"

DO NOT write any application code until Gate 0 passes.
"""


# ════════════════════════════════════════════════════════════════
# STAGE 1 — DATA PIPELINE
# Gate: python scripts/check_gate.py --stage 1
# Requires: Gate 0 passed
# ════════════════════════════════════════════════════════════════

STAGE_1_SPEC = """
Build the offline data pipeline that transforms raw Cricsheet JSON into
pre-computed Parquet tensor files on S3.

PREREQUISITE: Gate 0 must pass before starting this stage.
Run: python scripts/check_gate.py --stage 0

--- What to build ---

File: scripts/build_data_pipeline.py

The script must:

1. PARSE
   Load all JSON files from data/ipl_json_raw/.
   Apply team_name_map.json normalisation to all team name fields.
   Load into DuckDB at data/ipl.duckdb with these tables:
     - matches(match_id, season, date, venue, team_1, team_2, winner, toss_winner, toss_decision)
     - deliveries(match_id, season, venue, batting_team, bowling_team, innings, over,
                  batter, bowler, runs_batter, runs_extras, is_wicket, wicket_kind)
     - players(player_id, name, cricsheet_name)
     - squads(team, season, player_id, is_overseas)

   squads table is populated from:
     - Cricsheet playing XI (playing_xi field in match JSON)
     - data/reference/overseas_flags.json for the is_overseas column
     - data/reference/squad_pools.json for the 25-man pool per season

2. COMPUTE TENSORS
   For each (batter, bowler, venue) triplet with sample_size >= 30 balls:
     - avg_runs_per_ball
     - dismissal_rate_per_ball
     - economy_rate (for bowlers)
     - boundary_rate
     - sample_size
   
   For sparse triplets (< 30 balls): use career average as fallback.
   Tag these rows with is_fallback=True.
   
   Also compute a form_ewm table:
     - Per player, per match: exponentially weighted mean runs/wkts
       over last 5 matches (alpha=0.4)
     - Used by Scout Agent for in-session form adjustment

3. EXPORT
   Export tensors as Parquet partitioned by season:
   data/tensors/season={year}/tensors.parquet
   
   Also export form_ewm:
   data/tensors/form/form_ewm.parquet

4. UPLOAD (when --upload flag set)
   Upload all Parquet files to S3 bucket from DATA_BUCKET env var.
   Create data/tensors/manifest.json pointing to active version.
   
   manifest.json format:
   { "version": "YYYYMMDD-HHMMSS", "bucket": "...", "prefix": "tensors/", "seasons": [2008..2016] }

CLI interface:
  python scripts/build_data_pipeline.py --seasons 2008 2009 2010 2011 2012 2013 2014 2015 2016
  python scripts/build_data_pipeline.py --seasons 2008 ... --dry-run   (no S3 upload)
  python scripts/build_data_pipeline.py --seasons 2008 ... --upload    (includes S3 upload)

--- Tests ---

Write pytest unit tests in scripts/tests/:
  test_pipeline_schema.py    — DuckDB table schemas match expected
  test_tensor_computation.py — tensor values are in valid ranges, no nulls in required fields
  test_team_normalisation.py — all team names normalise correctly via the map
  test_fallback_flagging.py  — sparse triplets correctly flagged is_fallback=True

--- Gate confirmation ---

After building:
  python scripts/check_gate.py --stage 1

Expected: "GATE 1 PASSED — safe to proceed to Stage 2"
"""


# ════════════════════════════════════════════════════════════════
# STAGE 2 — BACKEND CORE
# Gate: python scripts/check_gate.py --stage 2
# Requires: Gate 1 passed
# ════════════════════════════════════════════════════════════════

STAGE_2_SPEC = """
Build the FastAPI backend with all five computational models,
the six-agent system, stateful session memory, and full test coverage.

PREREQUISITE: Gate 1 must pass before starting this stage.
Run: python scripts/check_gate.py --stage 1

--- Directory structure ---

api/
  main.py                     FastAPI app + Mangum Lambda wrapper
  routers/
    simulation.py             POST /api/simulation/start
    match.py                  POST /api/match/recommend-xi, POST /api/match/simulate
    tournament.py             GET /api/tournament/path
    stats.py                  GET /api/stats/community
  models/
    schemas.py                All Pydantic request/response models
    commentary.py             CommentaryStep schema + generator
    scout_agent.py            S3 Parquet tensor reads + form adjustment
    conditions_agent.py       venue_vec computation from venue_geometry.json
    opponent_agent.py         bipartite matchup graph construction
    ilp_solver.py             PuLP ILP + CommentaryStep[4] generation
    monte_carlo.py            MDP state space + 10k rollout simulator
    narrative_agent.py        Claude claude-sonnet-4-6 + structured output
    tournament_graph.py       NetworkX DAG + max-flow path
    session_store.py          DynamoDB read/write for session state
    calibration.py            Platt scaling fit + correction
  middleware/
    error_reporter.py         Auto-create Linear bug tickets on 5xx
  tests/
    test_ilp_constraints.py
    test_monte_carlo.py
    test_commentary_schema.py
    test_session_store.py
    test_routes.py

--- Key implementation requirements ---

ILP solver (ilp_solver.py):
  Objective: max Σ(α·E[runs_i] + β·E[wkts_i] - γ·CI_width_i - δ·threat_i) · x_i
  α and β set by venue_vec from Conditions Agent (sum to 1.0)
  Hard constraints: Σx=11, WK≥1, bowlers≥4, overseas≤4, x_i∈{0,1}
  User locks: must_include → x_i=1, must_exclude → x_i=0
  Formation bias: 'batting' → α=0.65, 'balanced' → α=0.55, 'bowling' → α=0.45
  Must produce CommentaryStep[4] after every solve.
  Target: < 500ms solve time.

Monte Carlo (monte_carlo.py):
  State: (runs, wickets, overs_remaining)
  Transition: sample runs_batter from Poisson(tensor_value), dismissal from Bernoulli
  Run 10,000 rollouts. Use numpy vectorisation — no Python loops over deliveries.
  Apply Platt scaling correction if calibration_log has ≥ 3 entries (from session store).
  Target: < 3s for 10,000 rollouts.

Narrative Agent (narrative_agent.py):
  Model: claude-sonnet-4-6
  Input: CommentaryStep[4] as structured JSON
  Output schema (tool_use): { briefing_text: str, key_risk: str, key_advantage: str }
  max_tokens: 200
  Cache response in memory keyed on match_id.
  Cost guard: check DynamoDB claude_spend_cents before calling. Skip if over budget.

Session store (session_store.py):
  DynamoDB table: ipl-simulator-sessions
  Key: simulation_id (String)
  Fields: form_vec, calibration_log, squad_fatigue, matches_played, created_at
  TTL field: expires_at (Unix timestamp, now + 7 days)
  After each match result: update form_vec (EWM alpha=0.4), append to calibration_log

--- Test requirements ---

test_ilp_constraints.py:
  Assert: sum(xi) == 11 for every solve
  Assert: at least 1 WK in xi
  Assert: at least 4 bowlers in xi
  Assert: overseas count <= 4
  Assert: must_include players always in xi
  Assert: must_exclude players never in xi
  Use 5 different squad compositions as fixtures

test_monte_carlo.py:
  Assert: P(win) in [0.0, 1.0] for all inputs
  Assert: CI[0] < CI[1] always
  Assert: 10k rollouts complete in < 3s (pytest-benchmark)
  Assert: Platt-corrected probability is between 0 and 1

test_commentary_schema.py:
  Assert: every ILP solve produces exactly 4 CommentaryStep objects
  Assert: each step has non-empty title, formula, description, insight
  Assert: step 2 always has graph_data with batters, bowlers, edges arrays

--- Gate confirmation ---

After building:
  pytest api/tests/ -v
  python scripts/check_gate.py --stage 2

Expected: "GATE 2 PASSED — safe to proceed to Stage 3"
"""


# ════════════════════════════════════════════════════════════════
# STAGE 3 — REACT FRONTEND
# Gate: python scripts/check_gate.py --stage 3
# Requires: Gate 2 passed
# ════════════════════════════════════════════════════════════════

STAGE_3_SPEC = """
Build the React frontend with the captain's console, live reasoning panel,
math documentation, result card, and PostHog analytics.

PREREQUISITE: Gate 2 must pass before starting this stage.
Run: python scripts/check_gate.py --stage 2

--- Pages ---

src/pages/
  LandingPage.tsx       Season picker, team picker, mode picker, Start button
  SimulationPage.tsx    Main captain's console (two-panel layout)
  ResultPage.tsx        Tournament result + share card + donation

--- Core components ---

src/components/
  XISelector/
    XISelector.tsx        Drag-and-drop squad → XI, must-include toggle, formation bias
    PlayerCard.tsx        Shows name, role badge, E[runs], P(wkt/over), form indicator
  LiveReasoningPanel/
    LiveReasoningPanel.tsx    Tab container
    StepList.tsx              Renders CommentaryStep[] as numbered steps
    BipartiteGraph.tsx        Inline SVG from step 2 graph_data
                              - Batter nodes left, bowler nodes right
                              - Edge stroke-width proportional to threat weight
                              - High-threat edges red, medium amber, low teal
                              - CSS transition stagger 50ms per edge on mount
    MathDocsPanel.tsx         2x2 model card grid (Bi-LSTM, ILP, MC, Bipartite)
    CompareXIsPanel.tsx       Side-by-side current vs AI suggested XI
    TournamentPathPanel.tsx   Tree SVG with max-flow path highlighted
  ResultCard/
    ResultCard.tsx            Result summary (team, season, W/L, avg win prob, AI accept rate)
    ShareButtons.tsx          LinkedIn share + Copy link + Download PNG (html2canvas)
  DonationSection.tsx         Ko-fi button + cost breakdown + community stats
  WinProbabilityBar.tsx       Horizontal bar 0–100% with CI shaded region
  MatchHeader.tsx             Opponent, venue, date, toss result

src/analytics/
  events.ts             All 6 PostHog events:
                          simulation_started(season, team, mode)
                          xi_confirmed(match_id, accepted_ai_suggestion, overrides_count)
                          match_completed(match_id, win, win_probability)
                          tournament_completed(result, total_matches, avg_win_prob)
                          result_shared(platform)
                          donation_clicked()

src/data/
  mathDocs.ts           MathDoc[] entries for all 5 models
                        Each: { model_id, name, formula_latex, plain_english, deep_dive_prompt }

--- BipartiteGraph SVG spec ---

The BipartiteGraph component is the centrepiece of the commentary panel.
Render from CommentaryStep[2].graph_data which has shape:
  { batters: Player[], bowlers: Player[], edges: { batter_id, bowler_id, weight, threat_level }[] }

SVG layout:
  - viewBox: "0 0 560 max(batters.length, bowlers.length) * 50 + 40"
  - Batter nodes: x=40, y=40+i*50, rect 140x36, teal fill
  - Bowler nodes: x=380, y=40+i*50, rect 140x36, coral fill
  - Edges: line from batter right edge to bowler left edge
    - threat_level 'high'   → stroke #E24B4A, strokeWidth=4
    - threat_level 'medium' → stroke #EF9F27, strokeWidth=2
    - threat_level 'low'    → stroke #1D9E75, strokeWidth=1
    - opacity=0 initially, transition to 1 with 50ms stagger per edge
  - Legend bottom-right: three coloured lines with labels

--- Tests ---

src/__tests__/
  BipartiteGraph.test.tsx   renders correct edge count, high-threat edge is red
  XISelector.test.tsx       must-include toggle locks player, DnD moves player
  ResultCard.test.tsx       correct stats rendered, Share button fires posthog event
  LandingPage.test.tsx      Start button disabled until team + season selected

--- Gate confirmation ---

After building:
  npm test -- --watchAll=false
  npm run type-check
  python scripts/check_gate.py --stage 3

Expected: "GATE 3 PASSED — safe to proceed to Stage 4"
"""


# ════════════════════════════════════════════════════════════════
# STAGE 4 — INFRASTRUCTURE AND DEPLOYMENT
# Gate: python scripts/check_gate.py --stage 4
# Requires: Gate 3 passed
# ════════════════════════════════════════════════════════════════

STAGE_4_SPEC = """
Deploy the backend to AWS Lambda and the frontend to Vercel.
Set up CI, monitoring, and Linear issue auto-creation.

PREREQUISITE: Gate 3 must pass before starting this stage.
Run: python scripts/check_gate.py --stage 3

--- AWS SAM (template.yaml) ---

Resources:
  IPLSimulatorFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.11
      Handler: api.main.handler
      MemorySize: 512
      Timeout: 15
      Layers:
        - !Ref NumpyScipyLayer
        - !Ref PuLPLayer
      Environment:
        Variables:
          DATA_BUCKET:          !Sub '{{resolve:ssm:/ipl-sim/data-bucket}}'
          ANTHROPIC_API_KEY:    !Sub '{{resolve:ssm:/ipl-sim/anthropic-key}}'
          LINEAR_API_KEY:       !Sub '{{resolve:ssm:/ipl-sim/linear-key}}'
          POSTHOG_API_KEY:      !Sub '{{resolve:ssm:/ipl-sim/posthog-key}}'
          DYNAMODB_SESSIONS:    !Sub '{{resolve:ssm:/ipl-sim/dynamo-sessions}}'
          DYNAMODB_COUNTERS:    !Sub '{{resolve:ssm:/ipl-sim/dynamo-counters}}'
          SQS_CALIBRATION_URL:  !Sub '{{resolve:ssm:/ipl-sim/sqs-calibration}}'
      Events:
        ApiEvent:
          Type: HttpApi

  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      VersioningConfiguration: Enabled
      LifecycleConfiguration:
        Rules:
          - Id: IntelligentTiering
            Status: Enabled
            Transitions:
              - TransitionInDays: 30
                StorageClass: INTELLIGENT_TIERING

  SessionsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: ipl-simulator-sessions
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - { AttributeName: simulation_id, AttributeType: S }
      KeySchema:
        - { AttributeName: simulation_id, KeyType: HASH }
      TimeToLiveSpecification:
        AttributeName: expires_at
        Enabled: true

  CountersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: ipl-simulator-counters
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - { AttributeName: counter_name, AttributeType: S }
      KeySchema:
        - { AttributeName: counter_name, KeyType: HASH }

  CalibrationQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 60
      MessageRetentionPeriod: 86400
      RedrivePolicy:
        maxReceiveCount: 3
        deadLetterTargetArn: !GetAtt CalibrationDLQ.Arn

--- CloudWatch alarms ---

Create these alarms in template.yaml:
  - Lambda p95 latency > 8000ms → SNS email
  - Lambda error rate > 2% → SNS email
  - Custom metric NarrativeBudgetExceeded (published by backend) → SNS email

--- Vercel (vercel.json) ---

{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/api/(.*)", "destination": "API_GATEWAY_URL/api/$1" }],
  "env": {
    "VITE_API_BASE_URL": "@api-base-url",
    "VITE_POSTHOG_KEY": "@posthog-key",
    "VITE_KOFI_URL": "@kofi-url"
  }
}

--- GitHub Actions (.github/workflows/ci.yml) ---

on: push to main

jobs:
  test:
    - pip install -r api/requirements.txt
    - pytest api/tests/ -q
    - npm ci
    - npm test -- --watchAll=false
    - npm run type-check

  deploy-backend:
    needs: test
    - sam build
    - sam deploy --no-confirm-changeset

  nightly-evals:
    schedule: "0 2 * * *"  (2am UTC daily)
    - pytest api/tests/evals/ -v (runs eval_2_ilp_lift, eval_3_brier)
    - python scripts/run_narrative_eval.py (eval_4_narrative)
    - python scripts/run_override_eval.py  (eval_5_overrides)
    - Post results to Linear as a weekly eval issue

--- Linear auto-ticketing ---

api/middleware/error_reporter.py must:
  On any 5xx exception:
  - Create Linear bug ticket via Python SDK
  - Title: [BUG] {component}: {error_type}: {message[:80]}
  - Include: stack trace, match_id, venue_id, xi_hash from request context
  - Priority: 1 (urgent)

Also: after Gate 4 passes, run:
  python scripts/create_linear_tickets.py --stage 4
  (creates Linear epic + child issues for any remaining work)

--- Gate confirmation ---

After deploying:
  sam validate
  python scripts/check_gate.py --stage 4

Expected: "GATE 4 PASSED — all stages complete"
"""


if __name__ == "__main__":
    print("Kiro Spec Prompts — IPL Captain Simulator")
    print("==========================================")
    print("Stages:")
    for i, (name, spec) in enumerate([
        ("Data Validation",    STAGE_0_SPEC),
        ("Data Pipeline",      STAGE_1_SPEC),
        ("Backend Core",       STAGE_2_SPEC),
        ("React Frontend",     STAGE_3_SPEC),
        ("Infrastructure",     STAGE_4_SPEC),
    ]):
        lines = len(spec.strip().split('\n'))
        print(f"  Stage {i}: {name} ({lines} lines)")
    print("\nPaste each STAGE_N_SPEC into Kiro Spec Mode in order.")
    print("Run check_gate.py between each stage.")
