"""
api/routers/tournament.py
==========================
GET /api/tournament/path - Tournament progression analysis.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import uuid

from models.tournament_graph import TournamentGraph
from models.session_store import SessionStore

router = APIRouter()

# Initialize agents
session_store = SessionStore()
tournament_graph = TournamentGraph()


@router.get("/path")
async def get_tournament_path(
    team: str,
    season: int = 2023
) -> Dict[str, Any]:
    """Get optimal tournament path for a team."""
    
    try:
        # Generate mock group matches (in real implementation, would come from database)
        group_matches = _generate_mock_group_matches(team, season)
        
        # Build tournament DAG
        graph = tournament_graph.build_tournament_dag(
            teams=[team],  # Simplified - would be all teams
            season=season,
            group_matches=group_matches
        )
        
        # Compute max flow path
        path_result = tournament_graph.compute_max_flow_path(
            source_team=team,
            target_team="championship"
        )
        
        return {
            "team": team,
            "season": season,
            "path": [
                {
                    "node_id": node.node_id,
                    "match": f"{node.team} vs {node.opponent}",
                    "venue": node.venue,
                    "win_probability": node.win_probability,
                    "stage": "group" if "vs" in node.node_id else "playoff"
                }
                for node in path_result.path_nodes
            ],
            "max_flow_value": path_result.min_flow_value,
            "total_matches": len(path_result.path_nodes),
            "critical_matches": path_result.critical_matches,
            "path_probability": path_result.total_probability,
            "analysis": {
                "tournament_structure": "IPL T20 format",
                "path_optimization": "Maximum flow algorithm",
                "key_insights": [
                    f"Path involves {len(path_result.path_nodes)} matches",
                    f"Overall tournament success probability: {path_result.total_probability:.1%}",
                    f"Critical matches identified: {len(path_result.critical_matches)}"
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tournament path computation failed: {str(e)}")


@router.get("/analysis")
async def get_tournament_analysis(
    season: int = 2023
) -> Dict[str, Any]:
    """Get comprehensive tournament analysis."""
    
    try:
        # Get all teams for the season
        teams = [
            "Chennai Super Kings", "Mumbai Indians", "Kolkata Knight Riders",
            "Royal Challengers Bangalore", "Delhi Capitals", "Punjab Kings",
            "Sunrisers Hyderabad", "Rajasthan Royals", "Gujarat Titans",
            "Lucknow Super Giants"
        ]
        
        # Build tournament graph for all teams
        group_matches = _generate_mock_group_matches("", season)  # Empty team for all teams
        graph = tournament_graph.build_tournament_dag(
            teams=teams,
            season=season,
            group_matches=group_matches
        )
        
        # Get tournament analysis
        analysis = tournament_graph.get_tournament_analysis(teams)
        
        return {
            "season": season,
            "tournament_structure": analysis["tournament_structure"],
            "team_rankings": analysis["team_rankings"],
            "key_insights": analysis["key_insights"],
            "graph_visualization": tournament_graph.get_graph_visualization_data(),
            "strength_distribution": {
                "strongest_team": analysis["team_rankings"][0] if analysis["team_rankings"] else None,
                "weakest_team": analysis["team_rankings"][-1] if analysis["team_rankings"] else None,
                "competitive_balance": len(analysis["team_rankings"]) > 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tournament analysis failed: {str(e)}")


@router.get("/simulate/{team}")
async def simulate_tournament_progression(
    team: str,
    season: int = 2023,
    scenarios: int = 100
) -> Dict[str, Any]:
    """Simulate tournament progression with Monte Carlo."""
    
    try:
        # Generate mock tournament structure
        teams = [
            "Chennai Super Kings", "Mumbai Indians", "Kolkata Knight Riders",
            "Royal Challengers Bangalore", "Delhi Capitals", "Punjab Kings",
            "Sunrisers Hyderabad", "Rajasthan Royals", "Gujarat Titans",
            "Lucknow Super Giants"
        ]
        
        # Run multiple tournament simulations
        simulation_results = []
        
        for i in range(scenarios):
            # Random win probabilities for each match
            group_matches = _generate_mock_group_matches(team, season, randomize=True)
            
            graph = tournament_graph.build_tournament_dag(
                teams=teams,
                season=season,
                group_matches=group_matches
            )
            
            path_result = tournament_graph.compute_max_flow_path(
                source_team=team,
                target_team="championship"
            )
            
            simulation_results.append({
                "scenario": i + 1,
                "path_probability": path_result.total_probability,
                "matches_won": sum(1 for node in path_result.path_nodes if node.win_probability > 0.5),
                "critical_matches_won": sum(1 for match_id in path_result.critical_matches 
                                        if any(node.win_probability > 0.5 
                                              for node in path_result.path_nodes 
                                              if node.node_id == match_id))
            })
        
        # Calculate statistics
        win_probabilities = [r["path_probability"] for r in simulation_results]
        matches_won = [r["matches_won"] for r in simulation_results]
        
        return {
            "team": team,
            "season": season,
            "scenarios_run": scenarios,
            "simulation_results": simulation_results[:10],  # Return first 10 for brevity
            "statistics": {
                "avg_win_probability": sum(win_probabilities) / len(win_probabilities),
                "median_win_probability": sorted(win_probabilities)[len(win_probabilities) // 2],
                "win_probability_std": (sum((p - sum(win_probabilities)/len(win_probabilities))**2 
                                       for p in win_probabilities) / len(win_probabilities))**0.5,
                "avg_matches_won": sum(matches_won) / len(matches_won),
                "tournament_win_probability": sum(1 for p in win_probabilities if p > 0.8) / len(win_probabilities)
            },
            "distribution": {
                "championship_favorite": win_probabilities.count(max(win_probabilities)),
                "playoff_probability": sum(1 for p in win_probabilities if 0.3 < p < 0.8) / len(win_probabilities),
                "group_stage_probability": sum(1 for p in win_probabilities if p <= 0.3) / len(win_probabilities)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tournament simulation failed: {str(e)}")


def _generate_mock_group_matches(team: str, season: int, randomize: bool = False) -> List[Dict[str, Any]]:
    """Generate mock group match data for demonstration."""
    
    import random
    
    # Mock venues
    venues = [
        "M Chinnaswamy Stadium", "Wankhede Stadium", "Eden Gardens",
        "MA Chidambaram Stadium", "Brabourne Stadium", "Punjab Cricket Association Stadium"
    ]
    
    # Mock teams
    teams = [
        "Chennai Super Kings", "Mumbai Indians", "Kolkata Knight Riders",
        "Royal Challengers Bangalore", "Delhi Capitals", "Punjab Kings",
        "Sunrisers Hyderabad", "Rajasthan Royals", "Gujarat Titans",
        "Lucknow Super Giants"
    ]
    
    matches = []
    
    # Generate group stage matches (each team plays others twice)
    for i, team1 in enumerate(teams):
        for j, team2 in enumerate(teams):
            if i < j:  # Avoid duplicates
                # Random win probability with home advantage
                base_prob = 0.5
                if randomize:
                    # Add some randomness
                    base_prob += random.uniform(-0.2, 0.2)
                
                # Home advantage
                if i % 2 == 0:  # Simplified home/away
                    base_prob += 0.05
                
                win_prob = max(0.1, min(0.9, base_prob))
                
                matches.append({
                    "team1": team1,
                    "team2": team2,
                    "venue": random.choice(venues),
                    "win_probability": win_prob,
                    "is_played": randomize and random.random() > 0.3,  # Some matches unplayed
                    "match_id": f"match_{i}_{j}"
                })
    
    return matches
