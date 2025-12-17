#!/usr/bin/env python3
"""
Ghana Odds Comparison API
FastAPI backend for OddsChecker-style web and mobile apps
"""
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.arbitrage import GhanaBettingArbitrage, calculate_stakes
from core.db import get_conn
from core.canonical_leagues import normalize_competition_name

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

app = FastAPI(
    title="Ghana Odds Comparison API",
    description="Compare betting odds across Ghana bookmakers and find arbitrage opportunities",
    version="1.0.0"
)

# CORS for web/mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache for scraped data
_cache: Dict = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 300  # 5 minute cache
}


class OddsResponse(BaseModel):
    bookmaker: str
    home_odds: float
    draw_odds: float
    away_odds: float


class MatchResponse(BaseModel):
    home_team: str
    away_team: str
    league: Optional[str] = None
    start_time: Optional[int] = None
    odds: List[OddsResponse]
    best_home: OddsResponse
    best_draw: Optional[OddsResponse] = None
    best_away: OddsResponse


class ArbitrageResponse(BaseModel):
    home_team: str
    away_team: str
    profit_pct: float
    home_odds: float
    home_bookmaker: str
    draw_odds: float
    draw_bookmaker: str
    away_odds: float
    away_bookmaker: str
    stakes: Dict


class ScannerStatus(BaseModel):
    last_scan: Optional[str] = None
    total_matches: int = 0
    matched_events: int = 0
    arbitrage_count: int = 0
    bookmakers: List[str] = []


class LeagueOut(BaseModel):
    league_id: str
    display_name: str
    sport: str
    country_code: str
    tier: Optional[int] = None
    season_start: Optional[int] = None
    season_end: Optional[int] = None


class FixtureOut(BaseModel):
    fixture_id: str
    league_id: Optional[str]
    provider: str
    provider_fixture_id: str
    home_team: str
    away_team: str
    kickoff_time: Optional[int]
    country_code: Optional[str]
    sport: Optional[str]
    raw_league_name: Optional[str]
    confidence: Optional[float]


def require_admin(key: Optional[str]):
    if ADMIN_API_KEY and key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


def get_scanner() -> GhanaBettingArbitrage:
    """Get or refresh the scanner data."""
    now = datetime.now()

    # Check cache validity
    if _cache["data"] and _cache["timestamp"]:
        age = (now - _cache["timestamp"]).total_seconds()
        if age < _cache["ttl_seconds"]:
            return _cache["data"]

    # Run fresh scan
    scanner = GhanaBettingArbitrage()
    scanner.scrape_all(max_matches=800)
    scanner.match_events()

    _cache["data"] = scanner
    _cache["timestamp"] = now

    return scanner


@app.get("/")
async def root():
    """API health check."""
    return {
        "status": "online",
        "service": "Ghana Odds Comparison API",
        "version": "1.0.0"
    }


@app.get("/api/status", response_model=ScannerStatus)
async def get_status():
    """Get current scanner status."""
    if not _cache["data"]:
        return ScannerStatus()

    scanner = _cache["data"]
    return ScannerStatus(
        last_scan=_cache["timestamp"].isoformat() if _cache["timestamp"] else None,
        total_matches=sum(len(m) for m in scanner.all_matches.values()),
        matched_events=len(scanner.matched_events),
        arbitrage_count=len(scanner.find_arbitrage()),
        bookmakers=list(scanner.all_matches.keys())
    )


@app.post("/api/scan")
async def trigger_scan():
    """Trigger a fresh odds scan."""
    _cache["data"] = None  # Force refresh
    scanner = get_scanner()

    return {
        "status": "completed",
        "total_matches": sum(len(m) for m in scanner.all_matches.values()),
        "matched_events": len(scanner.matched_events)
    }


@app.get("/api/matches", response_model=List[MatchResponse])
async def get_matches(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    min_bookmakers: int = Query(2, ge=2, le=5)
):
    """Get all matched events with odds from all bookmakers."""
    scanner = get_scanner()

    results = []
    for event in scanner.matched_events[offset:offset + limit]:
        if len(event) < min_bookmakers:
            continue

        odds_list = []
        for m in event:
            odds_list.append(OddsResponse(
                bookmaker=m.get('bookmaker', ''),
                home_odds=m.get('home_odds', 0),
                draw_odds=m.get('draw_odds', 0),
                away_odds=m.get('away_odds', 0)
            ))

        # Find best odds
        best_home = max(event, key=lambda x: x.get('home_odds', 0))
        best_draw = max(event, key=lambda x: x.get('draw_odds', 0))
        best_away = max(event, key=lambda x: x.get('away_odds', 0))

        results.append(MatchResponse(
            home_team=event[0].get('home_team', ''),
            away_team=event[0].get('away_team', ''),
            league=event[0].get('league'),
            start_time=event[0].get('start_time'),
            odds=odds_list,
            best_home=OddsResponse(
                bookmaker=best_home.get('bookmaker', ''),
                home_odds=best_home.get('home_odds', 0),
                draw_odds=best_home.get('draw_odds', 0),
                away_odds=best_home.get('away_odds', 0)
            ),
            best_draw=OddsResponse(
                bookmaker=best_draw.get('bookmaker', ''),
                home_odds=best_draw.get('home_odds', 0),
                draw_odds=best_draw.get('draw_odds', 0),
                away_odds=best_draw.get('away_odds', 0)
            ) if best_draw.get('draw_odds', 0) > 1 else None,
            best_away=OddsResponse(
                bookmaker=best_away.get('bookmaker', ''),
                home_odds=best_away.get('home_odds', 0),
                draw_odds=best_away.get('draw_odds', 0),
                away_odds=best_away.get('away_odds', 0)
            )
        ))

    return results


@app.get("/api/arbitrage", response_model=List[ArbitrageResponse])
async def get_arbitrage(bankroll: float = Query(100, ge=1)):
    """Get current arbitrage opportunities with stake calculations."""
    scanner = get_scanner()
    opportunities = scanner.find_arbitrage()

    results = []
    for opp in opportunities:
        stakes = calculate_stakes(opp, bankroll)
        results.append(ArbitrageResponse(
            home_team=opp['home_team'],
            away_team=opp['away_team'],
            profit_pct=opp['profit_pct'],
            home_odds=opp['home_odds'],
            home_bookmaker=opp['home_bookmaker'],
            draw_odds=opp['draw_odds'],
            draw_bookmaker=opp['draw_bookmaker'],
            away_odds=opp['away_odds'],
            away_bookmaker=opp['away_bookmaker'],
            stakes=stakes
        ))

    return results


@app.get("/api/bookmakers")
async def get_bookmakers():
    """Get list of supported bookmakers."""
    return {
        "bookmakers": [
            {"id": "betway", "name": "Betway Ghana", "url": "https://www.betway.com.gh"},
            {"id": "sportybet", "name": "SportyBet Ghana", "url": "https://www.sportybet.com/gh"},
            {"id": "1xbet", "name": "1xBet Ghana", "url": "https://1xbet.com/gh"},
            {"id": "22bet", "name": "22Bet Ghana", "url": "https://22bet.com.gh"},
            {"id": "soccabet", "name": "SoccaBet Ghana", "url": "https://www.soccabet.com"},
        ]
    }


# ---------------------------------------------------------------------------
# Canonical leagues + fixtures (Postgres)
# ---------------------------------------------------------------------------

@app.get("/api/leagues", response_model=List[LeagueOut])
async def list_leagues():
    """List canonical leagues for filters."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT league_id, display_name, sport, country_code, tier, season_start, season_end
                    FROM leagues
                    ORDER BY sport, country_code, display_name
                """)
                rows = cur.fetchall()
        return [
            LeagueOut(
                league_id=row[0],
                display_name=row[1],
                sport=row[2],
                country_code=row[3],
                tier=row[4],
                season_start=row[5],
                season_end=row[6],
            )
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error listing leagues: {e}")


@app.get("/api/fixtures", response_model=List[FixtureOut])
async def list_fixtures(
    league_id: Optional[str] = None,
    country: Optional[str] = None,
    sport: Optional[str] = "soccer",
    date_from: Optional[int] = None,
    date_to: Optional[int] = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List fixtures joined to canonical leagues (if mapped)."""
    filters = []
    params = []
    if league_id:
        filters.append("f.league_id = %s")
        params.append(league_id)
    if country:
        filters.append("f.country_code = %s")
        params.append(country)
    if sport:
        filters.append("f.sport = %s")
        params.append(sport)
    if date_from:
        filters.append("f.kickoff_time >= to_timestamp(%s)")
        params.append(date_from)
    if date_to:
        filters.append("f.kickoff_time <= to_timestamp(%s)")
        params.append(date_to)

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    sql = f"""
        SELECT f.fixture_id, f.league_id, f.provider, f.provider_fixture_id,
               f.home_team, f.away_team, EXTRACT(EPOCH FROM f.kickoff_time)::bigint,
               f.country_code, f.sport, f.raw_league_name, f.confidence
        FROM fixtures f
        {where_clause}
        ORDER BY f.kickoff_time NULLS LAST
        OFFSET %s LIMIT %s
    """
    params.extend([offset, limit])

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [
            FixtureOut(
                fixture_id=row[0],
                league_id=row[1],
                provider=row[2],
                provider_fixture_id=row[3],
                home_team=row[4],
                away_team=row[5],
                kickoff_time=row[6],
                country_code=row[7],
                sport=row[8],
                raw_league_name=row[9],
                confidence=float(row[10]) if row[10] is not None else None,
            )
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error listing fixtures: {e}")


@app.get("/api/unmapped")
async def list_unmapped(admin_key: Optional[str] = Query(None)):
    """List recent unmapped fixtures with candidates (admin)."""
    require_admin(admin_key)
    sql = """
        SELECT f.provider, f.provider_fixture_id, f.home_team, f.away_team, f.raw_league_name,
               uc.candidates, uc.reason, f.confidence, f.created_at
        FROM unmapped_candidates uc
        JOIN fixtures f ON f.fixture_id = uc.fixture_id
        ORDER BY uc.created_at DESC
        LIMIT 200
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        return [
            {
                "provider": r[0],
                "provider_fixture_id": r[1],
                "home_team": r[2],
                "away_team": r[3],
                "raw_league_name": r[4],
                "candidates": r[5],
                "reason": r[6],
                "confidence": float(r[7]) if r[7] is not None else None,
                "created_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error listing unmapped: {e}")


@app.post("/api/approve_mapping")
async def approve_mapping(
    provider: str,
    provider_league_id: str,
    league_id: str,
    provider_name: Optional[str] = None,
    admin_key: Optional[str] = Query(None),
):
    """Approve a mapping by inserting into league_aliases (admin)."""
    require_admin(admin_key)
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO league_aliases
                        (league_id, provider, provider_league_id, provider_name, active, priority)
                    VALUES (%s, %s, %s, %s, TRUE, 1)
                    ON CONFLICT (provider, provider_league_id) DO UPDATE
                    SET league_id = EXCLUDED.league_id,
                        provider_name = COALESCE(EXCLUDED.provider_name, league_aliases.provider_name),
                        active = TRUE,
                        updated_at = now();
                    """,
                    (league_id, provider, provider_league_id, provider_name),
                )
                conn.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error approving mapping: {e}")


@app.get("/api/unmapped_stats")
async def unmapped_stats(admin_key: Optional[str] = Query(None)):
    """Basic stats on unmapped rate (admin)."""
    require_admin(admin_key)
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM fixtures")
                total = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM fixtures WHERE league_id IS NULL")
                unmapped = cur.fetchone()[0]
        rate = (unmapped / total) if total else 0
        return {"total_fixtures": total, "unmapped": unmapped, "unmapped_rate": rate}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error computing stats: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
