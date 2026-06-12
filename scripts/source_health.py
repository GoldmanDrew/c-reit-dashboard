"""Source-health artifact helpers."""
from __future__ import annotations

import datetime as dt
from typing import Any


def seed_source_health(row_count: int, price_asof: str, audit: dict[str, Any] | None = None) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    audit_summary = (audit or {}).get("summary", {})
    adapter_gaps = {gap["key"]: gap for gap in (audit or {}).get("adapter_gaps", [])}

    def gap_source(key: str, name: str, status: str = "not_configured") -> dict[str, Any]:
        gap = adapter_gaps.get(key, {})
        return {
            "key": key,
            "name": name,
            "status": status,
            "last_success": None,
            "source_asof": None,
            "rows_fetched": 0,
            "rows_parsed": 0,
            "coverage_pct": 0.0,
            "license_note": gap.get("why_missing", "Adapter placeholder."),
            "next_fetcher": gap.get("next_fetcher"),
            "error": None,
        }

    return {
        "build_time": now,
        "data_quality_summary": audit_summary,
        "sources": [
            {
                "key": "manual_wind_workbook_seed",
                "name": "Manual workbook seed",
                "status": "stale" if audit_summary.get("stale_seed_price_rows") else "ok",
                "last_success": now,
                "source_asof": price_asof,
                "rows_fetched": row_count,
                "rows_parsed": row_count,
                "coverage_pct": 100.0,
                "license_note": "Workbook appears Wind-derived; keep raw workbook local unless redistribution is permitted.",
                "next_fetcher": "Keep as fallback seed; official adapters should override these fields.",
                "error": None,
            },
            {
                "key": "data_quality_audit",
                "name": "Data quality audit",
                "status": "ok",
                "last_success": now,
                "source_asof": now,
                "rows_fetched": row_count,
                "rows_parsed": row_count,
                "coverage_pct": 100.0,
                "license_note": "Classifies stale seed, expected pending blanks, missing fields, and adapter gaps.",
                "next_fetcher": "scripts/audit_data_quality.py",
                "error": None,
            },
            gap_source("online_prices", "Online prices / volume", "stale"),
            gap_source("nav_market_cap", "NAV / market cap reports"),
            gap_source("distributions", "Distributions and yield"),
            gap_source("news_events", "Company and project news"),
            gap_source("regulatory_tape", "Regulatory notices"),
            gap_source("pipeline_zoning", "Pipeline and zoning facts"),
            gap_source("macro_data", "Macro rates and deflation context"),
        ],
    }
