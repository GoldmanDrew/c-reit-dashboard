"""Source-health artifact helpers."""
from __future__ import annotations

import datetime as dt
from typing import Any


def seed_source_health(row_count: int, price_asof: str) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "build_time": now,
        "sources": [
            {
                "key": "manual_wind_workbook_seed",
                "name": "Manual workbook seed",
                "status": "ok",
                "last_success": now,
                "source_asof": price_asof,
                "rows_fetched": row_count,
                "rows_parsed": row_count,
                "coverage_pct": 100.0,
                "license_note": "Workbook appears Wind-derived; keep raw workbook local unless redistribution is permitted.",
                "error": None,
            },
            {
                "key": "online_prices",
                "name": "Online prices / volume",
                "status": "not_configured",
                "last_success": None,
                "rows_fetched": 0,
                "rows_parsed": 0,
                "coverage_pct": 0.0,
                "license_note": "Adapter placeholder.",
                "error": None,
            },
            {
                "key": "company_news",
                "name": "Company and project news",
                "status": "not_configured",
                "last_success": None,
                "rows_fetched": 0,
                "rows_parsed": 0,
                "coverage_pct": 0.0,
                "license_note": "Adapter placeholder.",
                "error": None,
            },
            {
                "key": "regulatory_tape",
                "name": "Regulatory notices",
                "status": "not_configured",
                "last_success": None,
                "rows_fetched": 0,
                "rows_parsed": 0,
                "coverage_pct": 0.0,
                "license_note": "Adapter placeholder.",
                "error": None,
            },
        ],
    }
