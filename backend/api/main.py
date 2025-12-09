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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
