#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    path = Path("odds_data.json")
    if not path.exists():
        raise SystemExit("odds_data.json missing after scrape")
    payload = json.loads(path.read_text(encoding="utf-8"))
    last_updated = payload.get("last_updated")
    if not last_updated:
        raise SystemExit("odds_data.json missing last_updated")
    try:
        ts = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
    except Exception as exc:
        raise SystemExit(f"Invalid last_updated format: {last_updated}") from exc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60.0
    print(f"Snapshot last_updated: {last_updated} (age {age_min:.1f} min)")
    if age_min > 20:
        raise SystemExit(f"Snapshot too old: {age_min:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
