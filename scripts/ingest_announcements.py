"""Fetch and classify C-REIT news/events for the static dashboard.

The first live provider is Google News RSS because it needs no key and returns
current Chinese C-REIT headlines reliably. The script is intentionally strict:
items are attached to a REIT only when the symbol/fund name appears, or when a
per-REIT query plus a REIT-specific weak alias supports an inferred match.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ingest_wind_excel import DEFAULT_WORKBOOK, load_records


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_NEWS = DATA_DIR / "creit_company_news.json"
OUT_EVENTS = DATA_DIR / "creit_structured_events.json"
OUT_REGULATORY = DATA_DIR / "creit_regulatory_events.json"
OUT_CACHE = DATA_DIR / "creit_news_source_cache.json"

HTTP_TIMEOUT_SEC = int(os.getenv("CREIT_NEWS_HTTP_TIMEOUT_SEC", "20"))
WINDOW_DAYS = int(os.getenv("CREIT_NEWS_WINDOW_DAYS", "90"))
MAX_PER_QUERY = int(os.getenv("CREIT_NEWS_MAX_PER_QUERY", "20"))
MAX_REIT_QUERIES = int(os.getenv("CREIT_NEWS_MAX_REIT_QUERIES", "90"))
QUERY_DELAY_SEC = float(os.getenv("CREIT_NEWS_QUERY_DELAY_SEC", "0.15"))
MAX_WORKERS = int(os.getenv("CREIT_NEWS_MAX_WORKERS", "8"))
ENABLE_GLOBAL_QUERIES = os.getenv("CREIT_NEWS_ENABLE_GLOBAL_QUERIES", "1") not in {"0", "false", "False"}


EVENT_PRIORITY = {
    "listing_schedule": 95,
    "listing_approval": 90,
    "offering_result": 80,
    "expansion_acquisition": 75,
    "distribution": 70,
    "nav_report": 60,
    "regulatory_policy": 55,
    "manager_change": 50,
    "originator_credit_event": 45,
    "pipeline_asset_update": 40,
    "macro_policy": 30,
    "market_context": 10,
}

POSITIVE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "listing_schedule": [
        re.compile(p, re.I)
        for p in (
            r"上市",
            r"挂牌",
            r"登陆",
            r"合同生效",
            r"正式成立",
            r"listed",
            r"listing",
        )
    ],
    "listing_approval": [
        re.compile(p, re.I)
        for p in (
            r"获批",
            r"注册生效",
            r"准予注册",
            r"受理",
            r"通过",
            r"approved",
            r"approval",
        )
    ],
    "offering_result": [
        re.compile(p, re.I)
        for p in (r"募集", r"发行", r"发售", r"询价", r"认购", r"offering", r"issuance")
    ],
    "expansion_acquisition": [
        re.compile(p, re.I)
        for p in (r"扩募", r"新购入", r"购入", r"收购", r"并购", r"asset acquisition", r"expansion")
    ],
    "distribution": [
        re.compile(p, re.I)
        for p in (r"分红", r"分派", r"收益分配", r"除息", r"派息", r"distribution", r"dividend")
    ],
    "nav_report": [
        re.compile(p, re.I)
        for p in (r"净值", r"估值", r"年报", r"季报", r"中报", r"NAV", r"valuation", r"annual report")
    ],
    "regulatory_policy": [
        re.compile(p, re.I)
        for p in (r"监管", r"证监会", r"发改委", r"交易所", r"指引", r"规则", r"policy", r"regulator")
    ],
    "manager_change": [
        re.compile(p, re.I)
        for p in (r"基金管理人变更", r"管理人变更", r"管理层变动", r"manager change")
    ],
    "originator_credit_event": [
        re.compile(p, re.I)
        for p in (r"违约", r"评级下调", r"债务", r"流动性", r"credit", r"default", r"downgrade")
    ],
    "pipeline_asset_update": [
        re.compile(p, re.I)
        for p in (r"底层资产", r"储备项目", r"项目储备", r"管线", r"pipeline", r"underlying asset")
    ],
    "macro_policy": [
        re.compile(p, re.I)
        for p in (r"利率", r"通缩", r"地产政策", r"货币政策", r"降息", r"宏观", r"deflation", r"rate cut")
    ],
    "market_context": [
        re.compile(p, re.I)
        for p in (r"公募REIT", r"基础设施REIT", r"C-REIT", r"REITs?")
    ],
}

NEGATIVE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"招聘",
        r"广告",
        r"培训",
        r"课程",
        r"研报摘要",
        r"直播",
        r"podcast",
        r"opinion",
    )
]

GLOBAL_QUERIES = [
    '"公募REIT" "上市"',
    '"公募REIT" "获批"',
    '"公募REIT" "扩募"',
    '"公募REIT" "分红"',
    '"基础设施REIT" "收益分配"',
    '"商业不动产REIT" "上市"',
    '"基础设施REIT" "监管"',
    '"REIT" "发改委"',
]


@dataclass
class ReitProfile:
    symbol: str
    name_cn: str
    exchange: str
    lifecycle_status: str
    asset_group: str | None
    strong_aliases: list[str] = field(default_factory=list)
    weak_aliases: list[str] = field(default_factory=list)


@dataclass
class NewsItem:
    id: str
    symbols: list[str]
    category: str
    confidence: float
    match_tier: str
    published_at: str | None
    title_zh: str | None
    title_en: str | None
    summary_zh: str | None
    summary_en: str | None
    url: str | None
    publisher: str | None
    source_type: str
    source_query: str
    linked_event_id: str | None = None
    source_count: int = 1
    source_publishers: list[str] = field(default_factory=list)


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def _norm_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _strip_html(value: str | None) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _slug(value: str | None, limit: int = 80) -> str:
    text = (value or "").lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text).strip("-")
    return text[:limit] or "untitled"


def _parse_pub_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat()


def _is_recent(iso: str | None, window_days: int) -> bool:
    if not iso:
        return True
    try:
        parsed = dt.datetime.fromisoformat(iso)
    except ValueError:
        return True
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=window_days)
    return parsed >= cutoff


def classify_text(text: str) -> tuple[str | None, float]:
    if not text or not re.search(r"REIT|公募|基础设施|不动产", text, re.I):
        return None, 0.0
    neg_hits = sum(1 for pat in NEGATIVE_PATTERNS if pat.search(text))
    scores: dict[str, int] = {}
    for category, patterns in POSITIVE_PATTERNS.items():
        hits = sum(1 for pat in patterns if pat.search(text))
        if hits:
            scores[category] = hits
    if not scores:
        return None, 0.0
    category = max(scores, key=lambda key: (EVENT_PRIORITY.get(key, 0), scores[key]))
    confidence = min(0.96, 0.68 + 0.08 * scores[category])
    if neg_hits:
        confidence = max(0.35, confidence - 0.18 * neg_hits)
    return category, round(confidence, 3)


def load_profiles(workbook: Path = DEFAULT_WORKBOOK) -> list[ReitProfile]:
    profiles: list[ReitProfile] = []
    for record in load_records(workbook):
        symbol = _norm_symbol(record.get("symbol"))
        code = symbol.split(".", 1)[0]
        strong = {
            symbol,
            code,
            str(record.get("name_cn") or "").strip(),
        }
        weak = {
            str(record.get("originator") or "").strip(),
            str(record.get("fund_manager") or "").strip(),
            str(record.get("abs_plan_manager") or "").strip(),
        }
        profiles.append(
            ReitProfile(
                symbol=symbol,
                name_cn=str(record.get("name_cn") or "").strip(),
                exchange=str(record.get("exchange") or "").strip(),
                lifecycle_status=str(record.get("lifecycle_status") or "").strip(),
                asset_group=record.get("asset_group"),
                strong_aliases=sorted({x for x in strong if len(x) >= 4}),
                weak_aliases=sorted({x for x in weak if len(x) >= 6}),
            )
        )
    return profiles


def build_queries(profiles: list[ReitProfile], symbols: set[str] | None = None) -> list[tuple[str, str | None]]:
    queries: list[tuple[str, str | None]] = []
    if ENABLE_GLOBAL_QUERIES:
        queries.extend((q, None) for q in GLOBAL_QUERIES)

    selected = [p for p in profiles if not symbols or p.symbol in symbols or p.symbol.split(".", 1)[0] in symbols]
    selected.sort(key=lambda p: (p.lifecycle_status != "listed", p.symbol), reverse=True)
    for profile in selected[:MAX_REIT_QUERIES]:
        if profile.name_cn:
            queries.append((f'"{profile.name_cn}" OR "{profile.symbol.split(".", 1)[0]}" REIT', profile.symbol))
        else:
            queries.append((f'"{profile.symbol.split(".", 1)[0]}" REIT', profile.symbol))
    return queries


def fetch_google_news_rss(query: str) -> list[dict[str, str]]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {
            "q": query,
            "hl": "zh-CN",
            "gl": "CN",
            "ceid": "CN:zh-Hans",
        }
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "creit-dashboard-news/1.0 (+https://goldmandrew.github.io/c-reit-dashboard/)",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
            body = resp.read()
    except Exception as exc:  # noqa: BLE001 - provider failures are soft
        return [{"_error": str(exc), "_query": query}]

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        return [{"_error": f"rss parse error: {exc}", "_query": query}]

    items: list[dict[str, str]] = []
    for item in root.iter("item"):
        source_el = item.find("source")
        items.append(
            {
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "pub_date": (item.findtext("pubDate") or "").strip(),
                "description": (item.findtext("description") or "").strip(),
                "source": (source_el.text or "").strip() if source_el is not None and source_el.text else "",
            }
        )
        if len(items) >= MAX_PER_QUERY:
            break
    return items


def resolve_symbols(
    text: str,
    profiles: list[ReitProfile],
    query_symbol: str | None = None,
) -> tuple[list[str], str]:
    explicit: set[str] = set()
    high: set[str] = set()
    weak: set[str] = set()
    for profile in profiles:
        if any(alias and alias in text for alias in profile.strong_aliases):
            explicit.add(profile.symbol)
        elif any(alias and alias in text for alias in profile.weak_aliases):
            high.add(profile.symbol)
    if explicit:
        return sorted(explicit), "explicit"
    if high:
        return sorted(high), "high"
    if query_symbol and re.search(r"REIT|公募|基础设施|不动产", text, re.I):
        weak.add(query_symbol)
    return sorted(weak), "inferred" if weak else "market"


def _item_confidence(base: float, match_tier: str, symbols: list[str]) -> float:
    if match_tier == "explicit":
        base += 0.12
    elif match_tier == "high":
        base += 0.06
    elif match_tier == "inferred":
        base -= 0.12
    elif not symbols:
        base -= 0.08
    return round(max(0.2, min(0.98, base)), 3)


def dedupe_news(items: list[NewsItem]) -> list[NewsItem]:
    tier_rank = {"explicit": 3, "high": 2, "inferred": 1, "market": 0}

    def key(item: NewsItem) -> tuple[str, str, str]:
        day = (item.published_at or "")[:10]
        return (_slug(item.title_zh or item.title_en, 120), day, item.category)

    def better(a: NewsItem, b: NewsItem) -> NewsItem:
        score_a = (tier_rank.get(a.match_tier, 0), a.confidence, a.published_at or "")
        score_b = (tier_rank.get(b.match_tier, 0), b.confidence, b.published_at or "")
        return a if score_a >= score_b else b

    by_key: dict[tuple[str, str, str], NewsItem] = {}
    for item in items:
        prev = by_key.get(key(item))
        if prev is None:
            if item.publisher and not item.source_publishers:
                item.source_publishers = [item.publisher]
            by_key[key(item)] = item
            continue
        keep = better(item, prev)
        other = prev if keep is item else item
        merged = NewsItem(**asdict(keep))
        merged.symbols = sorted({*keep.symbols, *other.symbols})
        merged.source_count = int(keep.source_count or 1) + int(other.source_count or 1)
        merged.source_publishers = sorted(
            {
                *(keep.source_publishers or []),
                *(other.source_publishers or []),
                *([keep.publisher] if keep.publisher else []),
                *([other.publisher] if other.publisher else []),
            }
        )
        by_key[key(item)] = merged
    out = list(by_key.values())
    out.sort(key=lambda item: (item.published_at or ""), reverse=True)
    return out


def build_structured_events(news: list[NewsItem]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    structured_categories = set(EVENT_PRIORITY) - {"market_context", "macro_policy", "regulatory_policy"}
    regulatory_categories = {"regulatory_policy", "macro_policy"}
    events: dict[str, dict[str, Any]] = {}
    regulatory: dict[str, dict[str, Any]] = {}

    for item in news:
        if item.category not in structured_categories and item.category not in regulatory_categories:
            continue
        symbols = item.symbols or ["MARKET"]
        for symbol in symbols:
            event_id = f"{item.source_type}:{item.category}:{symbol}:{(item.published_at or '')[:10]}:{_slug(item.title_zh)}"
            event = {
                "id": event_id,
                "symbols": [] if symbol == "MARKET" else [symbol],
                "category": item.category,
                "status": "observed",
                "event_date": (item.published_at or "")[:10] or None,
                "headline_zh": item.title_zh,
                "headline_en": item.title_en,
                "summary_zh": item.summary_zh,
                "summary_en": item.summary_en,
                "source": item.publisher,
                "source_type": item.source_type,
                "source_url": item.url,
                "confidence": item.confidence,
                "match_tier": item.match_tier,
            }
            if item.category in regulatory_categories:
                regulatory[event_id] = event
            else:
                events[event_id] = event
                item.linked_event_id = event_id

    sorted_events = sorted(events.values(), key=lambda e: e.get("event_date") or "", reverse=True)
    sorted_reg = sorted(regulatory.values(), key=lambda e: e.get("event_date") or "", reverse=True)
    return sorted_events, sorted_reg


def fetch_news(
    profiles: list[ReitProfile],
    symbols: set[str] | None = None,
    window_days: int = WINDOW_DAYS,
) -> tuple[list[NewsItem], dict[str, Any]]:
    queries = build_queries(profiles, symbols)
    raw_seen: set[tuple[str, str]] = set()
    items: list[NewsItem] = []
    errors: list[dict[str, str]] = []
    raw_count = 0

    def run_query(query_info: tuple[str, str | None]) -> tuple[str, str | None, list[dict[str, str]]]:
        query, query_symbol = query_info
        if QUERY_DELAY_SEC:
            time.sleep(QUERY_DELAY_SEC)
        return query, query_symbol, fetch_google_news_rss(query)

    workers = max(1, min(MAX_WORKERS, len(queries) or 1))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_query, query_info) for query_info in queries]
        for future in as_completed(futures):
            query, query_symbol, raw_items = future.result()
            for raw in raw_items:
                if raw.get("_error"):
                    errors.append({"query": query, "error": raw["_error"]})
                    continue
                raw_count += 1
                title = raw.get("title") or ""
                desc = _strip_html(raw.get("description"))
                url = raw.get("link") or ""
                pub_iso = _parse_pub_date(raw.get("pub_date"))
                if not _is_recent(pub_iso, window_days):
                    continue
                raw_key = (title, url)
                if raw_key in raw_seen:
                    continue
                raw_seen.add(raw_key)
                text = f"{title}\n{desc}"
                category, base_conf = classify_text(text)
                if not category:
                    continue
                related, match_tier = resolve_symbols(text, profiles, query_symbol)
                confidence = _item_confidence(base_conf, match_tier, related)
                if match_tier == "inferred" and confidence < 0.62:
                    continue
                item_id = f"gnews:{_slug(title)}:{(pub_iso or '')[:10]}:{related[0] if related else 'market'}"
                publisher = raw.get("source") or "Google News"
                items.append(
                    NewsItem(
                        id=item_id,
                        symbols=related,
                        category=category,
                        confidence=confidence,
                        match_tier=match_tier,
                        published_at=pub_iso,
                        title_zh=title or None,
                        title_en=None,
                        summary_zh=desc or None,
                        summary_en=None,
                        url=url or None,
                        publisher=publisher,
                        source_type="google_news_rss",
                        source_query=query,
                        source_publishers=[publisher] if publisher else [],
                    )
                )

    deduped = dedupe_news(items)
    stats = {
        "provider": "google_news_rss",
        "queries_run": len(queries),
        "raw_articles_seen": raw_count,
        "items_before_dedupe": len(items),
        "items_after_dedupe": len(deduped),
        "errors": errors[:10],
        "error_count": len(errors),
        "category_counts": dict(Counter(item.category for item in deduped)),
        "match_tier_counts": dict(Counter(item.match_tier for item in deduped)),
        "symbols_with_news": len({s for item in deduped for s in item.symbols}),
    }
    return deduped, stats


def write_outputs(news: list[NewsItem], stats: dict[str, Any], window_days: int = WINDOW_DAYS) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    events, regulatory = build_structured_events(news)
    news_items = [asdict(item) for item in news]
    status = "ok" if news_items else ("failed" if stats.get("error_count") else "empty")

    news_payload = {
        "build_time": now,
        "status": status,
        "kind": "company_news",
        "window_days": window_days,
        "source_stats": stats,
        "items": news_items,
    }
    event_payload = {
        "build_time": now,
        "status": "ok" if events else "empty",
        "kind": "structured_events",
        "window_days": window_days,
        "source_stats": stats,
        "items": events,
    }
    regulatory_payload = {
        "build_time": now,
        "status": "ok" if regulatory else "empty",
        "kind": "regulatory_events",
        "window_days": window_days,
        "source_stats": stats,
        "items": regulatory,
    }
    cache_payload = {
        "build_time": now,
        "status": status,
        "provider": "google_news_rss",
        "stats": stats,
    }
    _json_dump(OUT_NEWS, news_payload)
    _json_dump(OUT_EVENTS, event_payload)
    _json_dump(OUT_REGULATORY, regulatory_payload)
    _json_dump(OUT_CACHE, cache_payload)
    return {
        "news": news_payload,
        "events": event_payload,
        "regulatory": regulatory_payload,
        "cache": cache_payload,
    }


def parse_symbols(value: str | None) -> set[str] | None:
    if not value:
        return None
    symbols = {_norm_symbol(v) for v in value.split(",") if v.strip()}
    expanded = set(symbols)
    for symbol in symbols:
        if "." not in symbol and symbol.isdigit():
            expanded.add(f"{symbol}.SH")
            expanded.add(f"{symbol}.SZ")
    return expanded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default="", help="Optional comma-separated symbols/codes to refresh.")
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print summary without writing artifacts.")
    args = parser.parse_args()

    profiles = load_profiles()
    news, stats = fetch_news(profiles, parse_symbols(args.symbols), args.window_days)
    if not args.dry_run:
        write_outputs(news, stats, args.window_days)
    print(
        "Fetched C-REIT news: "
        f"queries={stats['queries_run']} raw={stats['raw_articles_seen']} "
        f"items={stats['items_after_dedupe']} symbols={stats['symbols_with_news']} "
        f"errors={stats['error_count']}"
    )
    if news[:5]:
        for item in news[:5]:
            print(f"- {item.published_at}: {','.join(item.symbols) or 'MARKET'} {item.category} {item.title_zh}")


if __name__ == "__main__":
    main()
