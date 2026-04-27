"""
api/tests/conftest.py
======================
Shared pytest fixtures and session-level hooks.

Runs automatically before every test session — no import needed.
The session header written here lets you grep logs/pytest/run.log
to find exactly when a given run started and what code version was tested.
"""

import logging
import os
import sys
import subprocess
import pytest

# Insert the REPO ROOT so `import api` works the same way it does in Lambda
# (handler `api.main.handler` runs from a zip where api/ is a top-level package).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

logger = logging.getLogger("ipl_kiro.tests")


# ─── Session header ────────────────────────────────────────────────────────────

def _git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(__file__),
        ).decode().strip()
    except Exception:
        return "unknown"


def _git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(__file__),
        ).decode().strip()
    except Exception:
        return "unknown"


@pytest.fixture(scope="session", autouse=True)
def log_session_header():
    """
    Writes a timestamped header at the top of every test run log so that
    logs/pytest/run.log is always self-documenting.
    """
    from datetime import datetime, timezone

    rev = _git_revision()
    branch = _git_branch()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    logger.info("=" * 72)
    logger.info("IPL-Kiro test session started")
    logger.info("  Timestamp : %s", now)
    logger.info("  Git branch: %s", branch)
    logger.info("  Git commit: %s", rev)
    logger.info("=" * 72)

    yield

    logger.info("=" * 72)
    logger.info("IPL-Kiro test session finished")
    logger.info("=" * 72)


# ─── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def full_squad():
    """
    A complete 13-player squad reused across unit, functional, and regression
    tests.  Any model schema change that breaks this fixture will surface
    immediately in all three test categories.
    """
    from api.models.schemas import Player, PlayerRole

    return [
        Player(player_id="p1",  name="Batsman 1",      role=PlayerRole.BATSMAN,       is_overseas=False, expected_runs=1.2, expected_wickets=0.0,  form_score=1.0),
        Player(player_id="p2",  name="Batsman 2",      role=PlayerRole.BATSMAN,       is_overseas=False, expected_runs=1.1, expected_wickets=0.0,  form_score=1.0),
        Player(player_id="p3",  name="Batsman 3",      role=PlayerRole.BATSMAN,       is_overseas=False, expected_runs=1.0, expected_wickets=0.0,  form_score=1.0),
        Player(player_id="p4",  name="Batsman 4",      role=PlayerRole.BATSMAN,       is_overseas=False, expected_runs=0.95,expected_wickets=0.0,  form_score=1.0),
        Player(player_id="p5",  name="Wicket Keeper",  role=PlayerRole.WICKET_KEEPER, is_overseas=False, expected_runs=0.9, expected_wickets=0.0,  form_score=1.0),
        Player(player_id="p6",  name="All Rounder 1",  role=PlayerRole.ALL_ROUNDER,   is_overseas=False, expected_runs=0.8, expected_wickets=0.03, form_score=1.0),
        Player(player_id="p7",  name="All Rounder 2",  role=PlayerRole.ALL_ROUNDER,   is_overseas=True,  expected_runs=0.7, expected_wickets=0.04, form_score=1.0),
        Player(player_id="p8",  name="Bowler 1",       role=PlayerRole.BOWLER,        is_overseas=False, expected_runs=0.3, expected_wickets=0.07, form_score=1.0),
        Player(player_id="p9",  name="Bowler 2",       role=PlayerRole.BOWLER,        is_overseas=True,  expected_runs=0.4, expected_wickets=0.06, form_score=1.0),
        Player(player_id="p10", name="Bowler 3",       role=PlayerRole.BOWLER,        is_overseas=False, expected_runs=0.2, expected_wickets=0.07, form_score=1.0),
        Player(player_id="p11", name="Bowler 4",       role=PlayerRole.BOWLER,        is_overseas=True,  expected_runs=0.5, expected_wickets=0.05, form_score=1.0),
        Player(player_id="p12", name="Overseas Bat",   role=PlayerRole.BATSMAN,       is_overseas=True,  expected_runs=1.3, expected_wickets=0.0,  form_score=1.0),
        Player(player_id="p13", name="Overseas Bowl",  role=PlayerRole.BOWLER,        is_overseas=True,  expected_runs=0.6, expected_wickets=0.08, form_score=1.0),
    ]


@pytest.fixture(scope="session")
def balanced_venue():
    """Balanced venue weights — used across all test categories."""
    return {"batting_weight": 0.55, "bowling_weight": 0.45}


@pytest.fixture(scope="session")
def fastapi_client():
    """
    A live TestClient wrapping the FastAPI app.
    Used by functional tests to hit real routes without a network.
    """
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)
