"""
api/main.py
===========
FastAPI backend with Mangum Lambda wrapper for IPL Captain Simulator.
"""

import os
from fastapi import FastAPI
from mangum import Mangum

from routers import simulation, match, tournament, stats

app = FastAPI(
    title="IPL Captain Simulator API",
    description="AI-powered cricket team selection and match simulation",
    version="1.0.0"
)

# Include routers
app.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])
app.include_router(match.router, prefix="/api/match", tags=["match"])
app.include_router(tournament.router, prefix="/api/tournament", tags=["tournament"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

@app.get("/")
async def root():
    return {"message": "IPL Captain Simulator API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
