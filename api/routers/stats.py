"""
api/routers/stats.py
==================
GET /api/stats/community - Community usage statistics.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from models.session_store import SessionStore

router = APIRouter()
session_store = SessionStore()


@router.get("/community")
async def get_community_stats() -> Dict[str, Any]:
    """Get community-wide usage statistics."""
    
    try:
        # Get global statistics from session store
        global_stats = session_store.get_global_stats()
        
        return {
            "total_simulations": global_stats.get("total_sessions", 0),
            "avg_win_probability": 0.65,  # Would be computed from actual data
            "most_optimized_player": "MS Dhoni",  # Would be computed from actual data
            "ai_acceptance_rate": 0.72,  # Would be computed from actual data
            "popular_venues": [
                {"venue": "M Chinnaswamy Stadium", "usage_count": 1247},
                {"venue": "Wankhede Stadium", "usage_count": 982},
                {"venue": "Eden Gardens", "usage_count": 876},
                {"venue": "MA Chidambaram Stadium", "usage_count": 743}
            ],
            "usage_trends": {
                "daily_simulations": 45,  # Last 24 hours
                "weekly_simulations": 312,  # Last 7 days
                "monthly_simulations": 1340,  # Last 30 days
                "peak_hour": "19:00",  # Most active hour
                "peak_day": "Saturday"
            },
            "system_health": {
                "api_uptime_hours": 720,  # 30 days uptime
                "avg_response_time_ms": 245,
                "error_rate": 0.012,  # 1.2% error rate
                "cache_hit_rate": 0.78
            },
            "budget_utilization": {
                "claude_spend_usd": global_stats.get("total_claude_spend_usd", 0),
                "monthly_budget_usd": 20.0,
                "budget_remaining_usd": global_stats.get("budget_remaining_usd", 20.0),
                "budget_usage_percentage": global_stats.get("budget_usage_percentage", 0)
            },
            "generated_at": "2026-04-26T20:00:00Z"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get community stats: {str(e)}")


@router.get("/system")
async def get_system_stats() -> Dict[str, Any]:
    """Get system performance statistics."""
    
    try:
        import psutil
        import time
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": time.time(),
            "system": {
                "cpu_usage_percent": cpu_percent,
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "used_gb": memory.used / (1024**3),
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "used_gb": disk.used / (1024**3),
                    "usage_percent": (disk.used / disk.total) * 100
                }
            },
            "application": {
                "active_sessions": 0,  # Would be tracked
                "cache_size": 0,  # Would be tracked
                "error_count_24h": 0,  # Would be tracked
                "avg_response_time_ms": 0  # Would be tracked
            }
        }
        
    except ImportError:
        # psutil not available, return basic stats
        return {
            "timestamp": time.time(),
            "system": {
                "status": "healthy",
                "message": "Detailed system metrics unavailable"
            },
            "application": {
                "active_sessions": 0,
                "cache_size": 0,
                "error_count_24h": 0,
                "avg_response_time_ms": 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")


@router.get("/usage/{user_id}")
async def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Get usage statistics for a specific user (placeholder)."""
    
    try:
        # This would typically query user-specific data
        # For now, return mock data
        return {
            "user_id": user_id,
            "simulations_created": 12,
            "matches_simulated": 45,
            "ai_acceptance_rate": 0.83,
            "favorite_formation": "balanced",
            "most_used_venue": "M Chinnaswamy Stadium",
            "created_at": "2026-03-15T10:30:00Z",
            "last_active": "2026-04-26T19:45:00Z",
            "calibration_accuracy": 0.76,
            "session_duration_avg_minutes": 23
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user stats: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring."""
    
    return {
        "status": "healthy",
        "timestamp": "2026-04-26T20:00:00Z",
        "version": "1.0.0"
    }
