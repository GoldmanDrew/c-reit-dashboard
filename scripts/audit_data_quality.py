"""Build row-level data-quality diagnostics for dashboard artifacts."""
from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from trading_calendar import freshness_for_asof


ADAPTER_GAPS = [
    {
        "key": "online_prices",
        "label": "Prices, volume, turnover",
        "priority": 1,
        "expected_fields": ["last_close_rmb", "price_asof", "volume", "turnover"],
        "why_missing": "Only the local workbook seed is available; no exchange or licensed market-data adapter is configured.",
        "next_fetcher": "scripts/ingest_exchange_prices.py",
    },
    {
        "key": "nav_market_cap",
        "label": "NAV, units, market cap, premium/discount",
        "priority": 2,
        "expected_fields": ["nav_rmb", "units_outstanding", "market_cap_rmb_bn", "premium_discount_to_nav"],
        "why_missing": "The workbook does not include NAV or units; these need fund-manager reports or exchange disclosures.",
        "next_fetcher": "scripts/ingest_nav_reports.py",
    },
    {
        "key": "distributions",
        "label": "Distributions and yield",
        "priority": 3,
        "expected_fields": ["last_distribution_rmb", "ttm_distribution_rmb", "distribution_yield_ttm"],
        "why_missing": "Distribution announcements are not ingested yet.",
        "next_fetcher": "scripts/ingest_distributions.py",
    },
    {
        "key": "news_events",
        "label": "Company news and structured events",
        "priority": 4,
        "expected_fields": ["latest_news", "event_type", "headline", "source_url"],
        "why_missing": "Entity aliases exist, but no news or announcement adapter is configured.",
        "next_fetcher": "scripts/ingest_announcements.py",
    },
    {
        "key": "regulatory_tape",
        "label": "Regulatory notices",
        "priority": 5,
        "expected_fields": ["regulatory_stage", "notice_title", "notice_url"],
        "why_missing": "NDRC/CSRC/exchange notice feeds are listed in config but not parsed.",
        "next_fetcher": "scripts/ingest_regulatory_events.py",
    },
    {
        "key": "pipeline_zoning",
        "label": "Zoning, pipeline, and property-level facts",
        "priority": 6,
        "expected_fields": ["zoning_type", "pipeline_multiple_of_initial_assets", "pipeline_readiness_score"],
        "why_missing": "These are investment-research fields and are not consistently present in the seed workbook.",
        "next_fetcher": "data/manual/pipeline_assets.json plus prospectus/report parser",
    },
    {
        "key": "macro_data",
        "label": "Macro rates and deflation context",
        "priority": 7,
        "expected_fields": ["china_rates", "deposit_rates", "cpi_ppi", "policy_rates"],
        "why_missing": "Macro source URLs exist in config, but no parser writes dashboard-ready macro artifacts.",
        "next_fetcher": "scripts/ingest_macro.py",
    },
]


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None


def _price_age_days(price_asof: str | None, build_date: dt.date) -> int | None:
    asof = _parse_date(price_asof)
    if not asof:
        return None
    return max((build_date - asof).days, 0)


def _record_audit(record: dict[str, Any], build_date: dt.date) -> dict[str, Any]:
    listed = record.get("lifecycle_status") == "listed"
    price_age = _price_age_days(record.get("price_asof"), build_date)
    price_freshness = freshness_for_asof(record.get("price_asof"), build_date)
    seed_price = record.get("source_freshness") == "stale_seed"
    stale_price = listed and record.get("last_close_rmb") is not None and (
        seed_price or price_freshness == "stale"
    )

    missing_expected: list[str] = []
    missing_unexpected: list[str] = []
    stale_fields: list[str] = []
    adapter_gaps: list[str] = []
    reasons: list[str] = []

    if listed:
        if record.get("last_close_rmb") is None:
            missing_unexpected.extend(["last_close_rmb", "return_since_listing_pct"])
            reasons.append("Listed REIT is missing price fields.")
        elif stale_price:
            stale_fields.extend(["last_close_rmb", "return_since_listing_pct", "price_asof"])
            if seed_price:
                reasons.append("Listed REIT price comes from the stale workbook seed.")
            else:
                reasons.append("Listed REIT price is older than the latest expected trading day.")
    else:
        if record.get("last_close_rmb") is None:
            missing_expected.extend(["last_close_rmb", "return_since_listing_pct"])
            reasons.append("No trading price expected until the REIT lists.")

    if not record.get("source_url"):
        adapter_gaps.append("source_url")
    if record.get("zoning_type") is None:
        adapter_gaps.append("zoning_type")
    if record.get("pipeline_multiple_of_initial_assets") is None:
        adapter_gaps.append("pipeline_multiple_of_initial_assets")
    if not record.get("latest_news"):
        adapter_gaps.append("latest_news")

    status = "manual_seed"
    severity = "warn"
    if missing_unexpected:
        status = "missing_unexpected"
        severity = "bad"
    elif stale_fields:
        status = "stale_seed" if seed_price else "stale"
    elif not listed and missing_expected:
        status = "pending_not_listed"
        severity = "muted"
    elif listed and record.get("last_close_rmb") is not None:
        status = "ok"
        severity = "ok"
        if not seed_price and record.get("source_confidence") != "seed":
            reasons.append("Listed REIT price was refreshed by the automated price adapter.")

    return {
        "symbol": record.get("symbol"),
        "name_cn": record.get("name_cn"),
        "lifecycle_status": record.get("lifecycle_status"),
        "status": status,
        "severity": severity,
        "primary_reason": reasons[0] if reasons else "Seed row loaded; official source adapters still need to be connected.",
        "price_age_days": price_age,
        "stale_fields": stale_fields,
        "missing_expected": missing_expected,
        "missing_unexpected": missing_unexpected,
        "adapter_gaps": adapter_gaps,
        "fetch_priority": "prices_first" if listed else "wait_until_listed_for_prices",
    }


def audit_records(records: list[dict[str, Any]], price_asof: str, build_date: dt.date | None = None) -> dict[str, Any]:
    build_date = build_date or dt.date.today()
    items = [_record_audit(record, build_date) for record in records]
    status_counts = Counter(item["status"] for item in items)
    listed = [r for r in records if r.get("lifecycle_status") == "listed"]
    pending = [r for r in records if r.get("lifecycle_status") != "listed"]

    field_gap_counts: Counter[str] = Counter()
    stale_field_counts: Counter[str] = Counter()
    unexpected_missing_counts: Counter[str] = Counter()
    for item in items:
        field_gap_counts.update(item["adapter_gaps"])
        stale_field_counts.update(item["stale_fields"])
        unexpected_missing_counts.update(item["missing_unexpected"])

    return {
        "build_time": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "schema_v": 1,
        "price_asof": price_asof,
        "audit_date": build_date.isoformat(),
        "summary": {
            "total_records": len(records),
            "listed_records": len(listed),
            "pending_records": len(pending),
            "stale_seed_price_rows": sum(1 for item in items if item["status"] == "stale_seed"),
            "stale_seed_rows": sum(1 for item in items if item["status"] == "stale_seed"),
            "stale_non_seed_price_rows": sum(1 for item in items if item["status"] == "stale"),
            "fresh_price_rows": sum(1 for item in items if item["status"] == "ok"),
            "pending_price_rows": sum(1 for item in items if item["status"] == "pending_not_listed"),
            "unexpected_missing_price_rows": sum(1 for item in items if item["missing_unexpected"]),
            "rows_missing_source_url": field_gap_counts.get("source_url", 0),
            "status_counts": dict(status_counts),
            "adapter_gap_counts": dict(field_gap_counts),
            "stale_field_counts": dict(stale_field_counts),
            "unexpected_missing_counts": dict(unexpected_missing_counts),
        },
        "adapter_gaps": ADAPTER_GAPS,
        "items": items,
    }
