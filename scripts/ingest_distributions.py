"""Adapter plan for C-REIT distributions and trailing yield."""
from __future__ import annotations

from adapter_status import adapter_payload, run_adapter


PAYLOAD = adapter_payload(
    key="distributions",
    label="Distributions and yield",
    target_artifact="creit_distributions.json",
    official_sources=[
        "SSE/SZSE distribution announcements",
        "Fund-manager announcement pages",
        "Periodic reports",
    ],
    target_fields=[
        "symbol",
        "distribution_date",
        "distribution_rmb",
        "ttm_distribution_rmb",
        "distribution_yield_ttm",
        "source_url",
    ],
    blocked_by="Distribution announcement ingestion is not connected.",
)


if __name__ == "__main__":
    run_adapter(PAYLOAD)
