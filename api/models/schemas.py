"""
api/models/schemas.py
====================
All Pydantic request/response models for the IPL Captain Simulator.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum


class PlayerRole(str, Enum):
    BATSMAN = "batsman"
    BOWLER = "bowler"
    ALL_ROUNDER = "all_rounder"
    WICKET_KEEPER = "wicket_keeper"


class Player(BaseModel):
    player_id: str
    name: str
    role: PlayerRole
    is_overseas: bool
    expected_runs: float = Field(ge=0, description="Expected runs per ball")
    expected_wickets: float = Field(ge=0, description="Expected wickets per ball")
    form_score: float = Field(default=1.0, description="Current form EWM score")


class Team(BaseModel):
    team_id: str
    name: str
    squad: List[Player]


class MatchContext(BaseModel):
    match_id: str
    venue: str
    opponent_team: str
    season: int
    is_home: bool = False


class SimulationRequest(BaseModel):
    team: Team
    match_context: MatchContext
    formation_bias: Literal["batting", "balanced", "bowling"] = "balanced"
    must_include: List[str] = Field(default_factory=list, description="Player IDs to force include")
    must_exclude: List[str] = Field(default_factory=list, description="Player IDs to force exclude")


class CommentaryStep(BaseModel):
    step_number: int
    title: str
    formula: str
    description: str
    insight: str
    insight_type: Literal["venue_encoding", "bipartite_threat", "ilp_solution", "monte_carlo"]
    graph_data: Optional[Dict[str, Any]] = None


class XIOptimization(BaseModel):
    selected_xi: List[Player]
    commentary_steps: List[CommentaryStep]
    objective_value: float
    baseline_value: float
    improvement_pct: float


class WinProbability(BaseModel):
    win_probability: float = Field(ge=0, le=1, description="Probability of winning")
    confidence_interval: tuple[float, float] = Field(description="95% confidence interval")
    calibration_applied: bool = False
    sample_size: int = Field(description="Number of Monte Carlo rollouts")


class MatchSimulation(BaseModel):
    match_id: str
    team_xi: List[Player]
    opponent_xi: List[Player]
    win_probability: WinProbability
    venue_analysis: Dict[str, float]
    key_threats: List[Dict[str, Any]]


class SimulationResponse(BaseModel):
    simulation_id: str
    optimization: XIOptimization
    simulation: MatchSimulation
    narrative: Dict[str, str]


class SimulationStart(BaseModel):
    simulation_id: str
    team: str
    season: int
    mode: str
    created_at: str


class XIConfirmation(BaseModel):
    match_id: str
    accepted_ai_suggestion: bool
    overrides_count: int
    final_xi: List[Player]


class MatchResult(BaseModel):
    match_id: str
    win: bool
    win_probability: float
    runs_scored: Optional[int] = None
    runs_conceded: Optional[int] = None


class TournamentPath(BaseModel):
    team: str
    season: int
    path: List[Dict[str, Any]]
    max_flow_value: float
    total_matches: int


class CommunityStats(BaseModel):
    total_simulations: int
    avg_win_probability: float
    most_optimized_player: str
    ai_acceptance_rate: float
    popular_venues: List[Dict[str, int]]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str
