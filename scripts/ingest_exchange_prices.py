"""Fetch latest C-REIT prices, volume, and turnover."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ingest_wind_excel import DEFAULT_WORKBOOK, load_records
from trading_calendar import freshness_for_asof, latest_weekday


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TARGET = DATA_DIR / "creit_prices_latest.json"
ENDPOINT = "https://push2.eastmoney.com/api/qt/ulist.np/get"
FIELDS = "f12,f13,f14,f2,f3,f4,f5,f6,f18,f124"


def _secid(symbol: str) -> str:
    code, exchange = symbol.split(".", 1)
    market = "1" if exchange == "SH" else "0"
    return f"{market}.{code}"


def _symbol(code: str, market: Any) -> str:
    return f"{code}.SH" if int(market) == 1 else f"{code}.SZ"


def _num(value: Any) -> float | None:
    if value in (None, "-", ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _quote_url(secids: list[str]) -> str:
    query = urlencode(
        {
            "fltt": "2",
            "invt": "2",
            "fields": FIELDS,
            "secids": ",".join(secids),
        }
    )
    return f"{ENDPOINT}?{query}"


def _fetch_batch(secids: list[str], timeout: int = 20) -> dict[str, Any]:
    url = _quote_url(secids)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 c-reit-dashboard/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _quote_page_url(symbol: str) -> str:
    code, exchange = symbol.split(".", 1)
    prefix = "sh" if exchange == "SH" else "sz"
    return f"https://quote.eastmoney.com/{prefix}{code}.html"


def _parse_quote(row: dict[str, Any], fetch_time: str) -> dict[str, Any] | None:
    price = _num(row.get("f2"))
    code = row.get("f12")
    market = row.get("f13")
    timestamp = row.get("f124")
    if not code or market is None or price is None or not timestamp:
        return None
    quote_time = dt.datetime.fromtimestamp(int(timestamp), dt.timezone.utc)
    price_asof = quote_time.date().isoformat()
    previous_close = _num(row.get("f18"))
    symbol = _symbol(str(code), market)
    return {
        "symbol": symbol,
        "name_cn": row.get("f14"),
        "last_close_rmb": price,
        "previous_close_rmb": previous_close,
        "daily_return_pct": _num(row.get("f3")),
        "daily_change_rmb": _num(row.get("f4")),
        "volume": _num(row.get("f5")),
        "turnover": _num(row.get("f6")),
        "price_asof": price_asof,
        "quote_time": quote_time.isoformat(),
        "source_name": "Eastmoney public quote endpoint",
        "source_url": _quote_page_url(symbol),
        "source_type": "public_quote",
        "source_confidence": "public_quote",
        "source_asof": price_asof,
        "fetch_time": fetch_time,
    }


def fetch_prices(symbols: list[str], batch_size: int = 80) -> dict[str, Any]:
    fetch_time = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for start in range(0, len(symbols), batch_size):
        batch = symbols[start : start + batch_size]
        secids = [_secid(symbol) for symbol in batch]
        url = _quote_url(secids)
        try:
            payload = _fetch_batch(secids)
            rows = ((payload.get("data") or {}).get("diff") or [])
            for row in rows:
                parsed = _parse_quote(row, fetch_time)
                if parsed:
                    items.append(parsed)
        except Exception as exc:  # noqa: BLE001 - preserve adapter failure in artifact
            errors.append({"batch": ",".join(batch), "error": str(exc)})
        time.sleep(0.2)

    asof_dates = sorted({item["price_asof"] for item in items if item.get("price_asof")})
    latest_asof = asof_dates[-1] if asof_dates else None
    expected_asof = latest_weekday().isoformat()
    status = "ok" if items and not errors else "partial" if items else "failed"
    return {
        "build_time": fetch_time,
        "status": status,
        "adapter": "online_prices",
        "provider": "eastmoney_public_quote",
        "provider_note": (
            "Automated public quote source. Replace with an official exchange data product "
            "or licensed vendor feed if redistribution or production use requires it."
        ),
        "expected_price_asof": expected_asof,
        "source_asof": latest_asof,
        "source_freshness": freshness_for_asof(latest_asof),
        "items": items,
        "source_stats": {
            "symbols_requested": len(symbols),
            "rows_parsed": len(items),
            "coverage_pct": round((len(items) / float(len(symbols) or 1)) * 100, 1),
            "error_count": len(errors),
            "errors": errors,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch latest C-REIT price data.")
    parser.add_argument("--output", type=Path, default=TARGET)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    args = parser.parse_args()

    records = load_records(args.workbook)
    symbols = sorted({r["symbol"] for r in records if r.get("lifecycle_status") == "listed"})
    payload = fetch_prices(symbols)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {args.output} with {len(payload['items'])}/{len(symbols)} prices "
        f"({payload['status']}, asof {payload.get('source_asof')})"
    )


if __name__ == "__main__":
    main()
