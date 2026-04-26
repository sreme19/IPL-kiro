"""
scripts/validate_ipl_data.py
============================
Stage 0, Check 1.
Downloads Cricsheet IPL data, validates coverage and quality,
writes data/ipl_validation_summary.json.

Usage:
    python scripts/validate_ipl_data.py
    python scripts/validate_ipl_data.py --skip-download   # if zip already exists
"""

import argparse
import json
import os
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd
import duckdb

ROOT            = Path(__file__).parent.parent
DATA_DIR        = ROOT / "data"
ZIP_PATH        = DATA_DIR / "ipl_male_json.zip"
EXTRACT_DIR     = DATA_DIR / "ipl_json_raw"
SUMMARY_PATH    = DATA_DIR / "ipl_validation_summary.json"
REPORT_PATH     = DATA_DIR / "ipl_validation_report.md"

CRICSHEET_URL   = "https://cricsheet.org/downloads/ipl_male_json.zip"
TARGET_SEASONS  = list(range(2008, 2017))
MIN_SAMPLE      = 30


def download(skip=False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if skip and ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 100_000:
        print(f"[download] Using cached {ZIP_PATH} ({ZIP_PATH.stat().st_size/1e6:.1f} MB)")
        return
    print(f"[download] Fetching {CRICSHEET_URL} ...")
    r = requests.get(CRICSHEET_URL, timeout=120, stream=True)
    r.raise_for_status()
    with open(ZIP_PATH, "wb") as f:
        for chunk in r.iter_content(65536):
            f.write(chunk)
    print(f"[download] Done — {ZIP_PATH.stat().st_size/1e6:.1f} MB")


def extract():
    EXTRACT_DIR.mkdir(exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as z:
        json_files = [n for n in z.namelist() if n.endswith(".json")]
        if len(list(EXTRACT_DIR.glob("*.json"))) < len(json_files):
            z.extractall(EXTRACT_DIR)
    files = list(EXTRACT_DIR.glob("*.json"))
    print(f"[extract] {len(files)} JSON files available")
    return files


def parse_all(json_files):
    matches, deliveries, errors = [], [], []
    for path in EXTRACT_DIR.glob("*.json"):
        try:
            with open(path) as f:
                d = json.load(f)
            info   = d.get("info", {})
            innings = d.get("innings", [])
            dates  = info.get("dates", [])
            season_raw = info.get("event", {}).get("season", "")
            if "/" in str(season_raw):
                season = int(str(season_raw).split("/")[0]) + 1
            else:
                try:    season = int(season_raw)
                except: season = int(dates[0][:4]) if dates else 0
            teams    = info.get("teams", [])
            venue    = info.get("venue", "")
            registry = info.get("registry", {}).get("people", {})
            matches.append({
                "match_id": path.stem, "season": season,
                "date": dates[0] if dates else "",
                "venue": venue,
                "team_1": teams[0] if teams else "",
                "team_2": teams[1] if len(teams) > 1 else "",
                "winner": info.get("outcome", {}).get("winner", ""),
                "n_players": len(registry),
            })
            for ii, inn in enumerate(innings):
                bt = inn.get("team", "")
                bl = teams[1] if bt == teams[0] else teams[0]
                for ov in inn.get("overs", []):
                    for ball in ov.get("deliveries", []):
                        wkts = ball.get("wickets", [])
                        deliveries.append({
                            "match_id":     path.stem,
                            "season":       season,
                            "venue":        venue,
                            "batting_team": bt,
                            "bowling_team": bl,
                            "innings":      ii + 1,
                            "over":         ov.get("over", 0),
                            "batter":       ball.get("batter", ""),
                            "bowler":       ball.get("bowler", ""),
                            "runs_batter":  ball.get("runs", {}).get("batter", 0),
                            "runs_extras":  ball.get("runs", {}).get("extras", 0),
                            "is_wicket":    1 if wkts else 0,
                            "wicket_kind":  wkts[0].get("kind", "") if wkts else "",
                        })
        except Exception as e:
            errors.append((str(path), str(e)))

    df_m = pd.DataFrame(matches)
    df_d = pd.DataFrame(deliveries)
    print(f"[parse] {len(df_m)} matches · {len(df_d):,} deliveries · {len(errors)} errors")
    return df_m, df_d, errors


def season_check(df_m):
    counts = df_m.groupby("season").size()
    results = {}
    for s in TARGET_SEASONS:
        n = int(counts.get(s, 0))
        results[str(s)] = {"matches": n, "pass": n >= 14}
    return results


def field_check(df_d):
    checks = {
        "batter":        (df_d["batter"] != "").mean(),
        "bowler":        (df_d["bowler"] != "").mean(),
        "venue":         (df_d["venue"]  != "").mean(),
        "batting_team":  (df_d["batting_team"] != "").mean(),
        "runs_batter":   df_d["runs_batter"].notna().mean(),
    }
    return {k: {"completeness": round(float(v), 4), "pass": v >= 0.99} for k, v in checks.items()}


def tensor_check(df_d):
    con = duckdb.connect()
    con.register("d", df_d)
    r = con.execute(f"""
        SELECT COUNT(*) total,
               SUM(CASE WHEN n >= {MIN_SAMPLE} THEN 1 ELSE 0 END) above
        FROM (
            SELECT batter, bowler, venue, COUNT(*) n
            FROM d
            WHERE season <= 2015 AND batter!='' AND bowler!='' AND venue!=''
            GROUP BY batter, bowler, venue
        )
    """).fetchone()
    total, above = int(r[0]), int(r[1])
    return {
        "total_triplets": total,
        "above_threshold": above,
        "coverage_pct": round(above / total, 4) if total else 0,
        "pass": total > 0 and above > 20,
    }


def team_check(df_m):
    teams = sorted(set(df_m["team_1"]) | set(df_m["team_2"]) - {""})
    rcb = [t for t in teams if "Royal" in t or "Bangalore" in t]
    return {"all_teams": teams, "rcb_variants": rcb, "n_teams": len(teams), "pass": len(teams) > 5}


def write_summary(season_r, field_r, tensor_r, team_r, errors, df_m, df_d):
    all_pass = (
        all(v["pass"] for v in season_r.values()) and
        all(v["pass"] for v in field_r.values()) and
        tensor_r["pass"] and
        team_r["pass"]
    )
    # Convert numpy bool_ to Python bool for JSON serialization
    def convert_bools(obj):
        if hasattr(obj, 'item'):
            return obj.item()
        elif isinstance(obj, dict):
            return {k: convert_bools(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_bools(v) for v in obj]
        return obj
    
    season_r = convert_bools(season_r)
    field_r = convert_bools(field_r)
    tensor_r = convert_bools(tensor_r)
    team_r = convert_bools(team_r)
    
    summary = {
        "run_at":           datetime.now().isoformat(),
        "total_matches":    len(df_m),
        "total_deliveries": len(df_d),
        "parse_errors":     len(errors),
        "all_checks_pass":  bool(all_pass),
        "season_coverage":  season_r,
        "field_completeness": field_r,
        "tensor_density":   tensor_r,
        "team_identity":    team_r,
        "data_gaps": [
            "overseas_player_flags — not in Cricsheet, source from Kaggle auction CSV",
            "full_squad_pool — Cricsheet has playing XI only, supplement from Kaggle",
            "venue_boundary_geometry — manually curate data/reference/venue_geometry.json",
            "team_name_normalisation — apply data/reference/team_name_map.json in pipeline",
        ]
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))

    verdict = "ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED"
    print(f"\n[result] {verdict}")
    print(f"[result] Summary → {SUMMARY_PATH}")
    if not all_pass:
        for s, v in season_r.items():
            if not v["pass"]: print(f"  ✗ Season {s}: only {v['matches']} matches")
        for f, v in field_r.items():
            if not v["pass"]: print(f"  ✗ Field '{f}': {v['completeness']:.1%} completeness")
    return all_pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    download(skip=args.skip_download)
    json_files = extract()
    df_m, df_d, errors = parse_all(json_files)
    season_r  = season_check(df_m)
    field_r   = field_check(df_d)
    tensor_r  = tensor_check(df_d)
    team_r    = team_check(df_m)
    passed    = write_summary(season_r, field_r, tensor_r, team_r, errors, df_m, df_d)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
