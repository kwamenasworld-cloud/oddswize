#!/usr/bin/env python3
"""
Verify scraper coverage against ESPN fixtures for major leagues.

Compares upcoming fixtures (next N days) with scraped odds data and
reports missing matches. Uses ESPN scoreboard as the baseline.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple

import requests


ESPN_SCOREBOARD_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
DEFAULT_DAYS = 7

LEAGUE_CONFIG = {
    "premier": {"id": "eng.1", "name": "Premier League"},
    "laliga": {"id": "esp.1", "name": "La Liga"},
    "seriea": {"id": "ita.1", "name": "Serie A"},
    "bundesliga": {"id": "ger.1", "name": "Bundesliga"},
    "ligue1": {"id": "fra.1", "name": "Ligue 1"},
    "ucl": {"id": "uefa.champions", "name": "UEFA Champions League"},
}

TEAM_ALIASES = {
    "man utd": "manchester united",
    "man united": "manchester united",
    "man city": "manchester city",
    "spurs": "tottenham hotspur",
    "wolves": "wolverhampton wanderers",
    "psg": "paris saint germain",
    "inter": "internazionale",
    "ac milan": "milan",
    "bayern munchen": "bayern munich",
    "athletic club": "athletic bilbao",
    "olympique marseille": "marseille",
    "olympique lyonnais": "lyon",
    "real sociedad san sebastian": "real sociedad",
    "rc celta de vigo": "celta vigo",
    "celta de vigo": "celta vigo",
    "borussia monchengladbach": "monchengladbach",
    "vfb stuttgart": "stuttgart",
    "vfl wolfsburg": "wolfsburg",
    "1 fc union berlin": "union berlin",
    "1 fc heidenheim 1846": "heidenheim",
    "fc copenhagen": "kobenhavn",
    "f c kopenhavn": "kobenhavn",
    "fc kopenhavn": "kobenhavn",
    "bodoglimt": "bodo glimt",
}

TEAM_SUFFIXES = {
    "fc",
    "cf",
    "sc",
    "ac",
    "afc",
    "ssc",
    "bc",
    "club",
    "fk",
    "sk",
    "nk",
    "cd",
    "sv",
    "rc",
    "rcd",
    "vfb",
    "vfl",
    "rb",
    "de",
    "del",
    "la",
    "le",
    "calcio",
    "olympique",
    "stade",
    "deportivo",
    "balompie",
    "seville",
    "piraeus",
}

TOKEN_REPLACEMENTS = {
    "saint": "st",
    "rennais": "rennes",
}

TRANSLITERATION = str.maketrans({
    "\u00f8": "o",
    "\u00d8": "o",
    "\u00e6": "ae",
    "\u00c6": "ae",
    "\u00e5": "a",
    "\u00c5": "a",
    "\u00df": "ss",
    "\u0153": "oe",
    "\u0152": "oe",
})


def strip_accents(value: str) -> str:
    value = value.translate(TRANSLITERATION)
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize_team(name: str) -> str:
    if not name:
        return ""
    value = strip_accents(name)
    value = value.lower().strip()
    value = re.sub(r"[^\w\s]", " ", value)
    value = " ".join(value.split())
    value = TEAM_ALIASES.get(value, value)
    parts = []
    for p in value.split():
        if p.isdigit() or len(p) <= 1:
            continue
        p = TOKEN_REPLACEMENTS.get(p, p)
        if p in TEAM_SUFFIXES:
            continue
        parts.append(p)
    return " ".join(parts)


def fixture_key(home: str, away: str) -> Tuple[str, str]:
    h = normalize_team(home)
    a = normalize_team(away)
    if h <= a:
        return (h, a)
    return (a, h)


def fetch_espn_fixtures(league_id: str, days: int) -> List[Dict]:
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=days)
    params = {"dates": f"{today:%Y%m%d}-{end:%Y%m%d}"}
    url = f"{ESPN_SCOREBOARD_BASE}/{league_id}/scoreboard"
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    fixtures = []
    for event in data.get("events", []):
        competitions = event.get("competitions") or []
        competition = competitions[0] if competitions else {}
        competitors = competition.get("competitors") or []
        if len(competitors) < 2:
            continue
        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[-1])
        home_team = (home.get("team") or {}).get("displayName") or (home.get("team") or {}).get("name")
        away_team = (away.get("team") or {}).get("displayName") or (away.get("team") or {}).get("name")
        kickoff = event.get("date") or competition.get("date")
        fixtures.append(
            {
                "home_team": home_team or "",
                "away_team": away_team or "",
                "kickoff": kickoff,
            }
        )
    return fixtures


def load_odds_matches(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    matches = data.get("matches")
    if isinstance(matches, list):
        return matches
    return []


def load_raw_matches(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return []
    matches = []
    for bookie, items in data.items():
        if not isinstance(items, list):
            continue
        for match in items:
            if not isinstance(match, dict):
                continue
            match = {**match, "bookmaker": match.get("bookmaker") or bookie}
            matches.append(match)
    return matches


def build_match_keys(matches: Iterable[Dict]) -> Set[Tuple[str, str]]:
    keys = set()
    for match in matches:
        home = match.get("home_team") or ""
        away = match.get("away_team") or ""
        if not home or not away:
            continue
        keys.add(fixture_key(home, away))
    return keys


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify scraper coverage against ESPN fixtures.")
    parser.add_argument("--odds-data", default="odds_data.json", help="Path to odds_data.json")
    parser.add_argument("--raw-data", help="Optional raw_scraped_data.json for per-bookmaker coverage")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Days ahead to check")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    odds_matches = load_odds_matches(args.odds_data)
    scraped_keys = build_match_keys(odds_matches)

    if args.raw_data:
        raw_matches = load_raw_matches(args.raw_data)
        scraped_keys |= build_match_keys(raw_matches)

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "days": args.days,
        "leagues": {},
    }

    missing_total = 0
    for league_key, meta in LEAGUE_CONFIG.items():
        fixtures = fetch_espn_fixtures(meta["id"], args.days)
        missing = []
        for fixture in fixtures:
            key = fixture_key(fixture["home_team"], fixture["away_team"])
            if key not in scraped_keys:
                missing.append(fixture)

        report["leagues"][league_key] = {
            "name": meta["name"],
            "total": len(fixtures),
            "found": len(fixtures) - len(missing),
            "missing": missing,
        }
        missing_total += len(missing)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    print("Coverage report (next {} days):".format(args.days))
    for league_key, data in report["leagues"].items():
        print(
            f"- {data['name']}: {data['found']}/{data['total']} found"
            f"{' (missing ' + str(len(data['missing'])) + ')' if data['missing'] else ''}"
        )
        for fixture in data["missing"][:10]:
            print(f"  - MISSING: {fixture['home_team']} vs {fixture['away_team']}")
        if len(data["missing"]) > 10:
            print(f"  - ...and {len(data['missing']) - 10} more")

    if missing_total > 0:
        print(f"\nMissing total fixtures: {missing_total}")
    else:
        print("\nAll fixtures found in scraped data.")


if __name__ == "__main__":
    main()
