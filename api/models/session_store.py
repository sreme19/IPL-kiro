"""
api/models/session_store.py
==========================
DynamoDB read/write for session state with TTL.
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


@dataclass
class SessionState:
    simulation_id: str
    form_vec: Dict[str, float]  # player_id -> EWM form score
    calibration_log: List[Dict[str, float]]  # [{predicted, actual}]
    squad_fatigue: Dict[str, float]  # player_id -> fatigue score
    created_at: float
    expires_at: float
    matches_played: int = 0


class SessionStore:
    """DynamoDB session storage with TTL and form tracking."""
    
    def __init__(self):
        self.table_name = os.environ.get("DYNAMODB_TABLE", os.environ.get("DYNAMODB_SESSIONS", "ipl-simulator-sessions"))
        self.counters_table = os.environ.get("DYNAMODB_COUNTERS", self.table_name + "-counters")
        
        # Initialize DynamoDB clients
        self.dynamodb = boto3.resource('dynamodb')
        self.client = boto3.client('dynamodb')
        
        # Get table references
        self.sessions_table = self.dynamodb.Table(self.table_name)
        self.counters_table = self.dynamodb.Table(self.counters_table)
        
        # Only auto-create tables when running locally (env var not set by SAM)
        if not os.environ.get("DYNAMODB_TABLE"):
            self._ensure_tables_exist()
    
    def _ensure_tables_exist(self) -> None:
        """Ensure DynamoDB tables exist with proper configuration."""
        
        try:
            # Check sessions table
            self.client.describe_table(TableName=self.table_name)
        except self.client.exceptions.ResourceNotFoundException:
            # Create sessions table
            self.client.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'simulation_id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'simulation_id',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST',
                TimeToLiveSpecification={
                    'AttributeName': 'expires_at',
                    'Enabled': True
                }
            )
        
        try:
            # Check counters table
            self.client.describe_table(TableName=self.counters_table)
        except self.client.exceptions.ResourceNotFoundException:
            # Create counters table
            self.client.create_table(
                TableName=self.counters_table,
                KeySchema=[
                    {
                        'AttributeName': 'counter_name',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'counter_name',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
    
    def create_session(self, simulation_id: str) -> SessionState:
        """Create a new simulation session."""
        
        now = time.time()
        expires_at = now + (7 * 24 * 60 * 60)  # 7 days TTL
        
        session = SessionState(
            simulation_id=simulation_id,
            form_vec={},  # Initialize empty form vector
            calibration_log=[],
            squad_fatigue={},
            matches_played=0,
            created_at=now,
            expires_at=expires_at
        )
        
        # Store in DynamoDB
        try:
            self.sessions_table.put_item(
                Item={
                    'simulation_id': simulation_id,
                    'data': json.dumps(asdict(session))
                }
            )
            
            # Increment session counter
            self._increment_counter('total_sessions')
            
            return session
            
        except ClientError as e:
            raise RuntimeError(f"Failed to create session: {e}")
    
    def get_session(self, simulation_id: str) -> Optional[SessionState]:
        """Retrieve session state from DynamoDB."""
        
        try:
            response = self.sessions_table.get_item(
                Key={'simulation_id': simulation_id}
            )
            
            if 'Item' in response:
                data = json.loads(response['Item']['data'])
                return SessionState(**data)
            
            return None
            
        except ClientError as e:
            print(f"Error retrieving session {simulation_id}: {e}")
            return None
    
    def update_session(self, session: SessionState) -> bool:
        """Update existing session state."""
        
        try:
            # Update with new TTL
            session.expires_at = time.time() + (7 * 24 * 60 * 60)
            
            self.sessions_table.put_item(
                Item={
                    'simulation_id': session.simulation_id,
                    'data': json.dumps(asdict(session))
                }
            )
            
            return True
            
        except ClientError as e:
            print(f"Error updating session {session.simulation_id}: {e}")
            return False
    
    def update_form_vector(
        self, 
        simulation_id: str, 
        player_updates: Dict[str, float]
    ) -> bool:
        """Update form vector for specific players."""
        
        session = self.get_session(simulation_id)
        if not session:
            return False
        
        # Update form vector with EWM
        for player_id, new_form_score in player_updates.items():
            current_form = session.form_vec.get(player_id, 1.0)
            # EWM update: new_form = α*current + (1-α)*new
            alpha = 0.4
            updated_form = alpha * current_form + (1 - alpha) * new_form_score
            session.form_vec[player_id] = updated_form
        
        return self.update_session(session)
    
    def add_calibration_point(
        self, 
        simulation_id: str, 
        predicted: float, 
        actual: float
    ) -> bool:
        """Add a calibration point for Platt scaling."""
        
        session = self.get_session(simulation_id)
        if not session:
            return False
        
        # Add calibration point
        calibration_point = {
            'predicted': predicted,
            'actual': actual,
            'timestamp': time.time()
        }
        
        session.calibration_log.append(calibration_point)
        
        # Keep only last 50 points
        if len(session.calibration_log) > 50:
            session.calibration_log = session.calibration_log[-50:]
        
        return self.update_session(session)
    
    def update_fatigue(
        self, 
        simulation_id: str, 
        player_fatigue_updates: Dict[str, float]
    ) -> bool:
        """Update squad fatigue scores."""
        
        session = self.get_session(simulation_id)
        if not session:
            return False
        
        # Update fatigue with decay
        for player_id, fatigue_change in player_fatigue_updates.items():
            current_fatigue = session.squad_fatigue.get(player_id, 0.0)
            updated_fatigue = current_fatigue + fatigue_change
            session.squad_fatigue[player_id] = max(0.0, min(1.0, updated_fatigue))
        
        return self.update_session(session)
    
    def increment_matches_played(self, simulation_id: str) -> bool:
        """Increment matches played counter."""
        
        session = self.get_session(simulation_id)
        if not session:
            return False
        
        session.matches_played += 1
        
        # Apply fatigue decay after each match
        for player_id in session.squad_fatigue:
            session.squad_fatigue[player_id] *= 0.9  # Decay fatigue
        
        return self.update_session(session)
    
    def get_session_summary(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Get session summary for analytics."""
        
        session = self.get_session(simulation_id)
        if not session:
            return None
        
        # Calculate form statistics
        form_values = list(session.form_vec.values())
        fatigue_values = list(session.squad_fatigue.values())
        
        # Calculate calibration accuracy
        calibration_accuracy = 0.0
        if len(session.calibration_log) > 0:
            correct_predictions = sum(
                1 for point in session.calibration_log
                if abs(point['predicted'] - point['actual']) < 0.1
            )
            calibration_accuracy = correct_predictions / len(session.calibration_log)
        
        return {
            'simulation_id': session.simulation_id,
            'matches_played': session.matches_played,
            'session_age_hours': (time.time() - session.created_at) / 3600,
            'form_vector_size': len(session.form_vec),
            'fatigue_vector_size': len(session.squad_fatigue),
            'calibration_points': len(session.calibration_log),
            'calibration_accuracy': calibration_accuracy,
            'avg_form_score': sum(form_values) / len(form_values) if form_values else 1.0,
            'avg_fatigue_score': sum(fatigue_values) / len(fatigue_values) if fatigue_values else 0.0,
            'top_form_players': sorted(
                session.form_vec.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
            'most_fatigued_players': sorted(
                session.squad_fatigue.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }
    
    def _increment_counter(self, counter_name: str) -> None:
        """Increment a named counter."""
        
        try:
            self.counters_table.update_item(
                Key={'counter_name': counter_name},
                UpdateExpression='ADD #val :inc',
                ExpressionAttributeNames={'#val': 'value'},
                ExpressionAttributeValues={':inc': 1},
                ReturnValues='UPDATED_NEW'
            )
        except ClientError:
            # Counter doesn't exist, create it
            self.counters_table.put_item(
                Item={
                    'counter_name': counter_name,
                    'value': 1
                }
            )
    
    def get_counter(self, counter_name: str) -> int:
        """Get current counter value."""
        
        try:
            response = self.counters_table.get_item(
                Key={'counter_name': counter_name}
            )
            
            if 'Item' in response:
                return response['Item'].get('value', 0)
            
            return 0
            
        except ClientError:
            return 0
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global usage statistics."""
        
        total_sessions = self.get_counter('total_sessions')
        total_matches = self.get_counter('total_matches')
        claude_spend = self.get_counter('claude_spend_cents')
        
        return {
            'total_sessions': total_sessions,
            'total_matches': total_matches,
            'total_claude_spend_cents': claude_spend,
            'total_claude_spend_usd': claude_spend / 100,
            'avg_matches_per_session': total_matches / max(1, total_sessions),
            'monthly_budget_usd': 20.0,
            'budget_remaining_usd': max(0, 20.0 - (claude_spend / 100)),
            'budget_usage_percentage': min(100, (claude_spend / 2000) * 100)
        }
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (should be handled by TTL)."""
        
        # This is mainly for manual cleanup or testing
        # DynamoDB TTL should handle this automatically
        now = time.time()
        expired_count = 0
        
        try:
            # Scan for expired sessions
            response = self.client.scan(
                TableName=self.table_name,
                FilterExpression='#expires_at < :now',
                ExpressionAttributeNames={'#expires_at': 'expires_at'},
                ExpressionAttributeValues={':now': now},
                ProjectionExpression='simulation_id'
            )
            
            # Delete expired sessions
            for item in response.get('Items', []):
                self.sessions_table.delete_item(
                    Key={'simulation_id': item['simulation_id']}
                )
                expired_count += 1
            
            return expired_count
            
        except ClientError as e:
            print(f"Error cleaning expired sessions: {e}")
            return 0
    
    def delete_session(self, simulation_id: str) -> bool:
        """Delete a specific session."""
        
        try:
            self.sessions_table.delete_item(
                Key={'simulation_id': simulation_id}
            )
            return True
        except ClientError as e:
            print(f"Error deleting session {simulation_id}: {e}")
            return False
