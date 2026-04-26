#!/usr/bin/env python3
"""
scripts/build_data_pipeline.py
==============================
Stage 1: Transform raw Cricsheet JSON into pre-computed Parquet tensor files.

Usage:
    python scripts/build_data_pipeline.py --seasons 2008 2009 2010 2011 2012 2013 2014 2015 2016
    python scripts/build_data_pipeline.py --seasons 2008 ... --dry-run   (no S3 upload)
    python scripts/build_data_pipeline.py --seasons 2008 ... --upload    (includes S3 upload)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
EXTRACT_DIR = DATA_DIR / "ipl_json_raw"
TENSORS_DIR = DATA_DIR / "tensors"
DUCKDB_PATH = DATA_DIR / "ipl.duckdb"
REFERENCE_DIR = DATA_DIR / "reference"

# Load reference data
TEAM_NAME_MAP = json.loads((REFERENCE_DIR / "team_name_map.json").read_text())
OVERSEAS_FLAGS = json.loads((REFERENCE_DIR / "overseas_flags.json").read_text())
SQUAD_POOLS = json.loads((REFERENCE_DIR / "squad_pools.json").read_text())

MIN_SAMPLE_SIZE = 30
FORM_EWM_ALPHA = 0.4


def load_json_to_duckdb(con: duckdb.DuckDBPyConnection):
    """Load all JSON files into DuckDB with team name normalization."""
    
    print("[parse] Loading JSON files into DuckDB...")
    
    # Create tables
    con.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id VARCHAR,
            season INTEGER,
            date DATE,
            venue VARCHAR,
            team_1 VARCHAR,
            team_2 VARCHAR,
            winner VARCHAR,
            toss_winner VARCHAR,
            toss_decision VARCHAR
        )
    """)
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            match_id VARCHAR,
            season INTEGER,
            venue VARCHAR,
            batting_team VARCHAR,
            bowling_team VARCHAR,
            innings INTEGER,
            over INTEGER,
            ball INTEGER,
            batter VARCHAR,
            bowler VARCHAR,
            runs_batter INTEGER,
            runs_extras INTEGER,
            is_wicket BOOLEAN,
            wicket_kind VARCHAR
        )
    """)
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id VARCHAR,
            name VARCHAR,
            cricsheet_name VARCHAR
        )
    """)
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS squads (
            team VARCHAR,
            season INTEGER,
            player_id VARCHAR,
            is_overseas BOOLEAN
        )
    """)
    
    # Process JSON files
    match_rows = []
    delivery_rows = []
    player_set = set()
    squad_rows = []
    
    json_files = list(EXTRACT_DIR.glob("*.json"))
    
    for i, json_file in enumerate(json_files):
        if i % 100 == 0:
            print(f"[parse] Processing file {i+1}/{len(json_files)}: {json_file.name}")
        
        try:
            data = json.loads(json_file.read_text())
            info = data.get("info", {})
            
            # Extract match info
            match_id = json_file.stem
            season = info.get("event", {}).get("season", 0) if isinstance(info.get("event"), dict) else 0
            if season == 0:  # Fallback to date-based season detection
                dates = info.get("dates", [])
                if dates and isinstance(dates, list) and dates[0]:
                    season = int(dates[0].split("-")[0])
            
            date_str = info.get("dates", [""])[0] if info.get("dates") and isinstance(info.get("dates"), list) else ""
            venue = info.get("city", "")  # Use city as venue fallback
            
            # Extract teams from players dict keys
            teams = list(info.get("players", {}).keys())
            team_1 = TEAM_NAME_MAP.get(teams[0], teams[0]) if len(teams) > 0 else ""
            team_2 = TEAM_NAME_MAP.get(teams[1], teams[1]) if len(teams) > 1 else ""
            
            # Normalize winner
            winner = info.get("outcome", {}).get("winner", "")
            winner = TEAM_NAME_MAP.get(winner, winner)
            
            # Extract toss info
            toss_data = info.get("toss", {})
            toss_winner = toss_data.get("winner", "") if isinstance(toss_data, dict) else ""
            toss_winner = TEAM_NAME_MAP.get(toss_winner, toss_winner)
            toss_decision = toss_data.get("decision", "") if isinstance(toss_data, dict) else ""
            
            match_rows.append({
                "match_id": match_id,
                "season": season,
                "date": date_str,
                "venue": venue,
                "team_1": team_1,
                "team_2": team_2,
                "winner": winner,
                "toss_winner": toss_winner,
                "toss_decision": toss_decision
            })
            
            # Extract playing XI for squads
            for team_name, xi in info.get("players", {}).items():
                normalized_team = TEAM_NAME_MAP.get(team_name, team_name)
                for player_name in xi:
                    player_id = player_name.lower().replace(" ", "_")
                    player_set.add((player_id, player_name, player_name))
                    
                    # Check if overseas
                    is_overseas = OVERSEAS_FLAGS.get("flags", {}).get(player_name, False)
                    
                    squad_rows.append({
                        "team": normalized_team,
                        "season": season,
                        "player_id": player_id,
                        "is_overseas": is_overseas
                    })
            
            # Extract deliveries
            for innings_data in data.get("innings", []):
                batting_team = TEAM_NAME_MAP.get(innings_data.get("team", ""), innings_data.get("team", ""))
                
                for over_data in innings_data.get("overs", []):
                    over_num = over_data.get("over", 0)
                    
                    for delivery_data in over_data.get("deliveries", []):
                        batter = delivery_data.get("batter", "")
                        bowler = delivery_data.get("bowler", "")
                        runs_batter = delivery_data.get("runs", {}).get("batter", 0)
                        runs_extras = delivery_data.get("runs", {}).get("extras", 0)
                        
                        # Determine wicket info
                        wicket_info = delivery_data.get("wickets", [{}])[0] if delivery_data.get("wickets") else {}
                        is_wicket = bool(wicket_info)
                        wicket_kind = wicket_info.get("kind", "") if is_wicket else ""
                        
                        # Determine bowling team (the other team)
                        bowling_team = team_2 if batting_team == team_1 else team_1
                        
                        delivery_rows.append({
                            "match_id": match_id,
                            "season": season,
                            "venue": venue,
                            "batting_team": batting_team,
                            "bowling_team": bowling_team,
                            "innings": len(innings_data.get("team", "")) + 1,  # Simple innings numbering
                            "over": over_num,
                            "ball": delivery_data.get("ball", 0),
                            "batter": batter,
                            "bowler": bowler,
                            "runs_batter": runs_batter,
                            "runs_extras": runs_extras,
                            "is_wicket": is_wicket,
                            "wicket_kind": wicket_kind
                        })
                        
                        # Add players to player set
                        player_id = batter.lower().replace(" ", "_")
                        player_set.add((player_id, batter, batter))
                        player_id = bowler.lower().replace(" ", "_")
                        player_set.add((player_id, bowler, bowler))
                        
        except Exception as e:
            print(f"[error] Failed to parse {json_file}: {e}")
            continue
    
    # Insert data
    if match_rows:
        match_df = pd.DataFrame(match_rows)
        con.execute("INSERT INTO matches SELECT * FROM match_df")
    if delivery_rows:
        delivery_df = pd.DataFrame(delivery_rows)
        con.execute("INSERT INTO deliveries SELECT * FROM delivery_df")
    if player_set:
        player_rows = [{"player_id": pid, "name": name, "cricsheet_name": cricsheet} for pid, name, cricsheet in player_set]
        player_df = pd.DataFrame(player_rows)
        con.execute("INSERT INTO players SELECT * FROM player_df")
    if squad_rows:
        squad_df = pd.DataFrame(squad_rows)
        con.execute("INSERT INTO squads SELECT * FROM squad_df")
    
    print(f"[parse] Loaded {len(match_rows)} matches, {len(delivery_rows)} deliveries, {len(player_set)} players")


def compute_tensors(con: duckdb.DuckDBPyConnection, seasons: List[int]):
    """Compute (batter, bowler, venue) tensors with fallback logic."""
    
    print("[tensors] Computing player-venue tensors...")
    
    tensors = []
    
    for season in seasons:
        print(f"[tensors] Processing season {season}...")
        
        # Compute per-triplet statistics
        query = f"""
        SELECT 
            batter,
            bowler,
            venue,
            COUNT(*) as sample_size,
            AVG(runs_batter) as avg_runs_per_ball,
            SUM(CASE WHEN is_wicket THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as dismissal_rate_per_ball,
            AVG(runs_batter + runs_extras) as economy_rate,
            SUM(CASE WHEN runs_batter >= 4 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as boundary_rate
        FROM deliveries 
        WHERE season = {season} 
          AND batter != '' 
          AND bowler != '' 
          AND venue != ''
        GROUP BY batter, bowler, venue
        """
        
        df = con.execute(query).df()
        
        # Add fallback flag
        df['is_fallback'] = df['sample_size'] < MIN_SAMPLE_SIZE
        
        # For sparse triplets, compute career averages as fallback
        career_query = f"""
        SELECT 
            batter,
            bowler,
            AVG(runs_batter) as career_avg_runs,
            SUM(CASE WHEN is_wicket THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as career_dismissal_rate,
            AVG(runs_batter + runs_extras) as career_economy,
            SUM(CASE WHEN runs_batter >= 4 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as career_boundary_rate
        FROM deliveries 
        WHERE season <= {season}
          AND batter != '' 
          AND bowler != '' 
          AND venue != ''
        GROUP BY batter, bowler
        """
        
        career_df = con.execute(career_query).df()
        
        # Merge career averages for fallback values
        df = df.merge(career_df, on=['batter', 'bowler'], how='left')
        
        # Apply fallback logic
        mask = df['is_fallback']
        df.loc[mask, 'avg_runs_per_ball'] = df.loc[mask, 'career_avg_runs']
        df.loc[mask, 'dismissal_rate_per_ball'] = df.loc[mask, 'career_dismissal_rate']
        df.loc[mask, 'economy_rate'] = df.loc[mask, 'career_economy']
        df.loc[mask, 'boundary_rate'] = df.loc[mask, 'career_boundary_rate']
        
        # Add season column with explicit type
        df['season'] = pd.Series([season] * len(df), dtype='int64')
        
        # Select final columns
        final_cols = [
            'season', 'batter', 'bowler', 'venue',
            'avg_runs_per_ball', 'dismissal_rate_per_ball', 
            'economy_rate', 'boundary_rate', 'sample_size', 'is_fallback'
        ]
        tensors.append(df[final_cols])
    
    return pd.concat(tensors, ignore_index=True)


def compute_form_ewm(con: duckdb.DuckDBPyConnection):
    """Compute exponentially weighted moving averages for player form."""
    
    print("[form] Computing EWM form metrics...")
    
    # Get player performance per match
    query = """
    SELECT 
        d.match_id,
        d.season,
        d.batter,
        d.bowler,
        SUM(d.runs_batter) as runs_scored,
        SUM(CASE WHEN d.is_wicket THEN 1 ELSE 0 END) as wickets_taken,
        COUNT(*) as balls_faced,
        COUNT(*) FILTER (WHERE d.bowling_team = d.batting_team) as balls_bowled
    FROM deliveries d
    GROUP BY d.match_id, d.season, d.batter, d.bowler
    ORDER BY d.match_id
    """
    
    df = con.execute(query).df()
    
    # Compute EWM for each player
    form_data = []
    
    for player in df['batter'].unique():
        player_df = df[df['batter'] == player].sort_values('match_id')
        
        # EWM for runs
        runs_ewm = player_df['runs_scored'].ewm(alpha=FORM_EWM_ALPHA, adjust=False).mean()
        
        for i, (_, row) in enumerate(player_df.iterrows()):
            form_data.append({
                'match_id': row['match_id'],
                'player_id': player,
                'metric_type': 'batting_runs_ewm',
                'value': runs_ewm.iloc[i] if i < len(runs_ewm) else 0
            })
    
    for player in df['bowler'].unique():
        player_df = df[df['bowler'] == player].sort_values('match_id')
        
        # EWM for wickets
        wickets_ewm = player_df['wickets_taken'].ewm(alpha=FORM_EWM_ALPHA, adjust=False).mean()
        
        for i, (_, row) in enumerate(player_df.iterrows()):
            form_data.append({
                'match_id': row['match_id'],
                'player_id': player,
                'metric_type': 'bowling_wickets_ewm',
                'value': wickets_ewm.iloc[i] if i < len(wickets_ewm) else 0
            })
    
    return pd.DataFrame(form_data)


def export_parquet(tensors_df: pd.DataFrame, form_df: pd.DataFrame, seasons: List[int]):
    """Export tensors and form data as Parquet files."""
    
    print("[export] Writing Parquet files...")
    
    TENSORS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Export tensors by season
    for season in seasons:
        season_df = tensors_df[tensors_df['season'] == season]
        season_dir = TENSORS_DIR / f"season={season}"
        season_dir.mkdir(exist_ok=True)
        
        parquet_path = season_dir / "tensors.parquet"
        table = pa.Table.from_pandas(season_df)
        pq.write_table(table, parquet_path)
        
        print(f"[export] {len(season_df)} tensors for season {season} → {parquet_path}")
    
    # Export form data
    form_dir = TENSORS_DIR / "form"
    form_dir.mkdir(exist_ok=True)
    form_path = form_dir / "form_ewm.parquet"
    
    form_table = pa.Table.from_pandas(form_df)
    pq.write_table(form_table, form_path)
    
    print(f"[export] {len(form_df)} form records → {form_path}")
    
    # Create manifest
    import datetime
    manifest = {
        "version": datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
        "bucket": os.environ.get("DATA_BUCKET", "local"),
        "prefix": "tensors/",
        "seasons": seasons,
        "total_tensors": len(tensors_df),
        "total_form_records": len(form_df)
    }
    
    manifest_path = TENSORS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[export] Manifest → {manifest_path}")


def upload_to_s3(seasons: List[int]):
    """Upload Parquet files to S3."""
    
    bucket = os.environ.get("DATA_BUCKET")
    if not bucket:
        print("[upload] DATA_BUCKET environment variable not set, skipping S3 upload")
        return
    
    print(f"[upload] Uploading to S3 bucket: {bucket}")
    
    s3 = boto3.client('s3')
    
    # Upload tensors
    for season in seasons:
        season_dir = TENSORS_DIR / f"season={season}"
        if season_dir.exists():
            for file_path in season_dir.glob("*.parquet"):
                s3_key = f"tensors/season={season}/{file_path.name}"
                try:
                    s3.upload_file(str(file_path), bucket, s3_key)
                    print(f"[upload] {file_path.name} → s3://{bucket}/{s3_key}")
                except ClientError as e:
                    print(f"[error] Failed to upload {file_path.name}: {e}")
    
    # Upload form data
    form_dir = TENSORS_DIR / "form"
    if form_dir.exists():
        for file_path in form_dir.glob("*.parquet"):
            s3_key = f"tensors/form/{file_path.name}"
            try:
                s3.upload_file(str(file_path), bucket, s3_key)
                print(f"[upload] {file_path.name} → s3://{bucket}/{s3_key}")
            except ClientError as e:
                print(f"[error] Failed to upload {file_path.name}: {e}")
    
    # Upload manifest
    manifest_path = TENSORS_DIR / "manifest.json"
    if manifest_path.exists():
        s3_key = "tensors/manifest.json"
        try:
            s3.upload_file(str(manifest_path), bucket, s3_key)
            print(f"[upload] manifest.json → s3://{bucket}/{s3_key}")
        except ClientError as e:
            print(f"[error] Failed to upload manifest: {e}")


def main():
    parser = argparse.ArgumentParser(description="Build IPL data pipeline")
    parser.add_argument("--seasons", nargs="+", type=int, required=True, 
                       help="Seasons to process (e.g., 2008 2009 2010)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Skip S3 upload")
    parser.add_argument("--upload", action="store_true", 
                       help="Upload to S3 after processing")
    
    args = parser.parse_args()
    
    if not EXTRACT_DIR.exists():
        print(f"[error] Extract directory not found: {EXTRACT_DIR}")
        print("Run: python scripts/validate_ipl_data.py")
        sys.exit(1)
    
    # Initialize DuckDB
    con = duckdb.connect(str(DUCKDB_PATH))
    
    try:
        # Load data
        load_json_to_duckdb(con)
        
        # Compute tensors
        tensors_df = compute_tensors(con, args.seasons)
        
        # Compute form metrics
        form_df = compute_form_ewm(con)
        
        # Export Parquet
        export_parquet(tensors_df, form_df, args.seasons)
        
        # Upload to S3 if requested
        if args.upload and not args.dry_run:
            upload_to_s3(args.seasons)
        elif args.dry_run:
            print("[upload] Dry run - skipping S3 upload")
        
        print(f"[done] Pipeline completed for seasons {args.seasons}")
        
    finally:
        con.close()


if __name__ == "__main__":
    main()
