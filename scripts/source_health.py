"""Source-health artifact helpers."""
from __future__ import annotations

import datetime as dt
from typing import Any


def seed_source_health(
    row_count: int,
    price_asof: str,
    audit: dict[str, Any] | None = None,
    news_payload: dict[str, Any] | None = None,
    events_payload: dict[str, Any] | None = None,
    regulatory_payload: dict[str, Any] | None = None,
    price_payload: dict[str, Any] | None = None,
    translation_payload: dict[str, Any] | None = None,
    roles_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
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

    def news_source() -> dict[str, Any]:
        payload = news_payload or {}
        stats = payload.get("source_stats") or {}
        status = payload.get("status") or "not_configured"
        if status == "empty" and stats.get("queries_run"):
            status = "stale"
        rows = len(payload.get("items") or [])
        coverage = round((float(stats.get("symbols_with_news") or 0) / float(row_count or 1)) * 100, 1)
        return {
            "key": "news_events",
            "name": "Company and project news",
            "status": status,
            "last_success": payload.get("build_time") if payload.get("status") in {"ok", "empty"} else None,
            "source_asof": payload.get("build_time"),
            "rows_fetched": int(stats.get("raw_articles_seen") or 0),
            "rows_parsed": rows,
            "coverage_pct": coverage,
            "license_note": (
                "Google News RSS adapter; strict alias matching with confidence tiers. "
                f"queries={stats.get('queries_run', 0)} errors={stats.get('error_count', 0)}"
            ),
            "next_fetcher": "scripts/ingest_announcements.py",
            "error": "; ".join(e.get("error", "") for e in (stats.get("errors") or [])[:2]) or None,
        }

    def price_source() -> dict[str, Any]:
        payload = price_payload or {}
        stats = payload.get("source_stats") or {}
        status = payload.get("status") or "missing"
        freshness = payload.get("source_freshness")
        if status == "ok" and freshness == "stale":
            status = "stale"
        elif status == "missing":
            status = "stale" if audit_summary.get("stale_seed_price_rows") else "missing"
        return {
            "key": "online_prices",
            "name": "Online prices / volume",
            "status": status,
            "last_success": payload.get("build_time") if payload.get("items") else None,
            "source_asof": payload.get("source_asof"),
            "rows_fetched": int(stats.get("symbols_requested") or 0),
            "rows_parsed": int(stats.get("rows_parsed") or len(payload.get("items") or [])),
            "coverage_pct": float(stats.get("coverage_pct") or 0.0),
            "license_note": payload.get(
                "provider_note",
                "Only the local workbook seed is available; no exchange or licensed market-data adapter is configured.",
            ),
            "next_fetcher": "scripts/ingest_exchange_prices.py",
            "error": "; ".join(e.get("error", "") for e in (stats.get("errors") or [])[:2]) or None,
        }

    def translation_source() -> dict[str, Any]:
        payload = translation_payload or {}
        coverage = payload.get("coverage") or {}
        rows = int(coverage.get("records_with_name_en") or 0)
        return {
            "key": "english_translations",
            "name": "English name translations",
            "status": "ok" if rows else "missing",
            "last_success": payload.get("build_time"),
            "source_asof": payload.get("last_reviewed"),
            "rows_fetched": int(coverage.get("total_records") or row_count),
            "rows_parsed": rows,
            "coverage_pct": float(coverage.get("coverage_pct") or 0.0),
            "license_note": "Rule-based draft translations; manual review should promote high-confidence official names.",
            "next_fetcher": "data/creit_name_translations.json manual/source-document review",
            "error": None,
        }

    def role_source() -> dict[str, Any]:
        payload = roles_payload or {}
        coverage = payload.get("coverage") or {}
        rows = int(coverage.get("roles_parsed") or 0)
        return {
            "key": "institution_roles",
            "name": "Broker, banker, and manager roles",
            "status": "ok" if rows else "missing",
            "last_success": payload.get("build_time"),
            "source_asof": None,
            "rows_fetched": int(coverage.get("total_records") or row_count),
            "rows_parsed": rows,
            "coverage_pct": float(coverage.get("coverage_pct") or 0.0),
            "license_note": "Normalized from workbook seed; prospectus and disclosure adapters should refine roles.",
            "next_fetcher": "prospectus/report role parser",
            "error": None,
        }

    def event_source(key: str, name: str, payload: dict[str, Any] | None, fallback_fetcher: str) -> dict[str, Any]:
        payload = payload or {}
        rows = len(payload.get("items") or [])
        status = payload.get("status") or "not_configured"
        return {
            "key": key,
            "name": name,
            "status": status,
            "last_success": payload.get("build_time") if status in {"ok", "empty"} else None,
            "source_asof": payload.get("build_time"),
            "rows_fetched": rows,
            "rows_parsed": rows,
            "coverage_pct": 100.0 if rows else 0.0,
            "license_note": "Derived from classified C-REIT news until official exchange/regulator adapters are added.",
            "next_fetcher": fallback_fetcher,
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
            price_source(),
            translation_source(),
            role_source(),
            gap_source("nav_market_cap", "NAV / market cap reports"),
            gap_source("distributions", "Distributions and yield"),
            news_source(),
            event_source("structured_events", "Structured C-REIT events", events_payload, "scripts/ingest_announcements.py"),
            event_source("regulatory_tape", "Regulatory notices", regulatory_payload, "scripts/ingest_regulatory_events.py"),
            gap_source("pipeline_zoning", "Pipeline and zoning facts"),
            gap_source("macro_data", "Macro rates and deflation context"),
        ],
    }
