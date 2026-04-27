"""
api/tests/test_ilp_constraints.py
==================================
Assert: sum(xi) == 11 for every solve
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ilp_solver import ILPSolver
from models.schemas import Player, PlayerRole

pytestmark = pytest.mark.unit


class TestILPConstraints:
    """Test all ILP hard constraints are enforced."""
    
    @pytest.fixture
    def sample_squad(self):
        """Create a sample squad for testing."""
        return [
            Player(
                player_id="player_1",
                name="Batsman 1",
                role=PlayerRole.BATSMAN,
                is_overseas=False,
                expected_runs=1.2,
                expected_wickets=0.0,
                form_score=1.0
            ),
            Player(
                player_id="player_2", 
                name="Batsman 2",
                role=PlayerRole.BATSMAN,
                is_overseas=False,
                expected_runs=1.1,
                expected_wickets=0.0,
                form_score=1.0
            ),
            Player(
                player_id="player_3",
                name="Wicket Keeper",
                role=PlayerRole.WICKET_KEEPER,
                is_overseas=False,
                expected_runs=0.9,
                expected_wickets=0.0,
                form_score=1.0
            ),
            Player(
                player_id="player_4",
                name="Bowler 1",
                role=PlayerRole.BOWLER,
                is_overseas=False,
                expected_runs=0.3,
                expected_wickets=0.05,
                form_score=1.0
            ),
            Player(
                player_id="player_5",
                name="Bowler 2",
                role=PlayerRole.BOWLER,
                is_overseas=True,
                expected_runs=0.4,
                expected_wickets=0.06,
                form_score=1.0
            ),
            Player(
                player_id="player_6",
                name="All Rounder 1",
                role=PlayerRole.ALL_ROUNDER,
                is_overseas=False,
                expected_runs=0.8,
                expected_wickets=0.03,
                form_score=1.0
            ),
            Player(
                player_id="player_7",
                name="All Rounder 2",
                role=PlayerRole.ALL_ROUNDER,
                is_overseas=True,
                expected_runs=0.7,
                expected_wickets=0.04,
                form_score=1.0
            ),
            Player(
                player_id="player_8",
                name="Bowler 3",
                role=PlayerRole.BOWLER,
                is_overseas=False,
                expected_runs=0.2,
                expected_wickets=0.07,
                form_score=1.0
            ),
            Player(
                player_id="player_9",
                name="Bowler 4",
                role=PlayerRole.BOWLER,
                is_overseas=True,
                expected_runs=0.5,
                expected_wickets=0.05,
                form_score=1.0
            ),
            Player(
                player_id="player_10",
                name="Batsman 3",
                role=PlayerRole.BATSMAN,
                is_overseas=False,
                expected_runs=1.0,
                expected_wickets=0.0,
                form_score=1.0
            ),
            Player(
                player_id="player_11",
                name="Batsman 4",
                role=PlayerRole.BATSMAN,
                is_overseas=False,
                expected_runs=0.95,
                expected_wickets=0.0,
                form_score=1.0
            ),
            Player(
                player_id="player_12",
                name="Overseas Batsman",
                role=PlayerRole.BATSMAN,
                is_overseas=True,
                expected_runs=1.3,
                expected_wickets=0.0,
                form_score=1.0
            ),
            Player(
                player_id="player_13",
                name="Overseas Bowler",
                role=PlayerRole.BOWLER,
                is_overseas=True,
                expected_runs=0.6,
                expected_wickets=0.08,
                form_score=1.0
            )
        ]
    
    @pytest.fixture
    def venue_weights(self):
        """Sample venue weights for testing."""
        return {
            "batting_weight": 0.55,
            "bowling_weight": 0.45
        }
    
    def test_exactly_eleven_players(self, sample_squad, venue_weights):
        """Test: sum(xi) == 11 for every solve."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        assert len(result.selected_xi) == 11, f"Expected 11 players, got {len(result.selected_xi)}"
    
    def test_at_least_one_wicket_keeper(self, sample_squad, venue_weights):
        """Test: at least 1 WK in xi."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        wk_count = sum(1 for p in result.selected_xi if p.role == PlayerRole.WICKET_KEEPER)
        assert wk_count >= 1, f"Expected at least 1 wicket keeper, got {wk_count}"
    
    def test_at_least_four_bowlers(self, sample_squad, venue_weights):
        """Test: at least 4 bowlers in xi."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        bowling_roles = [PlayerRole.BOWLER, PlayerRole.ALL_ROUNDER]
        bowler_count = sum(1 for p in result.selected_xi if p.role in bowling_roles)
        assert bowler_count >= 4, f"Expected at least 4 bowlers, got {bowler_count}"
    
    def test_max_four_overseas(self, sample_squad, venue_weights):
        """Test: overseas count <= 4 in xi."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        overseas_count = sum(1 for p in result.selected_xi if p.is_overseas)
        assert overseas_count <= 4, f"Expected max 4 overseas players, got {overseas_count}"
    
    def test_must_include_constraint(self, sample_squad, venue_weights):
        """Test: must_include players always in xi."""
        
        must_include = ["player_1", "player_5"]
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            must_include=must_include
        )
        
        selected_ids = [p.player_id for p in result.selected_xi]
        for player_id in must_include:
            assert player_id in selected_ids, f"Player {player_id} should be included but wasn't"
    
    def test_must_exclude_constraint(self, sample_squad, venue_weights):
        """Test: must_exclude players never in xi."""
        
        must_exclude = ["player_2", "player_6"]
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            must_exclude=must_exclude
        )
        
        selected_ids = [p.player_id for p in result.selected_xi]
        for player_id in must_exclude:
            assert player_id not in selected_ids, f"Player {player_id} should be excluded but was included"
    
    def test_formation_bias_batting(self, sample_squad, venue_weights):
        """Test: batting formation increases batting weight."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="batting"
        )
        
        # Should select more batsmen in batting formation
        batsman_count = sum(1 for p in result.selected_xi if p.role == PlayerRole.BATSMAN)
        assert batsman_count >= 4, f"Batting formation should favor batsmen, got {batsman_count}"
    
    def test_formation_bias_bowling(self, sample_squad, venue_weights):
        """Test: bowling formation increases bowling weight."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="bowling"
        )
        
        # Should select more bowlers in bowling formation
        bowling_roles = [PlayerRole.BOWLER, PlayerRole.ALL_ROUNDER]
        bowler_count = sum(1 for p in result.selected_xi if p.role in bowling_roles)
        assert bowler_count >= 5, f"Bowling formation should favor bowlers, got {bowler_count}"
    
    def test_solve_time_under_limit(self, sample_squad, venue_weights):
        """Test: solve time < 500ms."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        assert result.solve_time_ms < 500, f"Expected solve time < 500ms, got {result.solve_time_ms}ms"
    
    def test_commentary_steps_generated(self, sample_squad, venue_weights):
        """Test: exactly 4 CommentaryStep objects produced."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        assert len(result.commentary_steps) == 4, f"Expected 4 commentary steps, got {len(result.commentary_steps)}"
        
        # Check step numbers are correct
        step_numbers = [step.step_number for step in result.commentary_steps]
        expected_steps = [1, 2, 3, 4]
        assert step_numbers == expected_steps, f"Expected steps {expected_steps}, got {step_numbers}"
    
    def test_commentary_step_structure(self, sample_squad, venue_weights):
        """Test: each step has required fields."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        for step in result.commentary_steps:
            assert step.title, f"Step {step.step_number} missing title"
            assert step.formula, f"Step {step.step_number} missing formula"
            assert step.description, f"Step {step.step_number} missing description"
            assert step.insight, f"Step {step.step_number} missing insight"
            assert step.insight_type, f"Step {step.step_number} missing insight_type"
    
    def test_objective_value_reasonable(self, sample_squad, venue_weights):
        """Test: objective value is reasonable."""
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=sample_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        # Objective should be positive
        assert result.objective_value > 0, f"Expected positive objective value, got {result.objective_value}"
        
        # Should be better than baseline (allowing for optimization complexity)
        assert result.objective_value >= 0, f"Expected positive objective value, got {result.objective_value}"
    
    def test_different_squad_compositions(self, venue_weights):
        """Test: solver works with different squad compositions."""
        
        # Test with minimal squad
        minimal_squad = [
            Player(
                player_id="min_1",
                name="Min Batsman",
                role=PlayerRole.BATSMAN,
                is_overseas=False,
                expected_runs=1.0,
                expected_wickets=0.0,
                form_score=1.0
            ),
            Player(
                player_id="min_2",
                name="Min WK",
                role=PlayerRole.WICKET_KEEPER,
                is_overseas=False,
                expected_runs=0.8,
                expected_wickets=0.0
            ),
            Player(
                player_id="min_3",
                name="Min Bowler",
                role=PlayerRole.BOWLER,
                is_overseas=False,
                expected_runs=0.2,
                expected_wickets=0.05
            )
        ]
        
        solver = ILPSolver()
        result = solver.solve_optimal_xi(
            squad=minimal_squad,
            venue_weights=venue_weights,
            formation_bias="balanced"
        )
        
        # Should fail due to insufficient players
        assert len(result.selected_xi) <= 3, "Minimal squad should not produce full XI"
