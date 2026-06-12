"""Adapter plan for regulatory notices and approval events."""
from __future__ import annotations

from adapter_status import adapter_payload, run_adapter


PAYLOAD = adapter_payload(
    key="regulatory_tape",
    label="Regulatory notices",
    target_artifact="creit_regulatory_events.json",
    official_sources=[
        "NDRC notices",
        "CSRC registrations",
        "SSE/SZSE review and listing notices",
    ],
    target_fields=[
        "symbol",
        "event_date",
        "body",
        "notice_title",
        "project_stage",
        "regulatory_risk_tag",
        "source_url",
    ],
    blocked_by="Regulator notice feeds are registered in config but not parsed.",
)


if __name__ == "__main__":
    run_adapter(PAYLOAD)
