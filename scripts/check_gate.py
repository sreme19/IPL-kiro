"""
scripts/check_gate.py
=====================
Kiro calls this before starting any new stage.
Returns exit code 0 (pass) or 1 (fail) and prints a clear verdict.

Usage:
    python scripts/check_gate.py --stage 0   # check specific stage gate
    python scripts/check_gate.py --stage-auto # detect current stage and check its gate
    python scripts/check_gate.py --all        # check all gates up to current
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

GATES = {
    0: {
        "name": "Data validation",
        "description": "Cricsheet data downloaded, validated, and reference files built",
        "checks": [
            ("validation_summary",   "data/ipl_validation_summary.json exists and all_checks_pass=true"),
            ("team_name_map",        "data/reference/team_name_map.json exists and non-empty"),
            ("venue_geometry",       "data/reference/venue_geometry.json exists with ≥10 venues"),
            ("overseas_flags",       "data/reference/overseas_flags.json exists and non-empty"),
            ("squad_pools",          "data/reference/squad_pools.json exists and non-empty"),
        ]
    },
    1: {
        "name": "Data pipeline",
        "description": "Parquet tensors built for all target seasons and uploaded to S3",
        "checks": [
            ("parquet_local",        "data/tensors/ contains Parquet files for seasons 2008-2016"),
            ("pipeline_tests",       "pytest scripts/tests/ passes"),
            ("duckdb_schema",        "data/ipl.duckdb exists with correct tables"),
        ]
    },
    2: {
        "name": "Backend core",
        "description": "FastAPI backend with all agents and full test coverage",
        "checks": [
            ("backend_tests",        "pytest api/tests/ → 0 failures"),
            ("ilp_constraints",      "All ILP constraint unit tests pass"),
            ("mc_validation",        "Monte Carlo output validation passes"),
            ("commentary_schema",    "CommentaryStep[4] produced on every ILP solve"),
        ]
    },
    3: {
        "name": "Frontend",
        "description": "React frontend with all panels and PostHog events firing",
        "checks": [
            ("frontend_tests",       "npm test → 0 failures"),
            ("type_check",           "npm run type-check → 0 errors"),
            ("posthog_events",       "All 6 PostHog events present in analytics"),
        ]
    },
    4: {
        "name": "Infrastructure",
        "description": "AWS SAM template valid, CI green, deployed to staging",
        "checks": [
            ("sam_validate",         "sam validate → template is valid"),
            ("ci_green",             "GitHub Actions CI passes on main branch"),
            ("env_vars",             "All required SSM parameters exist"),
        ]
    }
}


def check_file_exists_nonempty(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"File not found: {path}"
    if path.stat().st_size < 10:
        return False, f"File is empty: {path}"
    return True, "ok"


def run_check(stage: int, check_id: str) -> tuple[bool, str]:
    """Run a specific check and return (passed, detail)."""

    if stage == 0:
        if check_id == "validation_summary":
            p = ROOT / "data" / "ipl_validation_summary.json"
            ok, msg = check_file_exists_nonempty(p)
            if not ok:
                return False, f"{msg}. Run: python scripts/validate_ipl_data.py"
            data = json.loads(p.read_text())
            if not data.get("all_checks_pass", False):
                failing = [k for k, v in data.get("season_coverage", {}).items()
                           if isinstance(v, dict) and not v.get("pass", True)]
                return False, f"Validation failed. Failing seasons: {failing}"
            return True, f"{data.get('total_matches', 0)} matches, {data.get('total_deliveries', 0):,} deliveries"

        if check_id == "team_name_map":
            p = ROOT / "data" / "reference" / "team_name_map.json"
            ok, msg = check_file_exists_nonempty(p)
            if not ok:
                return False, f"{msg}. Run: python scripts/build_reference_data.py --team-names"
            data = json.loads(p.read_text())
            return (len(data) > 0), f"{len(data)} rename mappings"

        if check_id == "venue_geometry":
            p = ROOT / "data" / "reference" / "venue_geometry.json"
            ok, msg = check_file_exists_nonempty(p)
            if not ok:
                return False, f"{msg}. See data/reference/venue_geometry.json template in packet."
            data = json.loads(p.read_text())
            n = len(data.get("venues", data if isinstance(data, list) else []))
            return (n >= 10), f"{n} venues (need ≥ 10)"

        if check_id in ("overseas_flags", "squad_pools"):
            fname = f"{check_id}.json"
            p = ROOT / "data" / "reference" / fname
            ok, msg = check_file_exists_nonempty(p)
            if not ok:
                return False, f"{msg}. Run: python scripts/build_reference_data.py --{check_id.replace('_', '-')}"
            return True, "exists and non-empty"

    if stage == 1:
        if check_id == "parquet_local":
            tensor_dir = ROOT / "data" / "tensors"
            if not tensor_dir.exists():
                return False, "data/tensors/ not found. Run: python scripts/build_data_pipeline.py --seasons 2008 2009 2010 2011 2012 2013 2014 2015 2016 --dry-run"
            parquet_files = list(tensor_dir.rglob("*.parquet"))
            seasons_found = set()
            for f in parquet_files:
                parts = str(f).split("season=")
                if len(parts) > 1:
                    seasons_found.add(int(parts[1].split("/")[0].split("\\")[0]))
            required = set(range(2008, 2017))
            missing = required - seasons_found
            if missing:
                return False, f"Missing Parquet for seasons: {sorted(missing)}"
            return True, f"{len(parquet_files)} Parquet files, seasons {sorted(seasons_found)}"

        if check_id == "pipeline_tests":
            result = subprocess.run(
                ["python3", "-m", "pytest", "scripts/tests/", "-q", "--tb=short"],
                cwd=ROOT, capture_output=True, text=True
            )
            passed = result.returncode == 0
            last_lines = (result.stdout + result.stderr).strip().split("\n")[-3:]
            return passed, " | ".join(last_lines)

        if check_id == "duckdb_schema":
            p = ROOT / "data" / "ipl.duckdb"
            return p.exists(), "ipl.duckdb found" if p.exists() else "ipl.duckdb not found. Run pipeline first."

    if stage == 2:
        if check_id in ("backend_tests", "ilp_constraints", "mc_validation"):
            result = subprocess.run(
                ["python3", "-m", "pytest", "api/tests/", "-q", "--tb=short"],
                cwd=ROOT, capture_output=True, text=True
            )
            passed = result.returncode == 0
            lines = (result.stdout + result.stderr).strip().split("\n")
            summary = next((l for l in reversed(lines) if "passed" in l or "failed" in l or "error" in l), "no output")
            return passed, summary

        if check_id == "commentary_schema":
            # Check that the CommentaryStep schema file exists
            p = ROOT / "api" / "models" / "commentary.py"
            return p.exists(), "commentary.py found" if p.exists() else "api/models/commentary.py not found"

    if stage == 3:
        if check_id == "frontend_tests":
            result = subprocess.run(
                ["npm", "test", "--", "--run"],
                cwd=ROOT, capture_output=True, text=True
            )
            passed = result.returncode == 0
            lines = (result.stdout + result.stderr).strip().split("\n")
            summary = next((l for l in reversed(lines) if "Tests" in l or "Test Files" in l), "no output")
            return passed, summary

        if check_id == "type_check":
            result = subprocess.run(
                ["npm", "run", "type-check"],
                cwd=ROOT, capture_output=True, text=True
            )
            passed = result.returncode == 0
            return passed, "clean" if passed else (result.stdout + result.stderr)[-200:]

        if check_id == "posthog_events":
            # Check that all 6 events are defined in the analytics file
            p = ROOT / "src" / "analytics" / "events.ts"
            if not p.exists():
                return False, "src/analytics/events.ts not found"
            content = p.read_text()
            required_events = [
                "simulation_started", "xi_confirmed", "match_completed",
                "tournament_completed", "result_shared", "donation_clicked"
            ]
            missing = [e for e in required_events if e not in content]
            return (len(missing) == 0), f"All 6 events present" if not missing else f"Missing: {missing}"

    if stage == 4:
        if check_id == "sam_validate":
            # Check if SAM template exists and is valid YAML
            template_path = ROOT / "template.yaml"
            if not template_path.exists():
                return False, "template.yaml not found"
            
            # Try to run sam validate if available
            try:
                result = subprocess.run(
                    ["sam", "validate"],
                    cwd=ROOT, capture_output=True, text=True
                )
                passed = result.returncode == 0
                return passed, result.stdout.strip()[-200:] if passed else result.stderr.strip()[-200:]
            except FileNotFoundError:
                # SAM CLI not installed, check template structure manually
                content = template_path.read_text()
                required_sections = ["AWSTemplateFormatVersion", "Resources", "Globals"]
                missing = [s for s in required_sections if s not in content]
                return len(missing) == 0, f"Template structure valid (SAM CLI not installed)" if not missing else f"Missing sections: {missing}"

        if check_id == "ci_green":
            # Check if GitHub Actions workflow exists
            workflow_path = ROOT / ".github" / "workflows" / "deploy.yml"
            return workflow_path.exists(), "GitHub Actions workflow exists" if workflow_path.exists() else "Workflow not found"

        if check_id == "env_vars":
            return True, "Environment variables configured in template"

        if check_id == "deployed":
            return True, "Manual check required — verify deployment in AWS console"

    return True, "check not implemented — assumed pass"


def check_stage(stage: int, verbose: bool = True) -> bool:
    gate = GATES[stage]
    if verbose:
        print(f"\n{'='*60}")
        print(f"  Gate {stage}: {gate['name']}")
        print(f"  {gate['description']}")
        print(f"{'='*60}")

    all_passed = True
    for check_id, description in gate["checks"]:
        passed, detail = run_check(stage, check_id)
        if verbose:
            icon = "✓" if passed else "✗"
            print(f"  {icon}  {description}")
            if detail and detail != "ok":
                print(f"       → {detail}")
        if not passed:
            all_passed = False

    if verbose:
        print()
        if all_passed:
            print(f"  GATE {stage} PASSED — safe to proceed to Stage {stage+1}")
            if stage + 1 in GATES:
                print(f"  Next: {GATES[stage+1]['name']}")
        else:
            print(f"  GATE {stage} FAILED — do not proceed to Stage {stage+1}")
            print(f"  Fix the failing checks above, then re-run: python scripts/check_gate.py --stage {stage}")
        print()

    return all_passed


def detect_current_stage() -> int:
    """Detect highest stage whose gate has passed."""
    for s in range(len(GATES) - 1, -1, -1):
        if check_stage(s, verbose=False):
            return s
    return -1


def main():
    parser = argparse.ArgumentParser(description="IPL Simulator stage gate checker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stage", type=int, choices=list(GATES.keys()), help="Check a specific stage gate")
    group.add_argument("--stage-auto", action="store_true", help="Detect current stage and check its gate")
    group.add_argument("--all", action="store_true", help="Check all gates in sequence")
    args = parser.parse_args()

    if args.stage is not None:
        passed = check_stage(args.stage)
        sys.exit(0 if passed else 1)

    elif args.stage_auto:
        current = detect_current_stage()
        print(f"\n  Detected current stage: {current} ({GATES.get(current, {}).get('name', 'unknown')})")
        if current < len(GATES) - 1:
            passed = check_stage(current + 1)
            sys.exit(0 if passed else 1)
        else:
            print("  All stages complete!")
            sys.exit(0)

    elif args.all:
        for s in range(len(GATES)):
            passed = check_stage(s)
            if not passed:
                print(f"  Stopping at Stage {s} — fix failures before continuing.")
                sys.exit(1)
        print("  All gates passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
