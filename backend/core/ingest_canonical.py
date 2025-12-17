"""
Ingestion helpers to map provider fixtures to canonical leagues and persist to Postgres.
"""
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import execute_values

from .canonical_leagues import LeagueMatcher, LeagueRecord, LeagueAlias, normalize_competition_name


def fetch_leagues_and_aliases(conn) -> Tuple[List[LeagueRecord], List[LeagueAlias]]:
    leagues: List[LeagueRecord] = []
    aliases: List[LeagueAlias] = []

    with conn.cursor() as cur:
        cur.execute("""
            SELECT league_id, sport, country_code, tier, gender, season_start, season_end, display_name, normalized_name
            FROM leagues
        """)
        for row in cur.fetchall():
            leagues.append(LeagueRecord(*row))

        cur.execute("""
            SELECT league_id, provider, provider_league_id, provider_name, provider_country, provider_season, provider_sport, priority, active
            FROM league_aliases
            WHERE active = TRUE
        """)
        for row in cur.fetchall():
            aliases.append(LeagueAlias(*row))

    return leagues, aliases


def fetch_league_clubs(conn) -> Dict[str, List[str]]:
    """
    Build a simple league_id -> club token set map from recent fixtures.
    """
    league_clubs: Dict[str, set] = {}
    with conn.cursor() as cur:
        cur.execute("""
            SELECT league_id, home_team, away_team
            FROM fixtures
            WHERE league_id IS NOT NULL
            ORDER BY kickoff_time DESC NULLS LAST
            LIMIT 5000
        """)
        for league_id, home, away in cur.fetchall():
            if not league_id:
                continue
            league_clubs.setdefault(league_id, set()).add(normalize_competition_name(home or ""))
            league_clubs.setdefault(league_id, set()).add(normalize_competition_name(away or ""))
    return {k: [c for c in v if c] for k, v in league_clubs.items()}


def upsert_fixtures(conn, rows: List[Tuple]):
    """
    Bulk upsert fixtures.
    Rows fields:
      (league_id, provider, provider_fixture_id, home_team, away_team, kickoff_time, country_code, sport, raw_league_name, raw_league_id, confidence)
    """
    sql = """
    INSERT INTO fixtures (league_id, provider, provider_fixture_id, home_team, away_team, kickoff_time, country_code, sport, raw_league_name, raw_league_id, confidence)
    VALUES %s
    ON CONFLICT (provider, provider_fixture_id) DO UPDATE
    SET league_id = EXCLUDED.league_id,
        home_team = EXCLUDED.home_team,
        away_team = EXCLUDED.away_team,
        kickoff_time = EXCLUDED.kickoff_time,
        country_code = EXCLUDED.country_code,
        sport = EXCLUDED.sport,
        raw_league_name = EXCLUDED.raw_league_name,
        raw_league_id = EXCLUDED.raw_league_id,
        confidence = EXCLUDED.confidence,
        updated_at = now();
    """
    execute_values(conn.cursor(), sql, rows, page_size=500)


def insert_unmapped(conn, fixture_rows: List[Tuple]):
    """
    fixture_rows: (provider, provider_fixture_id, home_team, away_team, raw_league_name, raw_league_id, candidates_json, confidence, reason)
    """
    sql = """
    INSERT INTO fixtures (provider, provider_fixture_id, home_team, away_team, raw_league_name, raw_league_id, confidence)
    VALUES %s
    ON CONFLICT (provider, provider_fixture_id) DO NOTHING;
    """
    execute_values(conn.cursor(), sql, [(None,) + row for row in []])  # kept placeholder

    sql_unmapped = """
    INSERT INTO unmapped_candidates (fixture_id, candidates, reason)
    SELECT f.fixture_id, cands::jsonb, reason
    FROM (VALUES %s) AS v(provider, provider_fixture_id, cands, reason)
    JOIN fixtures f ON f.provider = v.provider AND f.provider_fixture_id = v.provider_fixture_id
    """
    execute_values(conn.cursor(), sql_unmapped, fixture_rows, page_size=200)


def ingest_matched_events(
    conn,
    matcher: LeagueMatcher,
    provider: str,
    fixtures: List[Dict],
    default_sport: str = "soccer",
    default_country: Optional[str] = None,
    season: Optional[str] = None,
):
    """
    fixtures: list of dicts with keys:
      provider_fixture_id, league, league_id(optional), home_team, away_team, start_time (epoch seconds)
    """
    upsert_rows = []
    unmapped_rows = []

    for f in fixtures:
        prov_league_id = f.get("league_id") or f.get("provider_league_id")
        prov_league_name = f.get("league", "") or f.get("provider_league_name", "")

        league_id, conf, debug = matcher.match(
            provider=provider,
            provider_league_id=prov_league_id,
            provider_name=prov_league_name,
            provider_country=f.get("country") or default_country,
            provider_sport=default_sport,
            provider_season=season,
            recent_clubs=[f.get("home_team", ""), f.get("away_team", "")]
        )

        kickoff = f.get("start_time")
        kickoff_ts = None
        if kickoff:
            try:
                kickoff_ts = int(kickoff)
            except Exception:
                kickoff_ts = None

        if league_id:
            upsert_rows.append((
                league_id,
                provider,
                str(f.get("provider_fixture_id") or f.get("event_id") or f.get("id")),
                f.get("home_team"),
                f.get("away_team"),
                kickoff_ts,
                f.get("country") or default_country,
                default_sport,
                prov_league_name,
                prov_league_id,
                conf
            ))
        else:
            fixture_id = str(f.get("provider_fixture_id") or f.get("event_id") or f.get("id"))
            candidates = {"debug": debug, "name": prov_league_name}
            unmapped_rows.append((
                provider,
                fixture_id,
                f.get("home_team"),
                f.get("away_team"),
                prov_league_name,
                prov_league_id,
                candidates,
                conf,
                debug.get("mode", "unmapped")
            ))

    if upsert_rows:
        upsert_fixtures(conn, upsert_rows)
    if unmapped_rows:
        # Store fixture shell then unmapped rows with candidate payload
        with conn.cursor() as cur:
            sql = """
            INSERT INTO fixtures (league_id, provider, provider_fixture_id, home_team, away_team, raw_league_name, raw_league_id, confidence)
            VALUES %s
            ON CONFLICT (provider, provider_fixture_id) DO NOTHING;
            """
            base_rows = [
                (
                    None,
                    provider,
                    r[1],
                    r[2],
                    r[3],
                    r[4],
                    r[5],
                    r[7]
                )
                for r in unmapped_rows
            ]
            execute_values(cur, sql, base_rows, page_size=200)

            sql2 = """
            INSERT INTO unmapped_candidates (fixture_id, candidates, reason)
            SELECT f.fixture_id, v.cands::jsonb, v.reason
            FROM (VALUES %s) AS v(provider_fixture_id, cands, reason)
            JOIN fixtures f ON f.provider_fixture_id = v.provider_fixture_id AND f.provider = %s
            """
            vals = [(r[1], r[6], r[7]) for r in unmapped_rows]
            execute_values(cur, sql2, vals, template="(%s,%s,%s)", page_size=200)

    conn.commit()
