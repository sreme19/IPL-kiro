"""
api/middleware/error_reporter.py
===============================
Auto-create Linear bug tickets on 5xx exceptions.
"""

import os
import json
import traceback
import time
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from linear import Linear
    LINEAR_AVAILABLE = True
except ImportError:
    LINEAR_AVAILABLE = False


class ErrorReporterMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically create Linear bug tickets on 5xx errors."""
    
    def __init__(self, app, linear_api_key: Optional[str] = None):
        super().__init__(app)
        self.linear_api_key = linear_api_key or os.environ.get("LINEAR_API_KEY")
        self.linear_client = None
        
        if self.linear_api_key and LINEAR_AVAILABLE:
            try:
                self.linear_client = Linear.api(self.linear_api_key)
                # Get or create team/project
                self.team_id = self._get_or_create_team()
                self.project_id = self._get_or_create_project()
            except Exception as e:
                print(f"Failed to initialize Linear client: {e}")
                self.linear_client = None
    
    async def dispatch(self, request: Request, call_next):
        """Process request and handle errors."""
        
        try:
            response = await call_next(request)
            
            # Check for 5xx status codes
            if hasattr(response, 'status_code') and response.status_code >= 500:
                await self._handle_server_error(request, response)
            
            return response
            
        except HTTPException as e:
            # HTTP exceptions are typically client errors (4xx)
            # Only report 5xx
            if e.status_code >= 500:
                await self._handle_http_exception(request, e)
            raise
            
        except Exception as e:
            # Unexpected server errors
            await self._handle_unexpected_error(request, e)
            raise
    
    async def _handle_server_error(self, request: Request, response) -> None:
        """Handle server error responses."""
        
        try:
            error_data = {
                "status_code": response.status_code,
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "unknown"),
                "timestamp": time.time(),
                "traceback": "Server error response"
            }
            
            await self._create_linear_ticket(error_data)
            
        except Exception as e:
            print(f"Failed to handle server error: {e}")
    
    async def _handle_http_exception(self, request: Request, exception: HTTPException) -> None:
        """Handle HTTP exceptions (5xx only)."""
        
        try:
            error_data = {
                "status_code": exception.status_code,
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "unknown"),
                "timestamp": time.time(),
                "error_type": type(exception).__name__,
                "detail": exception.detail,
                "traceback": traceback.format_exc()
            }
            
            await self._create_linear_ticket(error_data)
            
        except Exception as e:
            print(f"Failed to handle HTTP exception: {e}")
    
    async def _handle_unexpected_error(self, request: Request, exception: Exception) -> None:
        """Handle unexpected server exceptions."""
        
        try:
            error_data = {
                "status_code": 500,
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "unknown"),
                "timestamp": time.time(),
                "error_type": type(exception).__name__,
                "detail": str(exception),
                "traceback": traceback.format_exc()
            }
            
            await self._create_linear_ticket(error_data)
            
        except Exception as e:
            print(f"Failed to handle unexpected error: {e}")
    
    async def _create_linear_ticket(self, error_data: Dict[str, Any]) -> None:
        """Create Linear bug ticket from error data."""
        
        if not self.linear_client:
            print("Linear client not available - skipping ticket creation")
            return
        
        try:
            # Extract relevant context from request
            url = error_data.get("url", "")
            method = error_data.get("method", "")
            status_code = error_data.get("status_code", 500)
            error_type = error_data.get("error_type", "Unknown")
            detail = error_data.get("detail", "")[:80]  # Truncate for title
            traceback_str = error_data.get("traceback", "")
            
            # Try to extract context from URL or headers
            match_id = self._extract_match_id(url)
            venue_id = self._extract_venue_id(url)
            xi_hash = self._extract_xi_hash(error_data.get("headers", {}))
            
            # Create ticket title
            title = f"[BUG] {method} {status_code} {error_type}: {detail}"
            
            # Create ticket description
            description = f"""
## Error Details
- **Status Code**: {status_code}
- **Method**: {method}
- **URL**: {url}
- **Error Type**: {error_type}
- **Detail**: {error_data.get('detail', 'No details available')}
- **Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(error_data.get('timestamp', time.time())))}

## Request Context
- **Client IP**: {error_data.get('client_ip', 'unknown')}
- **User Agent**: {error_data.get('user_agent', 'unknown')}
- **Match ID**: {match_id or 'Not identified'}
- **Venue ID**: {venue_id or 'Not identified'}
- **XI Hash**: {xi_hash or 'Not identified'}

## Stack Trace
```
{traceback_str}
```

## Priority
This is a server error affecting user experience. Priority: Urgent.
"""
            
            # Create ticket in Linear
            issue = self.linear_client.issue_create(
                team_id=self.team_id,
                project_id=self.project_id,
                title=title,
                description=description,
                priority_id="1",  # Urgent priority
                state_id="1"     # Todo/Backlog state
            )
            
            print(f"Created Linear ticket: {issue.id} - {title}")
            
        except Exception as e:
            print(f"Failed to create Linear ticket: {e}")
    
    def _extract_match_id(self, url: str) -> Optional[str]:
        """Extract match ID from URL or headers."""
        
        # Try to extract from URL path
        if "/match/" in url:
            parts = url.split("/match/")
            if len(parts) > 1:
                remaining = parts[1].split("?")[0]  # Remove query params
                if "/" in remaining:
                    return remaining.split("/")[0]
                return remaining
        
        return None
    
    def _extract_venue_id(self, url: str) -> Optional[str]:
        """Extract venue ID from URL or headers."""
        
        # Try to extract from URL query params
        if "venue=" in url:
            parts = url.split("venue=")
            if len(parts) > 1:
                return parts[1].split("&")[0].split("/")[0]
        
        return None
    
    def _extract_xi_hash(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract XI hash from request headers."""
        
        # Look for custom headers that might identify the XI
        xi_headers = ["x-xi-hash", "x-team-composition", "x-squad-hash"]
        
        for header in xi_headers:
            if header.lower() in [h.lower() for h in headers.keys()]:
                return headers[header]
        
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        
        # Check various headers for real IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to client IP
        if hasattr(request, 'client'):
            return request.client.host if request.client else "unknown"
        
        return "unknown"
    
    def _get_or_create_team(self) -> str:
        """Get or create Linear team for IPL Simulator."""
        
        try:
            # Try to find existing team
            teams = self.linear_client.teams()
            for team in teams:
                if "IPL" in team.name or "Simulator" in team.name:
                    return team.id
            
            # Create new team if not found
            team = self.linear_client.team_create(
                name="IPL Simulator",
                description="AI-powered cricket team selection and simulation"
            )
            return team.id
            
        except Exception as e:
            print(f"Failed to get/create Linear team: {e}")
            return "unknown"
    
    def _get_or_create_project(self) -> str:
        """Get or create Linear project for backend issues."""
        
        try:
            # Try to find existing project
            projects = self.linear_client.projects(self.team_id)
            for project in projects:
                if "Backend" in project.name or "API" in project.name:
                    return project.id
            
            # Create new project if not found
            project = self.linear_client.project_create(
                team_id=self.team_id,
                name="Backend API Issues",
                description="Bug reports and issues for the IPL Simulator backend"
            )
            return project.id
            
        except Exception as e:
            print(f"Failed to get/create Linear project: {e}")
            return "unknown"


def setup_error_reporting(app, linear_api_key: Optional[str] = None):
    """Setup error reporting middleware for FastAPI app."""
    
    if LINEAR_AVAILABLE:
        app.add_middleware(ErrorReporterMiddleware, linear_api_key=linear_api_key)
        print("Linear error reporting middleware enabled")
    else:
        print("Linear SDK not available - error reporting disabled")
        
    # Add exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler."""
        
        error_data = {
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": time.time()
        }
        
        # Log the full error
        print(f"Unhandled exception: {exc}")
        print(traceback.format_exc())
        
        # Return JSON response
        return JSONResponse(
            status_code=500,
            content=error_data
        )
