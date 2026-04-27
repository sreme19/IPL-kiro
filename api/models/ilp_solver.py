"""
api/models/ilp_solver.py
=======================
PuLP ILP + CommentaryStep[4] generation for optimal XI selection.
"""

import pulp
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

from .schemas import Player, PlayerRole
from .commentary import CommentaryGenerator, CommentaryStep


@dataclass
class OptimizationResult:
    selected_xi: List[Player]
    commentary_steps: List[CommentaryStep]
    objective_value: float
    baseline_value: float
    improvement_pct: float
    solve_time_ms: float


class ILPSolver:
    """Integer Linear Programming solver for optimal cricket XI selection."""
    
    def __init__(self):
        self.model = None
        self.player_vars = {}
        self.solve_time = 0.0
    
    def solve_optimal_xi(
        self,
        squad: List[Player],
        venue_weights: Dict[str, float],
        formation_bias: str = "balanced",
        must_include: List[str] = None,
        must_exclude: List[str] = None,
        tensors: Dict[str, Dict[str, Any]] = None
    ) -> OptimizationResult:
        """Solve ILP for optimal XI selection."""
        
        import time
        start_time = time.time()
        
        # Initialize model
        self.model = pulp.LpProblem("IPL_XI_Optimization", pulp.LpMaximize)
        self.player_vars.clear()
        
        # Set formation weights
        alpha, beta = self._get_formation_weights(formation_bias)
        
        # Create decision variables
        self._create_decision_variables(squad, must_include, must_exclude)
        
        # Add constraints
        self._add_role_constraints(squad)
        self._add_team_size_constraint()
        
        # Set objective
        baseline_value = self._calculate_baseline_xi(squad, alpha, beta)
        objective_value = self._set_objective(squad, tensors, alpha, beta)
        
        # Solve model
        solve_start = time.time()
        self.model.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=5))
        self.solve_time = (time.time() - solve_start) * 1000  # Convert to ms
        
        # Extract solution
        selected_players = self._extract_solution(squad)
        
        # Generate commentary
        commentary_steps = self._generate_commentary(
            squad, selected_players, venue_weights, alpha, beta,
            objective_value, baseline_value, tensors
        )
        
        improvement = ((objective_value - baseline_value) / baseline_value * 100) if baseline_value > 0 else 0
        
        return OptimizationResult(
            selected_xi=selected_players,
            commentary_steps=commentary_steps,
            objective_value=objective_value,
            baseline_value=baseline_value,
            improvement_pct=improvement,
            solve_time_ms=self.solve_time
        )
    
    def _get_formation_weights(self, formation_bias: str) -> Tuple[float, float]:
        """Get α (batting) and β (bowling) weights for formation."""
        
        if formation_bias == "batting":
            return 0.65, 0.35  # α=0.65, β=0.35
        elif formation_bias == "bowling":
            return 0.35, 0.65  # α=0.35, β=0.65
        else:  # balanced
            return 0.55, 0.45  # α=0.55, β=0.45
    
    def _create_decision_variables(
        self,
        squad: List[Player],
        must_include: List[str],
        must_exclude: List[str]
    ) -> None:
        """Create binary decision variables for each player."""
        
        for player in squad:
            var_name = f"x_{player.player_id}"
            
            # Create binary variable
            var = pulp.LpVariable(var_name, cat="Binary")
            self.player_vars[player.player_id] = var
            
            # Apply user locks
            if must_include and player.player_id in must_include:
                # Force inclusion: x_i = 1
                self.model += var == 1, f"must_include_{player.player_id}"
            
            if must_exclude and player.player_id in must_exclude:
                # Force exclusion: x_i = 0
                self.model += var == 0, f"must_exclude_{player.player_id}"
    
    def _add_role_constraints(self, squad: List[Player]) -> None:
        """Add role-based constraints."""
        
        # Get players by role
        wicket_keepers = [p for p in squad if p.role == PlayerRole.WICKET_KEEPER]
        bowlers = [p for p in squad if p.role == PlayerRole.BOWLER]
        all_rounders = [p for p in squad if p.role == PlayerRole.ALL_ROUNDER]
        
        # Constraint 1: Exactly 11 players total
        self.model += (
            pulp.lpSum(self.player_vars[p.player_id] for p in squad) == 11,
            "constraint_total_players"
        )
        
        # Constraint 2: At least 1 wicket keeper
        if wicket_keepers:
            self.model += (
                pulp.lpSum(self.player_vars[p.player_id] for p in wicket_keepers) >= 1,
                "constraint_min_wicket_keeper"
            )
        
        # Constraint 3: At least 4 bowlers (including all-rounders)
        bowling_players = bowlers + all_rounders
        if bowling_players:
            self.model += (
                pulp.lpSum(self.player_vars[p.player_id] for p in bowling_players) >= 4,
                "constraint_min_bowlers"
            )
        
        # Constraint 4: Maximum 4 overseas players
        overseas_players = [p for p in squad if p.is_overseas]
        if overseas_players:
            self.model += (
                pulp.lpSum(self.player_vars[p.player_id] for p in overseas_players) <= 4,
                "constraint_max_overseas_players"
            )
    
    def _add_team_size_constraint(self) -> None:
        """Add constraint for exactly 11 players."""
        
        self.model += (
            pulp.lpSum(self.player_vars.values()) == 11,
            "constraint_exactly_11_players"
        )
    
    def _calculate_baseline_xi(
        self,
        squad: List[Player],
        alpha: float,
        beta: float
    ) -> float:
        """Calculate baseline XI (top performers by simple metrics)."""
        
        # Sort by combined expected runs + wickets
        scored_players = sorted(
            squad,
            key=lambda p: alpha * p.expected_runs + beta * p.expected_wickets,
            reverse=True
        )
        
        # Take top 11 respecting role constraints
        baseline_xi = self._select_feasible_xi(scored_players, squad)
        
        return sum(
            alpha * p.expected_runs + beta * p.expected_wickets
            for p in baseline_xi
        )
    
    def _select_feasible_xi(self, ranked_players: List[Player], squad: List[Player]) -> List[Player]:
        """Select a feasible XI from ranked players."""
        
        selected = []
        wicket_keepers = [p for p in squad if p.role == PlayerRole.WICKET_KEEPER]
        bowlers = [p for p in squad if p.role in [PlayerRole.BOWLER, PlayerRole.ALL_ROUNDER]]
        
        # First, pick best wicket keeper
        for player in ranked_players:
            if player.role == PlayerRole.WICKET_KEEPER and player.player_id not in [p.player_id for p in selected]:
                selected.append(player)
                break
        
        # Then fill with best available players, ensuring bowling requirements
        for player in ranked_players:
            if player.player_id not in [p.player_id for p in selected]:
                selected.append(player)
                
                # Check if we have enough bowlers
                current_bowlers = [p for p in selected if p.role in [PlayerRole.BOWLER, PlayerRole.ALL_ROUNDER]]
                remaining_slots = 11 - len(selected)
                
                # If we're close to full but don't have enough bowlers, skip this player
                if len(selected) >= 10 and len(current_bowlers) < 4:
                    selected.pop()
                    continue
                
                if len(selected) >= 11:
                    break
        
        return selected[:11]
    
    def _set_objective(
        self,
        squad: List[Player],
        tensors: Dict[str, Dict[str, Any]],
        alpha: float,
        beta: float
    ) -> float:
        """Set objective function for ILP."""
        
        # Objective: max Σ(α·E[runs] + β·E[wkts] - γ·CI_width - δ·threat)·x_i
        gamma = 0.1  # Confidence interval weight
        delta = 0.05  # Threat weight
        
        objective_terms = []
        
        for player in squad:
            if player.player_id in self.player_vars:
                # Base expected value
                expected_value = alpha * player.expected_runs + beta * player.expected_wickets
                
                # Add threat penalty (if tensors available)
                threat_penalty = 0.0
                if tensors and player.player_id in tensors:
                    player_tensors = tensors[player.player_id].get("base_tensors", {})
                    # Average threat across all matchups
                    total_threat = 0.0
                    threat_count = 0
                    
                    for opponent_id, matchup_data in player_tensors.items():
                        if "as_batsman" in matchup_data:
                            # Threat when this player is batting
                            batting_data = matchup_data["as_batsman"]
                            # Higher dismissal rate = higher threat
                            threat_penalty += batting_data.get("dismissal_rate_per_ball", 0.03) * delta
                            threat_count += 1
                    
                    if threat_count > 0:
                        threat_penalty = total_threat / threat_count
                
                # Confidence interval penalty based on form variance
                ci_penalty = gamma * (1.0 - player.form_score) * 0.2
                
                # Total objective coefficient for this player
                player_objective = expected_value - ci_penalty - threat_penalty
                
                objective_terms.append(
                    self.player_vars[player.player_id] * player_objective
                )
        
        # Set objective
        self.model += pulp.lpSum(objective_terms), "maximize_expected_performance"
        
        # Return expected objective value for commentary
        return sum(
            alpha * p.expected_runs + beta * p.expected_wickets
            for p in squad[:11]  # Approximate
        )
    
    def _extract_solution(self, squad: List[Player]) -> List[Player]:
        """Extract selected players from solved ILP."""
        
        selected_players = []
        
        for player in squad:
            if player.player_id in self.player_vars:
                var = self.player_vars[player.player_id]
                if pulp.value(var) == 1:
                    selected_players.append(player)
        
        return selected_players
    
    def _generate_commentary(
        self,
        squad: List[Player],
        selected_players: List[Player],
        venue_weights: Dict[str, float],
        alpha: float,
        beta: float,
        objective_value: float,
        baseline_value: float,
        tensors: Dict[str, Dict[str, Any]]
    ) -> List[CommentaryStep]:
        """Generate CommentaryStep[4] array."""
        
        generator = CommentaryGenerator()
        
        # Step 1: Venue encoding
        step1 = generator.generate_venue_encoding(venue_weights)
        
        # Step 2: Bipartite threat graph
        # Simplified for now - would be enhanced with actual graph data
        batters_data = [
            {"id": p.player_id, "name": p.name, "role": p.role.value}
            for p in selected_players if p.role in [PlayerRole.BATSMAN, PlayerRole.ALL_ROUNDER, PlayerRole.WICKET_KEEPER]
        ]
        
        bowlers_data = [
            {"id": p.player_id, "name": p.name, "role": p.role.value}
            for p in selected_players if p.role in [PlayerRole.BOWLER, PlayerRole.ALL_ROUNDER]
        ]
        
        # Generate sample edges (simplified)
        edges = []
        for i, batter in enumerate(batters_data):
            for j, bowler in enumerate(bowlers_data):
                # Sample threat calculation
                threat_score = np.random.beta(2, 5)  # Random threat for demo
                threat_level = "high" if threat_score > 0.7 else "medium" if threat_score > 0.4 else "low"
                
                edges.append({
                    "batter_id": batter["id"],
                    "bowler_id": bowler["id"],
                    "weight": float(threat_score),
                    "threat_level": threat_level
                })
        
        step2 = generator.generate_bipartite_threat(batters_data, bowlers_data, edges)
        
        # Step 3: ILP solution
        excluded_players = [p for p in squad if p not in selected_players]
        selected_data = [
            {"id": p.player_id, "name": p.name, "role": p.role.value}
            for p in selected_players
        ]
        excluded_data = [
            {"id": p.player_id, "name": p.name, "role": p.role.value}
            for p in excluded_players
        ]
        
        step3 = generator.generate_ilp_solution(
            selected_data, excluded_data, objective_value, baseline_value
        )
        
        # Step 4: Monte Carlo (will be updated by Monte Carlo agent with actual results)
        step4 = generator.generate_monte_carlo(
            win_probability=0.5,  # Initial estimate, will be updated
            confidence_interval=(0.45, 0.55),
            calibration_applied=False
        )
        
        return [step1, step2, step3, step4]
    
    def get_solve_status(self) -> Dict[str, Any]:
        """Get solve status and statistics."""
        
        if not self.model:
            return {"status": "not_solved"}
        
        status = pulp.LpStatus[self.model.status]
        
        return {
            "status": status,
            "objective_value": pulp.value(self.model.objective),
            "solve_time_ms": self.solve_time,
            "variables_count": len(self.player_vars),
            "constraints_count": len(self.model.constraints),
            "is_optimal": status == "Optimal"
        }
