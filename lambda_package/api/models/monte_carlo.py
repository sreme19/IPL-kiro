"""
api/models/monte_carlo.py
=========================
MDP state space + 10k rollout simulator for Monte Carlo.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time


@dataclass
class MatchState:
    runs: int
    wickets: int
    overs_remaining: float
    target: Optional[int] = None


@dataclass
class SimulationResult:
    win_probability: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    calibration_applied: bool
    runtime_ms: float


class MonteCarloSimulator:
    """Monte Carlo simulation for cricket match win probability."""
    
    def __init__(self):
        self.calibration_log = []
        self.cache = {}  # LRU cache for results
        
    def simulate_win_probability(
        self,
        team_tensors: Dict[str, Dict[str, float]],
        opponent_tensors: Dict[str, Dict[str, float]],
        venue_adjustments: Dict[str, float],
        target_runs: Optional[int] = None,
        sample_size: int = 10000
    ) -> SimulationResult:
        """Run Monte Carlo simulation with 10k rollouts."""
        
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(
            team_tensors, opponent_tensors, venue_adjustments, target_runs
        )
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            return cached_result
        
        # Run simulations
        results = self._run_simulations(
            team_tensors, opponent_tensors, venue_adjustments, 
            target_runs, sample_size
        )
        
        # Calculate win probability and confidence interval
        wins = np.sum(results)
        win_prob = wins / sample_size
        
        # 95% confidence interval using normal approximation
        std_error = np.sqrt((win_prob * (1 - win_prob)) / sample_size)
        ci_margin = 1.96 * std_error
        confidence_interval = (
            max(0.0, win_prob - ci_margin),
            min(1.0, win_prob + ci_margin)
        )
        
        # Apply Platt scaling if calibration data available
        calibration_applied = False
        if len(self.calibration_log) >= 3:
            win_prob = self._apply_platt_scaling(win_prob)
            calibration_applied = True
        
        runtime_ms = (time.time() - start_time) * 1000
        
        result = SimulationResult(
            win_probability=win_prob,
            confidence_interval=confidence_interval,
            sample_size=sample_size,
            calibration_applied=calibration_applied,
            runtime_ms=runtime_ms
        )
        
        # Cache result
        self.cache[cache_key] = result
        
        return result
    
    def _run_simulations(
        self,
        team_tensors: Dict[str, Dict[str, float]],
        opponent_tensors: Dict[str, Dict[str, float]],
        venue_adjustments: Dict[str, float],
        target_runs: Optional[int],
        sample_size: int
    ) -> np.ndarray:
        """Run vectorized Monte Carlo simulations."""
        
        # Initialize simulation arrays
        runs = np.zeros(sample_size, dtype=np.int32)
        wickets = np.zeros(sample_size, dtype=np.int32)
        overs = np.full(sample_size, 20.0, dtype=np.float32)  # 20 overs T20
        
        # Get team batting tensors
        team_batting_avg = self._extract_team_batting_avg(team_tensors)
        team_bowling_avg = self._extract_team_bowling_avg(opponent_tensors)
        
        # Apply venue adjustments
        batting_multiplier = venue_adjustments.get("batting_weight", 1.0)
        bowling_multiplier = venue_adjustments.get("bowling_weight", 1.0)
        
        # Vectorized simulation
        for over in range(20):  # 20 overs in T20
            # Determine which team is batting in this simulation
            # This is simplified - full implementation would alternate innings
            
            # Generate runs for this over using Poisson distribution
            expected_runs_per_ball = team_batting_avg * batting_multiplier
            runs_per_over = np.random.poisson(
                expected_runs_per_ball * 6,  # 6 balls per over
                size=sample_size
            )
            
            # Generate wickets using Bernoulli trials
            dismissal_prob = team_bowling_avg * bowling_multiplier * 0.01  # Scale down
            wickets_this_over = np.random.binomial(
                6, dismissal_prob, size=sample_size
            )
            
            # Update state
            runs += runs_per_over
            wickets += wickets_this_over
            overs -= 1.0
            
            # Check for all out (10 wickets)
            all_out_mask = wickets >= 10
            runs[all_out_mask] = runs[all_out_mask]  # Stop counting runs
            wickets[all_out_mask] = 10  # Cap at 10
            overs[all_out_mask] = 0  # No overs remaining
        
        # Determine wins (simplified - target based)
        if target_runs:
            wins = runs >= target_runs
        else:
            # Chase-based: compare runs scored
            # This is very simplified - proper implementation would simulate both innings
            opponent_runs = self._simulate_opponent_innings(
                opponent_tensors, venue_adjustments, sample_size
            )
            wins = runs > opponent_runs
        
        return wins.astype(np.float32)
    
    def _simulate_opponent_innings(
        self,
        opponent_tensors: Dict[str, Dict[str, float]],
        venue_adjustments: Dict[str, float],
        sample_size: int
    ) -> np.ndarray:
        """Simulate opponent innings for comparison."""
        
        opponent_batting_avg = self._extract_team_batting_avg(opponent_tensors)
        batting_multiplier = venue_adjustments.get("batting_weight", 1.0)
        
        # Simulate 20 overs for opponent
        total_runs = np.random.poisson(
            opponent_batting_avg * batting_multiplier * 6 * 20,  # 6 balls * 20 overs
            size=sample_size
        )
        
        return total_runs
    
    def _extract_team_batting_avg(self, team_tensors: Dict[str, Dict[str, float]]) -> float:
        """Extract average runs per ball for team."""
        
        if not team_tensors:
            return 0.8  # League average
        
        batting_values = []
        for player_data in team_tensors.values():
            if "batting_form" in player_data:
                batting_values.append(player_data["batting_form"])
        
        return np.mean(batting_values) if batting_values else 0.8
    
    def _extract_team_bowling_avg(self, team_tensors: Dict[str, Dict[str, float]]) -> float:
        """Extract average dismissal rate for team."""
        
        if not team_tensors:
            return 0.03  # League average
        
        bowling_values = []
        for player_data in team_tensors.values():
            if "bowling_form" in player_data:
                bowling_values.append(player_data["bowling_form"])
        
        return np.mean(bowling_values) if bowling_values else 0.03
    
    def _generate_cache_key(
        self,
        team_tensors: Dict[str, Dict[str, float]],
        opponent_tensors: Dict[str, Dict[str, float]],
        venue_adjustments: Dict[str, float],
        target_runs: Optional[int]
    ) -> str:
        """Generate cache key for simulation parameters."""
        
        # Create hash of input parameters
        team_hash = hash(str(sorted(team_tensors.items())))
        opponent_hash = hash(str(sorted(opponent_tensors.items())))
        venue_hash = hash(str(sorted(venue_adjustments.items())))
        target_hash = hash(target_runs) if target_runs else 0
        
        return f"{team_hash}_{opponent_hash}_{venue_hash}_{target_hash}"
    
    def _apply_platt_scaling(self, raw_probability: float) -> float:
        """Apply Platt scaling calibration to raw probability."""
        
        if len(self.calibration_log) < 3:
            return raw_probability
        
        # Extract calibration data
        predictions = [entry["predicted"] for entry in self.calibration_log]
        actuals = [entry["actual"] for entry in self.calibration_log]
        
        # Simple Platt scaling: logit transformation
        # This is a simplified version - proper implementation would fit parameters
        avg_error = np.mean([abs(p - a) for p, a in zip(predictions, actuals)])
        
        # Apply correction factor
        if avg_error > 0.1:  # Systematic overprediction
            correction_factor = 0.9
        elif avg_error < -0.1:  # Systematic underprediction
            correction_factor = 1.1
        else:
            correction_factor = 1.0
        
        # Apply correction with bounds
        corrected_prob = raw_probability * correction_factor
        return max(0.01, min(0.99, corrected_prob))
    
    def add_calibration_point(self, predicted: float, actual: float) -> None:
        """Add a calibration point for Platt scaling."""
        
        self.calibration_log.append({
            "predicted": predicted,
            "actual": actual,
            "timestamp": time.time()
        })
        
        # Keep only last 50 points
        if len(self.calibration_log) > 50:
            self.calibration_log = self.calibration_log[-50:]
    
    def get_simulation_stats(self) -> Dict[str, any]:
        """Get simulation performance statistics."""
        
        if not self.calibration_log:
            return {"status": "no_calibration_data"}
        
        predictions = [entry["predicted"] for entry in self.calibration_log]
        actuals = [entry["actual"] for entry in self.calibration_log]
        
        # Calculate metrics
        mae = np.mean([abs(p - a) for p, a in zip(predictions, actuals)])
        mse = np.mean([(p - a) ** 2 for p, a in zip(predictions, actuals)])
        rmse = np.sqrt(mse)
        
        # Calibration accuracy
        well_calibrated = sum(1 for p, a in zip(predictions, actuals) if abs(p - a) < 0.1)
        calibration_accuracy = well_calibrated / len(predictions)
        
        return {
            "total_predictions": len(predictions),
            "mean_absolute_error": mae,
            "root_mean_square_error": rmse,
            "calibration_accuracy": calibration_accuracy,
            "cache_size": len(self.cache),
            "recent_errors": [
                {"predicted": p, "actual": a, "error": p - a}
                for p, a in list(zip(predictions[-10:], actuals[-10:]))
            ]
        }
    
    def clear_cache(self) -> None:
        """Clear the simulation cache."""
        self.cache.clear()
    
    def set_cache_size_limit(self, limit: int) -> None:
        """Set cache size limit (LRU eviction)."""
        if len(self.cache) > limit:
            # Simple LRU: keep most recent entries
            items = list(self.cache.items())
            self.cache = dict(items[-limit:])
    
    def validate_simulation_parameters(
        self,
        team_tensors: Dict[str, Dict[str, float]],
        opponent_tensors: Dict[str, Dict[str, float]],
        sample_size: int
    ) -> Dict[str, any]:
        """Validate simulation parameters before running."""
        
        validation = {"valid": True, "errors": []}
        
        # Check sample size
        if sample_size <= 0:
            validation["valid"] = False
            validation["errors"].append("Sample size must be positive")
        elif sample_size > 100000:
            validation["valid"] = False
            validation["errors"].append("Sample size too large (max 100,000)")
        
        # Check team tensors
        if not team_tensors:
            validation["valid"] = False
            validation["errors"].append("Team tensors cannot be empty")
        
        if not opponent_tensors:
            validation["valid"] = False
            validation["errors"].append("Opponent tensors cannot be empty")
        
        # Check tensor values are reasonable
        for team_name, tensors in [("team", team_tensors), ("opponent", opponent_tensors)]:
            for player_id, player_data in tensors.items():
                if "batting_form" in player_data:
                    batting_form = player_data["batting_form"]
                    if batting_form < 0 or batting_form > 5:
                        validation["valid"] = False
                        validation["errors"].append(
                            f"Invalid batting form {batting_form} for {team_name} player {player_id}"
                        )
                
                if "bowling_form" in player_data:
                    bowling_form = player_data["bowling_form"]
                    if bowling_form < 0 or bowling_form > 5:
                        validation["valid"] = False
                        validation["errors"].append(
                            f"Invalid bowling form {bowling_form} for {team_name} player {player_id}"
                        )
        
        return validation
