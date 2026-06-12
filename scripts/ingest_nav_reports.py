"""Adapter plan for NAV, units, market cap, and premium/discount."""
from __future__ import annotations

from adapter_status import adapter_payload, run_adapter


PAYLOAD = adapter_payload(
    key="nav_market_cap",
    label="NAV, units, market cap, premium/discount",
    target_artifact="creit_nav_latest.json",
    official_sources=[
        "Fund-manager periodic reports",
        "SSE/SZSE fund disclosure pages",
        "Prospectus and periodic report PDFs",
    ],
    target_fields=[
        "symbol",
        "nav_rmb",
        "units_outstanding",
        "market_cap_rmb_bn",
        "premium_discount_to_nav",
        "nav_asof",
        "source_url",
    ],
    blocked_by="No report/PDF parser or fund-manager disclosure source is configured yet.",
)


if __name__ == "__main__":
    run_adapter(PAYLOAD)
