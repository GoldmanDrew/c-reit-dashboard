from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_data import build  # noqa: E402
from ingest_wind_excel import DEFAULT_WORKBOOK, load_records  # noqa: E402


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
        self.assertEqual(dashboard["price_asof"], "2026-06-10")
        self.assertEqual(dashboard["summary"]["total_rows"], 87)
        self.assertEqual(dashboard["summary"]["listed_count"], 82)
        self.assertIs(dashboard["assumption_audit"]["pipeline_2x_is_heuristic"], True)
        self.assertTrue(dashboard["records"][0]["score_notes"])

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

    def test_translation_toggle_is_present(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-lang="zh"', html)
        self.assertIn('data-lang="en"', html)
        self.assertIn("localStorage.getItem('creit-lang')", html)
        self.assertIn("tab_screener", html)


if __name__ == "__main__":
    unittest.main()
