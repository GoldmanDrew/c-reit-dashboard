"""Minimal China exchange trading-day helpers."""
from __future__ import annotations

import datetime as dt


def latest_weekday(asof: dt.date | None = None) -> dt.date:
    """Return the latest non-weekend date.

    This intentionally avoids pretending to know every exchange holiday. Source
    adapters can write their own source_asof, and the audit accepts that date
    when it is at least this latest expected weekday.
    """
    day = asof or dt.date.today()
    while day.weekday() >= 5:
        day -= dt.timedelta(days=1)
    return day


def freshness_for_asof(source_asof: str | None, build_date: dt.date | None = None) -> str:
    if not source_asof:
        return "missing"
    try:
        asof = dt.date.fromisoformat(str(source_asof)[:10])
    except ValueError:
        return "missing"
    return "fresh" if asof >= latest_weekday(build_date) else "stale"
