"""
api/routers/matches.py
======================
GET /api/matches/list  — list historical matches for a team/season
GET /api/matches/{match_id} — match details with actual XI played
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import os

router = APIRouter()

# City → full stadium name (matches frontend VENUES list)
CITY_TO_VENUE = {
    "mumbai":     "Wankhede Stadium",
    "navi mumbai": "Wankhede Stadium",
    "chennai":    "M. A. Chidambaram Stadium",
    "kolkata":    "Eden Gardens",
    "bangalore":  "M. Chinnaswamy Stadium",
    "bengaluru":  "M. Chinnaswamy Stadium",
    "ahmedabad":  "Narendra Modi Stadium",
    "mohali":     "Punjab Cricket Association Stadium",
    "chandigarh": "Punjab Cricket Association Stadium",
    "hyderabad":  "Rajiv Gandhi International Stadium",
    "jaipur":     "Sawai Mansingh Stadium",
    "delhi":      "Arun Jaitley Stadium",
    "pune":       "MCA Stadium, Pune",
    "lucknow":    "BRSABV Ekana Cricket Stadium",
}

# Full team name → frontend squad id
TEAM_TO_SQUAD_ID = {
    "chennai super kings":        "csk",
    "mumbai indians":             "mi",
    "royal challengers bangalore": "rcb",
    "royal challengers bengaluru": "rcb",
    "kolkata knight riders":      "kkr",
    "rajasthan royals":           "rr",
    "sunrisers hyderabad":        "srh",
    "delhi capitals":             "dc",
    "punjab kings":               "pbks",
    "kings xi punjab":            "pbks",
    "gujarat titans":             "gt",
    "lucknow super giants":       "lsg",
}


def _get_db():
    try:
        import duckdb
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ipl.duckdb")
        db_path = os.path.abspath(db_path)
        if not os.path.exists(db_path):
            return None
        return duckdb.connect(db_path, read_only=True)
    except Exception:
        return None


def _resolve_venue(city: str) -> str:
    return CITY_TO_VENUE.get(city.lower(), city)


def _resolve_opponent_id(team_name: str) -> str:
    return TEAM_TO_SQUAD_ID.get(team_name.lower(), team_name.lower().replace(" ", "_"))


def _normalise_team(name: str) -> str:
    """Convert squad id or partial name to a SQL LIKE fragment."""
    name_lower = name.lower()
    for full, sid in TEAM_TO_SQUAD_ID.items():
        if sid == name_lower or full == name_lower:
            return full.title()
    return name


@router.get("/list")
async def list_matches(
    team: str = Query(..., description="Team name or squad id, e.g. 'csk' or 'Chennai Super Kings'"),
    season: Optional[int] = Query(None, description="Season year, e.g. 2023. Omit for all seasons."),
    opponent: Optional[str] = Query(None, description="Filter to matches vs this opponent team/squad id."),
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    """List past IPL matches for a team, optionally filtered by season and/or opponent."""
    con = _get_db()

    full_name_fragment = _normalise_team(team)

    if con is None:
        return {"matches": [], "total": 0, "error": "Database unavailable — no historical data loaded"}

    try:
        season_clause = f"AND season = {season}" if season else ""

        # If opponent supplied, restrict to head-to-head matches only
        if opponent:
            opp_fragment = _normalise_team(opponent)
            opp_clause = f"""
                AND (
                    (LOWER(team_1) LIKE LOWER('%{full_name_fragment}%') AND LOWER(team_2) LIKE LOWER('%{opp_fragment}%'))
                    OR
                    (LOWER(team_2) LIKE LOWER('%{full_name_fragment}%') AND LOWER(team_1) LIKE LOWER('%{opp_fragment}%'))
                )
            """
            team_clause = ""
        else:
            opp_clause = ""
            team_clause = f"""
                (LOWER(team_1) LIKE LOWER('%{full_name_fragment}%')
                 OR LOWER(team_2) LIKE LOWER('%{full_name_fragment}%'))
            """

        where = f"WHERE {team_clause or '1=1'} {opp_clause} {season_clause}"

        sql = f"""
            SELECT DISTINCT match_id, season, date, venue, team_1, team_2, winner
            FROM matches
            {where}
            ORDER BY date DESC
            LIMIT {limit}
        """
        rows = con.execute(sql).fetchall()

        matches = []
        for match_id, s, date, city, t1, t2, winner in rows:
            # Determine opponent from our team's perspective
            is_team1 = full_name_fragment.lower() in t1.lower()
            our_team = t1 if is_team1 else t2
            opponent = t2 if is_team1 else t1
            result = "won" if winner and full_name_fragment.lower() in winner.lower() else "lost"

            matches.append({
                "match_id": match_id,
                "season": s,
                "date": str(date),
                "city": city,
                "venue": _resolve_venue(city),
                "our_team": our_team,
                "opponent": opponent,
                "opponent_squad_id": _resolve_opponent_id(opponent),
                "winner": winner or "No result",
                "result": result,
            })

        return {"matches": matches, "total": len(matches)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Match list query failed: {str(e)}")
    finally:
        con.close()


@router.get("/{match_id}")
async def get_match_detail(match_id: str) -> Dict[str, Any]:
    """Get match details including the actual XI played by each team."""
    con = _get_db()
    if con is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Basic match info
        row = con.execute("""
            SELECT DISTINCT match_id, season, date, venue, team_1, team_2, winner
            FROM matches WHERE match_id = ?
            LIMIT 1
        """, [match_id]).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

        mid, season, date, city, team_1, team_2, winner = row

        # Players who batted or bowled = the XI
        t1_players = con.execute("""
            SELECT DISTINCT batter AS player_id FROM deliveries
            WHERE match_id = ? AND batting_team = ?
            UNION
            SELECT DISTINCT bowler FROM deliveries
            WHERE match_id = ? AND bowling_team = ?
        """, [match_id, team_1, match_id, team_1]).fetchall()

        t2_players = con.execute("""
            SELECT DISTINCT batter AS player_id FROM deliveries
            WHERE match_id = ? AND batting_team = ?
            UNION
            SELECT DISTINCT bowler FROM deliveries
            WHERE match_id = ? AND bowling_team = ?
        """, [match_id, team_2, match_id, team_2]).fetchall()

        def _format_player(pid: str) -> Dict[str, Any]:
            return {
                "player_id": pid,
                "name": pid.replace("_", " ").title(),
                "role": "batsman",
                "is_overseas": False,
                "expected_runs": 0.9,
                "expected_wickets": 0.04,
                "form_score": 1.0,
            }

        return {
            "match_id": mid,
            "season": season,
            "date": str(date),
            "city": city,
            "venue": _resolve_venue(city),
            "team_1": team_1,
            "team_2": team_2,
            "winner": winner or "No result",
            "team_1_xi": [_format_player(p[0]) for p in t1_players],
            "team_2_xi": [_format_player(p[0]) for p in t2_players],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Match detail query failed: {str(e)}")
    finally:
        con.close()
