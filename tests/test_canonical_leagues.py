import unittest

from backend.core.canonical_leagues import (
    normalize_competition_name,
    LeagueMatcher,
    LeagueRecord,
    LeagueAlias,
)


class TestCanonicalLeagues(unittest.TestCase):
    def test_normalize_competition_name(self):
        cases = {
            "England. Premier League": "premier league",
            "Barclays Premier League": "premier league",
            "LaLiga EA Sports": "laliga ea sports",
            "Serie A TIM": "serie a tim",
            "UEFA Champions League": "uefa champions league",
            "Sky Bet Championship": "championship",
            "W-League Women": "women league",
            "1st Division": "1 division",
            "Utd": "united",
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_competition_name(raw), expected)

    def test_matcher_exact_alias(self):
        leagues = [
            LeagueRecord(
                league_id="L1",
                sport="soccer",
                country_code="eng",
                tier=1,
                gender=None,
                season_start=2024,
                season_end=2025,
                display_name="Premier League",
                normalized_name="premier league",
            )
        ]
        aliases = [
            LeagueAlias(
                league_id="L1",
                provider="betway",
                provider_league_id="123",
                provider_name="England Premier League",
                provider_country="eng",
                provider_season="2024/25",
                provider_sport="soccer",
                priority=1,
                active=True,
            )
        ]
        matcher = LeagueMatcher(leagues, aliases)
        league_id, conf, _ = matcher.match(
            provider="betway",
            provider_league_id="123",
            provider_name="England Premier League",
            provider_country="eng",
            provider_sport="soccer",
            provider_season="2024/25",
        )
        self.assertEqual(league_id, "L1")
        self.assertEqual(conf, 1.0)

    def test_matcher_fuzzy(self):
        leagues = [
            LeagueRecord(
                league_id="L1",
                sport="soccer",
                country_code="eng",
                tier=1,
                gender=None,
                season_start=2024,
                season_end=2025,
                display_name="Premier League",
                normalized_name="premier league",
            ),
            LeagueRecord(
                league_id="L2",
                sport="soccer",
                country_code="esp",
                tier=1,
                gender=None,
                season_start=2024,
                season_end=2025,
                display_name="La Liga",
                normalized_name="la liga",
            ),
        ]
        matcher = LeagueMatcher(leagues, [])
        league_id, conf, debug = matcher.match(
            provider="sporty",
            provider_league_id=None,
            provider_name="England - Premier League",
            provider_country="eng",
            provider_sport="soccer",
            provider_season="2024/25",
        )
        self.assertEqual(league_id, "L1")
        self.assertGreater(conf, 0.7)
        self.assertIn(debug.get("mode"), ("fuzzy", "signature_exact"))


if __name__ == "__main__":
    unittest.main()
