"""
api/models/commentary.py
=======================
CommentaryStep schema + generator for ILP solver.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from enum import Enum


class InsightType(str, Enum):
    VENUE_ENCODING = "venue_encoding"
    BIPARTITE_THREAT = "bipartite_threat"
    ILP_SOLUTION = "ilp_solution"
    MONTE_CARLO = "monte_carlo"


class CommentaryStep(BaseModel):
    step_number: int = Field(ge=1, le=4, description="Step number (1-4)")
    title: str = Field(description="Step title")
    formula: str = Field(description="Mathematical formula or rule")
    description: str = Field(description="Plain English explanation")
    insight: str = Field(description="Key insight or finding")
    insight_type: InsightType = Field(description="Type of insight")
    graph_data: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Optional graph data for visualization (step 2 only)"
    )


class CommentaryGenerator:
    """Generates CommentaryStep[4] array for ILP solutions."""
    
    @staticmethod
    def generate_venue_encoding(venue_vector: Dict[str, float]) -> CommentaryStep:
        """Step 1: Venue encoding and its implications."""
        
        alpha = venue_vector.get("batting_weight", 0.55)
        beta = venue_vector.get("bowling_weight", 0.45)
        
        return CommentaryStep(
            step_number=1,
            title="Venue Conditions Analysis",
            formula=f"α={alpha:.2f}, β={beta:.2f}, α+β=1.0",
            description=f"Venue characteristics determine the balance between batting (α) and bowling (β) optimization weights.",
            insight=f"Current venue favors {'batting' if alpha > 0.5 else 'bowling'} with α={alpha:.2f}",
            insight_type=InsightType.VENUE_ENCODING
        )
    
    @staticmethod
    def generate_bipartite_threat(
        batters: List[Dict[str, Any]], 
        bowlers: List[Dict[str, Any]], 
        edges: List[Dict[str, Any]]
    ) -> CommentaryStep:
        """Step 2: Bipartite threat graph analysis."""
        
        # Find highest threat edge
        max_threat_edge = max(edges, key=lambda x: x.get("weight", 0)) if edges else None
        max_threat_batter = max_threat_edge.get("batter_id", "") if max_threat_edge else ""
        max_threat_bowler = max_threat_edge.get("bowler_id", "") if max_threat_edge else ""
        max_threat_level = max_threat_edge.get("threat_level", "low") if max_threat_edge else "low"
        
        return CommentaryStep(
            step_number=2,
            title="Matchup Threat Analysis",
            formula="threat(batter, bowler) = f(runs, wickets, venue)",
            description="Analyzes head-to-head matchups to identify high-threat combinations.",
            insight=f"Highest threat: {max_threat_batter} vs {max_threat_bowler} ({max_threat_level} threat)",
            insight_type=InsightType.BIPARTITE_THREAT,
            graph_data={
                "batters": batters,
                "bowlers": bowlers,
                "edges": edges
            }
        )
    
    @staticmethod
    def generate_ilp_solution(
        selected_players: List[Dict[str, Any]],
        excluded_players: List[Dict[str, Any]],
        objective_value: float,
        baseline_value: float
    ) -> CommentaryStep:
        """Step 3: ILP optimization solution."""
        
        improvement = ((objective_value - baseline_value) / baseline_value) * 100 if baseline_value > 0 else 0
        
        return CommentaryStep(
            step_number=3,
            title="Optimal XI Selection",
            formula="max Σ(α·E[runs] + β·E[wkts] - γ·CI - δ·threat)·xᵢ",
            description="Integer Linear Programming selects optimal XI under constraints.",
            insight=f"Optimization improves expected performance by {improvement:.1f}% over baseline",
            insight_type=InsightType.ILP_SOLUTION
        )
    
    @staticmethod
    def generate_monte_carlo(
        win_probability: float,
        confidence_interval: tuple[float, float],
        calibration_applied: bool,
        sample_size: int = 10000
    ) -> CommentaryStep:
        """Step 4: Monte Carlo win probability simulation."""
        
        ci_lower, ci_upper = confidence_interval
        ci_width = ci_upper - ci_lower
        
        calibration_note = "with Platt scaling calibration" if calibration_applied else "without calibration"
        
        return CommentaryStep(
            step_number=4,
            title="Win Probability Simulation",
            formula=f"P(win) = Σ[simulation_outcomes] / {sample_size:,}",
            description=f"Monte Carlo simulation with {sample_size:,} rollouts estimates win probability.",
            insight=f"P(win) = {win_probability:.1%} ±{ci_width/2:.1%} (95% CI) {calibration_note}",
            insight_type=InsightType.MONTE_CARLO
        )
    
    @classmethod
    def generate_commentary(
        cls,
        venue_vector: Dict[str, float],
        batters: List[Dict[str, Any]],
        bowlers: List[Dict[str, Any]], 
        edges: List[Dict[str, Any]],
        selected_players: List[Dict[str, Any]],
        excluded_players: List[Dict[str, Any]],
        objective_value: float,
        baseline_value: float,
        win_probability: float,
        confidence_interval: tuple[float, float],
        calibration_applied: bool
    ) -> List[CommentaryStep]:
        """Generate complete CommentaryStep[4] array."""
        
        return [
            cls.generate_venue_encoding(venue_vector),
            cls.generate_bipartite_threat(batters, bowlers, edges),
            cls.generate_ilp_solution(selected_players, excluded_players, objective_value, baseline_value),
            cls.generate_monte_carlo(win_probability, confidence_interval, calibration_applied)
        ]
