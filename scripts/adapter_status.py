"""Shared helpers for not-yet-connected online data adapters."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def adapter_payload(
    *,
    key: str,
    label: str,
    target_artifact: str,
    official_sources: list[str],
    target_fields: list[str],
    blocked_by: str,
) -> dict[str, Any]:
    return {
        "build_time": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "not_configured",
        "adapter": key,
        "label": label,
        "target_artifact": target_artifact,
        "official_sources": official_sources,
        "target_fields": target_fields,
        "blocked_by": blocked_by,
        "items": [],
    }


def run_adapter(payload: dict[str, Any]) -> None:
    parser = argparse.ArgumentParser(description=f"Emit adapter status for {payload['label']}.")
    parser.add_argument("--write", action="store_true", help="Write the adapter status to its target artifact.")
    args = parser.parse_args()

    if args.write:
        path = DATA_DIR / payload["target_artifact"]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {path}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
