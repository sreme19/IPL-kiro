"""
api/models/tournament_graph.py
=============================
NetworkX DAG + max-flow path for Tournament Graph.
"""

import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass


@dataclass
class TournamentNode:
    node_id: str
    team: str
    opponent: str
    venue: str
    win_probability: float
    is_played: bool = False


@dataclass
class TournamentPath:
    path_nodes: List[TournamentNode]
    total_probability: float
    min_flow_value: float
    critical_matches: List[str]


class TournamentGraph:
    """Builds tournament DAG and computes optimal paths using max-flow."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes = {}
        self.matches = {}
    
    def build_tournament_dag(
        self,
        teams: List[str],
        season: int,
        group_matches: List[Dict[str, Any]]
    ) -> nx.DiGraph:
        """Build directed acyclic graph for tournament progression."""
        
        # Clear existing graph
        self.graph.clear()
        self.nodes.clear()
        self.matches.clear()
        
        # Create tournament structure (simplified IPL format)
        # IPL typically has group stage followed by playoffs
        
        # Group stage: each team plays each other twice
        group_nodes = self._build_group_stage_nodes(teams, group_matches)
        
        # Playoff stage: qualifiers advance
        playoff_nodes = self._build_playoff_nodes(teams, group_nodes)
        
        # Add all nodes to graph
        all_nodes = group_nodes + playoff_nodes
        for node in all_nodes:
            node_id = f"{node.team}_vs_{node.opponent}_{node.venue}"
            self.nodes[node_id] = node
            
            self.graph.add_node(
                node_id,
                team=node.team,
                opponent=node.opponent,
                venue=node.venue,
                win_prob=node.win_probability,
                stage="group" if node in group_nodes else "playoff",
                is_played=node.is_played
            )
        
        # Add edges representing tournament progression
        self._add_tournament_edges(all_nodes)
        
        return self.graph
    
    def _build_group_stage_nodes(
        self,
        teams: List[str],
        group_matches: List[Dict[str, Any]]
    ) -> List[TournamentNode]:
        """Build nodes for group stage matches."""
        
        nodes = []
        
        # Create nodes for each group match
        for match in group_matches:
            team1 = match.get("team1")
            team2 = match.get("team2")
            venue = match.get("venue")
            win_prob = match.get("win_probability", 0.5)
            is_played = match.get("is_played", False)
            
            # Node for team1 perspective
            node1 = TournamentNode(
                node_id=f"{team1}_vs_{team2}_{venue}",
                team=team1,
                opponent=team2,
                venue=venue,
                win_probability=win_prob,
                is_played=is_played
            )
            nodes.append(node1)
            
            # Node for team2 perspective (reverse win probability)
            node2 = TournamentNode(
                node_id=f"{team2}_vs_{team1}_{venue}",
                team=team2,
                opponent=team1,
                venue=venue,
                win_probability=1.0 - win_prob,
                is_played=is_played
            )
            nodes.append(node2)
        
        return nodes
    
    def _build_playoff_nodes(
        self,
        teams: List[str],
        group_nodes: List[TournamentNode]
    ) -> List[TournamentNode]:
        """Build nodes for playoff matches (qualifier, eliminator, final)."""
        
        # Simplified playoff structure
        # Top 4 teams typically qualify for playoffs
        
        # Get top teams by group performance (simplified)
        team_performance = {}
        for node in group_nodes:
            if node.team not in team_performance:
                team_performance[node.team] = []
            team_performance[node.team].append(node.win_probability)
        
        # Calculate average win probability for each team
        team_avg_performance = {
            team: np.mean(performance) 
            for team, performance in team_performance.items()
        }
        
        # Sort teams by performance
        qualified_teams = sorted(
            team_avg_performance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:4]
        
        nodes = []
        
        # Qualifier 1: 1st vs 4th
        if len(qualified_teams) >= 4:
            q1_node = TournamentNode(
                node_id="qualifier1",
                team=qualified_teams[0][0],
                opponent=qualified_teams[3][0],
                venue="neutral_playoff_venue",
                win_probability=0.6  # Higher seed advantage
            )
            nodes.append(q1_node)
        
        # Qualifier 2: 2nd vs 3rd
        if len(qualified_teams) >= 4:
            q2_node = TournamentNode(
                node_id="qualifier2", 
                team=qualified_teams[1][0],
                opponent=qualified_teams[2][0],
                venue="neutral_playoff_venue",
                win_probability=0.55
            )
            nodes.append(q2_node)
        
        # Final (simplified)
        final_node = TournamentNode(
            node_id="final",
            team="qualifier1_winner",
            opponent="qualifier2_winner",
            venue="final_venue",
            win_probability=0.5
        )
        nodes.append(final_node)
        
        return nodes
    
    def _add_tournament_edges(self, nodes: List[TournamentNode]) -> None:
        """Add edges representing tournament flow and dependencies."""
        
        # Group stage edges: teams can advance based on performance
        group_nodes = [n for n in nodes if "vs" in n.node_id]
        
        # Connect group matches to playoff qualification
        # This is simplified - real implementation would track points
        
        # Find top performing teams
        team_performance = {}
        for node in group_nodes:
            if node.team not in team_performance:
                team_performance[node.team] = []
            team_performance[node.team].append(node.win_probability)
        
        team_avg_performance = {
            team: np.mean(performance) 
            for team, performance in team_performance.items()
        }
        
        # Top 4 teams advance to playoffs
        top_teams = sorted(
            team_avg_performance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:4]
        
        # Add edges from group matches to playoff nodes
        for team, _ in top_teams:
            team_group_matches = [
                node for node in group_nodes 
                if node.team == team or node.opponent == team
            ]
            
            # Connect to appropriate playoff
            if team == top_teams[0][0]:  # Top seed
                for node in nodes:
                    if node.node_id == "qualifier1":
                        self.graph.add_edge(
                            f"{team}_group_complete", 
                            node.node_id,
                            capacity=1.0,
                            flow_type="advancement"
                        )
            
            elif team == top_teams[3][0]:  # 4th seed
                for node in nodes:
                    if node.node_id == "qualifier1":
                        self.graph.add_edge(
                            f"{team}_group_complete",
                            node.node_id,
                            capacity=1.0,
                            flow_type="advancement"
                        )
            
            elif team == top_teams[1][0]:  # 2nd seed
                for node in nodes:
                    if node.node_id == "qualifier2":
                        self.graph.add_edge(
                            f"{team}_group_complete",
                            node.node_id,
                            capacity=1.0,
                            flow_type="advancement"
                        )
            
            elif team == top_teams[2][0]:  # 3rd seed
                for node in nodes:
                    if node.node_id == "qualifier2":
                        self.graph.add_edge(
                            f"{team}_group_complete",
                            node.node_id,
                            capacity=1.0,
                            flow_type="advancement"
                        )
    
    def compute_max_flow_path(
        self,
        source_team: str,
        target_team: str = "championship"
    ) -> TournamentPath:
        """Compute maximum flow path from source to target."""
        
        try:
            # Create source and sink nodes
            source_node = f"{source_team}_source"
            sink_node = "tournament_sink"
            
            # Add source/sink if not present
            if source_node not in self.graph:
                self.graph.add_node(source_node, type="source")
            if sink_node not in self.graph:
                self.graph.add_node(sink_node, type="sink")
            
            # Connect source to team's matches
            team_nodes = [
                n for n, d in self.graph.nodes(data=True)
                if d.get("team") == source_team and "vs" in n
            ]
            
            for node_id in team_nodes:
                self.graph.add_edge(
                    source_node,
                    node_id,
                    capacity=1.0,
                    flow_type="team_entry"
                )
            
            # Connect final to sink
            if "final" in self.graph:
                self.graph.add_edge(
                    "final",
                    sink_node,
                    capacity=1.0,
                    flow_type="championship"
                )
            
            # Compute max flow
            flow_value = nx.maximum_flow_value(
                self.graph, 
                source_node, 
                sink_node
            )
            
            # Get flow paths
            flow_dict = nx.maximum_flow(
                self.graph,
                source_node,
                sink_node
            )
            
            # Extract path from flow
            path_nodes = self._extract_path_from_flow(flow_dict, source_team)
            
            return TournamentPath(
                path_nodes=path_nodes,
                total_probability=self._compute_path_probability(path_nodes),
                min_flow_value=flow_value,
                critical_matches=self._identify_critical_matches(flow_dict)
            )
            
        except Exception as e:
            print(f"Error computing max flow path: {e}")
            # Return fallback path
            return TournamentPath(
                path_nodes=[],
                total_probability=0.0,
                min_flow_value=0.0,
                critical_matches=[]
            )
    
    def _extract_path_from_flow(
        self, 
        flow_dict: Dict[str, Dict[str, float]], 
        source_team: str
    ) -> List[TournamentNode]:
        """Extract tournament path from flow dictionary."""
        
        path_nodes = []
        
        # Find matches with positive flow for source team
        for edge_u, edge_v in flow_dict.items():
            if edge_u == f"{source_team}_source":
                # This is a match the team can reach
                if edge_v in self.nodes:
                    path_nodes.append(self.nodes[edge_v])
        
        # Add playoff progression (simplified)
        playoff_matches = ["qualifier1", "qualifier2", "final"]
        for match_id in playoff_matches:
            if match_id in self.nodes:
                path_nodes.append(self.nodes[match_id])
        
        return path_nodes
    
    def _compute_path_probability(self, path_nodes: List[TournamentNode]) -> float:
        """Compute total probability of tournament path."""
        
        if not path_nodes:
            return 0.0
        
        # Multiply probabilities along the path
        total_prob = 1.0
        for node in path_nodes:
            total_prob *= node.win_probability
        
        return total_prob
    
    def _identify_critical_matches(
        self, 
        flow_dict: Dict[str, Dict[str, float]]
    ) -> List[str]:
        """Identify critical matches with high flow."""
        
        critical_matches = []
        
        for edge_u, edge_v_dict in flow_dict.items():
            for edge_v, flow_value in edge_v_dict.items():
                if flow_value > 0.8:  # High flow threshold
                    critical_matches.append(edge_v)
        
        return critical_matches
    
    def get_tournament_analysis(
        self,
        teams: List[str]
    ) -> Dict[str, Any]:
        """Get comprehensive tournament analysis."""
        
        # Compute team strengths
        team_strengths = {}
        for team in teams:
            team_nodes = [
                n for n, d in self.graph.nodes(data=True)
                if d.get("team") == team
            ]
            
            if team_nodes:
                avg_win_prob = np.mean([
                    d.get("win_prob", 0.5) 
                    for n, d in self.graph.nodes(data=True)
                    if d.get("team") == team
                ])
                team_strengths[team] = avg_win_prob
            else:
                team_strengths[team] = 0.5
        
        # Sort teams by strength
        ranked_teams = sorted(
            team_strengths.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "team_rankings": [
                {"team": team, "strength": strength}
                for team, strength in ranked_teams
            ],
            "tournament_structure": {
                "total_nodes": len(self.graph.nodes),
                "total_edges": len(self.graph.edges),
                "stages": ["group", "playoff"],
                "format": "IPL T20"
            },
            "key_insights": self._generate_tournament_insights(team_strengths)
        }
    
    def _generate_tournament_insights(self, team_strengths: Dict[str, float]) -> List[str]:
        """Generate insights about tournament structure."""
        
        insights = []
        
        if team_strengths:
            strongest_team = max(team_strengths.items(), key=lambda x: x[1])
            weakest_team = min(team_strengths.items(), key=lambda x: x[1])
            
            insights.append(f"{strongest_team[0]} has highest tournament strength ({strongest_team[1]:.1%})")
            insights.append(f"{weakest_team[0]} has lowest tournament strength ({weakest_team[1]:.1%})")
            
            # Competitive balance
            strength_std = np.std(list(team_strengths.values()))
            if strength_std < 0.1:
                insights.append("Tournament appears highly competitive")
            elif strength_std > 0.2:
                insights.append("Tournament has clear favorites and underdogs")
        
        return insights
    
    def update_match_result(
        self,
        match_id: str,
        actual_win: bool
    ) -> None:
        """Update graph with actual match result."""
        
        if match_id in self.nodes:
            node = self.nodes[match_id]
            node.is_played = True
            
            # Update node data in graph
            if self.graph.has_node(match_id):
                self.graph.nodes[match_id]["is_played"] = True
                self.graph.nodes[match_id]["actual_win"] = actual_win
    
    def get_graph_visualization_data(self) -> Dict[str, Any]:
        """Get graph data formatted for visualization."""
        
        nodes_data = []
        edges_data = []
        
        for node_id, node in self.nodes.items():
            nodes_data.append({
                "id": node_id,
                "team": node.team,
                "opponent": node.opponent,
                "venue": node.venue,
                "win_probability": node.win_probability,
                "is_played": node.is_played,
                "stage": "group" if "vs" in node_id else "playoff"
            })
        
        for edge_u, edge_v, edge_data in self.graph.edges(data=True):
            edges_data.append({
                "source": edge_u,
                "target": edge_v,
                "flow_type": edge_data.get("flow_type", "unknown"),
                "capacity": edge_data.get("capacity", 0.0)
            })
        
        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "layout": "hierarchical"  # Suggested layout
        }
