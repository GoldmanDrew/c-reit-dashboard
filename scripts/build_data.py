"""Build static JSON artifacts for the C-REIT dashboard."""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Any

from audit_data_quality import audit_records
from enrichment import apply_translations, build_institution_roles, build_translation_artifact
from ingest_wind_excel import DEFAULT_WORKBOOK, load_records, write_outputs
from score_creits import attach_scores
from source_health import seed_source_health
from trading_calendar import freshness_for_asof


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config" / "config.yaml"


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _json_load(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _write_placeholder_if_missing(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    current = _json_load(path, None)
    if current:
        return current
    _json_dump(path, payload)
    return payload


def _load_config() -> dict[str, Any]:
    # Keep runtime dependencies minimal. This parses the small repo-owned YAML shape
    # well enough for dashboard metadata and source registry defaults.
    cfg: dict[str, Any] = {
        "heuristics": {
            "pipeline_multiple_rule_of_thumb": 2.0,
            "pipeline_multiple_note": "Investment heuristic; not treated as law unless a source says otherwise.",
        },
        "sources": {},
    }
    if not CONFIG_PATH.exists():
        return cfg
    section = None
    current_source = None
    for raw_line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            key = raw_line.split(":", 1)[0].strip()
            section = key
            current_source = None
            continue
        if section == "heuristics" and ":" in raw_line:
            key, value = raw_line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"')
            if key == "pipeline_multiple_rule_of_thumb":
                try:
                    cfg["heuristics"][key] = float(value)
                except ValueError:
                    pass
            elif key:
                cfg["heuristics"][key] = value
        elif section == "sources":
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            if indent == 2 and raw_line.strip().endswith(":"):
                current_source = raw_line.strip()[:-1]
                cfg["sources"][current_source] = {}
            elif current_source and ":" in raw_line:
                key, value = raw_line.split(":", 1)
                cfg["sources"][current_source][key.strip()] = value.strip().strip('"')
    return cfg


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    listed = [r for r in records if r.get("lifecycle_status") == "listed"]
    pending = [r for r in records if r.get("lifecycle_status") != "listed"]
    by_asset = Counter(r.get("asset_type_cn") or "Unknown" for r in records)
    by_lifecycle = Counter(r.get("lifecycle_status") or "unknown" for r in records)
    by_exchange = Counter(r.get("exchange") or "unknown" for r in records)
    total_size = sum(float(r.get("issue_size_rmb_bn") or 0) for r in records)
    commercial_size = sum(
        float(r.get("issue_size_rmb_bn") or 0)
        for r in records
        if r.get("asset_group") == "commercial_real_estate"
    )
    top_return = sorted(
        [r for r in records if r.get("return_since_listing_pct") is not None],
        key=lambda r: r["return_since_listing_pct"],
        reverse=True,
    )[:5]
    weak_return = sorted(
        [r for r in records if r.get("return_since_listing_pct") is not None],
        key=lambda r: r["return_since_listing_pct"],
    )[:5]
    return {
        "total_rows": len(records),
        "listed_count": len(listed),
        "pending_or_not_trading_count": len(pending),
        "commercial_not_trading_count": sum(1 for r in pending if r.get("asset_group") == "commercial_real_estate"),
        "total_issue_size_rmb_bn": round(total_size, 3),
        "commercial_issue_size_rmb_bn": round(commercial_size, 3),
        "by_asset_type": dict(by_asset),
        "by_lifecycle": dict(by_lifecycle),
        "by_exchange": dict(by_exchange),
        "top_return_since_listing": [
            {
                "symbol": r["symbol"],
                "name_cn": r["name_cn"],
                "return_since_listing_pct": r["return_since_listing_pct"],
            }
            for r in top_return
        ],
        "weakest_return_since_listing": [
            {
                "symbol": r["symbol"],
                "name_cn": r["name_cn"],
                "return_since_listing_pct": r["return_since_listing_pct"],
            }
            for r in weak_return
        ],
    }


def _aliases(records: list[dict[str, Any]]) -> dict[str, Any]:
    items = {}
    for r in records:
        aliases = [
            r.get("symbol"),
            r.get("name_cn"),
            r.get("name_en"),
            r.get("originator"),
            r.get("originator_en"),
            r.get("fund_manager"),
            r.get("fund_manager_en"),
            r.get("abs_plan_manager"),
            r.get("abs_plan_manager_en"),
            r.get("financial_advisor"),
            r.get("financial_advisor_en"),
        ]
        items[r["symbol"]] = sorted({str(a).strip() for a in aliases if a})
    return {"items": items}


def _empty_payload(kind: str) -> dict[str, Any]:
    return {
        "build_time": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "not_configured",
        "kind": kind,
        "items": [],
    }


def _load_price_artifact() -> dict[str, Any]:
    return _json_load(
        DATA_DIR / "creit_prices_latest.json",
        {
            "status": "missing",
            "adapter": "online_prices",
            "items": [],
            "source_stats": {"rows_parsed": 0, "coverage_pct": 0.0},
        },
    )


def _merge_price_artifact(records: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    by_symbol = {item.get("symbol"): item for item in payload.get("items") or [] if item.get("symbol")}
    for record in records:
        quote = by_symbol.get(record["symbol"])
        if not quote:
            continue
        price = quote.get("last_close_rmb")
        if price is None:
            continue
        record["last_close_rmb"] = price
        record["previous_close_rmb"] = quote.get("previous_close_rmb")
        record["daily_return_pct"] = quote.get("daily_return_pct")
        record["daily_change_rmb"] = quote.get("daily_change_rmb")
        record["volume"] = quote.get("volume")
        record["turnover"] = quote.get("turnover")
        record["price_asof"] = quote.get("price_asof")
        offer = record.get("offer_price_rmb")
        if offer:
            record["return_since_listing_pct"] = round(((float(price) / float(offer)) - 1.0) * 100.0, 6)
            record["return_since_listing"] = record["return_since_listing_pct"] / 100.0
        record["source_url"] = quote.get("source_url") or record.get("source_url")
        record["source_name"] = quote.get("source_name")
        record["source_asof"] = quote.get("source_asof") or quote.get("price_asof")
        record["source_confidence"] = quote.get("source_confidence") or "automated"
        record["source_freshness"] = freshness_for_asof(record.get("price_asof"))
        record["price_source"] = {
            "source_name": quote.get("source_name"),
            "source_url": quote.get("source_url"),
            "source_type": quote.get("source_type"),
            "fetch_time": quote.get("fetch_time"),
            "quote_time": quote.get("quote_time"),
        }


def _metrics_latest(records: list[dict[str, Any]], audit_by_symbol: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "build_time": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "seed_only",
        "by_symbol": {
            r["symbol"]: {
                "symbol": r["symbol"],
                "last_close_rmb": r.get("last_close_rmb"),
                "previous_close_rmb": r.get("previous_close_rmb"),
                "daily_return_pct": r.get("daily_return_pct"),
                "daily_change_rmb": r.get("daily_change_rmb"),
                "price_asof": r.get("price_asof"),
                "issue_size_rmb_bn": r.get("issue_size_rmb_bn"),
                "offer_price_rmb": r.get("offer_price_rmb"),
                "return_since_listing_pct": r.get("return_since_listing_pct"),
                "nav_rmb": None,
                "units_outstanding": None,
                "premium_discount_to_nav": None,
                "market_cap_rmb_bn": None,
                "volume": r.get("volume"),
                "turnover": r.get("turnover"),
                "distribution_yield_ttm": None,
                "source_status": "seed_only",
                "data_quality_status": audit_by_symbol.get(r["symbol"], {}).get("status", "manual_seed"),
                "data_quality_reason": audit_by_symbol.get(r["symbol"], {}).get("primary_reason"),
                "fetch_priority": audit_by_symbol.get(r["symbol"], {}).get("fetch_priority"),
            }
            for r in records
        },
    }


def _attach_latest_news(records: list[dict[str, Any]], news_payload: dict[str, Any]) -> None:
    latest_by_symbol: dict[str, dict[str, Any]] = {}
    for item in news_payload.get("items") or []:
        for symbol in item.get("symbols") or []:
            prev = latest_by_symbol.get(symbol)
            if prev is None or str(item.get("published_at") or "") > str(prev.get("published_at") or ""):
                latest_by_symbol[symbol] = item
    for record in records:
        latest = latest_by_symbol.get(record["symbol"])
        if latest:
            record["latest_news"] = {
                "title": latest.get("title_zh") or latest.get("title_en"),
                "category": latest.get("category"),
                "published_at": latest.get("published_at"),
                "url": latest.get("url"),
                "confidence": latest.get("confidence"),
                "match_tier": latest.get("match_tier"),
            }


def build() -> dict[str, Any]:
    cfg = _load_config()
    heuristics = cfg.get("heuristics") or {}
    pipeline_threshold = float(heuristics.get("pipeline_multiple_rule_of_thumb") or 2.0)

    records = load_records(DEFAULT_WORKBOOK)
    write_outputs(records, DATA_DIR)
    price_payload = _load_price_artifact()
    _merge_price_artifact(records, price_payload)
    translation_payload = build_translation_artifact(
        records,
        _json_load(DATA_DIR / "creit_name_translations.json", {}).get("items", {}),
    )
    apply_translations(records, translation_payload)
    roles_payload = build_institution_roles(records)
    scored = [attach_scores(r, pipeline_threshold) for r in records]
    news_payload = _json_load(DATA_DIR / "creit_company_news.json", {"items": []})
    _attach_latest_news(scored, news_payload)
    latest_price_asof = price_payload.get("source_asof") or dt.date.today().isoformat()
    quality = audit_records(scored, latest_price_asof)
    audit_by_symbol = {item["symbol"]: item for item in quality["items"]}
    for record in scored:
        audit_item = audit_by_symbol.get(record["symbol"], {})
        record["data_quality_status"] = audit_item.get("status")
        record["data_quality_reason"] = audit_item.get("primary_reason")
        record["data_quality_severity"] = audit_item.get("severity")
        record["stale_fields"] = audit_item.get("stale_fields", [])
        record["missing_expected"] = audit_item.get("missing_expected", [])
        record["missing_unexpected"] = audit_item.get("missing_unexpected", [])
        record["adapter_gaps"] = audit_item.get("adapter_gaps", [])
        record["fetch_priority"] = audit_item.get("fetch_priority")
        for key in (
            "previous_close_rmb",
            "daily_return_pct",
            "daily_change_rmb",
            "volume",
            "turnover",
            "nav_rmb",
            "units_outstanding",
            "market_cap_rmb_bn",
            "premium_discount_to_nav",
            "distribution_yield_ttm",
        ):
            record.setdefault(key, None)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    dashboard = {
        "build_time": now,
        "schema_v": 1,
        "source_workbook": DEFAULT_WORKBOOK.name,
        "price_asof": latest_price_asof,
        "latest_price_asof": latest_price_asof,
        "assumption_audit": {
            "workbook_source_of_truth": False,
            "pipeline_2x_is_heuristic": True,
            "one_universal_score": False,
            "legal_conclusion_in_scope": False,
        },
        "heuristics": heuristics,
        "source_registry": cfg.get("sources") or {},
        "summary": _summary(scored),
        "data_quality_summary": quality["summary"],
        "records": scored,
    }

    DATA_DIR.mkdir(exist_ok=True)
    _json_dump(DATA_DIR / "dashboard_data.json", dashboard)
    _json_dump(DATA_DIR / "creit_name_translations.json", translation_payload)
    _json_dump(DATA_DIR / "creit_institution_roles.json", roles_payload)
    _json_dump(DATA_DIR / "creit_aliases.json", _aliases(scored))
    _json_dump(DATA_DIR / "creit_metrics_latest.json", _metrics_latest(scored, audit_by_symbol))
    _json_dump(DATA_DIR / "creit_data_quality.json", quality)
    news_payload = _write_placeholder_if_missing(DATA_DIR / "creit_company_news.json", _empty_payload("company_news"))
    events_payload = _write_placeholder_if_missing(DATA_DIR / "creit_structured_events.json", _empty_payload("structured_events"))
    regulatory_payload = _write_placeholder_if_missing(DATA_DIR / "creit_regulatory_events.json", _empty_payload("regulatory_events"))
    _json_dump(
        DATA_DIR / "creit_source_health.json",
        seed_source_health(
            len(scored),
            latest_price_asof,
            quality,
            news_payload,
            events_payload,
            regulatory_payload,
            price_payload,
            translation_payload,
            roles_payload,
        ),
    )
    _json_dump(DATA_DIR / "creit_distributions.json", _empty_payload("distributions"))
    _json_dump(DATA_DIR / "private_deal_watch.json", {
        "build_time": now,
        "items": [
            {
                "id": "hillhouse-rmb-note-watch",
                "counterparty": "Hillhouse-related real estate credit watch",
                "note_size_rmb_mn": 150,
                "coupon_pct": 15,
                "collateral": "Property collateral; details pending source documents",
                "loan_to_own_flag": True,
                "status": "manual_watch",
                "source_confidence": "user_note",
            }
        ],
    })
    _json_dump(DATA_DIR / "creit_pipeline.json", {"build_time": now, "items": []})
    return dashboard


def main() -> None:
    dashboard = build()
    print(
        f"Wrote dashboard_data.json with {dashboard['summary']['total_rows']} records "
        f"({dashboard['summary']['listed_count']} listed)."
    )


if __name__ == "__main__":
    main()
