"""
scripts/tests/test_fallback_flagging.py
=====================================
Test sparse triplets correctly flagged is_fallback=True.
"""

import pytest
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
TENSORS_DIR = ROOT / "data" / "tensors"
MIN_SAMPLE_SIZE = 30


@pytest.fixture
def sample_tensors():
    """Load a sample of tensor data for testing."""
    # Try season 2008 first
    season_2008_path = TENSORS_DIR / "season=2008" / "tensors.parquet"
    if season_2008_path.exists():
        return pd.read_parquet(season_2008_path)
    
    # Fallback to any season
    for season_dir in TENSORS_DIR.glob("season=*"):
        parquet_path = season_dir / "tensors.parquet"
        if parquet_path.exists():
            return pd.read_parquet(parquet_path)
    
    pytest.skip("No tensor data found for testing")


def test_fallback_flag_consistency(sample_tensors):
    """Test fallback flag is consistent with sample_size threshold."""
    
    # Rows with sample_size < MIN_SAMPLE_SIZE should be flagged as fallback
    should_be_fallback = sample_tensors['sample_size'] < MIN_SAMPLE_SIZE
    actual_fallback = sample_tensors['is_fallback']
    
    mismatched = sample_tensors[should_be_fallback != actual_fallback]
    assert len(mismatched) == 0, f"Found {len(mismatched)} rows with inconsistent fallback flagging"


def test_fallback_distribution(sample_tensors):
    """Test fallback distribution is reasonable."""
    
    total_rows = len(sample_tensors)
    fallback_rows = sample_tensors['is_fallback'].sum()
    fallback_rate = fallback_rows / total_rows
    
    # Should have some fallback rows (sparse data)
    assert fallback_rows > 0, "No fallback rows found"
    
    # But not too many (should have sufficient dense data)
    assert fallback_rate < 0.9, f"Too many fallback rows: {fallback_rate:.2%}"
    
    print(f"Fallback rate: {fallback_rate:.2%} ({fallback_rows}/{total_rows} rows)")


def test_fallback_rows_have_career_data(sample_tensors):
    """Test fallback rows have reasonable career averages."""
    
    fallback_rows = sample_tensors[sample_tensors['is_fallback']]
    
    # Should have valid values (not NaN)
    assert not fallback_rows['avg_runs_per_ball'].isnull().any(), "Fallback rows have null runs"
    assert not fallback_rows['dismissal_rate_per_ball'].isnull().any(), "Fallback rows have null dismissal rate"
    assert not fallback_rows['economy_rate'].isnull().any(), "Fallback rows have null economy"
    assert not fallback_rows['boundary_rate'].isnull().any(), "Fallback rows have null boundary rate"
    
    # Values should be in reasonable ranges
    assert (fallback_rows['avg_runs_per_ball'] >= 0).all(), "Fallback rows have negative runs"
    assert (fallback_rows['dismissal_rate_per_ball'] >= 0).all(), "Fallback rows have negative dismissal rate"
    assert (fallback_rows['economy_rate'] >= 0).all(), "Fallback rows have negative economy"
    assert (fallback_rows['boundary_rate'] >= 0).all(), "Fallback rows have negative boundary rate"


def test_non_fallback_rows_have_sufficient_data(sample_tensors):
    """Test non-fallback rows have sufficient sample size."""
    
    non_fallback_rows = sample_tensors[~sample_tensors['is_fallback']]
    
    # All should have sample_size >= MIN_SAMPLE_SIZE
    assert (non_fallback_rows['sample_size'] >= MIN_SAMPLE_SIZE).all(), \
        f"Non-fallback rows have insufficient sample size (< {MIN_SAMPLE_SIZE})"


def test_fallback_vs_non_fallback_quality(sample_tensors):
    """Test that fallback and non-fallback have different data quality characteristics."""
    
    fallback_rows = sample_tensors[sample_tensors['is_fallback']]
    non_fallback_rows = sample_tensors[~sample_tensors['is_fallback']]
    
    # Non-fallback should have higher average sample size
    assert non_fallback_rows['sample_size'].mean() > fallback_rows['sample_size'].mean(), \
        "Non-fallback rows should have higher average sample size"
    
    # Both should have valid ranges
    for df, name in [(fallback_rows, "fallback"), (non_fallback_rows, "non-fallback")]:
        assert (df['avg_runs_per_ball'] >= 0).all(), f"{name} rows have negative runs"
        assert (df['avg_runs_per_ball'] <= 6).all(), f"{name} rows have runs > 6"
        assert (df['dismissal_rate_per_ball'] >= 0).all(), f"{name} rows have negative dismissal rate"
        assert (df['dismissal_rate_per_ball'] <= 1).all(), f"{name} rows have dismissal rate > 1"
