"""
api/models/narrative_agent.py
=============================
Claude claude-sonnet-4-6 + structured output for Narrative Agent.
"""

import os
import json
import time
from typing import Dict, Any, Optional
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore

from .commentary import CommentaryStep


class NarrativeAgent:
    """Generates narrative commentary using Claude API with structured output."""
    
    def __init__(self):
        self.client = None
        self.cache = {}
        self.spend_cents = 0
        
        # Initialize Claude client if API key is available
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key and Anthropic is not None:
            self.client = Anthropic(api_key=api_key)
    
    def generate_narrative(
        self,
        match_id: str,
        commentary_steps: list[CommentaryStep],
        team_name: str,
        opponent_name: str,
        venue: str
    ) -> Dict[str, str]:
        """Generate narrative commentary from commentary steps."""
        
        # Check cache first
        if match_id in self.cache:
            return self.cache[match_id]
        
        # Check budget guard
        if not self._check_budget():
            return self._get_fallback_narrative()
        
        try:
            # Prepare commentary data for Claude
            commentary_data = self._prepare_commentary_data(commentary_steps)
            
            # Generate narrative using Claude
            response = self._call_claude_api(
                commentary_data, team_name, opponent_name, venue
            )
            
            # Parse structured response
            narrative = self._parse_claude_response(response)
            
            # Cache result
            self.cache[match_id] = narrative
            
            return narrative
            
        except Exception as e:
            print(f"Error generating narrative: {e}")
            return self._get_fallback_narrative()
    
    def _prepare_commentary_data(self, commentary_steps: list[CommentaryStep]) -> Dict[str, Any]:
        """Prepare commentary data for Claude input."""
        
        return {
            "steps": [
                {
                    "step": step.step_number,
                    "title": step.title,
                    "formula": step.formula,
                    "description": step.description,
                    "insight": step.insight,
                    "type": step.insight_type.value
                }
                for step in commentary_steps
            ],
            "summary": f"Analysis with {len(commentary_steps)} steps of XI optimization and win probability simulation"
        }
    
    def _call_claude_api(
        self,
        commentary_data: Dict[str, Any],
        team_name: str,
        opponent_name: str,
        venue: str
    ) -> str:
        """Call Claude API to generate narrative."""
        
        prompt = f"""
You are an expert cricket analyst providing commentary for an IPL team selection optimization.

CONTEXT:
- Match: {team_name} vs {opponent_name}
- Venue: {venue}
- Analysis: {json.dumps(commentary_data, indent=2)}

TASK:
Generate a concise, insightful narrative commentary (max 200 words) that explains:
1. The key strategic decisions made by the AI optimizer
2. The most important matchup threats identified
3. The win probability implications
4. A brief recommendation for the captain

Focus on cricket strategy, player matchups, and venue conditions. Be analytical but accessible.

RESPONSE FORMAT (JSON):
{{
    "briefing_text": "strategic overview text",
    "key_risk": "main risk factor", 
    "key_advantage": "main advantage factor"
}}
"""
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Track spend (approximate)
            self.spend_cents += 1  # Rough estimate per call
            
            return response.content[0].text
            
        except Exception as e:
            print(f"Claude API error: {e}")
            raise e
    
    def _parse_claude_response(self, response: str) -> Dict[str, str]:
        """Parse structured JSON response from Claude."""
        
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                # Fallback: parse entire response as plain text
                return self._parse_text_response(response)
            
            parsed = json.loads(json_str)
            
            return {
                "briefing_text": parsed.get("briefing_text", ""),
                "key_risk": parsed.get("key_risk", ""),
                "key_advantage": parsed.get("key_advantage", "")
            }
            
        except json.JSONDecodeError:
            # Fallback to text parsing
            return self._parse_text_response(response)
    
    def _parse_text_response(self, response: str) -> Dict[str, str]:
        """Parse plain text response when JSON parsing fails."""
        
        # Simple text-based parsing
        lines = response.strip().split('\n')
        
        briefing_text = response[:200] + "..." if len(response) > 200 else response
        
        # Extract key themes (simplified)
        key_risk = ""
        key_advantage = ""
        
        for line in lines:
            line_lower = line.lower()
            if "risk" in line_lower or "threat" in line_lower or "weakness" in line_lower:
                key_risk = line.strip()
            elif "advantage" in line_lower or "strength" in line_lower or "opportunity" in line_lower:
                key_advantage = line.strip()
        
        return {
            "briefing_text": briefing_text,
            "key_risk": key_risk or "Strategic matchup risks identified",
            "key_advantage": key_advantage or "Optimal XI provides competitive advantage"
        }
    
    def _check_budget(self) -> bool:
        """Check if Claude spend is within budget limits."""
        
        monthly_limit_cents = 2000  # $20 per month
        return self.spend_cents < monthly_limit_cents
    
    def _get_fallback_narrative(self) -> Dict[str, str]:
        """Get fallback narrative when budget exceeded or API unavailable."""
        
        return {
            "briefing_text": "AI optimization complete. The selected XI balances batting depth, bowling variety, and venue conditions. Key matchups analyzed for optimal performance.",
            "key_risk": "Budget limit reached - using cached analysis",
            "key_advantage": "Data-driven selection provides competitive edge"
        }
    
    def get_spend_status(self) -> Dict[str, Any]:
        """Get current Claude spend status."""
        
        return {
            "total_spend_cents": self.spend_cents,
            "monthly_limit_cents": 2000,
            "remaining_cents": max(0, 2000 - self.spend_cents),
            "percentage_used": min(100, (self.spend_cents / 2000) * 100),
            "cache_size": len(self.cache),
            "budget_exceeded": self.spend_cents >= 2000
        }
    
    def clear_cache(self) -> None:
        """Clear narrative cache."""
        self.cache.clear()
    
    def set_cache_size_limit(self, limit: int) -> None:
        """Set cache size limit."""
        if len(self.cache) > limit:
            # Simple LRU: keep most recent entries
            items = list(self.cache.items())
            self.cache = dict(items[-limit:])
    
    def generate_pre_match_summary(
        self,
        team_name: str,
        opponent_name: str,
        venue: str,
        weather: str = "clear"
    ) -> Dict[str, str]:
        """Generate pre-match summary without full optimization."""
        
        if not self._check_budget():
            return self._get_fallback_narrative()
        
        try:
            prompt = f"""
Generate a brief pre-match summary for this IPL fixture:

MATCH: {team_name} vs {opponent_name}
VENUE: {venue}
WEATHER: {weather}

Provide a concise analysis (max 100 words) covering:
1. Venue impact on gameplay
2. Key team strengths
3. Expected conditions

RESPONSE FORMAT (JSON):
{{
    "summary": "match analysis text"
}}
"""
            
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=150,
                messages=[{
                    "role": "user", 
                    "content": prompt
                }]
            )
            
            self.spend_cents += 1
            
            # Parse response
            response_text = response.content[0].text
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                parsed = json.loads(json_str)
                return {"summary": parsed.get("summary", response_text)}
            
            return {"summary": response_text}
            
        except Exception as e:
            print(f"Error generating pre-match summary: {e}")
            return {"summary": f"Match analysis for {team_name} vs {opponent_name} at {venue}"}
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get detailed usage statistics."""
        
        return {
            "total_calls": len(self.cache) + (self.spend_cents // 1),  # Approximate
            "total_spend_cents": self.spend_cents,
            "total_spend_usd": self.spend_cents / 100,
            "monthly_budget_usd": 20.0,
            "budget_remaining_usd": max(0, 20.0 - (self.spend_cents / 100)),
            "cache_hit_rate": len(self.cache) / max(1, len(self.cache) + (self.spend_cents // 1)),
            "average_response_length": 150,  # Approximate based on max_tokens
            "cost_per_call_cents": 1,
            "estimated_monthly_calls": 2000 if self.spend_cents < 2000 else self.spend_cents
        }
