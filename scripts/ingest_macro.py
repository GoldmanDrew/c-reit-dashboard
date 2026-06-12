"""Adapter plan for macro rates and deflation context."""
from __future__ import annotations

from adapter_status import adapter_payload, run_adapter


PAYLOAD = adapter_payload(
    key="macro_data",
    label="Macro rates and deflation context",
    target_artifact="macro_china_rates.json",
    official_sources=[
        "ChinaBond yield curves",
        "PBOC policy and deposit-rate releases",
        "National Bureau of Statistics CPI/PPI releases",
    ],
    target_fields=[
        "date",
        "curve_tenor",
        "yield_pct",
        "deposit_rate_pct",
        "cpi_yoy_pct",
        "ppi_yoy_pct",
        "source_url",
    ],
    blocked_by="Macro source URLs exist in config, but no parser writes dashboard-ready macro data.",
)


if __name__ == "__main__":
    run_adapter(PAYLOAD)
