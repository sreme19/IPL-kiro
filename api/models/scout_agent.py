"""
api/models/scout_agent.py
========================
S3 JSON tensor reads + form adjustment for Scout Agent.
Uses JSON (not Parquet/pandas) for Lambda compatibility.
"""

import os
import json
import boto3
import logging
from typing import Dict, List, Optional
from botocore.exceptions import ClientError

from api.models.schemas import Player

logger = logging.getLogger(__name__)

FALLBACK_TENSOR: Dict[str, float] = {
    'avg_runs_per_ball': 0.8,
    'dismissal_rate_per_ball': 0.03,
    'economy_rate': 7.0,
    'boundary_rate': 0.15,
    'sample_size': 0,
    'is_fallback': True,
}


class ScoutAgent:
    """Reads pre-computed tensors from S3 (JSON) and adjusts for player form."""

    def __init__(self):
        self.data_bucket = os.environ.get("S3_BUCKET", "")
        self.tensors_cache: Dict[str, dict] = {}
        self.form_cache: Dict[str, float] = {}
        self.s3 = boto3.client('s3') if self.data_bucket else None

    def _load_json_from_s3(self, key: str) -> Optional[dict]:
        """Load a JSON object from S3, returning None on any error."""
        if not self.s3 or not self.data_bucket:
            return None
        try:
            response = self.s3.get_object(Bucket=self.data_bucket, Key=key)
            return json.loads(response['Body'].read())
        except ClientError as e:
            logger.warning("S3 fetch failed for %s: %s", key, e)
            return None

    def load_season_tensors(self, season: int) -> dict:
        """Load tensor data for a specific season (JSON from S3)."""
        cache_key = f"season_{season}"
        if cache_key in self.tensors_cache:
            return self.tensors_cache[cache_key]
        data = self._load_json_from_s3(f"tensors/season={season}/tensors.json") or {}
        self.tensors_cache[cache_key] = data
        return data

    def load_form_data(self) -> dict:
        """Load form EWM data for all players (JSON from S3)."""
        if self.form_cache:
            return self.form_cache
        data = self._load_json_from_s3("tensors/form/form_ewm.json") or {}
        self.form_cache = data
        return data

    def get_player_tensor(
        self,
        batter: str,
        bowler: str,
        venue: str,
        season: int,
    ) -> Dict[str, float]:
        """Get tensor values for a (batter, bowler, venue) triplet."""
        tensors = self.load_season_tensors(season)
        key = f"{batter}|{bowler}|{venue}"
        return tensors.get(key, FALLBACK_TENSOR)

    def get_player_form(self, player_id: str, metric_type: str) -> float:
        """Get current form score for a player."""
        try:
            form = self.load_form_data()
            return float(form.get(player_id, {}).get(metric_type, 1.0))
        except Exception:
            return 1.0

    def adjust_tensor_for_form(
        self,
        base_tensor: Dict[str, float],
        player_form: float,
        position: str = "batsman",
    ) -> Dict[str, float]:
        """Adjust tensor values based on current player form."""
        form_multiplier = min(max(player_form, 0.5), 2.0)
        adjusted = base_tensor.copy()
        if position == "batsman":
            adjusted['avg_runs_per_ball'] *= form_multiplier
            adjusted['boundary_rate'] *= form_multiplier
            adjusted['dismissal_rate_per_ball'] /= form_multiplier
        elif position == "bowler":
            adjusted['economy_rate'] /= form_multiplier
            adjusted['dismissal_rate_per_ball'] *= form_multiplier
        return adjusted

    def get_squad_tensors(
        self,
        squad_players: List[str],
        venue: str,
        season: int,
    ) -> Dict[str, Dict]:
        """Get tensor data for all players in a squad."""
        squad_tensors = {}
        for player_id in squad_players:
            batting_form = self.get_player_form(player_id, "batting_runs_ewm")
            bowling_form = self.get_player_form(player_id, "bowling_wickets_ewm")
            player_data: Dict = {
                'batting_form': batting_form,
                'bowling_form': bowling_form,
                'base_tensors': {},
            }
            for opponent in squad_players:
                if opponent != player_id:
                    tensor = self.get_player_tensor(player_id, opponent, venue, season)
                    player_data['base_tensors'][opponent] = {
                        'as_batsman': self.adjust_tensor_for_form(tensor, batting_form, "batsman"),
                        'as_bowler': self.adjust_tensor_for_form(tensor, bowling_form, "bowler"),
                    }
            squad_tensors[player_id] = player_data
        return squad_tensors

    def get_player_stats_summary(self, player_id: str, season: int) -> Dict[str, float]:
        """Get summary statistics for a player (fallback values when no S3 data)."""
        form = self.get_player_form(player_id, "batting_runs_ewm")
        return {
            'batting_avg_runs': 0.8,
            'batting_dismissal_rate': 0.03,
            'bowling_economy': 7.0,
            'bowling_dismissal_rate': 0.03,
            'total_matchups': 0,
            'venues_played': 0,
            'form_score': form,
        }
