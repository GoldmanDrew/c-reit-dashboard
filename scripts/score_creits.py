"""Transparent first-pass C-REIT scoring helpers."""
from __future__ import annotations

from typing import Any


def clamp(value: float | None, lo: float = 0.0, hi: float = 100.0) -> float | None:
    if value is None:
        return None
    return max(lo, min(hi, value))


def valuation_score(record: dict[str, Any]) -> float | None:
    """Cheap/stronger price performance scores higher for seed-only v1."""
    ret = record.get("return_since_listing_pct")
    if ret is None:
        return None
    # Center around 0% since-listing return; penalize deep losers/rich winners less aggressively.
    return round(clamp(50 + (float(ret) / 2.0)), 1)


def liquidity_score(record: dict[str, Any]) -> float | None:
    size = record.get("issue_size_rmb_bn")
    if size is None:
        return None
    return round(clamp(float(size) * 1.5), 1)


def pipeline_readiness_score(record: dict[str, Any], threshold: float = 2.0) -> float | None:
    multiple = record.get("pipeline_multiple_of_initial_assets")
    if multiple is None:
        return None
    return round(clamp((float(multiple) / threshold) * 70), 1)


def regulatory_complexity_score(record: dict[str, Any]) -> float | None:
    if record.get("lifecycle_status") == "listed":
        return 20.0
    if record.get("lifecycle_status") == "listing_scheduled":
        return 40.0
    return 55.0


def deflation_sensitivity_score(record: dict[str, Any]) -> float | None:
    group = record.get("asset_group")
    table = {
        "toll_road_transport": 35,
        "logistics": 45,
        "energy_infrastructure": 35,
        "rental_housing": 55,
        "consumer_infrastructure": 70,
        "commercial_real_estate": 80,
        "industrial_park": 65,
        "new_infrastructure": 50,
    }
    return float(table.get(group, 60))


def attach_scores(record: dict[str, Any], pipeline_threshold: float = 2.0) -> dict[str, Any]:
    out = dict(record)
    out["valuation_score"] = valuation_score(out)
    out["liquidity_score"] = liquidity_score(out)
    out["pipeline_readiness_score"] = pipeline_readiness_score(out, pipeline_threshold)
    out["regulatory_complexity_score"] = regulatory_complexity_score(out)
    out["deflation_sensitivity_score"] = deflation_sensitivity_score(out)
    out["score_notes"] = {
        "valuation_score": "Seed v1 proxy from since-listing return until NAV/premium data is online.",
        "liquidity_score": "Seed v1 proxy from issue size until volume/turnover data is online.",
        "pipeline_readiness_score": "Uses 2x pipeline as an investment heuristic, not a legal rule.",
        "regulatory_complexity_score": "Lifecycle proxy until source-backed regulator stages are online.",
        "deflation_sensitivity_score": "Asset-type heuristic until property-level operating data is online.",
    }
    return out
