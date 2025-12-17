"""
Canonical league matching (Postgres-backed) with deterministic entity resolution.

This module provides:
 - Normalization helpers for league/competition names
 - A LeagueMatcher that:
     * Does fast exact alias lookup by (provider, provider_league_id)
     * Builds a normalized competition signature
     * Runs exact signature match
     * Runs fuzzy scoring with a configurable threshold
     * Falls back to unmapped when confidence is too low

The matcher expects to be instantiated with data loaded from Postgres
 (leagues, league_aliases, league_overrides). Loading is left to the caller.
"""

from dataclasses import dataclass
import re
import unicodedata
from typing import Dict, List, Optional, Tuple


# -------- Normalization helpers --------

SPONSOR_WORDS = {
    "barclays",
    "betway",
    "tinkoff",
    "vodafone",
    "skysports",
    "sky bet",
    "skybett",
    "skybet",
    "sky",
    "bet",
    "standard bank",
}

COUNTRY_TOKENS = {
    "england",
    "english",
    "spain",
    "germany",
    "france",
    "italy",
    "portugal",
    "netherlands",
    "scotland",
    "ghana",
    "europe",
}

TOKEN_EXPANSIONS = {
    "utd": "united",
    "fc": "",
    "cf": "",
    "sc": "",
    "ac": "",
    "afc": "",
    "bc": "",
    "bk": "",
    "b": "",
    "res": "reserve",
    "reserves": "reserve",
    "ii": "2",
    "iii": "3",
    "1st": "1",
    "first": "1",
    "2nd": "2",
    "second": "2",
    "3rd": "3",
    "third": "3",
    "w": "women",
}


def strip_diacritics(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def normalize_competition_name(name: str) -> str:
    if not name:
        return ""
    # Lower + strip diacritics/punctuation
    name = strip_diacritics(name.lower())
    name = re.sub(r"[^\w\s/]", " ", name)
    tokens = re.split(r"\s+|/", name)

    norm_tokens: List[str] = []
    for tok in tokens:
        if not tok:
            continue
        expanded = TOKEN_EXPANSIONS.get(tok, tok)
        if expanded == "":
            continue
        if expanded in SPONSOR_WORDS:
            continue
        if expanded in COUNTRY_TOKENS:
            continue
        norm_tokens.append(expanded)

    # Remove duplicates while preserving order
    seen = set()
    deduped = []
    for tok in norm_tokens:
        if tok not in seen:
            seen.add(tok)
            deduped.append(tok)

    return " ".join(deduped).strip()


def parse_season(season: Optional[str]) -> Optional[Tuple[int, int]]:
    if not season:
        return None
    season = season.strip()
    # Formats: "2024/25", "24-25", "2025"
    m = re.match(r"(?P<y1>\d{2,4})\s*[/\-]\s*(?P<y2>\d{2,4})", season)
    if m:
        y1 = int(m.group("y1"))
        y2 = int(m.group("y2"))
        if y1 < 100:
            y1 += 2000
        if y2 < 100:
            y2 += 2000
        if y2 < y1:
            y2 += 1  # e.g., 2024/25
        return (y1, y2)
    if re.match(r"\d{4}$", season):
        y = int(season)
        return (y, y + 1)
    return None


# -------- Data classes --------

@dataclass
class LeagueRecord:
    league_id: str
    sport: str
    country_code: str
    tier: Optional[int]
    gender: Optional[str]
    season_start: Optional[int]
    season_end: Optional[int]
    display_name: str
    normalized_name: str


@dataclass
class LeagueAlias:
    league_id: str
    provider: str
    provider_league_id: Optional[str]
    provider_name: Optional[str]
    provider_country: Optional[str]
    provider_season: Optional[str]
    provider_sport: Optional[str]
    priority: int = 0
    active: bool = True


# -------- Matcher --------

class LeagueMatcher:
    def __init__(
        self,
        leagues: List[LeagueRecord],
        aliases: List[LeagueAlias],
        threshold: float = 0.6,
        margin: float = 0.05,
        league_clubs: Optional[Dict[str, List[str]]] = None,
    ):
        self.threshold = threshold
        self.margin = margin
        self.leagues = leagues
        self.league_clubs = league_clubs or {}
        self.alias_map: Dict[Tuple[str, str], str] = {}
        for a in aliases:
            if not a.active or not a.provider_league_id:
                continue
            key = (a.provider.lower(), a.provider_league_id.lower())
            # prefer higher priority
            if key not in self.alias_map or a.priority > 0:
                self.alias_map[key] = a.league_id

        # index leagues by normalized signature
        self.league_index: Dict[Tuple[str, str, str, Optional[int], Optional[int]], LeagueRecord] = {}
        for l in leagues:
            key = (
                l.sport.lower(),
                l.country_code.lower(),
                l.normalized_name,
                l.season_start,
                l.season_end,
            )
            self.league_index[key] = l

    # --- public API ---
    def match(
        self,
        provider: str,
        provider_league_id: Optional[str],
        provider_name: str,
        provider_country: Optional[str],
        provider_sport: str,
        provider_season: Optional[str],
        recent_clubs: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], float, Dict]:
        """
        Returns: (league_id or None, confidence, debug_features)
        """
        debug = {}
        # 1) exact alias
        if provider_league_id:
            key = (provider.lower(), provider_league_id.lower())
            if key in self.alias_map:
                debug["mode"] = "alias_exact"
                return self.alias_map[key], 1.0, debug

        # 2) normalized signature exact
        norm_name = normalize_competition_name(provider_name)
        debug["norm_name"] = norm_name
        season_range = parse_season(provider_season)
        s_start, s_end = season_range if season_range else (None, None)
        signature = (
            provider_sport.lower(),
            (provider_country or "").lower(),
            norm_name,
            s_start,
            s_end,
        )
        if signature in self.league_index:
            debug["mode"] = "signature_exact"
            return self.league_index[signature].league_id, 0.95, debug

        # 3) fuzzy compare against leagues in same sport (and country if provided)
        candidates = []
        for l in self.leagues:
            if l.sport.lower() != provider_sport.lower():
                continue
            if provider_country and l.country_code.lower() != provider_country.lower():
                continue
            name_score = self._name_similarity(norm_name, l.normalized_name)
            season_score = self._season_score(season_range, (l.season_start, l.season_end))
            club_score = self._club_overlap_score(recent_clubs, l)
            total = (0.55 * name_score) + (0.2 * season_score) + (0.25 * club_score)
            candidates.append((total, l))

        if not candidates:
            debug["mode"] = "no_candidates"
            return None, 0.0, debug

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_league = candidates[0]
        runner_up_score = candidates[1][0] if len(candidates) > 1 else 0
        debug["mode"] = "fuzzy"
        debug["best_score"] = best_score
        debug["runner_up"] = runner_up_score
        if best_score >= self.threshold and (best_score - runner_up_score) >= self.margin:
            return best_league.league_id, best_score, debug

        return None, best_score, debug

    # --- scoring helpers ---
    @staticmethod
    def _name_similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        a_tokens = set(a.split())
        b_tokens = set(b.split())
        if not a_tokens or not b_tokens:
            return 0.0
        intersection = len(a_tokens & b_tokens)
        union = len(a_tokens | b_tokens)
        return intersection / union

    @staticmethod
    def _season_score(a: Optional[Tuple[int, int]], b: Tuple[Optional[int], Optional[int]]) -> float:
        if not a or not b or not b[0] or not b[1]:
            return 0.0
        if a == b:
            return 1.0
        # Overlap check
        if a[0] == b[0] or a[1] == b[1]:
            return 0.5
        return 0.0

    @staticmethod
    def _club_overlap_score(recent_clubs: Optional[List[str]], league: LeagueRecord) -> float:
        return 0.0

    def _club_overlap_score(self, recent_clubs: Optional[List[str]], league: LeagueRecord) -> float:
        if not recent_clubs:
            return 0.0
        league_clubs = set(self.league_clubs.get(league.league_id, []))
        if not league_clubs:
            return 0.0
        rc_norm = {normalize_competition_name(c) for c in recent_clubs if c}
        rc_norm = {c for c in rc_norm if c}
        if not rc_norm:
            return 0.0
        intersection = len(rc_norm & league_clubs)
        union = len(rc_norm | league_clubs)
        if union == 0:
            return 0.0
        return intersection / union
