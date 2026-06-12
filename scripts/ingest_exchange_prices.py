"""Adapter plan for official C-REIT prices, volume, and turnover."""
from __future__ import annotations

from adapter_status import adapter_payload, run_adapter


PAYLOAD = adapter_payload(
    key="online_prices",
    label="Prices, volume, turnover",
    target_artifact="creit_prices_latest.json",
    official_sources=[
        "Shanghai Stock Exchange REIT product/listing data",
        "Shenzhen Stock Exchange REIT product/listing data",
        "Licensed market-data provider if exchange pages are dynamic or restricted",
    ],
    target_fields=[
        "symbol",
        "last_close_rmb",
        "previous_close_rmb",
        "daily_return_pct",
        "volume",
        "turnover",
        "price_asof",
        "source_url",
    ],
    blocked_by="No official or licensed live price feed is configured in the repository.",
)


if __name__ == "__main__":
    run_adapter(PAYLOAD)
