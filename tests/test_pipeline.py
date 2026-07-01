from __future__ import annotations

import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_data import build  # noqa: E402
from ingest_wind_excel import DEFAULT_WORKBOOK, MASTER_JSON, load_records  # noqa: E402
from trading_calendar import freshness_for_asof  # noqa: E402


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
        latest_asof = dashboard["latest_price_asof"]
        self.assertRegex(latest_asof, r"^\d{4}-\d{2}-\d{2}$")
        dt.date.fromisoformat(latest_asof)
        self.assertEqual(dashboard["summary"]["total_rows"], 87)
        self.assertEqual(dashboard["summary"]["listed_count"], 82)
        dq = dashboard["data_quality_summary"]
        fresh = dq["fresh_price_rows"]
        stale_seed = dq["stale_seed_price_rows"]
        stale = dq.get("stale_non_seed_price_rows", 0)
        if freshness_for_asof(latest_asof) == "fresh":
            self.assertGreater(fresh, 0)
            self.assertLessEqual(fresh, 82)
        else:
            self.assertEqual(fresh, 0)
            self.assertGreater(stale_seed + stale, 0)
        self.assertEqual(fresh + stale_seed + stale, 82)
        self.assertEqual(dq["pending_price_rows"], 5)
        self.assertEqual(dashboard["data_quality_summary"]["unexpected_missing_price_rows"], 0)
        self.assertIs(dashboard["assumption_audit"]["pipeline_2x_is_heuristic"], True)
        self.assertTrue(dashboard["records"][0]["score_notes"])
        self.assertTrue(dashboard["records"][0]["data_quality_reason"])
        self.assertIn("name_cn", dashboard["records"][0])
        self.assertIn("name_en", dashboard["records"][0])
        self.assertIn("originator_en", dashboard["records"][0])
        self.assertIn("fund_manager_en", dashboard["records"][0])
        self.assertIn("abs_plan_manager_en", dashboard["records"][0])
        self.assertIn("financial_advisor_en", dashboard["records"][0])
        self.assertIn(dashboard["records"][0]["translation_confidence"], {"high", "medium", "low"})

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
        self.assertIn("displayName", html)
        self.assertIn("name_en", html)
        self.assertIn("originator_en", html)
        self.assertIn("financial_advisor_en", html)
        self.assertIn("tab_screener", html)
        self.assertIn("旧种子数据", html)

    def test_translation_and_institution_role_artifacts(self):
        dashboard = build()
        translation_path = ROOT / "data" / "creit_name_translations.json"
        roles_path = ROOT / "data" / "creit_institution_roles.json"
        self.assertTrue(translation_path.exists())
        self.assertTrue(roles_path.exists())
        translations = json.loads(translation_path.read_text(encoding="utf-8"))
        roles = json.loads(roles_path.read_text(encoding="utf-8"))
        self.assertEqual(translations["coverage"]["total_records"], 87)
        self.assertGreater(translations["coverage"]["records_with_name_en"], 0)
        self.assertIn(dashboard["records"][0]["symbol"], translations["items"])
        self.assertGreater(roles["coverage"]["roles_parsed"], 0)
        self.assertTrue(any(item["role"] == "financial_advisor" for item in roles["items"]))
        self.assertTrue(any(item["role"] == "abs_plan_manager" for item in roles["items"]))

    def test_metrics_latest_carries_trading_and_future_valuation_fields(self):
        build()
        metrics = json.loads((ROOT / "data" / "creit_metrics_latest.json").read_text(encoding="utf-8"))
        sample = next(item for item in metrics["by_symbol"].values() if item["last_close_rmb"] is not None)
        for key in (
            "previous_close_rmb",
            "daily_return_pct",
            "daily_change_rmb",
            "volume",
            "turnover",
            "nav_rmb",
            "units_outstanding",
            "market_cap_rmb_bn",
            "premium_discount_to_nav",
            "distribution_yield_ttm",
        ):
            self.assertIn(key, sample)
        self.assertIsNone(sample["nav_rmb"])
        self.assertIsNone(sample["market_cap_rmb_bn"])

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
        self.assertIn('"key": "english_translations"', health)
        self.assertIn('"key": "institution_roles"', health)
        self.assertIn("NAV / market cap reports", health)
        self.assertIn('"status": "ok"', health)


if __name__ == "__main__":
    unittest.main()
