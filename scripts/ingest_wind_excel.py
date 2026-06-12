"""Normalize the seed C-REIT workbook into CSV and JSON-friendly records."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = ROOT / "公募reits已发行项目清单.xlsx"
DATA_DIR = ROOT / "data"
CONFIG = ROOT / "config" / "asset_type_map.yaml"
PRICE_ASOF = "2026-06-10"
CODE_RE = re.compile(r"^\d{6}\.(SH|SZ)$")

COLUMN_MAP = {
    "证券代码": "symbol",
    "证券简称": "name_cn",
    "发行公告日": "issue_announcement_date",
    "上市日期": "listing_date",
    "资产类型": "asset_type_cn",
    "基金上市地点": "exchange_cn",
    "原始权益人": "originator",
    "财务顾问": "financial_advisor",
    "专项计划管理人": "abs_plan_manager",
    "基金管理人": "fund_manager",
    "上市基金发行价格（元）": "offer_price_rmb",
    "上市至今涨跌幅%": "return_since_listing_pct",
}


def _clean_col(name: Any) -> str:
    return str(name).replace("\n", "").strip()


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    return value


def _num(value: Any) -> float | None:
    value = _json_value(value)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_asset_groups() -> dict[str, str]:
    fallback = {
        "园区基础设施": "industrial_park",
        "交通基础设施": "toll_road_transport",
        "消费基础设施": "consumer_infrastructure",
        "仓储物流": "logistics",
        "能源基础设施": "energy_infrastructure",
        "保障性租赁住房": "rental_housing",
        "生态环保": "environmental",
        "新型基础设施": "new_infrastructure",
        "水利设施": "water_conservancy",
        "市政设施": "municipal_facilities",
        "商业不动产": "commercial_real_estate",
    }
    if not CONFIG.exists():
        return fallback
    groups: dict[str, str] = {}
    in_groups = False
    for raw_line in CONFIG.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("asset_groups:"):
            in_groups = True
            continue
        if in_groups and line and not line.startswith(" "):
            break
        if in_groups and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                groups[key] = value
    return groups or fallback


def _status(row: dict[str, Any], build_date: dt.date) -> str:
    listing = row.get("listing_date")
    has_price = row.get("last_close_rmb") is not None
    if has_price:
        return "listed"
    if listing:
        try:
            listing_date = dt.date.fromisoformat(str(listing))
        except ValueError:
            return "delayed_or_unknown"
        if listing_date > build_date:
            return "listing_scheduled"
        return "approved_not_listed"
    return "approved_not_listed"


def load_records(workbook: Path = DEFAULT_WORKBOOK, build_date: dt.date | None = None) -> list[dict[str, Any]]:
    build_date = build_date or dt.date.today()
    asset_groups = _load_asset_groups()
    records: list[dict[str, Any]] = []

    with pd.ExcelFile(workbook) as xls:
        for sheet_name in xls.sheet_names:
            raw = pd.read_excel(xls, sheet_name=sheet_name, header=0)
            raw.columns = [_clean_col(c) for c in raw.columns]

            code_col = "证券代码"
            raw[code_col] = raw[code_col].astype(str).str.strip()
            df = raw[raw[code_col].str.match(CODE_RE, na=False)].copy()

            issue_size_col = next((c for c in df.columns if c.startswith("发行规模")), None)
            close_col = next((c for c in df.columns if c.startswith("前收盘价")), None)

            for _, src in df.iterrows():
                rec: dict[str, Any] = {}
                for cn, en in COLUMN_MAP.items():
                    rec[en] = _json_value(src.get(cn))

                rec["symbol"] = str(rec["symbol"]).strip()
                rec["source_sheet"] = sheet_name
                rec["entity_type"] = "listed_reit"
                rec["price_asof"] = PRICE_ASOF
                rec["issue_size_rmb_bn"] = _num(src.get(issue_size_col)) if issue_size_col else None
                rec["offer_price_rmb"] = _num(rec.get("offer_price_rmb"))
                rec["last_close_rmb"] = _num(src.get(close_col)) if close_col else None
                rec["return_since_listing_pct"] = _num(rec.get("return_since_listing_pct"))
                rec["return_since_listing"] = (
                    rec["return_since_listing_pct"] / 100.0
                    if rec["return_since_listing_pct"] is not None
                    else None
                )
                rec["asset_group"] = asset_groups.get(rec.get("asset_type_cn") or "", "other")
                rec["exchange"] = "SSE" if rec["symbol"].endswith(".SH") else "SZSE"
                rec["lifecycle_status"] = _status(rec, build_date)
                if rec["lifecycle_status"] != "listed":
                    rec["entity_type"] = "approved_reit"
                rec["regulatory_path"] = "default"
                rec["regulatory_stage"] = "listing" if rec["lifecycle_status"] == "listed" else "offering_or_approved"
                rec["zoning_type"] = None
                rec["pipeline_multiple_of_initial_assets"] = None
                rec["pipeline_readiness_score"] = None
                rec["regulatory_complexity_score"] = None
                rec["deflation_sensitivity_score"] = None
                rec["latest_news"] = None
                rec["source_url"] = None
                rec["source_asof"] = PRICE_ASOF
                rec["source_confidence"] = "seed"
                rec["source_freshness"] = "stale_seed"
                records.append(rec)

    return records


def write_outputs(records: list[dict[str, Any]], output_dir: Path = DATA_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output_dir / "creit_master.csv", index=False, encoding="utf-8-sig")
    (output_dir / "creit_master.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize seed C-REIT workbook.")
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()

    records = load_records(args.workbook)
    write_outputs(records, args.output_dir)
    print(f"Wrote {len(records)} records to {args.output_dir}")


if __name__ == "__main__":
    main()
