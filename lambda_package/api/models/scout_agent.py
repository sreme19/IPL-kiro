"""
api/models/scout_agent.py
========================
S3 Parquet tensor reads + form adjustment for Scout Agent.
"""

import os
import json
import pandas as pd
import pyarrow.parquet as pq
import boto3
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .schemas import Player


class ScoutAgent:
    """Reads pre-computed tensors from S3 and adjusts for player form."""
    
    def __init__(self):
        self.data_bucket = os.environ.get("DATA_BUCKET", "local")
        self.tensors_cache = {}
        self.form_cache = {}
        
        # Initialize S3 client if bucket is configured
        if self.data_bucket != "local":
            self.s3 = boto3.client('s3')
        else:
            self.s3 = None
            # Use local tensors directory
            self.local_tensors_dir = Path(__file__).parent.parent.parent / "data" / "tensors"
    
    def load_season_tensors(self, season: int) -> pd.DataFrame:
        """Load tensor data for a specific season."""
        
        cache_key = f"season_{season}"
        if cache_key in self.tensors_cache:
            return self.tensors_cache[cache_key]
        
        try:
            if self.s3:
                # Load from S3
                s3_key = f"tensors/season={season}/tensors.parquet"
                response = self.s3.get_object(Bucket=self.data_bucket, Key=s3_key)
                df = pd.read_parquet(response['Body'].read())
            else:
                # Load from local filesystem
                parquet_path = self.local_tensors_dir / f"season={season}" / "tensors.parquet"
                if parquet_path.exists():
                    df = pd.read_parquet(parquet_path)
                else:
                    raise FileNotFoundError(f"No tensor data found for season {season}")
            
            self.tensors_cache[cache_key] = df
            return df
            
        except Exception as e:
            raise RuntimeError(f"Failed to load tensors for season {season}: {e}")
    
    def load_form_data(self) -> pd.DataFrame:
        """Load form EWM data for all players."""
        
        if self.form_cache:
            return self.form_cache
        
        try:
            if self.s3:
                # Load from S3
                s3_key = "tensors/form/form_ewm.parquet"
                response = self.s3.get_object(Bucket=self.data_bucket, Key=s3_key)
                df = pd.read_parquet(response['Body'].read())
            else:
                # Load from local filesystem
                form_path = self.local_tensors_dir / "form" / "form_ewm.parquet"
                if form_path.exists():
                    df = pd.read_parquet(form_path)
                else:
                    raise FileNotFoundError("No form data found")
            
            self.form_cache = df
            return df
            
        except Exception as e:
            raise RuntimeError(f"Failed to load form data: {e}")
    
    def get_player_tensor(
        self, 
        batter: str, 
        bowler: str, 
        venue: str, 
        season: int
    ) -> Dict[str, float]:
        """Get tensor values for a specific (batter, bowler, venue) triplet."""
        
        tensors_df = self.load_season_tensors(season)
        
        # Find matching triplet
        match = tensors_df[
            (tensors_df['batter'] == batter) & 
            (tensors_df['bowler'] == bowler) & 
            (tensors_df['venue'] == venue)
        ]
        
        if len(match) > 0:
            row = match.iloc[0]
            return {
                'avg_runs_per_ball': float(row['avg_runs_per_ball']),
                'dismissal_rate_per_ball': float(row['dismissal_rate_per_ball']),
                'economy_rate': float(row['economy_rate']),
                'boundary_rate': float(row['boundary_rate']),
                'sample_size': int(row['sample_size']),
                'is_fallback': bool(row['is_fallback'])
            }
        
        # Return fallback values if no exact match found
        return {
            'avg_runs_per_ball': 0.8,  # League average
            'dismissal_rate_per_ball': 0.03,
            'economy_rate': 7.0,
            'boundary_rate': 0.15,
            'sample_size': 0,
            'is_fallback': True
        }
    
    def get_player_form(self, player_id: str, metric_type: str) -> float:
        """Get current form score for a player."""
        
        try:
            form_df = self.load_form_data()
            
            # Get most recent form value for this player and metric
            player_form = form_df[
                (form_df['player_id'] == player_id) & 
                (form_df['metric_type'] == metric_type)
            ].sort_values('match_id', ascending=False)
            
            if len(player_form) > 0:
                return float(player_form.iloc[0]['value'])
            
            # Return neutral form if no data
            return 1.0
            
        except Exception:
            return 1.0  # Neutral form on error
    
    def adjust_tensor_for_form(
        self, 
        base_tensor: Dict[str, float], 
        player_form: float,
        position: str = "batsman"
    ) -> Dict[str, float]:
        """Adjust tensor values based on current player form."""
        
        # Form adjustment factors
        form_multiplier = min(max(player_form, 0.5), 2.0)  # Clamp between 0.5x and 2.0x
        
        adjusted = base_tensor.copy()
        
        if position == "batsman":
            adjusted['avg_runs_per_ball'] *= form_multiplier
            adjusted['boundary_rate'] *= form_multiplier
            # Better form reduces dismissal rate
            adjusted['dismissal_rate_per_ball'] /= form_multiplier
        elif position == "bowler":
            # Better form increases economy (more expensive)
            adjusted['economy_rate'] /= form_multiplier
            # Better form increases dismissal rate
            adjusted['dismissal_rate_per_ball'] *= form_multiplier
        
        return adjusted
    
    def get_squad_tensors(
        self, 
        squad_players: List[str], 
        venue: str, 
        season: int
    ) -> Dict[str, Dict[str, float]]:
        """Get tensor data for all players in a squad."""
        
        squad_tensors = {}
        
        for player_id in squad_players:
            # Get form scores
            batting_form = self.get_player_form(player_id, "batting_runs_ewm")
            bowling_form = self.get_player_form(player_id, "bowling_wickets_ewm")
            
            # For each player, we need to consider their matchups
            # This is simplified - in practice, we'd build a matrix
            player_data = {
                'batting_form': batting_form,
                'bowling_form': bowling_form,
                'base_tensors': {}
            }
            
            # Get some sample tensors (this would be expanded in practice)
            for opponent in squad_players:
                if opponent != player_id:
                    tensor = self.get_player_tensor(player_id, opponent, venue, season)
                    
                    # Adjust for form
                    batting_adjusted = self.adjust_tensor_for_form(
                        tensor, batting_form, "batsman"
                    )
                    bowling_adjusted = self.adjust_tensor_for_form(
                        tensor, bowling_form, "bowler"
                    )
                    
                    player_data['base_tensors'][opponent] = {
                        'as_batsman': batting_adjusted,
                        'as_bowler': bowling_adjusted
                    }
            
            squad_tensors[player_id] = player_data
        
        return squad_tensors
    
    def get_player_stats_summary(
        self, 
        player_id: str, 
        season: int
    ) -> Dict[str, float]:
        """Get summary statistics for a player across all venues."""
        
        tensors_df = self.load_season_tensors(season)
        
        # Get all tensors where this player is batter
        batting_stats = tensors_df[tensors_df['batter'] == player_id]
        
        # Get all tensors where this player is bowler  
        bowling_stats = tensors_df[tensors_df['bowler'] == player_id]
        
        return {
            'batting_avg_runs': float(batting_stats['avg_runs_per_ball'].mean()) if len(batting_stats) > 0 else 0.8,
            'batting_dismissal_rate': float(batting_stats['dismissal_rate_per_ball'].mean()) if len(batting_stats) > 0 else 0.03,
            'bowling_economy': float(bowling_stats['economy_rate'].mean()) if len(bowling_stats) > 0 else 7.0,
            'bowling_dismissal_rate': float(bowling_stats['dismissal_rate_per_ball'].mean()) if len(bowling_stats) > 0 else 0.03,
            'total_matchups': len(batting_stats) + len(bowling_stats),
            'venues_played': len(set(batting_stats['venue'].tolist() + bowling_stats['venue'].tolist())),
            'form_score': self.get_player_form(player_id, "batting_runs_ewm")
        }
