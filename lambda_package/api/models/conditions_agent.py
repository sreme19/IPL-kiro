"""
api/models/conditions_agent.py
============================
venue_vec computation from venue_geometry.json for Conditions Agent.
"""

import os
import json
from typing import Dict, Tuple
from pathlib import Path


class ConditionsAgent:
    """Computes venue vectors based on geometry and historical data."""
    
    def __init__(self):
        # Load venue geometry data
        reference_dir = Path(__file__).parent.parent.parent / "data" / "reference"
        venue_geom_path = reference_dir / "venue_geometry.json"
        
        with open(venue_geom_path) as f:
            self.venue_data = json.load(f)
        
        # Venue characteristics mapping
        self.venue_factors = {
            # Batting-friendly venues (high scores, small boundaries)
            "batting_boost": {
                "M Chinnaswamy Stadium": 1.15,  # Bangalore
                "MA Chidambaram Stadium": 1.10,  # Chennai
                "Wankhede Stadium": 1.08,  # Mumbai
                "Eden Gardens": 1.05,  # Kolkata
            },
            # Bowling-friendly venues (low scores, helpful conditions)
            "bowling_boost": {
                "M. A. Chidambaram Stadium": 0.85,  # Chennai (certain conditions)
                "Sawai Mansingh Stadium": 0.90,  # Jaipur
                "Nehru Stadium": 0.88,  # Kochi
            },
            # High-scoring venues (flat pitches)
            "high_scoring": {
                "M Chinnaswamy Stadium": 1.20,
                "Punjab Cricket Association Stadium": 1.18,  # Mohali
                "Brabourne Stadium": 1.15,  # Delhi
            },
            # Variable conditions (weather/dew impact)
            "variable_conditions": {
                "M. Chinnaswamy Stadium": 0.7,  # Evening dew factor
                "Eden Gardens": 0.6,  # Humidity impact
                "Wankhede Stadium": 0.5,  # Sea breeze
            }
        }
    
    def get_venue_boundaries(self, venue: str) -> Dict[str, float]:
        """Get boundary dimensions for a venue."""
        
        venue_info = self.venue_data.get("venues", {}).get(venue, {})
        return venue_info.get("boundaries", {
            "straight": 75,  # meters
            "square": 65    # meters
        })
    
    def compute_venue_size_factor(self, venue: str) -> float:
        """Compute size factor based on boundary dimensions."""
        
        boundaries = self.get_venue_boundaries(venue)
        straight = boundaries.get("straight", 75)
        square = boundaries.get("square", 65)
        
        # Average boundary size (smaller = higher scoring)
        avg_boundary = (straight + square) / 2
        
        # Normalize around standard IPL venue (70m average)
        # Smaller boundaries get higher factor
        size_factor = 70 / avg_boundary
        
        return min(max(size_factor, 0.8), 1.3)  # Clamp between 0.8 and 1.3
    
    def get_venue_historical_stats(self, venue: str) -> Dict[str, float]:
        """Get historical scoring patterns for venue."""
        
        # This would typically come from database of past matches
        # For now, use venue-specific factors
        batting_boost = self.venue_factors["batting_boost"].get(venue, 1.0)
        bowling_boost = self.venue_factors["bowling_boost"].get(venue, 1.0)
        high_scoring = self.venue_factors["high_scoring"].get(venue, 1.0)
        
        return {
            "batting_boost": batting_boost,
            "bowling_boost": bowling_boost,
            "high_scoring": high_scoring,
            "avg_first_innings": 160 * high_scoring,  # Typical score
            "chasing_success": 0.55 if batting_boost > 1.0 else 0.45
        }
    
    def compute_time_of_day_factor(self, venue: str, match_time: str = "day") -> str:
        """Determine time of day impact for venue."""
        
        variable_factor = self.venue_factors["variable_conditions"].get(venue, 0.0)
        
        if variable_factor > 0.6:
            return "evening_dew_likely" if match_time == "night" else "day_stable"
        elif variable_factor > 0.4:
            return "humidity_affected"
        else:
            return "stable_conditions"
    
    def compute_weather_adjustment(
        self, 
        venue: str, 
        weather: str = "clear",
        season: int = 2023
    ) -> Dict[str, float]:
        """Compute weather-based adjustments."""
        
        # Weather impact factors
        weather_factors = {
            "clear": {"batting": 1.0, "bowling": 1.0},
            "cloudy": {"batting": 0.95, "bowling": 1.05},  # Swing conditions
            "humid": {"batting": 0.90, "bowling": 1.10},  # Dew later
            "dry": {"batting": 1.05, "bowling": 0.95},  # Dry pitch
            "rain_interruption": {"batting": 0.85, "bowling": 1.15}  # Seamer-friendly
        }
        
        base_factors = weather_factors.get(weather, weather_factors["clear"])
        
        # Adjust for venue characteristics
        venue_type = self.compute_time_of_day_factor(venue)
        
        if venue_type == "evening_dew_likely" and weather == "humid":
            # Enhanced dew effect
            base_factors["batting"] *= 0.9
            base_factors["bowling"] *= 1.1
        
        return base_factors
    
    def compute_venue_vector(
        self, 
        venue: str, 
        formation_bias: str = "balanced",
        weather: str = "clear",
        match_time: str = "day"
    ) -> Dict[str, float]:
        """Compute complete venue vector for optimization."""
        
        # Base factors
        size_factor = self.compute_venue_size_factor(venue)
        historical = self.get_venue_historical_stats(venue)
        weather_adj = self.compute_weather_adjustment(venue, weather)
        time_factor = self.compute_time_of_day_factor(venue, match_time)
        
        # Combine batting and bowling weights
        base_batting_weight = historical["batting_boost"] * size_factor * weather_adj["batting"]
        base_bowling_weight = historical["bowling_boost"] * (2.0 - size_factor) * weather_adj["bowling"]
        
        # Normalize to sum to 1.0
        total_weight = base_batting_weight + base_bowling_weight
        batting_weight = base_batting_weight / total_weight
        bowling_weight = base_bowling_weight / total_weight
        
        # Apply formation bias
        if formation_bias == "batting":
            batting_weight = batting_weight * 1.18  # α=0.65
            bowling_weight = bowling_weight * 0.82   # β=0.35
        elif formation_bias == "bowling":
            batting_weight = batting_weight * 0.82   # α=0.35
            bowling_weight = bowling_weight * 1.18   # β=0.65
        else:  # balanced
            batting_weight = batting_weight * 1.10  # α=0.55
            bowling_weight = bowling_weight * 0.90   # β=0.45
        
        # Renormalize
        total_weight = batting_weight + bowling_weight
        final_batting = batting_weight / total_weight
        final_bowling = bowling_weight / total_weight
        
        return {
            "batting_weight": final_batting,
            "bowling_weight": final_bowling,
            "size_factor": size_factor,
            "weather_adjustment": weather_adj,
            "time_conditions": time_factor,
            "venue_type": self._classify_venue_type(venue),
            "expected_first_innings": historical["avg_first_innings"],
            "chasing_advantage": historical["chasing_success"]
        }
    
    def _classify_venue_type(self, venue: str) -> str:
        """Classify venue type based on characteristics."""
        
        boundaries = self.get_venue_boundaries(venue)
        avg_boundary = (boundaries.get("straight", 75) + boundaries.get("square", 65)) / 2
        
        if avg_boundary < 65:
            return "small_batting_friendly"
        elif avg_boundary > 75:
            return "large_bowling_friendly"
        else:
            return "neutral"
    
    def get_venue_analysis(self, venue: str) -> Dict[str, any]:
        """Get comprehensive venue analysis."""
        
        vector = self.compute_venue_vector(venue)
        boundaries = self.get_venue_boundaries(venue)
        historical = self.get_venue_historical_stats(venue)
        
        return {
            "venue_name": venue,
            "boundaries": boundaries,
            "size_classification": self._classify_venue_type(venue),
            "historical_performance": historical,
            "optimization_weights": {
                "batting_weight": vector["batting_weight"],
                "bowling_weight": vector["bowling_weight"]
            },
            "key_insights": self._generate_venue_insights(venue, vector)
        }
    
    def _generate_venue_insights(self, venue: str, vector: Dict[str, float]) -> list[str]:
        """Generate venue-specific insights."""
        
        insights = []
        
        batting_weight = vector["batting_weight"]
        
        if batting_weight > 0.60:
            insights.append(f"{venue} strongly favors batting - expect high scores")
        elif batting_weight < 0.40:
            insights.append(f"{venue} favors bowling - lower scoring expected")
        else:
            insights.append(f"{venue} offers balanced conditions")
        
        if vector["size_factor"] > 1.1:
            insights.append("Small boundaries increase boundary probability")
        elif vector["size_factor"] < 0.9:
            insights.append("Large ground makes boundaries harder")
        
        if vector["time_conditions"] == "evening_dew_likely":
            insights.append("Evening dew may help bowlers later")
        
        return insights
