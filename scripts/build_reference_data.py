"""
scripts/build_reference_data.py
================================
Stage 0, Checks 2-5.
Builds the four reference JSON files that the pipeline and agents depend on.
Run AFTER validate_ipl_data.py passes.

Usage:
    python scripts/build_reference_data.py --all
    python scripts/build_reference_data.py --team-names
    python scripts/build_reference_data.py --venue-geometry
    python scripts/build_reference_data.py --overseas-flags --kaggle-csv path/to/auction.csv
    python scripts/build_reference_data.py --squad-pools    --kaggle-csv path/to/squads.csv
"""

import argparse
import json
from pathlib import Path

ROOT     = Path(__file__).parent.parent
REF_DIR  = ROOT / "data" / "reference"


# ── 1. TEAM NAME NORMALISATION MAP ──────────────────────────────
# Maps historical franchise names → canonical current name.
# The pipeline applies this before loading to DuckDB.
TEAM_NAME_MAP = {
    # Delhi franchise
    "Delhi Daredevils":             "Delhi Capitals",
    # Punjab franchise
    "Kings XI Punjab":              "Punjab Kings",
    # Hyderabad franchise
    "Deccan Chargers":              "Sunrisers Hyderabad",
    # Pune franchises (defunct)
    "Pune Warriors":                "Pune Warriors",   # keep — only existed 2011-2013
    "Rising Pune Supergiant":       "Rising Pune Supergiant",
    "Rising Pune Supergiants":      "Rising Pune Supergiant",
    # Gujarat franchises
    "Gujarat Lions":                "Gujarat Lions",   # keep — only 2016-2017
    "Gujarat Titans":               "Gujarat Titans",
    # Kochi (defunct)
    "Kochi Tuskers Kerala":         "Kochi Tuskers Kerala",
    # Lucknow
    "Lucknow Super Giants":         "Lucknow Super Giants",
    # Canonical names (map to themselves for safe lookup)
    "Royal Challengers Bangalore":  "Royal Challengers Bangalore",
    "Chennai Super Kings":          "Chennai Super Kings",
    "Mumbai Indians":               "Mumbai Indians",
    "Kolkata Knight Riders":        "Kolkata Knight Riders",
    "Rajasthan Royals":             "Rajasthan Royals",
    "Sunrisers Hyderabad":          "Sunrisers Hyderabad",
    "Delhi Capitals":               "Delhi Capitals",
    "Punjab Kings":                 "Punjab Kings",
}


# ── 2. VENUE GEOMETRY ────────────────────────────────────────────
# sq_boundary_m: square boundary in metres (roughly)
# straight_m:    straight boundary in metres
# avg_score:     historical average first-innings T20 score at this venue
# surface:       'flat' | 'spin' | 'pace' | 'swing'
VENUE_GEOMETRY = {
    "venues": [
        {
            "cricsheet_name": "M Chinnaswamy Stadium",
            "city": "Bangalore",
            "team": "Royal Challengers Bangalore",
            "sq_boundary_m": 58,
            "straight_m": 73,
            "avg_score": 178,
            "surface": "flat",
            "notes": "High altitude, short square, historically high-scoring"
        },
        {
            "cricsheet_name": "MA Chidambaram Stadium",
            "city": "Chennai",
            "team": "Chennai Super Kings",
            "sq_boundary_m": 65,
            "straight_m": 74,
            "avg_score": 162,
            "surface": "spin",
            "notes": "Slows up in second half, favours spinners from over 10"
        },
        {
            "cricsheet_name": "Wankhede Stadium",
            "city": "Mumbai",
            "team": "Mumbai Indians",
            "sq_boundary_m": 60,
            "straight_m": 69,
            "avg_score": 171,
            "surface": "flat",
            "notes": "Sea breeze affects swing; two-paced surface"
        },
        {
            "cricsheet_name": "Eden Gardens",
            "city": "Kolkata",
            "team": "Kolkata Knight Riders",
            "sq_boundary_m": 70,
            "straight_m": 80,
            "avg_score": 158,
            "surface": "pace",
            "notes": "Larger boundaries; dew factor in evening games"
        },
        {
            "cricsheet_name": "Sawai Mansingh Stadium",
            "city": "Jaipur",
            "team": "Rajasthan Royals",
            "sq_boundary_m": 65,
            "straight_m": 75,
            "avg_score": 165,
            "surface": "flat",
            "notes": "High altitude (431m), slightly quicker outfield"
        },
        {
            "cricsheet_name": "Rajiv Gandhi International Stadium",
            "city": "Hyderabad",
            "team": "Sunrisers Hyderabad",
            "sq_boundary_m": 63,
            "straight_m": 74,
            "avg_score": 164,
            "surface": "flat",
            "notes": "Used by Deccan Chargers 2008-2012 before SRH"
        },
        {
            "cricsheet_name": "Punjab Cricket Association IS Bindra Stadium",
            "city": "Mohali",
            "team": "Punjab Kings",
            "sq_boundary_m": 68,
            "straight_m": 76,
            "avg_score": 163,
            "surface": "pace",
            "notes": "Seam movement early; outfield fast"
        },
        {
            "cricsheet_name": "Arun Jaitley Stadium",
            "city": "Delhi",
            "team": "Delhi Capitals",
            "sq_boundary_m": 65,
            "straight_m": 75,
            "avg_score": 161,
            "surface": "flat",
            "notes": "Also known as Feroz Shah Kotla"
        },
        {
            "cricsheet_name": "Feroz Shah Kotla",
            "city": "Delhi",
            "team": "Delhi Capitals",
            "sq_boundary_m": 65,
            "straight_m": 75,
            "avg_score": 161,
            "surface": "flat",
            "notes": "Legacy name for Arun Jaitley Stadium"
        },
        {
            "cricsheet_name": "DY Patil Stadium",
            "city": "Mumbai",
            "team": "neutral",
            "sq_boundary_m": 70,
            "straight_m": 78,
            "avg_score": 155,
            "surface": "flat",
            "notes": "Larger venue; used as neutral for early IPL and playoffs"
        },
        {
            "cricsheet_name": "Brabourne Stadium",
            "city": "Mumbai",
            "team": "neutral",
            "sq_boundary_m": 62,
            "straight_m": 72,
            "avg_score": 168,
            "surface": "flat",
            "notes": "CCI ground; used when Wankhede unavailable"
        },
        {
            "cricsheet_name": "Sharjah Cricket Stadium",
            "city": "Sharjah",
            "team": "neutral",
            "sq_boundary_m": 60,
            "straight_m": 68,
            "avg_score": 160,
            "surface": "flat",
            "notes": "Used for IPL 2020 (COVID bubble)"
        },
        {
            "cricsheet_name": "Dubai International Cricket Stadium",
            "city": "Dubai",
            "team": "neutral",
            "sq_boundary_m": 65,
            "straight_m": 75,
            "avg_score": 156,
            "surface": "flat",
            "notes": "Used for IPL 2020"
        },
        {
            "cricsheet_name": "Sheikh Zayed Stadium",
            "city": "Abu Dhabi",
            "team": "neutral",
            "sq_boundary_m": 68,
            "straight_m": 77,
            "avg_score": 154,
            "surface": "flat",
            "notes": "Used for IPL 2020 and 2021"
        },
    ]
}


def build_team_names():
    out = REF_DIR / "team_name_map.json"
    REF_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(TEAM_NAME_MAP, indent=2))
    print(f"[team-names] Written {len(TEAM_NAME_MAP)} mappings → {out}")


def build_venue_geometry():
    out = REF_DIR / "venue_geometry.json"
    REF_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(VENUE_GEOMETRY, indent=2))
    print(f"[venue-geometry] Written {len(VENUE_GEOMETRY['venues'])} venues → {out}")


from typing import Union, Optional
def build_overseas_flags(kaggle_csv: Optional[str]):
    """
    Build overseas_flags.json from a Kaggle IPL auction CSV.
    Expected CSV columns: player, team, year, nationality (or country)

    If no CSV supplied, writes a template with known 2008-2016 overseas players.
    Supplement this file with the Kaggle dataset:
    https://www.kaggle.com/datasets/nowke9/ipldata  (Players.csv has nationality)
    """
    out = REF_DIR / "overseas_flags.json"
    REF_DIR.mkdir(parents=True, exist_ok=True)

    if kaggle_csv:
        import pandas as pd
        df = pd.read_csv(kaggle_csv)
        # Normalise column names
        df.columns = [c.lower().strip() for c in df.columns]
        name_col = next((c for c in df.columns if "player" in c or "name" in c), None)
        nat_col  = next((c for c in df.columns if "nation" in c or "country" in c or "overseas" in c), None)
        if not name_col or not nat_col:
            print(f"[overseas] Could not find player/nationality columns in {kaggle_csv}")
            print(f"  Columns found: {list(df.columns)}")
            return
        flags = {}
        for _, row in df.iterrows():
            name = str(row[name_col]).strip()
            is_overseas = str(row[nat_col]).strip().lower() not in ("india", "indian", "ind", "false", "0", "no")
            flags[name] = is_overseas
        out.write_text(json.dumps({"source": kaggle_csv, "flags": flags}, indent=2))
        print(f"[overseas] Written {len(flags)} players → {out}")
    else:
        # Template with well-known overseas players 2008-2016
        template = {
            "source": "manual — supplement with Kaggle Players.csv",
            "note": "Keys are player names as they appear in Cricsheet. True = overseas.",
            "flags": {
                "AB de Villiers": True, "CH Gayle": True, "JH Kallis": True,
                "BB McCullum": True, "MS Gilchrist": True, "AC Gilchrist": True,
                "SR Watson": True, "MJ Clarke": True, "BJ Hodge": True,
                "DJ Hussey": True, "MEK Hussey": True, "DA Warner": True,
                "SPD Smith": True, "GJ Maxwell": True, "JP Faulkner": True,
                "DJ Bravo": True, "KA Pollard": True, "DJG Sammy": True,
                "M Morkel": True, "DW Steyn": True, "JP Duminy": True,
                "F du Plessis": True, "HM Amla": True,
                "SCJ Broad": True, "PD Collingwood": True, "KP Pietersen": True,
                "EJG Morgan": True, "OA Shah": True,
                "RP Arnold": True, "DPMD Jayawardene": True, "KC Sangakkara": True,
                "M Muralitharan": True, "ST Jayasuriya": True,
                "Shoaib Akhtar": True, "Umar Gul": True, "Shahid Afridi": True,
                "Kamran Akmal": True,
            }
        }
        out.write_text(json.dumps(template, indent=2))
        print(f"[overseas] Written template ({len(template['flags'])} known players) → {out}")
        print("  ACTION REQUIRED: Supplement with Kaggle Players.csv for full coverage")
        print("  Download: https://www.kaggle.com/datasets/nowke9/ipldata")
        print("  Then re-run: python scripts/build_reference_data.py --overseas-flags --kaggle-csv Players.csv")


def build_squad_pools(kaggle_csv: Optional[str]):
    """
    Build squad_pools.json: team → season → [player_names]
    If no CSV, writes a note pointing to the source.

    Source: https://www.kaggle.com/datasets/nowke9/ipldata
    File: Players.csv has columns: id, team, season, player_name
    """
    out = REF_DIR / "squad_pools.json"
    REF_DIR.mkdir(parents=True, exist_ok=True)

    if kaggle_csv:
        import pandas as pd
        df = pd.read_csv(kaggle_csv)
        df.columns = [c.lower().strip() for c in df.columns]
        pools = {}
        for _, row in df.iterrows():
            team   = str(row.get("team", "")).strip()
            season = str(row.get("season", row.get("year", ""))).strip()
            player = str(row.get("player_name", row.get("player", row.get("name", "")))).strip()
            if not team or not season or not player:
                continue
            pools.setdefault(team, {}).setdefault(season, []).append(player)
        out.write_text(json.dumps(pools, indent=2))
        total = sum(len(p) for t in pools.values() for p in t.values())
        print(f"[squad-pools] Written {total} player-season entries across {len(pools)} teams → {out}")
    else:
        template = {
            "_note": "Supplement from Kaggle: https://www.kaggle.com/datasets/nowke9/ipldata",
            "_action": "Run: python scripts/build_reference_data.py --squad-pools --kaggle-csv Players.csv",
            "Royal Challengers Bangalore": {
                "2010": ["V Kohli", "AB de Villiers", "JH Kallis", "KP Pietersen",
                         "R Dravid", "R Uthappa", "CM Gautam", "MV Boucher",
                         "DW Steyn", "Z Khan", "A Kumble", "P Kumar",
                         "S Aravind", "VR Aaron", "R Vinay Kumar",
                         "PP Ojha", "A Mishra", "W Jaffer", "CL White",
                         "T Henderson", "AB McDonald", "B Chipli",
                         "S Sohal", "DB Das", "BEA Coetzee"]
            }
        }
        out.write_text(json.dumps(template, indent=2))
        print(f"[squad-pools] Written template → {out}")
        print("  ACTION REQUIRED: Download Kaggle IPL dataset and run with --kaggle-csv")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",            action="store_true")
    parser.add_argument("--team-names",     action="store_true")
    parser.add_argument("--venue-geometry", action="store_true")
    parser.add_argument("--overseas-flags", action="store_true")
    parser.add_argument("--squad-pools",    action="store_true")
    parser.add_argument("--kaggle-csv",     type=str, default=None,
                        help="Path to Kaggle Players.csv for overseas flags and squad pools")
    args = parser.parse_args()

    if args.all or args.team_names:     build_team_names()
    if args.all or args.venue_geometry: build_venue_geometry()
    if args.all or args.overseas_flags: build_overseas_flags(args.kaggle_csv)
    if args.all or args.squad_pools:    build_squad_pools(args.kaggle_csv)

    if not any([args.all, args.team_names, args.venue_geometry,
                args.overseas_flags, args.squad_pools]):
        parser.print_help()


if __name__ == "__main__":
    main()
