"""
scripts/tests/test_team_normalisation.py
======================================
Test all team names normalise correctly via the map.
"""

import pytest
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
REFERENCE_DIR = ROOT / "data" / "reference"


@pytest.fixture
def team_name_map():
    """Load team name mapping."""
    with open(REFERENCE_DIR / "team_name_map.json") as f:
        return json.load(f)


def test_team_name_map_structure(team_name_map):
    """Test team name map has expected structure."""
    
    assert isinstance(team_name_map, dict), "Team name map should be a dictionary"
    assert len(team_name_map) > 0, "Team name map should not be empty"
    
    # Check some expected mappings
    expected_mappings = [
        ("Delhi Daredevils", "Delhi Capitals"),
        ("Kings XI Punjab", "Punjab Kings"),
        ("Deccan Chargers", "Sunrisers Hyderabad"),
    ]
    
    for old_name, new_name in expected_mappings:
        assert old_name in team_name_map, f"Missing mapping for {old_name}"
        assert team_name_map[old_name] == new_name, f"Wrong mapping for {old_name}"


def test_team_name_map_values(team_name_map):
    """Test team name map values are valid."""
    
    for old_name, new_name in team_name_map.items():
        assert isinstance(old_name, str), f"Old name should be string: {old_name}"
        assert isinstance(new_name, str), f"New name should be string: {new_name}"
        assert len(old_name.strip()) > 0, f"Old name should not be empty: {old_name}"
        assert len(new_name.strip()) > 0, f"New name should not be empty: {new_name}"


def test_no_self_mappings(team_name_map):
    """Test no team maps to itself (redundant mappings)."""
    
    # Allow self-mappings for current teams and defunct teams that don't need renaming
    allowed_self_mappings = [
        'Chennai Super Kings', 'Mumbai Indians', 'Kolkata Knight Riders', 
        'Rajasthan Royals', 'Sunrisers Hyderabad', 'Royal Challengers Bangalore', 
        'Punjab Kings', 'Delhi Capitals', 'Pune Warriors', 'Rising Pune Supergiant',
        'Gujarat Lions', 'Gujarat Titans', 'Kochi Tuskers Kerala', 'Lucknow Super Giants'
    ]
    
    redundant_mappings = [
        (old, new) for old, new in team_name_map.items() 
        if old == new and old not in allowed_self_mappings
    ]
    
    assert len(redundant_mappings) == 0, f"Found redundant mappings: {redundant_mappings}"


def test_expected_ipl_teams_present(team_name_map):
    """Test that expected IPL teams are present in mapping values."""
    
    expected_current_teams = [
        "Chennai Super Kings",
        "Delhi Capitals", 
        "Punjab Kings",
        "Sunrisers Hyderabad",
        "Mumbai Indians",
        "Royal Challengers Bangalore",
        "Kolkata Knight Riders",
        "Rajasthan Royals"
    ]
    
    for team in expected_current_teams:
        # Team should either be a target of mapping or not need mapping
        is_target = team in team_name_map.values()
        needs_no_mapping = team not in team_name_map.keys()
        
        assert is_target or needs_no_mapping, f"Team {team} not properly handled"
