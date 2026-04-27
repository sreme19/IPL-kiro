"""
api/tests/test_monte_carlo.py
===============================
Monte Carlo output validation: P(win) in [0,1], CI[0] < CI[1].
"""

import pytest
import numpy as np
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models.monte_carlo import MonteCarloSimulator

pytestmark = pytest.mark.unit


class TestMonteCarlo:
    """Test Monte Carlo simulation outputs are valid."""
    
    @pytest.fixture
    def simulator(self):
        """Monte Carlo simulator instance."""
        return MonteCarloSimulator()
    
    @pytest.fixture
    def sample_team_tensors(self):
        """Sample team tensor data."""
        return {
            "player_1": {"batting_form": 1.2, "bowling_form": 0.8},
            "player_2": {"batting_form": 0.9, "bowling_form": 1.1},
            "player_3": {"batting_form": 1.0, "bowling_form": 1.0},
            "player_4": {"batting_form": 1.1, "bowling_form": 0.9},
            "player_5": {"batting_form": 0.8, "bowling_form": 1.2}
        }
    
    @pytest.fixture
    def sample_opponent_tensors(self):
        """Sample opponent tensor data."""
        return {
            "opp_1": {"batting_form": 1.0, "bowling_form": 1.0},
            "opp_2": {"batting_form": 0.9, "bowling_form": 1.1},
            "opp_3": {"batting_form": 1.1, "bowling_form": 0.9}
        }
    
    @pytest.fixture
    def venue_adjustments(self):
        """Sample venue adjustments."""
        return {
            "batting_weight": 0.55,
            "bowling_weight": 0.45
        }
    
    def test_win_probability_in_range(self, simulator, sample_team_tensors, sample_opponent_tensors, venue_adjustments):
        """Test: P(win) in [0.0, 1.0] for all inputs."""
        
        result = simulator.simulate_win_probability(
            team_tensors=sample_team_tensors,
            opponent_tensors=sample_opponent_tensors,
            venue_adjustments=venue_adjustments
        )
        
        assert 0.0 <= result.win_probability <= 1.0, \
            f"Win probability {result.win_probability} not in [0.0, 1.0]"
    
    def test_confidence_interval_valid(self, simulator, sample_team_tensors, sample_opponent_tensors, venue_adjustments):
        """Test: CI[0] < CI[1] always."""
        
        result = simulator.simulate_win_probability(
            team_tensors=sample_team_tensors,
            opponent_tensors=sample_opponent_tensors,
            venue_adjustments=venue_adjustments
        )
        
        ci_lower, ci_upper = result.confidence_interval
        assert ci_lower < ci_upper, \
            f"CI lower bound {ci_lower} not less than upper bound {ci_upper}"
        
        assert 0.0 <= ci_lower <= 1.0, \
            f"CI lower bound {ci_lower} not in [0.0, 1.0]"
        
        assert 0.0 <= ci_upper <= 1.0, \
            f"CI upper bound {ci_upper} not in [0.0, 1.0]"
    
    def test_sample_size_positive(self, simulator, sample_team_tensors, sample_opponent_tensors, venue_adjustments):
        """Test: sample_size > 0."""
        
        result = simulator.simulate_win_probability(
            team_tensors=sample_team_tensors,
            opponent_tensors=sample_opponent_tensors,
            venue_adjustments=venue_adjustments
        )
        
        assert result.sample_size > 0, \
            f"Sample size {result.sample_size} must be positive"
    
    def test_default_sample_size(self, simulator, sample_team_tensors, sample_opponent_tensors, venue_adjustments):
        """Test: default sample size is 10,000."""
        
        result = simulator.simulate_win_probability(
            team_tensors=sample_team_tensors,
            opponent_tensors=sample_opponent_tensors,
            venue_adjustments=venue_adjustments
        )
        
        assert result.sample_size == 10000, \
            f"Expected default sample size 10000, got {result.sample_size}"
    
    def test_runtime_under_limit(self, simulator, sample_team_tensors, sample_opponent_tensors, venue_adjustments):
        """Test: 10k rollouts complete in < 3s."""
        
        import time
        start_time = time.time()
        
        result = simulator.simulate_win_probability(
            team_tensors=sample_team_tensors,
            opponent_tensors=sample_opponent_tensors,
            venue_adjustments=venue_adjustments
        )
        
        runtime = result.runtime_ms
        assert runtime < 3000, \
            f"Expected runtime < 3000ms, got {runtime}ms"
    
    def test_platt_scaling_applied(self, simulator, sample_team_tensors, sample_opponent_tensors, venue_adjustments):
        """Test: Platt-corrected probability is between 0 and 1."""
        
        # Add calibration points to trigger Platt scaling
        simulator.add_calibration_point(predicted=0.6, actual=1.0)
        simulator.add_calibration_point(predicted=0.4, actual=0.0)
        simulator.add_calibration_point(predicted=0.7, actual=1.0)
        
        result = simulator.simulate_win_probability(
            team_tensors=sample_team_tensors,
            opponent_tensors=sample_opponent_tensors,
            venue_adjustments=venue_adjustments
        )
        
        assert result.calibration_applied, \
            "Platt scaling should be applied with 3+ calibration points"
    
    def test_cache_functionality(self, simulator, sample_team_tensors, sample_opponent_tensors, venue_adjustments):
        """Test: caching works for identical inputs."""
        
        # First run
        start_time = time.time()
        result1 = simulator.simulate_win_probability(
            team_tensors=sample_team_tensors,
            opponent_tensors=sample_opponent_tensors,
            venue_adjustments=venue_adjustments
        )
        first_runtime = result1.runtime_ms
        
        # Second run with same inputs (should hit cache)
        start_time = time.time()
        result2 = simulator.simulate_win_probability(
            team_tensors=sample_team_tensors,
            opponent_tensors=sample_opponent_tensors,
            venue_adjustments=venue_adjustments
        )
        second_runtime = result2.runtime_ms
        
        # Results should be identical (cache working)
        assert result1.win_probability == result2.win_probability, \
            "Cached results should be identical"
        
        assert result1.confidence_interval == result2.confidence_interval, \
            "Cached confidence intervals should be identical"
    
    def test_parameter_validation(self, simulator):
        """Test: parameter validation works correctly."""
        
        # Test invalid sample size
        validation = simulator.validate_simulation_parameters(
            team_tensors={},
            opponent_tensors={},
            sample_size=-1
        )
        
        assert not validation["valid"], \
            "Negative sample size should be invalid"
        
        assert "Sample size must be positive" in validation["errors"], \
            "Should report sample size error"
        
        # Test empty team tensors
        validation = simulator.validate_simulation_parameters(
            team_tensors={},
            opponent_tensors={"opp_1": {"batting_form": 1.0}},
            sample_size=1000
        )
        
        assert not validation["valid"], \
            "Empty team tensors should be invalid"
        
        assert "Team tensors cannot be empty" in validation["errors"], \
            "Should report empty team tensors error"
        
        # Test invalid form values
        validation = simulator.validate_simulation_parameters(
            team_tensors={"player_1": {"batting_form": -1.0}},
            opponent_tensors={"opp_1": {"batting_form": 1.0}},
            sample_size=1000
        )
        
        assert not validation["valid"], \
            "Negative batting form should be invalid"
        
        # Test large sample size
        validation = simulator.validate_simulation_parameters(
            team_tensors={"player_1": {"batting_form": 1.0}},
            opponent_tensors={"opp_1": {"batting_form": 1.0}},
            sample_size=200000
        )
        
        assert not validation["valid"], \
            "Sample size > 100,000 should be invalid"
        
        assert any("Sample size too large" in error for error in validation["errors"]), \
            "Should report sample size too large error"
    
    def test_simulation_statistics(self, simulator, sample_team_tensors, sample_opponent_tensors, venue_adjustments):
        """Test: simulation statistics are computed correctly."""
        
        # Add some calibration points
        simulator.add_calibration_point(predicted=0.6, actual=0.8)
        simulator.add_calibration_point(predicted=0.4, actual=0.3)
        simulator.add_calibration_point(predicted=0.7, actual=0.9)
        
        # Get stats
        stats = simulator.get_simulation_stats()
        
        assert stats["total_predictions"] == 3, \
            f"Expected 3 predictions, got {stats['total_predictions']}"
        
        assert "mean_absolute_error" in stats, \
            "MAE should be computed"
        
        assert "root_mean_square_error" in stats, \
            "RMSE should be computed"
        
        assert "calibration_accuracy" in stats, \
            "Calibration accuracy should be computed"
        
        assert 0.0 <= stats["mean_absolute_error"] <= 1.0, \
            f"MAE {stats['mean_absolute_error']} should be in [0,1]"
        
        assert 0.0 <= stats["calibration_accuracy"] <= 1.0, \
            f"Calibration accuracy {stats['calibration_accuracy']} should be in [0,1]"
    
    def test_cache_management(self, simulator):
        """Test: cache size limits work correctly."""
        
        # Add some items to cache
        simulator.clear_cache()
        
        # Set cache limit
        simulator.set_cache_size_limit(5)
        
        # Add more items than limit
        for i in range(10):
            simulator.simulate_win_probability(
                team_tensors={"player": {"batting_form": 1.0}},
                opponent_tensors={"opp": {"batting_form": 1.0}},
                venue_adjustments={"batting_weight": 0.5}
            )
        
        stats = simulator.get_simulation_stats()
        assert stats.get("cache_size", 0) <= 5, \
            f"Cache size {stats.get('cache_size', 0)} should not exceed limit 5"
        
        # Clear cache
        simulator.clear_cache()
        stats_after_clear = simulator.get_simulation_stats()
        assert stats_after_clear.get("cache_size", 0) == 0, \
            "Cache should be empty after clear"
