"""
api/routers/simulation.py
==========================
POST /api/simulation/start - Initialize new simulation session.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import uuid
import time

from models.schemas import SimulationStart, SimulationResponse
from models.session_store import SessionStore
from models.scout_agent import ScoutAgent
from models.conditions_agent import ConditionsAgent
from models.opponent_agent import OpponentAgent
from models.ilp_solver import ILPSolver
from models.monte_carlo import MonteCarloSimulator
from models.narrative_agent import NarrativeAgent
from models.schemas import Player, PlayerRole

router = APIRouter()

# Initialize agents
session_store = SessionStore()
scout_agent = ScoutAgent()
conditions_agent = ConditionsAgent()
opponent_agent = OpponentAgent()
ilp_solver = ILPSolver()
monte_carlo = MonteCarloSimulator()
narrative_agent = NarrativeAgent()


@router.post("/start", response_model=SimulationResponse)
async def start_simulation(request: Dict[str, Any]) -> SimulationResponse:
    """Initialize a new simulation session and return analysis."""
    
    try:
        # Extract request data
        team_data = request.get("team", {})
        match_context = request.get("match_context", {})
        formation_bias = request.get("formation_bias", "balanced")
        must_include = request.get("must_include", [])
        must_exclude = request.get("must_exclude", [])
        
        # Generate simulation ID
        simulation_id = str(uuid.uuid4())
        
        # Create session
        session = session_store.create_session(simulation_id)
        
        # Convert to Player objects
        squad_players = [
            Player(
                player_id=p["player_id"],
                name=p["name"],
                role=PlayerRole(p.get("role", "batsman")),
                is_overseas=p.get("is_overseas", False),
                expected_runs=p.get("expected_runs", 0.8),
                expected_wickets=p.get("expected_wickets", 0.03),
                form_score=1.0
            )
            for p in team_data.get("squad", [])
        ]
        
        # Get venue analysis
        venue = match_context.get("venue", "")
        venue_weights = conditions_agent.compute_venue_vector(
            venue=venue,
            formation_bias=formation_bias
        )
        
        # Load tensor data
        tensors = scout_agent.get_squad_tensors(
            [p.player_id for p in squad_players],
            venue=venue,
            season=match_context.get("season", 2023)
        )
        
        # Build opponent matchup graph
        # For now, use dummy opponent data
        opponent_players = []  # Would come from request
        matchup_graph = opponent_agent.build_matchup_graph(
            squad_players, opponent_players, venue, tensors
        )
        
        # Solve ILP optimization
        optimization_result = ilp_solver.solve_optimal_xi(
            squad=squad_players,
            venue_weights=venue_weights,
            formation_bias=formation_bias,
            must_include=must_include,
            must_exclude=must_exclude,
            tensors=tensors
        )
        
        # Run Monte Carlo simulation
        team_tensor_summary = {
            player.player_id: tensors.get(player.player_id, {}).get("batting_form", 1.0)
            for player in optimization_result.selected_xi
        }
        
        # Dummy opponent tensors for simulation
        opponent_tensor_summary = {
            player.player_id: 1.0  # Placeholder
            for player in opponent_players
        }
        
        monte_carlo_result = monte_carlo.simulate_win_probability(
            team_tensors=team_tensor_summary,
            opponent_tensors=opponent_tensor_summary,
            venue_adjustments=venue_weights
        )
        
        # Generate narrative
        narrative = narrative_agent.generate_narrative(
            match_id=simulation_id,
            commentary_steps=optimization_result.commentary_steps,
            team_name=team_data.get("name", "Team"),
            opponent_name=match_context.get("opponent_team", "Opponent"),
            venue=venue
        )
        
        # Update session with results
        session_store.update_session(session)
        
        return SimulationResponse(
            simulation_id=simulation_id,
            optimization={
                "selected_xi": optimization_result.selected_xi,
                "commentary_steps": [step.__dict__ for step in optimization_result.commentary_steps],
                "objective_value": optimization_result.objective_value,
                "baseline_value": optimization_result.baseline_value,
                "improvement_pct": optimization_result.improvement_pct
            },
            simulation={
                "match_id": simulation_id,
                "team_xi": [player.__dict__ for player in optimization_result.selected_xi],
                "opponent_xi": [player.__dict__ for player in opponent_players],
                "win_probability": {
                    "win_probability": monte_carlo_result.win_probability,
                    "confidence_interval": monte_carlo_result.confidence_interval,
                    "calibration_applied": monte_carlo_result.calibration_applied,
                    "sample_size": monte_carlo_result.sample_size
                },
                "venue_analysis": venue_weights,
                "key_threats": opponent_agent.get_high_threat_matchups("home")[:5]
            },
            narrative=narrative
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.get("/{simulation_id}/status")
async def get_simulation_status(simulation_id: str) -> Dict[str, Any]:
    """Get current status of a simulation session."""
    
    session = session_store.get_session(simulation_id)
    if not session:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    summary = session_store.get_session_summary(simulation_id)
    return {
        "simulation_id": simulation_id,
        "status": "active",
        "session_age_hours": summary.get("session_age_hours", 0),
        "matches_played": summary.get("matches_played", 0),
        "calibration_accuracy": summary.get("calibration_accuracy", 0.0),
        "form_vector_size": summary.get("form_vector_size", 0)
    }


@router.post("/{simulation_id}/confirm-xi")
async def confirm_xi(simulation_id: str, confirmation: Dict[str, Any]) -> Dict[str, Any]:
    """Confirm or override AI-suggested XI."""
    
    session = session_store.get_session(simulation_id)
    if not session:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Update session with XI confirmation
    accepted_ai = confirmation.get("accepted_ai_suggestion", False)
    overrides_count = confirmation.get("overrides_count", 0)
    final_xi = confirmation.get("final_xi", [])
    
    # Update fatigue based on final XI
    fatigue_updates = {}
    for player in final_xi:
        player_id = player.get("player_id", "")
        if player_id:
            # Increase fatigue for selected players
            current_fatigue = session.squad_fatigue.get(player_id, 0.0)
            fatigue_updates[player_id] = current_fatigue + 0.1
    
    if fatigue_updates:
        session_store.update_fatigue(simulation_id, fatigue_updates)
    
    return {
        "simulation_id": simulation_id,
        "accepted_ai_suggestion": accepted_ai,
        "overrides_count": overrides_count,
        "final_xi_confirmed": True,
        "fatigue_updated": len(fatigue_updates)
    }
