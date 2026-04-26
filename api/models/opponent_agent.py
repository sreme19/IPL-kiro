"""
api/models/opponent_agent.py
===========================
bipartite matchup graph construction for Opponent Agent.
"""

import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class Player:
    player_id: str
    name: str
    role: str
    stats: Dict[str, float]


@dataclass
class ThreatEdge:
    batter_id: str
    bowler_id: str
    weight: float
    threat_level: str  # "high", "medium", "low"
    runs_conceded: float
    dismissal_rate: float
    sample_size: int


class OpponentAgent:
    """Constructs bipartite matchup graphs for threat analysis."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.threat_edges = []
    
    def build_matchup_graph(
        self,
        team_players: List[Player],
        opponent_players: List[Player],
        venue: str,
        tensors: Dict[str, Dict[str, Any]]
    ) -> nx.DiGraph:
        """Build bipartite graph of team vs opponent matchups."""
        
        # Clear existing graph
        self.graph.clear()
        self.threat_edges.clear()
        
        # Add nodes for both teams
        for player in team_players:
            self.graph.add_node(
                player.player_id,
                name=player.name,
                role=player.role,
                team="home"
            )
        
        for player in opponent_players:
            self.graph.add_node(
                player.player_id,
                name=player.name,
                role=player.role,
                team="opponent"
            )
        
        # Build threat edges (team batting vs opponent bowling)
        for batter in team_players:
            if batter.role in ["batsman", "all_rounder", "wicket_keeper"]:
                for bowler in opponent_players:
                    if bowler.role in ["bowler", "all_rounder"]:
                        edge = self._compute_threat_edge(
                            batter, bowler, venue, tensors
                        )
                        self.threat_edges.append(edge)
                        
                        # Add edge to graph
                        self.graph.add_edge(
                            bowler.player_id,  # bowler to batter
                            batter.player_id,
                            weight=edge.weight,
                            threat_level=edge.threat_level,
                            runs_conceded=edge.runs_conceded,
                            dismissal_rate=edge.dismissal_rate,
                            sample_size=edge.sample_size,
                            edge_type="bowling_threat"
                        )
        
        # Build reverse threat edges (opponent batting vs team bowling)
        for batter in opponent_players:
            if batter.role in ["batsman", "all_rounder", "wicket_keeper"]:
                for bowler in team_players:
                    if bowler.role in ["bowler", "all_rounder"]:
                        edge = self._compute_threat_edge(
                            batter, bowler, venue, tensors
                        )
                        
                        self.graph.add_edge(
                            bowler.player_id,
                            batter.player_id,
                            weight=edge.weight,
                            threat_level=edge.threat_level,
                            runs_conceded=edge.runs_conceded,
                            dismissal_rate=edge.dismissal_rate,
                            sample_size=edge.sample_size,
                            edge_type="bowling_threat"
                        )
        
        return self.graph
    
    def _compute_threat_edge(
        self,
        batter: Player,
        bowler: Player,
        venue: str,
        tensors: Dict[str, Dict[str, Any]]
    ) -> ThreatEdge:
        """Compute threat level for a specific batter-bowler matchup."""
        
        # Get tensor data for this matchup
        batter_id = batter.player_id
        bowler_id = bowler.player_id
        
        # Try to get specific matchup data
        matchup_key = f"{batter_id}_vs_{bowler_id}"
        batter_tensors = tensors.get(batter_id, {}).get("base_tensors", {})
        
        # Get matchup data where batter faces this bowler
        matchup_data = None
        for opponent_id, opponent_data in batter_tensors.items():
            if "as_batsman" in opponent_data:
                batsman_data = opponent_data["as_batsman"]
                # Look for this bowler in the data
                if bowler_id in str(opponent_data):
                    # This is a simplified check - in practice, we'd have better indexing
                    batting_tensor = batsman_data.get("avg_runs_per_ball", 0.8)
                    dismissal_tensor = batsman_data.get("dismissal_rate_per_ball", 0.03)
                    economy_tensor = batsman_data.get("economy_rate", 7.0)
                    sample_size = batsman_data.get("sample_size", 0)
                    
                    matchup_data = {
                        "avg_runs_per_ball": batting_tensor,
                        "dismissal_rate_per_ball": dismissal_tensor,
                        "economy_rate": economy_tensor,
                        "sample_size": sample_size
                    }
                    break
        
        # Fallback to player averages if no specific matchup
        if not matchup_data:
            batting_form = tensors.get(batter_id, {}).get("batting_form", 1.0)
            bowling_form = tensors.get(bowler_id, {}).get("bowling_form", 1.0)
            
            matchup_data = {
                "avg_runs_per_ball": 0.8 * batting_form,
                "dismissal_rate_per_ball": 0.03 / bowling_form,
                "economy_rate": 7.0 / bowling_form,
                "sample_size": 0
            }
        
        # Compute threat score (higher = more threat to batting team)
        runs_conceded = matchup_data["avg_runs_per_ball"] * 6  # Per over
        dismissal_rate = matchup_data["dismissal_rate_per_ball"]
        sample_size = matchup_data["sample_size"]
        
        # Threat scoring: high runs + high dismissal rate = high threat
        threat_score = (runs_conceded * 0.6) + (dismissal_rate * 100 * 0.4)
        
        # Adjust for sample size (more data = more reliable)
        confidence_factor = min(sample_size / 30, 1.0) if sample_size > 0 else 0.5
        adjusted_threat = threat_score * confidence_factor
        
        # Classify threat level
        if adjusted_threat > 8.0:
            threat_level = "high"
        elif adjusted_threat > 4.0:
            threat_level = "medium"
        else:
            threat_level = "low"
        
        return ThreatEdge(
            batter_id=batter_id,
            bowler_id=bowler_id,
            weight=adjusted_threat,
            threat_level=threat_level,
            runs_conceded=runs_conceded,
            dismissal_rate=dismissal_rate,
            sample_size=sample_size
        )
    
    def get_high_threat_matchups(self, team: str = "home") -> List[ThreatEdge]:
        """Get highest threat matchups for analysis."""
        
        # Filter edges by team if specified
        if team == "home":
            # Edges where opponent bowlers threaten home batters
            home_batters = [n for n, d in self.graph.nodes(data=True) if d.get("team") == "home"]
            opponent_bowlers = [n for n, d in self.graph.nodes(data=True) if d.get("team") == "opponent"]
            
            high_threat_edges = [
                edge for edge in self.threat_edges
                if (edge.batter_id in [b["player_id"] for b in home_batters] and
                    edge.bowler_id in [b["player_id"] for b in opponent_bowlers] and
                    edge.threat_level == "high")
            ]
        else:
            high_threat_edges = [
                edge for edge in self.threat_edges
                if edge.threat_level == "high"
            ]
        
        # Sort by threat weight (descending)
        return sorted(high_threat_edges, key=lambda x: x.weight, reverse=True)
    
    def get_player_threats(
        self, 
        player_id: str, 
        as_batsman: bool = True
    ) -> List[ThreatEdge]:
        """Get threats for a specific player."""
        
        if as_batsman:
            return [
                edge for edge in self.threat_edges
                if edge.batter_id == player_id
            ]
        else:
            return [
                edge for edge in self.threat_edges
                if edge.bowler_id == player_id
            ]
    
    def compute_team_threat_score(self, team: str = "home") -> Dict[str, float]:
        """Compute overall threat scores for a team."""
        
        if team == "home":
            # Threats TO home team (opposition bowlers vs home batters)
            home_threats = [
                edge for edge in self.threat_edges
                if self._is_home_batter(edge.batter_id)
            ]
        else:
            # Threats FROM home team (home bowlers vs opposition batters)
            home_threats = [
                edge for edge in self.threat_edges
                if self._is_home_bowler(edge.bowler_id)
            ]
        
        if not home_threats:
            return {"total_threat": 0.0, "avg_threat": 0.0, "high_threat_count": 0}
        
        total_threat = sum(edge.weight for edge in home_threats)
        avg_threat = total_threat / len(home_threats)
        high_threat_count = sum(1 for edge in home_threats if edge.threat_level == "high")
        
        return {
            "total_threat": total_threat,
            "avg_threat": avg_threat,
            "high_threat_count": high_threat_count,
            "threat_distribution": {
                "high": high_threat_count,
                "medium": sum(1 for edge in home_threats if edge.threat_level == "medium"),
                "low": sum(1 for edge in home_threats if edge.threat_level == "low")
            }
        }
    
    def _is_home_batter(self, player_id: str) -> bool:
        """Check if player is a home batter."""
        node_data = self.graph.nodes.get(player_id, {})
        return node_data.get("team") == "home" and node_data.get("role") in ["batsman", "all_rounder", "wicket_keeper"]
    
    def _is_home_bowler(self, player_id: str) -> bool:
        """Check if player is a home bowler."""
        node_data = self.graph.nodes.get(player_id, {})
        return node_data.get("team") == "home" and node_data.get("role") in ["bowler", "all_rounder"]
    
    def get_graph_data_for_visualization(self) -> Dict[str, Any]:
        """Get graph data formatted for frontend visualization."""
        
        # Separate nodes by team
        home_nodes = []
        away_nodes = []
        
        for node_id, data in self.graph.nodes(data=True):
            node_dict = {
                "id": node_id,
                "name": data.get("name", node_id),
                "role": data.get("role", "unknown")
            }
            
            if data.get("team") == "home":
                home_nodes.append(node_dict)
            else:
                away_nodes.append(node_dict)
        
        # Format edges
        edges = []
        for edge in self.threat_edges:
            edges.append({
                "batter_id": edge.batter_id,
                "bowler_id": edge.bowler_id,
                "weight": edge.weight,
                "threat_level": edge.threat_level
            })
        
        return {
            "batters": home_nodes,
            "bowlers": away_nodes,
            "edges": edges
        }
    
    def analyze_key_matchups(self, top_n: int = 5) -> Dict[str, Any]:
        """Analyze the most critical matchups."""
        
        high_threats = self.get_high_threat_matchups()
        top_threats = high_threats[:top_n]
        
        return {
            "critical_matchups": [
                {
                    "batter": edge.batter_id,
                    "bowler": edge.bowler_id,
                    "threat_score": edge.weight,
                    "threat_level": edge.threat_level,
                    "runs_per_over": edge.runs_conceded,
                    "dismissal_rate": edge.dismissal_rate,
                    "sample_size": edge.sample_size,
                    "impact": self._assess_matchup_impact(edge)
                }
                for edge in top_threats
            ],
            "summary": {
                "total_high_threats": len(high_threats),
                "avg_threat_score": np.mean([e.weight for e in high_threats]) if high_threats else 0,
                "venue_impact": "High threat matchups suggest venue conditions favor bowlers"
            }
        }
    
    def _assess_matchup_impact(self, edge: ThreatEdge) -> str:
        """Assess the potential impact of a matchup."""
        
        if edge.threat_level == "high" and edge.sample_size >= 30:
            return "Historically dominant matchup with strong data"
        elif edge.threat_level == "high" and edge.sample_size < 30:
            return "High potential threat but limited historical data"
        elif edge.runs_conceded > 10:
            return "Very expensive bowling - major threat to economy"
        elif edge.dismissal_rate > 0.05:
            return "High dismissal rate - breakthrough threat"
        else:
            return "Moderate threat level"
