"""
api/tests/test_commentary_schema.py
==================================
Assert CommentaryStep schema exists and is used by ILP solver.
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models.commentary import CommentaryGenerator, InsightType
from api.models.schemas import Player, PlayerRole

pytestmark = pytest.mark.unit


class TestCommentarySchema:
    """Test CommentaryStep schema structure and usage."""
    
    @pytest.fixture
    def generator(self):
        """Commentary generator instance."""
        return CommentaryGenerator()
    
    @pytest.fixture
    def sample_venue_vector(self):
        """Sample venue vector for testing."""
        return {
            "batting_weight": 0.55,
            "bowling_weight": 0.45
        }
    
    @pytest.fixture
    def sample_batters(self):
        """Sample batter data."""
        return [
            {"id": "batter_1", "name": "Batsman 1", "role": "batsman"},
            {"id": "batter_2", "name": "Batsman 2", "role": "batsman"}
        ]
    
    @pytest.fixture
    def sample_bowlers(self):
        """Sample bowler data."""
        return [
            {"id": "bowler_1", "name": "Bowler 1", "role": "bowler"},
            {"id": "bowler_2", "name": "Bowler 2", "role": "bowler"}
        ]
    
    @pytest.fixture
    def sample_edges(self):
        """Sample threat edges."""
        return [
            {
                "batter_id": "batter_1",
                "bowler_id": "bowler_1",
                "weight": 0.8,
                "threat_level": "high"
            },
            {
                "batter_id": "batter_2",
                "bowler_id": "bowler_2",
                "weight": 0.4,
                "threat_level": "medium"
            }
        ]
    
    def test_commentary_generator_exists(self, generator):
        """Test: CommentaryGenerator class exists."""
        assert generator is not None, "CommentaryGenerator should be instantiable"
    
    def test_insight_type_enum(self):
        """Test: InsightType enum has all required values."""
        expected_types = [
            InsightType.VENUE_ENCODING,
            InsightType.BIPARTITE_THREAT,
            InsightType.ILP_SOLUTION,
            InsightType.MONTE_CARLO
        ]
        
        actual_types = list(InsightType)
        for expected_type in expected_types:
            assert expected_type in actual_types, \
                f"InsightType {expected_type} should exist"
    
    def test_generate_venue_encoding(self, generator, sample_venue_vector):
        """Test: venue encoding step generation."""
        
        step = generator.generate_venue_encoding(sample_venue_vector)
        
        assert step.step_number == 1, \
            f"Venue encoding should be step 1, got {step.step_number}"
        
        assert step.insight_type == InsightType.VENUE_ENCODING, \
            f"Insight type should be venue_encoding, got {step.insight_type}"
        
        assert "Venue" in step.title, \
            f"Title should mention venue, got {step.title}"
        
        assert "α+β=1.0" in step.formula, \
            f"Formula should contain constraint, got {step.formula}"
        
        assert step.description, \
            "Description should not be empty"
        
        assert step.insight, \
            "Insight should not be empty"
    
    def test_generate_bipartite_threat(self, generator, sample_batters, sample_bowlers, sample_edges):
        """Test: bipartite threat step generation."""
        
        step = generator.generate_bipartite_threat(sample_batters, sample_bowlers, sample_edges)
        
        assert step.step_number == 2, \
            f"Bipartite threat should be step 2, got {step.step_number}"
        
        assert step.insight_type == InsightType.BIPARTITE_THREAT, \
            f"Insight type should be bipartite_threat, got {step.insight_type}"
        
        assert "threat(" in step.formula, \
            f"Formula should contain threat function, got {step.formula}"
        
        assert step.graph_data is not None, \
            "Graph data should be provided for step 2"
        
        assert "batters" in step.graph_data, \
            "Graph data should contain batters"
        
        assert "bowlers" in step.graph_data, \
            "Graph data should contain bowlers"
        
        assert "edges" in step.graph_data, \
            "Graph data should contain edges"
    
    def test_generate_ilp_solution(self, generator):
        """Test: ILP solution step generation."""
        
        selected_players = [
            {"id": "player_1", "name": "Selected 1", "role": "batsman"},
            {"id": "player_2", "name": "Selected 2", "role": "bowler"}
        ]
        
        excluded_players = [
            {"id": "player_3", "name": "Excluded 1", "role": "batsman"}
        ]
        
        objective_value = 15.5
        baseline_value = 12.0
        
        step = generator.generate_ilp_solution(
            selected_players, excluded_players, objective_value, baseline_value
        )
        
        assert step.step_number == 3, \
            f"ILP solution should be step 3, got {step.step_number}"
        
        assert step.insight_type == InsightType.ILP_SOLUTION, \
            f"Insight type should be ilp_solution, got {step.insight_type}"
        
        assert "max Σ(" in step.formula, \
            f"Formula should contain max sum, got {step.formula}"
        
        assert "xᵢ" in step.formula, \
            f"Formula should contain decision variables, got {step.formula}"
        
        assert "improves" in step.insight.lower(), \
            f"Insight should mention improvement, got {step.insight}"
    
    def test_generate_monte_carlo(self, generator):
        """Test: Monte Carlo step generation."""
        
        win_probability = 0.65
        confidence_interval = (0.58, 0.72)
        calibration_applied = True
        
        step = generator.generate_monte_carlo(
            win_probability, confidence_interval, calibration_applied
        )
        
        assert step.step_number == 4, \
            f"Monte Carlo should be step 4, got {step.step_number}"
        
        assert step.insight_type == InsightType.MONTE_CARLO, \
            f"Insight type should be monte_carlo, got {step.insight_type}"
        
        assert "P(win)" in step.formula, \
                f"Formula should contain probability, got {step.formula}"
        
        assert "10,000" in step.formula, \
            f"Formula should mention sample size, got {step.formula}"
        
        assert "65.0%" in step.insight, \
            f"Insight should contain win probability, got {step.insight}"
        
        assert "±" in step.insight, \
            f"Insight should contain confidence interval, got {step.insight}"
        
        assert "Platt scaling" in step.insight, \
            f"Insight should mention calibration when applied, got {step.insight}"
    
    def test_generate_commentary_array(self, generator, sample_venue_vector, sample_batters, sample_bowlers, sample_edges):
        """Test: complete commentary array generation."""
        
        commentary_steps = generator.generate_commentary(
            venue_vector=sample_venue_vector,
            batters=sample_batters,
            bowlers=sample_bowlers,
            edges=sample_edges,
            selected_players=[{"id": "p1", "name": "P1", "role": "batsman"}],
            excluded_players=[{"id": "p2", "name": "P2", "role": "bowler"}],
            objective_value=15.5,
            baseline_value=12.0,
            win_probability=0.65,
            confidence_interval=(0.58, 0.72),
            calibration_applied=False
        )
        
        assert len(commentary_steps) == 4, \
            f"Expected 4 commentary steps, got {len(commentary_steps)}"
        
        # Check step numbers are sequential
        step_numbers = [step.step_number for step in commentary_steps]
        assert step_numbers == [1, 2, 3, 4], \
            f"Expected steps [1,2,3,4], got {step_numbers}"
        
        # Check insight types are correct
        insight_types = [step.insight_type for step in commentary_steps]
        expected_types = [
            InsightType.VENUE_ENCODING,
            InsightType.BIPARTITE_THREAT,
            InsightType.ILP_SOLUTION,
            InsightType.MONTE_CARLO
        ]
        assert insight_types == expected_types, \
            f"Expected insight types {expected_types}, got {insight_types}"
        
        # Check all steps have required fields
        for i, step in enumerate(commentary_steps):
            assert step.title, f"Step {i+1} should have title"
            assert step.formula, f"Step {i+1} should have formula"
            assert step.description, f"Step {i+1} should have description"
            assert step.insight, f"Step {i+1} should have insight"
    
    def test_step_titles_are_descriptive(self, generator, sample_venue_vector):
        """Test: step titles are descriptive and unique."""
        
        step1 = generator.generate_venue_encoding(sample_venue_vector)
        step2 = generator.generate_bipartite_threat([], [], [])
        step3 = generator.generate_ilp_solution([], [], 10.0, 8.0)
        step4 = generator.generate_monte_carlo(0.6, (0.5, 0.7), False)
        
        titles = [step1.title, step2.title, step3.title, step4.title]
        
        # All titles should be unique
        assert len(set(titles)) == 4, \
            "All step titles should be unique"
        
        # All titles should be descriptive
        for i, title in enumerate(titles):
            assert len(title) > 5, \
                f"Step {i+1} title should be descriptive, got: '{title}'"
    
    def test_formulas_are_mathematical(self, generator, sample_venue_vector):
        """Test: formulas contain mathematical expressions."""
        
        step1 = generator.generate_venue_encoding(sample_venue_vector)
        step2 = generator.generate_bipartite_threat([], [], [])
        step3 = generator.generate_ilp_solution([], [], 10.0, 8.0)
        step4 = generator.generate_monte_carlo(0.6, (0.5, 0.7), False)
        
        formulas = [step1.formula, step2.formula, step3.formula, step4.formula]
        
        mathematical_symbols = ["α", "β", "Σ", "xᵢ", "P(win)", "f(", "="]
        
        for i, formula in enumerate(formulas):
            has_math = any(symbol in formula for symbol in mathematical_symbols)
            assert has_math, \
                f"Step {i+1} formula should contain math symbols: '{formula}'"
    
    def test_insights_are_actionable(self, generator, sample_venue_vector):
        """Test: insights provide actionable information."""
        
        step1 = generator.generate_venue_encoding(sample_venue_vector)
        step2 = generator.generate_bipartite_threat(
            [{"id": "b1", "name": "B1", "role": "batsman"}],
            [{"id": "b2", "name": "B2", "role": "bowler"}],
            [{"batter_id": "b1", "bowler_id": "b2", "weight": 0.8, "threat_level": "high"}]
        )
        step3 = generator.generate_ilp_solution([], [], 15.5, 12.0)
        step4 = generator.generate_monte_carlo(0.65, (0.58, 0.72), True)
        
        insights = [step1.insight, step2.insight, step3.insight, step4.insight]
        
        for i, insight in enumerate(insights):
            assert len(insight) > 10, \
                f"Step {i+1} insight should be substantial, got: '{insight}'"
            
            # Check for actionable keywords
            actionable_keywords = ["favor", "threat", "improves", "probability", "advantage", "calibration"]
            has_actionable = any(keyword in insight.lower() for keyword in actionable_keywords)
            assert has_actionable, \
                f"Step {i+1} insight should be actionable, got: '{insight}'"
