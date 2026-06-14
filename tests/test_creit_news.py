from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ingest_announcements import (  # noqa: E402
    MASTER_DATA,
    NewsItem,
    ReitProfile,
    build_structured_events,
    classify_text,
    dedupe_news,
    fetch_news,
    load_profiles,
    resolve_symbols,
)


class CreitNewsTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [
            ReitProfile(
                symbol="508600.SH",
                name_cn="汇添富上海地产商业REIT",
                exchange="SSE",
                lifecycle_status="listing_scheduled",
                asset_group="commercial_real_estate",
                strong_aliases=["508600", "508600.SH", "汇添富上海地产商业REIT"],
                weak_aliases=["汇添富基金管理股份有限公司", "上海世博发展(集团)有限公司"],
            ),
            ReitProfile(
                symbol="180601.SZ",
                name_cn="华夏华润消费REIT",
                exchange="SZSE",
                lifecycle_status="listed",
                asset_group="consumer_infrastructure",
                strong_aliases=["180601", "180601.SZ", "华夏华润消费REIT"],
                weak_aliases=["华夏基金管理有限公司", "华润商业资产控股有限公司"],
            ),
        ]

    def test_classify_listing_and_distribution(self):
        cat, conf = classify_text("汇添富上海地产商业REIT将于6月18日上市")
        self.assertEqual(cat, "listing_schedule")
        self.assertGreaterEqual(conf, 0.7)

        cat, conf = classify_text("华夏华润消费REIT发布收益分配公告")
        self.assertEqual(cat, "distribution")
        self.assertGreaterEqual(conf, 0.7)

    def test_resolve_symbol_exact_fund_name(self):
        symbols, tier = resolve_symbols("汇添富上海地产商业REIT正式成立", self.profiles)
        self.assertEqual(symbols, ["508600.SH"])
        self.assertEqual(tier, "explicit")

    def test_fetch_news_parses_rss_rows(self):
        rows = [
            {
                "title": "汇添富上海地产商业REIT将于6月18日登陆上交所",
                "description": "基金合同已生效，产品即将上市。",
                "link": "https://example.com/508600",
                "pub_date": "Fri, 12 Jun 2026 12:00:00 GMT",
                "source": "观点网",
            },
            {
                "title": "华夏华润消费REIT发布收益分配公告",
                "description": "本次收益分配相关公告。",
                "link": "https://example.com/180601",
                "pub_date": "Fri, 12 Jun 2026 11:00:00 GMT",
                "source": "公告",
            },
        ]

        with patch("ingest_announcements.fetch_google_news_rss", return_value=rows), patch(
            "ingest_announcements.QUERY_DELAY_SEC", 0
        ):
            news, stats = fetch_news(self.profiles, symbols={"508600.SH"}, window_days=120)

        self.assertGreaterEqual(len(news), 2)
        self.assertEqual(stats["items_after_dedupe"], len(news))
        self.assertIn("508600.SH", {s for item in news for s in item.symbols})
        self.assertIn("listing_schedule", {item.category for item in news})
        self.assertIn("distribution", {item.category for item in news})

    def test_dedupe_merges_sources_and_symbols(self):
        base = dict(
            category="listing_schedule",
            confidence=0.9,
            match_tier="explicit",
            published_at="2026-06-12T12:00:00+00:00",
            title_zh="汇添富上海地产商业REIT将上市",
            title_en=None,
            summary_zh=None,
            summary_en=None,
            url="https://example.com/a",
            source_type="google_news_rss",
            source_query="q",
        )
        out = dedupe_news(
            [
                NewsItem(id="a", symbols=["508600.SH"], publisher="A", source_publishers=["A"], **base),
                NewsItem(id="b", symbols=["508600.SH"], publisher="B", source_publishers=["B"], **base),
            ]
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].source_count, 2)
        self.assertEqual(set(out[0].source_publishers), {"A", "B"})

    def test_build_structured_events_links_news(self):
        news = [
            NewsItem(
                id="a",
                symbols=["508600.SH"],
                category="listing_schedule",
                confidence=0.91,
                match_tier="explicit",
                published_at="2026-06-12T12:00:00+00:00",
                title_zh="汇添富上海地产商业REIT将上市",
                title_en=None,
                summary_zh=None,
                summary_en=None,
                url="https://example.com/a",
                publisher="A",
                source_type="google_news_rss",
                source_query="q",
            )
        ]
        events, regulatory = build_structured_events(news)
        self.assertEqual(len(events), 1)
        self.assertEqual(regulatory, [])
        self.assertEqual(news[0].linked_event_id, events[0]["id"])

    def test_load_profiles_prefers_committed_master_json(self):
        self.assertTrue(MASTER_DATA.exists(), f"Expected committed data file at {MASTER_DATA}")
        profiles = load_profiles()
        self.assertGreater(len(profiles), 0)
        self.assertTrue(any(profile.symbol == "180301.SZ" for profile in profiles))


if __name__ == "__main__":
    unittest.main()
