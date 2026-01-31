import re
import unicodedata
from typing import Tuple

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
    for part in value.split():
        if part.isdigit() or len(part) <= 1:
            continue
        part = TOKEN_REPLACEMENTS.get(part, part)
        if part in TEAM_SUFFIXES:
            continue
        parts.append(part)
    return " ".join(parts)


def fixture_key(home: str, away: str) -> Tuple[str, str]:
    h = normalize_team(home)
    a = normalize_team(away)
    if h <= a:
        return (h, a)
    return (a, h)
