"""
scripts/tests/test_tensor_computation.py
=====================================
Test tensor values are in valid ranges, no nulls in required fields.
"""

import pytest
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
TENSORS_DIR = ROOT / "data" / "tensors"


@pytest.fixture
def sample_tensors():
    """Load a sample of tensor data for testing."""
    # Try season 2008 first
    season_2008_path = TENSORS_DIR / "season=2008" / "tensors.parquet"
    if season_2008_path.exists():
        # Use pandas to read Parquet directly
        return pd.read_parquet(season_2008_path)
    
    # Fallback to any season
    for season_dir in TENSORS_DIR.glob("season=*"):
        parquet_path = season_dir / "tensors.parquet"
        if parquet_path.exists():
            return pd.read_parquet(parquet_path)
    
    pytest.skip("No tensor data found for testing")


def test_tensor_no_nulls_in_required_fields(sample_tensors):
    """Test required fields have no null values."""
    
    required_fields = [
        'season', 'batter', 'bowler', 'venue',
        'avg_runs_per_ball', 'dismissal_rate_per_ball',
        'economy_rate', 'boundary_rate', 'sample_size', 'is_fallback'
    ]
    
    for field in required_fields:
        null_count = sample_tensors[field].isnull().sum()
        assert null_count == 0, f"Field {field} has {null_count} null values"


def test_tensor_value_ranges(sample_tensors):
    """Test tensor values are in expected ranges."""
    
    # Test runs per ball (should be 0 to 6 typically)
    assert sample_tensors['avg_runs_per_ball'].min() >= 0, "avg_runs_per_ball has negative values"
    assert sample_tensors['avg_runs_per_ball'].max() <= 6, "avg_runs_per_ball exceeds 6"
    
    # Test dismissal rate (0 to 1)
    assert sample_tensors['dismissal_rate_per_ball'].min() >= 0, "dismissal_rate_per_ball has negative values"
    assert sample_tensors['dismissal_rate_per_ball'].max() <= 1, "dismissal_rate_per_ball exceeds 1"
    
    # Test boundary rate (0 to 1)
    assert sample_tensors['boundary_rate'].min() >= 0, "boundary_rate has negative values"
    assert sample_tensors['boundary_rate'].max() <= 1, "boundary_rate exceeds 1"
    
    # Test economy rate (should be reasonable)
    assert sample_tensors['economy_rate'].min() >= 0, "economy_rate has negative values"
    assert sample_tensors['economy_rate'].max() <= 36, "economy_rate exceeds 36 (6 runs/over max)"
    
    # Test sample size
    assert sample_tensors['sample_size'].min() > 0, "sample_size has zero or negative values"


def test_fallback_logic(sample_tensors):
    """Test fallback flag logic is consistent."""
    
    # Some rows should be fallback (sparse triplets)
    fallback_count = sample_tensors['is_fallback'].sum()
    total_count = len(sample_tensors)
    
    assert fallback_count < total_count, "All rows marked as fallback"
    assert fallback_count > 0, "No rows marked as fallback (unexpected)"
    
    # Check that fallback rows have reasonable values
    fallback_rows = sample_tensors[sample_tensors['is_fallback']]
    non_fallback_rows = sample_tensors[~sample_tensors['is_fallback']]
    
    # Fallback rows should generally have smaller sample sizes
    assert fallback_rows['sample_size'].max() < 30, "Fallback rows have sample_size >= 30"
    assert non_fallback_rows['sample_size'].min() >= 30, "Non-fallback rows have sample_size < 30"


def test_tensor_completeness(sample_tensors):
    """Test we have sufficient tensor coverage."""
    
    # Should have multiple seasons if processed
    unique_seasons = sample_tensors['season'].nunique()
    assert unique_seasons >= 1, f"Expected at least 1 season, got {unique_seasons}"
    
    # Should have multiple batters, bowlers, venues
    unique_batters = sample_tensors['batter'].nunique()
    unique_bowlers = sample_tensors['bowler'].nunique()
    unique_venues = sample_tensors['venue'].nunique()
    
    assert unique_batters >= 50, f"Too few unique batters: {unique_batters}"
    assert unique_bowlers >= 50, f"Too few unique bowlers: {unique_bowlers}"
    assert unique_venues >= 5, f"Too few unique venues: {unique_venues}"


def test_form_ewm_data():
    """Test form EWM data exists and has correct structure."""
    
    form_path = TENSORS_DIR / "form" / "form_ewm.parquet"
    if not form_path.exists():
        pytest.skip("Form EWM data not found")
    
    form_df = pd.read_parquet(form_path)
    
    # Check required columns
    required_cols = ['match_id', 'player_id', 'metric_type', 'value']
    for col in required_cols:
        assert col in form_df.columns, f"Missing column in form data: {col}"
    
    # Check no nulls in required fields
    for col in required_cols:
        null_count = form_df[col].isnull().sum()
        assert null_count == 0, f"Form data column {col} has {null_count} nulls"
    
    # Check metric types
    metric_types = form_df['metric_type'].unique()
    expected_types = ['batting_runs_ewm', 'bowling_wickets_ewm']
    
    for metric_type in expected_types:
        assert metric_type in metric_types, f"Missing metric type: {metric_type}"
    
    # Check value ranges
    batting_form = form_df[form_df['metric_type'] == 'batting_runs_ewm']
    bowling_form = form_df[form_df['metric_type'] == 'bowling_wickets_ewm']
    
    assert batting_form['value'].min() >= 0, "Batting form has negative values"
    assert bowling_form['value'].min() >= 0, "Bowling form has negative values"
