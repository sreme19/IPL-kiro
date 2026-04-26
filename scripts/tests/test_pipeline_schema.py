"""
scripts/tests/test_pipeline_schema.py
===================================
Test DuckDB table schemas match expected structure.
"""

import pytest
import duckdb
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DUCKDB_PATH = ROOT / "data" / "ipl.duckdb"


@pytest.fixture(scope="module")
def con():
    """DuckDB connection fixture."""
    return duckdb.connect(str(DUCKDB_PATH))


def test_matches_table_schema(con):
    """Test matches table has expected columns and data types."""
    
    # Check table exists
    result = con.execute("SHOW TABLES").fetchall()
    table_names = [row[0] for row in result]
    assert "matches" in table_names
    
    # Check schema
    schema = con.execute("DESCRIBE matches").fetchall()
    columns = {row[0]: row[1] for row in schema}
    
    expected_columns = {
        "match_id": "VARCHAR",
        "season": "INTEGER", 
        "date": "DATE",
        "venue": "VARCHAR",
        "team_1": "VARCHAR",
        "team_2": "VARCHAR", 
        "winner": "VARCHAR",
        "toss_winner": "VARCHAR",
        "toss_decision": "VARCHAR"
    }
    
    for col, expected_type in expected_columns.items():
        assert col in columns, f"Column {col} missing from matches table"
        assert expected_type in columns[col], f"Column {col} has wrong type: {columns[col]}"
    
    # Check data integrity
    count = con.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    assert count > 0, "matches table is empty"
    
    # Check season range
    seasons = con.execute("SELECT DISTINCT season FROM matches ORDER BY season").fetchall()
    season_list = [row[0] for row in seasons]
    assert 2008 in season_list, "Season 2008 not found"
    assert 2016 in season_list, "Season 2016 not found"


def test_deliveries_table_schema(con):
    """Test deliveries table has expected columns and data types."""
    
    # Check table exists
    result = con.execute("SHOW TABLES").fetchall()
    table_names = [row[0] for row in result]
    assert "deliveries" in table_names
    
    # Check schema
    schema = con.execute("DESCRIBE deliveries").fetchall()
    columns = {row[0]: row[1] for row in schema}
    
    expected_columns = {
        "match_id": "VARCHAR",
        "season": "INTEGER",
        "venue": "VARCHAR", 
        "batting_team": "VARCHAR",
        "bowling_team": "VARCHAR",
        "innings": "INTEGER",
        "over": "INTEGER",
        "ball": "INTEGER",
        "batter": "VARCHAR",
        "bowler": "VARCHAR",
        "runs_batter": "INTEGER",
        "runs_extras": "INTEGER",
        "is_wicket": "BOOLEAN",
        "wicket_kind": "VARCHAR"
    }
    
    for col, expected_type in expected_columns.items():
        assert col in columns, f"Column {col} missing from deliveries table"
        assert expected_type in columns[col], f"Column {col} has wrong type: {columns[col]}"
    
    # Check data integrity
    count = con.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0]
    assert count > 100000, "deliveries table seems too small"
    
    # Check for valid runs values
    max_runs = con.execute("SELECT MAX(runs_batter) FROM deliveries").fetchone()[0]
    assert max_runs <= 6, f"Invalid runs_batter value: {max_runs}"


def test_players_table_schema(con):
    """Test players table has expected columns and data types."""
    
    # Check table exists
    result = con.execute("SHOW TABLES").fetchall()
    table_names = [row[0] for row in result]
    assert "players" in table_names
    
    # Check schema
    schema = con.execute("DESCRIBE players").fetchall()
    columns = {row[0]: row[1] for row in schema}
    
    expected_columns = {
        "player_id": "VARCHAR",
        "name": "VARCHAR",
        "cricsheet_name": "VARCHAR"
    }
    
    for col, expected_type in expected_columns.items():
        assert col in columns, f"Column {col} missing from players table"
        assert expected_type in columns[col], f"Column {col} has wrong type: {columns[col]}"
    
    # Check data integrity
    count = con.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    assert count > 100, "players table seems too small"


def test_squads_table_schema(con):
    """Test squads table has expected columns and data types."""
    
    # Check table exists
    result = con.execute("SHOW TABLES").fetchall()
    table_names = [row[0] for row in result]
    assert "squads" in table_names
    
    # Check schema
    schema = con.execute("DESCRIBE squads").fetchall()
    columns = {row[0]: row[1] for row in schema}
    
    expected_columns = {
        "team": "VARCHAR",
        "season": "INTEGER",
        "player_id": "VARCHAR",
        "is_overseas": "BOOLEAN"
    }
    
    for col, expected_type in expected_columns.items():
        assert col in columns, f"Column {col} missing from squads table"
        assert expected_type in columns[col], f"Column {col} has wrong type: {columns[col]}"
    
    # Check data integrity
    count = con.execute("SELECT COUNT(*) FROM squads").fetchone()[0]
    assert count > 0, "squads table is empty"
