from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_data import build  # noqa: E402
from ingest_wind_excel import DEFAULT_WORKBOOK, MASTER_JSON, load_records  # noqa: E402


class PipelineTests(unittest.TestCase):
    def test_workbook_ingest_counts(self):
        records = load_records(DEFAULT_WORKBOOK)
        self.assertEqual(len(records), 87)
        self.assertEqual(sum(1 for r in records if r["source_sheet"] == "基础设施不动产REITs"), 83)
        self.assertEqual(sum(1 for r in records if r["source_sheet"] == "商业不动产Reits"), 4)

    def test_pending_rows_are_not_failed_listed_records(self):
        records = load_records(DEFAULT_WORKBOOK)
        by_symbol = {r["symbol"]: r for r in records}
        self.assertEqual(by_symbol["508030.SH"]["lifecycle_status"], "approved_not_listed")
        self.assertEqual(by_symbol["508600.SH"]["lifecycle_status"], "listing_scheduled")
        self.assertEqual(by_symbol["508602.SH"]["lifecycle_status"], "listing_scheduled")
        self.assertEqual(by_symbol["508603.SH"]["lifecycle_status"], "approved_not_listed")
        self.assertEqual(by_symbol["508601.SH"]["lifecycle_status"], "approved_not_listed")

    def test_dashboard_contract(self):
        dashboard = build()
        self.assertEqual(dashboard["schema_v"], 1)
        self.assertEqual(dashboard["price_asof"], dashboard["latest_price_asof"])
        self.assertRegex(dashboard["latest_price_asof"], r"^2026-06-\d{2}$")
        self.assertEqual(dashboard["summary"]["total_rows"], 87)
        self.assertEqual(dashboard["summary"]["listed_count"], 82)
        self.assertGreater(dashboard["data_quality_summary"]["fresh_price_rows"], 0)
        self.assertLessEqual(dashboard["data_quality_summary"]["fresh_price_rows"], 82)
        self.assertEqual(
            dashboard["data_quality_summary"]["fresh_price_rows"] + dashboard["data_quality_summary"]["stale_seed_price_rows"],
            82,
        )
        self.assertEqual(dashboard["data_quality_summary"]["pending_price_rows"], 5)
        self.assertEqual(dashboard["data_quality_summary"]["unexpected_missing_price_rows"], 0)
        self.assertIs(dashboard["assumption_audit"]["pipeline_2x_is_heuristic"], True)
        self.assertTrue(dashboard["records"][0]["score_notes"])
        self.assertTrue(dashboard["records"][0]["data_quality_reason"])

    def test_generated_json_is_readable_utf8(self):
        dashboard = build()
        names = [r["name_cn"] for r in dashboard["records"]]
        assets = set(dashboard["summary"]["by_asset_type"])
        self.assertIn("红土创新盐田港REIT", names)
        self.assertIn("仓储物流", assets)
        self.assertFalse(any("å" in name for name in names))
        self.assertEqual(dashboard["source_workbook"], "公募reits已发行项目清单.xlsx")

    def test_lifecycle_statuses_have_badge_classes(self):
        dashboard = build()
        statuses = {r["lifecycle_status"] for r in dashboard["records"]}
        supported = {"listed", "approved_not_listed", "listing_scheduled", "delayed_or_unknown"}
        self.assertTrue(statuses.issubset(supported))

    def test_load_records_falls_back_to_committed_json_when_workbook_missing(self):
        missing = ROOT / "does-not-exist.xlsx"
        self.assertFalse(missing.exists())
        self.assertTrue(MASTER_JSON.exists(), f"Expected committed data file at {MASTER_JSON}")
        records = load_records(missing)
        self.assertEqual(len(records), 87)
        self.assertTrue(any(record["symbol"] == "180301.SZ" for record in records))

    def test_translation_toggle_is_present(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-lang="zh"', html)
        self.assertIn('data-lang="en"', html)
        self.assertIn("localStorage.getItem('creit-lang')", html)
        self.assertIn("tab_screener", html)
        self.assertIn("旧种子数据", html)

    def test_data_quality_artifact_contract(self):
        build()
        quality_path = ROOT / "data" / "creit_data_quality.json"
        self.assertTrue(quality_path.exists())
        text = quality_path.read_text(encoding="utf-8")
        self.assertIn("fresh_price_rows", text)
        self.assertIn("pending_not_listed", text)
        self.assertIn("ingest_exchange_prices.py", text)

    def test_source_health_has_fetcher_plan(self):
        build()
        health = (ROOT / "data" / "creit_source_health.json").read_text(encoding="utf-8")
        self.assertIn("scripts/ingest_exchange_prices.py", health)
        self.assertIn("scripts/ingest_nav_reports.py", health)
        self.assertIn('"key": "online_prices"', health)
        self.assertIn('"status": "ok"', health)


if __name__ == "__main__":
    unittest.main()
