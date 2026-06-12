"""Adapter plan for company news and structured events."""
from __future__ import annotations

from adapter_status import adapter_payload, run_adapter


PAYLOAD = adapter_payload(
    key="news_events",
    label="Company and project news",
    target_artifact="creit_company_news.json",
    official_sources=[
        "SSE/SZSE announcements",
        "Fund-manager websites",
        "Originator investor-relations pages",
        "Approved search/news API when available",
    ],
    target_fields=[
        "symbol",
        "date",
        "headline",
        "event_type",
        "source",
        "source_url",
        "summary_en",
        "summary_zh",
    ],
    blocked_by="Entity aliases exist, but no news/search provider is configured.",
)


if __name__ == "__main__":
    run_adapter(PAYLOAD)
