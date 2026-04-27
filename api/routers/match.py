"""
api/routers/match.py
==================
POST /api/match/recommend-xi, POST /api/match/simulate endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import uuid

from api.models.schemas import XIConfirmation, MatchResult
from api.models.session_store import SessionStore
from api.models.scout_agent import ScoutAgent
from api.models.conditions_agent import ConditionsAgent
from api.models.opponent_agent import OpponentAgent
from api.models.ilp_solver import ILPSolver
from api.models.monte_carlo import MonteCarloSimulator

router = APIRouter()

# Initialize agents
session_store = SessionStore()
scout_agent = ScoutAgent()
conditions_agent = ConditionsAgent()
opponent_agent = OpponentAgent()
ilp_solver = ILPSolver()
monte_carlo = MonteCarloSimulator()


@router.post("/recommend-xi")
async def recommend_xi(request: Dict[str, Any]) -> Dict[str, Any]:
    """Get AI-recommended XI for a specific match."""
    
    try:
        # Extract request data
        match_context = request.get("match_context", {})
        squad = request.get("squad", [])
        formation_bias = request.get("formation_bias", "balanced")
        must_include = request.get("must_include", [])
        must_exclude = request.get("must_exclude", [])
        
        # Get venue analysis
        venue = match_context.get("venue", "")
        venue_weights = conditions_agent.compute_venue_vector(
            venue=venue,
            formation_bias=formation_bias
        )
        
        # Load tensor data
        tensors = scout_agent.get_squad_tensors(
            [p.get("player_id", "") for p in squad],
            venue=venue,
            season=match_context.get("season", 2023)
        )
        
        # Solve ILP optimization
        optimization_result = ilp_solver.solve_optimal_xi(
            squad=squad,
            venue_weights=venue_weights,
            formation_bias=formation_bias,
            must_include=must_include,
            must_exclude=must_exclude,
            tensors=tensors
        )
        
        return {
            "match_id": match_context.get("match_id", str(uuid.uuid4())),
            "recommended_xi": [player.__dict__ for player in optimization_result.selected_xi],
            "commentary_steps": [step.__dict__ for step in optimization_result.commentary_steps],
            "objective_value": optimization_result.objective_value,
            "baseline_value": optimization_result.baseline_value,
            "improvement_pct": optimization_result.improvement_pct,
            "venue_analysis": venue_weights,
            "solve_time_ms": optimization_result.solve_time_ms
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XI recommendation failed: {str(e)}")


@router.post("/simulate")
async def simulate_match(request: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate match outcome with current XI."""
    
    try:
        # Extract request data
        match_context = request.get("match_context", {})
        team_xi = request.get("team_xi", [])
        opponent_xi = request.get("opponent_xi", [])
        target_runs = request.get("target_runs", None)
        
        # Get venue adjustments
        venue = match_context.get("venue", "")
        venue_adjustments = conditions_agent.compute_venue_vector(
            venue=venue,
            formation_bias="balanced"
        )
        
        # Convert to tensor format
        team_tensors = {
            player.get("player_id", ""): {
                "batting_form": player.get("form_score", 1.0),
                "bowling_form": 1.0
            }
            for player in team_xi
        }
        
        opponent_tensors = {
            player.get("player_id", ""): {
                "batting_form": player.get("form_score", 1.0),
                "bowling_form": 1.0
            }
            for player in opponent_xi
        }
        
        # Run Monte Carlo simulation
        simulation_result = monte_carlo.simulate_win_probability(
            team_tensors=team_tensors,
            opponent_tensors=opponent_tensors,
            venue_adjustments=venue_adjustments,
            target_runs=target_runs
        )
        
        # Build matchup graph for threat analysis
        team_players = [
            type("Player", (), {
                "player_id": p.get("player_id", ""),
                "name": p.get("name", ""),
                "role": p.get("role", "batsman")
            })
            for p in team_xi
        ]
        
        opponent_players = [
            type("Player", (), {
                "player_id": p.get("player_id", ""),
                "name": p.get("name", ""),
                "role": p.get("role", "batsman")
            })
            for p in opponent_xi
        ]
        
        matchup_graph = opponent_agent.build_matchup_graph(
            team_players, opponent_players, venue, {}
        )
        
        # Get high threat matchups
        high_threats = opponent_agent.get_high_threat_matchups("home")[:5]
        
        return {
            "match_id": match_context.get("match_id", str(uuid.uuid4())),
            "team_xi": team_xi,
            "opponent_xi": opponent_xi,
            "win_probability": {
                "win_probability": simulation_result.win_probability,
                "confidence_interval": simulation_result.confidence_interval,
                "calibration_applied": simulation_result.calibration_applied,
                "sample_size": simulation_result.sample_size
            },
            "venue_analysis": venue_adjustments,
            "key_threats": [
                {
                    "batter": threat.batter_id,
                    "bowler": threat.bowler_id,
                    "threat_score": threat.weight,
                    "threat_level": threat.threat_level,
                    "runs_per_over": threat.runs_conceded,
                    "dismissal_rate": threat.dismissal_rate
                }
                for threat in high_threats
            ],
            "simulation_stats": {
                "runtime_ms": simulation_result.runtime_ms,
                "cache_hit": False  # Would be tracked in real implementation
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Match simulation failed: {str(e)}")


@router.post("/result")
async def record_match_result(request: Dict[str, Any]) -> Dict[str, Any]:
    """Record actual match result for calibration."""
    
    try:
        # Extract request data
        match_id = request.get("match_id", "")
        simulation_id = request.get("simulation_id", "")
        predicted_win_prob = request.get("predicted_win_probability", 0.5)
        actual_win = request.get("actual_win", False)
        runs_scored = request.get("runs_scored", None)
        runs_conceded = request.get("runs_conceded", None)
        
        if not simulation_id:
            raise HTTPException(status_code=400, detail="simulation_id is required")
        
        # Update session with calibration point
        success = session_store.add_calibration_point(
            simulation_id=simulation_id,
            predicted=predicted_win_prob,
            actual=1.0 if actual_win else 0.0
        )
        
        # Increment matches played
        session_store.increment_matches_played(simulation_id)
        
        # Update form vector based on actual performance
        if actual_win:
            # Update form for winning team (simplified - would use actual player IDs)
            form_updates = {}
            # In production, this would use actual player IDs from the match
            for player_id in range(11):
                form_updates[f"player_{player_id}"] = 1.1  # Boost form
            session_store.update_form_vector(simulation_id, form_updates)
        
        return {
            "match_id": match_id,
            "simulation_id": simulation_id,
            "recorded": success,
            "calibration_added": True,
            "matches_played": session_store.get_session(simulation_id).matches_played if session_store.get_session(simulation_id) else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Result recording failed: {str(e)}")


@router.get("/history/{simulation_id}")
async def get_match_history(simulation_id: str) -> Dict[str, Any]:
    """Get match history for a simulation session."""
    
    try:
        session = session_store.get_session(simulation_id)
        if not session:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        summary = session_store.get_session_summary(simulation_id)
        
        return {
            "simulation_id": simulation_id,
            "matches_played": summary.get("matches_played", 0),
            "calibration_points": summary.get("calibration_points", 0),
            "calibration_accuracy": summary.get("calibration_accuracy", 0.0),
            "current_form": session.form_vec,
            "current_fatigue": session.squad_fatigue,
            "session_age_hours": summary.get("session_age_hours", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")
