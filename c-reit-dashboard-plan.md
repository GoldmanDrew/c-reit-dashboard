# China C-REIT Dashboard - build plan

**Status:** planning draft, 2026-06-12

**Goal:** Build a static C-REIT monitoring dashboard in the same operating style as `C:\Users\werdn\Documents\Investing\etf-dashboard`: data ingestion scripts write compact JSON artifacts into `data/`, and a single-page dashboard reads those files for screening, valuation, regulatory tracking, news flow, and private/public deal watch.

**Primary seed file:** `公募reits已发行项目清单.xlsx`

**Not in scope for v1:** Automated trading, portfolio execution, full underwriting model per property, or a legal conclusion on C-REIT eligibility. The dashboard should flag issues and rank opportunities, not make binding regulatory or investment decisions.

---

## Source facts from workbook

| Sheet | Clean rows | Meaning | Trading data status |
|------|------------|---------|---------------------|
| `基础设施不动产REITs` | 83 real rows | Listed and approved infrastructure-related C-REITs | 82 rows have prior close and since-listing return as of `2026-06-10` in the workbook; `508030.SH` has issue data but no listing date or price |
| `商业不动产Reits` | 4 real rows | Approved commercial real estate C-REITs | Workbook note says the four approved commercial REITs had not yet listed as of June 11; two rows show future listing dates of `2026-06-18` |

Workbook fields to normalize:

| Chinese field | Normalized field |
|---------------|------------------|
| `证券代码` | `symbol` |
| `证券简称` | `name_cn` |
| `发行公告日` | `issue_announcement_date` |
| `上市日期` | `listing_date` |
| `资产类型` | `asset_type_cn` |
| `基金上市地点` | `exchange_cn` |
| `原始权益人` | `originator` |
| `财务顾问` | `financial_advisor` |
| `专项计划管理人` | `abs_plan_manager` |
| `基金管理人` | `fund_manager` |
| `发行规模` | `issue_size_rmb_bn` |
| `上市基金发行价格（元）` | `offer_price_rmb` |
| `前收盘价（20260610）（元）` | `last_close_rmb` and `price_asof=2026-06-10` |
| `上市至今涨跌幅%` | `return_since_listing_pct` |

Initial asset-type buckets in the workbook include industrial parks, toll roads, logistics, energy infrastructure, affordable rental housing, consumer infrastructure, ecological/environmental, new infrastructure, water conservancy, municipal facilities, and commercial real estate.

---

## Product facts and research questions

Track these as explicit dashboard tags rather than burying them in notes:

| Theme | Dashboard treatment |
|-------|---------------------|
| Two-regulator path | Add `regulatory_path` and `regulatory_stage` fields. Track CSRC/exchange listing workflow separately from NDRC/project recommendation or infrastructure approval workflow. Keep the labels configurable because rules may change. |
| 90% payout vs reinvestment | Add `distribution_policy`, `payout_ratio`, `retained_cash_for_reinvestment`, and `expansion_capacity` fields. The key China question is whether retained/recycled cash can compound asset value rather than simply distribute income. |
| Need 2x pipeline to go public | Add `pipeline_asset_value_rmb_bn`, `pipeline_multiple_of_initial_assets`, and `pipeline_readiness_score`. Default threshold flag: `<2.0x` is weak, `>=2.0x` is public-market-ready. |
| Zoning drives REIT status | Add `zoning_type`, `asset_eligibility`, and `eligibility_exception_notes`. This should be filterable by property and originator. |
| Prefer one regulator | Add `regulatory_complexity_score`: one clear path is lower risk; mixed or uncertain approval paths are higher risk. |
| Public-company precedent | Track `precedent_public_company`, `first_mover_risk`, and `comparable_reit_symbols`. The UI should show whether another public company has already tested the same path. |
| Private alternative | Add `private_path_feasible`, `private_credit_or_sale_case`, and `expected_public_delay_months`. Some assets may be better tracked as private deals before they are public C-REIT candidates. |
| Hillhouse / private credit watch | Add a separate deal-watch table for RMB notes, collateral, coupon, maturity, loan-to-own thesis, and sponsor. Seed example: Hillhouse-related RMB 150m, 15% note, property collateral, possible loan-to-own. |
| China rate and deflation regime | Add macro overlays for deposit rate, 10Y/15Y funding cost, CPI/PPI trend, rent growth, and cap-rate pressure. Flag businesses that benefit from low funding versus those hurt by deflationary rents. |

---

## Assumption audit - Musk-style first principles

Use this before implementation. The point is not to accept the plan because it sounds comprehensive; the point is to ask which requirements are real, which are guesses, and which can be deleted or delayed.

### 1. Make requirements less wrong

Every requirement needs a named source, owner, and failure mode.

| Assumption | Challenge | Plan adjustment |
|------------|-----------|-----------------|
| Workbook is the C-REIT universe | It is a seed snapshot, not a durable source of truth. It already has stale prices and pending rows. | Treat workbook as `source=manual_seed`. Build provider adapters so exchange/fund-manager data can replace it. |
| All rows are public investable REITs | Some rows are approved but not trading; future pipeline/private deals are not securities rows. | Add `entity_type`: `listed_reit`, `approved_reit`, `pipeline_asset`, `private_deal`. Do not force every entity into the same market-data schema. |
| "2x pipeline" is a hard public-listing rule | This is an investment heuristic unless tied to a regulatory source. | Store as `pipeline_rule_of_thumb=2.0`, not as law. Show threshold and source note in the UI. |
| Two-regulator model is static | Regulator responsibilities and application flow can change. | Put `regulatory_path` and stages in config, version them, and show source date. |
| Zoning determines eligibility cleanly | Zoning is necessary but not sufficient; asset income stability, ownership, compliance history, and operating records matter. | Split into `zoning_type`, `asset_scope_match`, `cashflow_stability`, `ownership_cleanliness`, `compliance_status`. |
| Commercial REITs are simply "not listed yet" | They may have expected listing dates, delayed listings, or missing source fields. | Use lifecycle statuses with dates: `approved_not_listed`, `listing_scheduled`, `awaiting_trade`, `delayed_or_unknown`. |
| Payout/reinvestment data is easily comparable | C-REIT distribution language, retained cash, capex reserves, and expansion proceeds may not map to US REIT payout ratios. | Track raw cash distribution fields plus a derived `cash_retention_for_growth` metric with source notes. |
| Online data will be freely scrapable | Many China financial data pages are dynamic, rate-limited, licensed, or PDF-heavy. | Build source adapters with `source_type`, `license_status`, `last_success`, and graceful missing-data states. |
| News flow can be attached by ticker alone | Chinese fund names, short names, originators, project companies, and managers all produce relevant news under different names. | Build alias maps for `symbol`, `name_cn`, `originator`, `fund_manager`, `project_company`, and English names where available. |
| A single score can rank everything | Listed REIT valuation, pending regulatory risk, and private loan-to-own risk are different problems. | Keep separate scores and avoid one blended "best" rank until enough data exists. |

### 2. Delete before optimizing

Do not build these in v1 unless the data source is already available:

| Candidate feature | Delete/defer reason |
|-------------------|---------------------|
| Full property-level DCF | Too much manual data and false precision for the first dashboard. |
| Legal eligibility conclusion | The dashboard should surface inputs and red flags, not act as counsel. |
| Live intraday trading | Less important than correct lifecycle, NAV, distributions, and announcements. |
| One universal opportunity score | Masks uncertainty; keep component scores first. |
| Automated private-deal valuation | Manual watchlist is enough until collateral data and loan terms are reliable. |

### 3. Simplify before scaling

Start with three durable primitives:

```text
Entity master:
  who/what is this row?

Event tape:
  what changed, when, from which source?

Metric panel:
  what measurable facts can be trended and audited?
```

Everything else should be a view over those primitives.

### 4. Accelerate cycle time

Ship the first usable dashboard with seed data, source-status panels, and empty-but-working adapters. Then add one online source at a time and measure coverage. Do not wait for every data provider before building the interface.

### 5. Automate last

Automation should follow proven manual runs. For each data source, first save raw snapshots, then parse, then validate, then schedule. Avoid silently overwriting source snapshots because PDF/regulatory data will need audit trails.

---

## Target dashboard semantics

Each row should be one investable or watchlist entity:

```text
Listed C-REIT:
  symbol + exchange + fund metadata + live price/NAV/distribution data

Approved but not listed C-REIT:
  symbol + expected listing date + offer price + issue size + missing trading fields shown as "pending"

Private or pipeline candidate:
  project/company name + asset type + zoning + sponsor + regulator path + pipeline score + private deal economics
```

Do not treat unlisted commercial REITs as bad data. They should appear with a lifecycle badge such as `approved_not_listed`, `listing_scheduled`, or `awaiting_trade`.

---

## Architecture

Mirror the ETF dashboard structure:

```text
c-reit-dashboard/
|-- README.md
|-- index.html
|-- config/
|   |-- config.yaml
|   `-- asset_type_map.yaml
|-- data/
|   |-- creit_master.csv
|   |-- dashboard_data.json
|   |-- creit_prices_daily.csv
|   |-- creit_prices_latest.json
|   |-- creit_nav_latest.json
|   |-- creit_distributions.json
|   |-- creit_announcements.json
|   |-- creit_company_news.json
|   |-- creit_structured_events.json
|   |-- creit_metrics_daily.parquet
|   |-- creit_metrics_latest.json
|   |-- creit_pipeline.json
|   |-- creit_regulatory_events.json
|   |-- creit_source_health.json
|   |-- creit_aliases.json
|   |-- macro_china_rates.json
|   `-- private_deal_watch.json
|-- scripts/
|   |-- ingest_wind_excel.py
|   |-- ingest_exchange_prices.py
|   |-- ingest_nav_distributions.py
|   |-- ingest_announcements.py
|   |-- ingest_regulatory_events.py
|   |-- ingest_news.py
|   |-- ingest_macro.py
|   |-- build_alias_map.py
|   |-- source_health.py
|   |-- score_creits.py
|   `-- build_data.py
`-- tests/
    |-- test_ingest_wind_excel.py
    |-- test_lifecycle_status.py
    |-- test_news_alias_matching.py
    |-- test_score_creits.py
    `-- test_dashboard_data_contract.py
```

If the workbook source is Wind-derived, keep the raw workbook as a local/manual input unless the license permits redistribution. Commit only normalized, license-safe derived fields if needed.

---

## Data artifacts

### `data/dashboard_data.json`

Primary SPA payload, following the ETF repo shape:

```json
{
  "build_time": "2026-06-12T00:00:00Z",
  "schema_v": 1,
  "source_workbook": "公募reits已发行项目清单.xlsx",
  "price_asof": "2026-06-10",
  "summary": {
    "total_rows": 87,
    "listed_count": 82,
    "pending_or_not_trading_count": 5,
    "commercial_not_trading_count": 4,
    "total_issue_size_rmb_bn": 2329.917,
    "commercial_issue_size_rmb_bn": 203.32
  },
  "records": []
}
```

### Record fields

Core:

```text
symbol, name_cn, exchange, lifecycle_status, asset_type, asset_group,
issue_announcement_date, listing_date, originator, financial_advisor,
abs_plan_manager, fund_manager, issue_size_rmb_bn, offer_price_rmb,
last_close_rmb, price_asof, return_since_listing_pct
```

Market and valuation:

```text
nav_rmb, premium_discount_to_nav, market_cap_rmb_bn, liquidity_score,
distribution_yield_ttm, payout_ratio, retained_cash_for_reinvestment,
debt_cost_annual, debt_maturity_years, occupancy, noi_margin, rent_growth
```

Policy and eligibility:

```text
regulatory_path, regulatory_stage, regulatory_complexity_score,
zoning_type, asset_eligibility, pipeline_asset_value_rmb_bn,
pipeline_multiple_of_initial_assets, pipeline_readiness_score,
precedent_public_company, first_mover_risk
```

Macro and deal watch:

```text
deposit_rate, long_term_rmb_funding_cost, yield_spread_to_deposit,
deflation_sensitivity_score, private_path_feasible, private_deal_id,
collateral_summary, note_coupon, note_size_rmb_mn, loan_to_own_flag
```

---

## ETF-dashboard feature parity for C-REITs

These are the ETF-dashboard-style features worth porting, translated to C-REIT facts rather than ETF decay/borrow mechanics.

| ETF-dashboard feature | C-REIT dashboard version | Data artifact |
|-----------------------|--------------------------|---------------|
| Classified news tab | Company/fund/project news flow per REIT, originator, manager, and project company | `creit_company_news.json` |
| Structured corporate actions | Structured C-REIT event tape: listing approval, registration, listing date, trading halt/resume, distribution, asset injection, refinancing, acquisition, appraisal update | `creit_structured_events.json` |
| Stats tab with NAV/AUM/shares | REIT stats tab: NAV, market cap, fund units, premium/discount, turnover, volume, asset valuation, occupancy, NOI, leverage, distribution yield | `creit_metrics_latest.json`, `creit_metrics_daily.parquet` |
| Distribution history | Cash distribution calendar, ex-date, payment date, distribution per unit, implied yield, payout ratio | `creit_distributions.json` |
| Data freshness bar | Per-source freshness and worst-source warning for prices, announcements, NAV, distribution, macro, news | `creit_source_health.json` |
| Row detail expansion | Single REIT detail drawer with price/NAV chart, announcements, asset facts, originator, pipeline, scoring components | `dashboard_data.json` + detail artifacts |
| Bucket/product taxonomy | Asset/lifecycle taxonomy: infrastructure, commercial, logistics, toll road, energy, rental housing, consumer infrastructure, data center; listed vs pending vs private | `config/asset_type_map.yaml` |
| Scenario tab | Deflation and funding-cost scenarios: rent decline, occupancy shock, debt-cost reset, cap-rate expansion, retained-cash reinvestment | `creit_scenarios.json` |
| Top lists | Top premium/discount, top yield, weakest liquidity, best pipeline, highest regulatory complexity, most negative news, highest deflation sensitivity | `summary` in `dashboard_data.json` |
| Event calendar | Upcoming listing dates, distribution dates, lockup expiries, asset-injection votes, announcement deadlines | `creit_event_calendar.json` |
| Provider cascade | Source fallback chain: official exchange/fund manager first, licensed provider/manual seed second, public web fallback last | `config/config.yaml` |
| Audit scripts | Schema, duplicate symbol, stale source, bad lifecycle, missing source URL, impossible yield/premium checks | `scripts/audit_dashboard_data_quality.py` |

---

## Online data features to pull

Prioritize sources that answer investment questions directly. Each feature should record `source_url`, `source_name`, `source_asof`, `fetch_time`, and `confidence`.

| Feature | Why it matters | Candidate online sources |
|---------|----------------|--------------------------|
| Daily price, volume, turnover | Valuation, liquidity, stale-price detection | Shanghai Stock Exchange REIT product pages, Shenzhen Stock Exchange REIT product pages, licensed market data, public quote APIs if license permits |
| NAV / fund net asset value | Premium/discount and fair value anchor | Fund manager announcements, exchange fund disclosures, custodian/fund reports |
| Market cap / fund units | Size, liquidity, investability | Exchange product list, fund reports, market-data provider |
| Cash distributions | Yield, payout durability, payout/reinvestment tradeoff | Fund manager distribution announcements, exchange disclosure PDFs |
| Annual/interim/quarterly reports | Occupancy, NOI, leverage, capex, project performance | Exchange announcement PDFs and fund manager pages |
| Asset valuation / appraisal | Cap-rate movement, premium/discount to appraised value | Offering documents, annual reports, acquisition/follow-on offering disclosures |
| Asset injection / expansion pipeline | Tests the 2x pipeline thesis and reinvestment upside | Fund announcements, originator company announcements, follow-on offering disclosures |
| Regulatory stage | Tracks two-regulator/public path risk | NDRC notices, CSRC registration notices, SSE/SZSE approval and inquiry pages |
| Zoning / asset eligibility | Determines whether assets fit C-REIT scope | Prospectus PDFs, legal opinions, land/property documents in disclosures |
| Sponsor/originator public-company filings | Finds who may try first and where private/public paths overlap | SSE/SZSE listed-company announcements, HKEX announcements, company IR feeds |
| News flow per company | Surfaces tenant stress, sponsor funding stress, policy changes, asset transactions | Exchange news, fund manager news, originator news, Google/Bing/RSS where accessible, paid news if available |
| Macro rates | Compares C-REIT yields to cash and funding cost | ChinaBond yield curves, PBOC releases, commercial bank deposit pages |
| Deflation indicators | Stress-tests rents, tolls, occupancy, tenant demand | National Bureau of Statistics CPI/PPI/PMI, sector price data |
| Credit/private deal watch | Tracks loan-to-own and private alternatives | Company announcements, court/enforcement data where available, private notes entered manually |

Useful source registry candidates to encode in `config/config.yaml`:

| Source | Start URL | Use | Notes |
|--------|-----------|-----|-------|
| SSE REIT product list | `https://english.sse.com.cn/markets/funds/reits/list/` | Shanghai-listed REIT universe and product metadata | Official source; Chinese pages may be richer |
| SZSE REIT product list | `https://www.szse.cn/market/product/list/reits/index.html` | Shenzhen-listed REIT universe and product metadata | Official source |
| SSE/SZSE disclosure PDFs | `https://www.sse.com.cn/`, `https://www.szse.cn/` | Fund reports, listing documents, distribution notices, inquiry replies | PDF parsing required |
| NDRC notices | `https://www.ndrc.gov.cn/xwdt/tzgg/` | Project scope, recommendation, policy and industry-scope changes | Official regulatory source |
| CSRC notices | `https://www.csrc.gov.cn/` | Registration and regulatory approvals | Official regulatory source |
| Fund manager websites | per-manager registry | NAV, distributions, reports, product pages | Need per-manager URL registry |
| Originator/listed-company announcements | exchange/company registry | Pipeline, asset transfers, financing, sponsor stress | Alias matching is critical |
| ChinaBond yield curves | `https://yield.chinabond.com.cn/` | RMB risk-free/funding curve | Use for yield-spread and debt-cost context |
| PBOC | `https://www.pbc.gov.cn/` | Policy/rate context | Useful macro overlay |
| National Bureau of Statistics | `https://www.stats.gov.cn/english/PressRelease/` | CPI/PPI/PMI/real-estate macro | Deflation and demand backdrop |
| CSI / index providers | `https://www.csindex.com.cn/` | REIT index level and constituents | Benchmark and sector context |

---

## Dashboard views

### 1. Market screener

Main grid with filters for lifecycle status, asset type, exchange, sponsor/originator, fund manager, regulator path, zoning, and listed/unlisted status.

Key columns:

```text
Symbol, Name, Status, Asset type, Exchange, Issue size, Offer price,
Last close, Return since listing, Distribution yield, Premium/discount,
Pipeline multiple, Regulatory score, News count, Source freshness
```

### 2. Asset type and zoning

Shows issue size, count, performance, and eligibility by asset type. This should answer: which zoning/asset classes have working public C-REIT precedent, and which still require a first mover?

### 3. Distribution and reinvestment

Compares payout yield, payout ratio, retained/reinvested cash, debt cost, and expansion capacity. This is the place to test "normal REIT 90% payout" versus the China reinvestment thesis.

### 4. REIT stats

ETF-dashboard-style stats panel for each REIT:

```text
NAV, premium/discount, market cap, units outstanding, volume, turnover,
distribution yield, latest distribution, asset valuation, occupancy,
NOI margin, leverage, debt maturity, report date, source freshness
```

### 5. Pipeline readiness

Ranks originators by pipeline multiple, quality of assets, regulator path clarity, and whether they can support future injections. Flag anything below the 2x pipeline rule of thumb.

### 6. Macro and deflation sensitivity

Shows funding cost versus deposit rates, inflation/deflation indicators, rent-growth sensitivity, and debt refinancing risk. Useful for asking how a deflationary environment affects each business model.

### 7. News and regulatory tape

Rolling feed of exchange announcements, CSRC/NDRC/regulatory updates, fund manager announcements, distribution notices, acquisitions, appraisals, and sponsor-related news. Classify by `listing`, `distribution`, `asset_injection`, `regulatory`, `financing`, `tenant/rent`, `private_deal`.

News needs entity-level aliasing:

```text
symbol -> fund short name -> full fund name -> originator -> fund manager
-> ABS plan manager -> project company -> English/common alias
```

Every news card should show matched entity, matched alias, source, confidence, source date, and linked structured event when applicable.

### 8. Private and loan-to-own watchlist

Separate table for non-public opportunities such as Hillhouse-style collateralized notes:

```text
Sponsor/counterparty, note size, coupon, maturity, collateral,
estimated LTV, borrower funding cost, property status, loan-to-own thesis,
public C-REIT exit probability, key news
```

### 9. Single REIT detail

Click-through panel with price chart, NAV/premium, distribution history, asset details, originator profile, regulatory path, pipeline assets, news, and source audit trail.

### 10. Source health

Operator page copied conceptually from ETF-dashboard freshness checks:

```text
Source, last successful fetch, rows fetched, rows parsed, coverage %, error,
license note, retry cadence, next scheduled refresh
```

---

## Scoring model

Start simple and transparent. Every score should expose its components in the UI.

| Score | Purpose | Initial inputs |
|-------|---------|----------------|
| `valuation_score` | Cheap/rich screen | Premium/discount, yield spread, return since listing, NAV trend |
| `income_quality_score` | Distribution durability | Payout ratio, NOI margin, occupancy, rent growth, debt cost |
| `pipeline_readiness_score` | Public market expansion potential | Pipeline multiple, sponsor quality, asset eligibility, precedent |
| `regulatory_complexity_score` | Approval risk | Number of regulator paths, zoning uncertainty, first-mover status |
| `deflation_sensitivity_score` | Macro stress | Rent reset exposure, debt burden, asset class, tenant type |
| `private_conversion_score` | Private-to-public path | Collateral value, sponsor, zoning, public precedent, exit optionality |

---

## Implementation plan

### Phase 1 - Seed data and dashboard contract

1. Create `scripts/ingest_wind_excel.py`.
2. Normalize both workbook sheets into `data/creit_master.csv`.
3. Drop workbook note rows such as `数据来源：Wind` and keep the source note in metadata.
4. Assign lifecycle status:
   - `listed` when `listing_date <= build_date` and price is present.
   - `approved_not_listed` when issue data exists but no trading price exists.
   - `listing_scheduled` when listing date is in the future.
5. Create `scripts/build_data.py` to write `data/dashboard_data.json`.
6. Add `entity_type` and `source_status` so seed rows, listed rows, pending rows, and private-deal rows do not share false assumptions.
7. Add tests for column mapping, row counts, commercial unlisted status, and `price_asof=2026-06-10`.

### Phase 2 - Static SPA

1. Build `index.html` as a single-file React dashboard like `etf-dashboard`.
2. Load `data/dashboard_data.json`.
3. Add market screener, summary KPI strip, filters, row detail drawer, lifecycle badges, and source freshness badges.
4. Add the initial views: market screener, stats panel, news placeholder, source health, and single REIT detail.
5. Render unlisted commercial REITs as pending rather than blank/broken rows.

### Phase 3 - Online market and stats data

1. Add exchange or licensed-provider price ingestion.
2. Write `creit_prices_daily.csv` and `creit_prices_latest.json`.
3. Add NAV, premium/discount, fund units, market cap, volume, turnover, distribution history, and asset report fields once sources are available.
4. Write `creit_metrics_latest.json` and `creit_metrics_daily.parquet`.
5. Keep workbook values as seed/fallback, never as the only source after v1.
6. Track per-source coverage in `creit_source_health.json`.

### Phase 4 - News and regulatory feed

1. Add source-specific ingestors for exchange announcements, fund manager announcements, regulator pages, and general news.
2. Build `creit_aliases.json` from symbol, fund names, originator, fund manager, ABS plan manager, project company, and known English aliases.
3. Classify news into dashboard categories.
4. Split machine-readable events from article/news cards:
   - `creit_structured_events.json` for listing, registration, distributions, asset injections, financing, appraisals, regulatory steps.
   - `creit_company_news.json` for articles and softer news.
   - `creit_regulatory_events.json` for regulator-specific tape.
5. Surface news count, latest headline, latest structured event, and source confidence per row.

### Phase 5 - Policy, pipeline, and private deals

1. Add manual editable `data/creit_pipeline.json`.
2. Add `data/private_deal_watch.json` seeded with the Hillhouse note concept.
3. Build scoring functions in `scripts/score_creits.py`.
4. Add dashboard tabs for pipeline readiness, regulatory complexity, macro/deflation, and private conversion.

### Phase 6 - CI and data quality

1. Add a scheduled workflow similar to `etf-dashboard` build/deploy.
2. Add data freshness badges.
3. Add an audit script that fails on schema breaks, duplicate symbols, invalid lifecycle status, impossible price/NAV/yield values, missing source URLs, or stale required sources.
4. Add source-specific soft failures so a broken news provider does not block the core dashboard build.

---

## Acceptance criteria

| Check | Required result |
|-------|-----------------|
| Workbook import | 83 infrastructure rows and 4 commercial rows after dropping note rows |
| Commercial rows | All 4 commercial rows render as approved/pending, not as failed price records |
| Primary JSON | `data/dashboard_data.json` has `build_time`, `schema_v`, `summary`, and `records` |
| Price as-of | Workbook seed prices are labeled `2026-06-10`; no implied current price |
| Dashboard | Screener loads from static JSON with no backend required |
| Filters | Asset type, lifecycle status, exchange, originator, fund manager, and regulator path filters work |
| Scoring | Scores are component-backed and explainable in row detail |
| News | News/regulatory events can be missing without breaking the dashboard; when present, each item shows matched entity, source, date, and confidence |
| Stats | REIT stats panel accepts missing online fields but shows NAV/premium/distribution/volume data when sources populate |
| Source health | Each provider has freshness, row count, and failure status |
| Assumption audit | Every non-source-backed heuristic is labeled as a heuristic, not law or fact |
| Tests | Ingest, lifecycle, scoring, and dashboard contract tests pass |

---

## Agent implementation prompt (copy-paste)

```text
Build a China C-REIT dashboard in the same style as C:\Users\werdn\Documents\Investing\etf-dashboard.

Use the workbook at C:\Users\werdn\Documents\Nam Tai\c-reit dashboard\公募reits已发行项目清单.xlsx as the seed source.

Goal:
- Static dashboard, no required backend.
- scripts/build_data.py writes data/dashboard_data.json.
- index.html reads data/dashboard_data.json and renders the dashboard.
- Keep architecture adjustable so new live price, NAV, distribution, news, regulatory, pipeline, and private-deal sources can be plugged in later.
- Apply a first-principles / Elon-style assumption audit before coding: question every requirement, delete or defer what is not needed for v1, simplify the data model, accelerate with seed data, and automate only after a manual source works.

Important workbook facts:
- Sheet 基础设施不动产REITs has 83 real rows.
- Sheet 商业不动产Reits has 4 real commercial C-REIT rows plus source/note rows that must be dropped.
- Workbook price column is prior close as of 2026-06-10, not live price.
- Commercial C-REIT rows have issue data but no trading price in the workbook; show them as approved/pending, not bad data.
- 508030.SH has infrastructure issue data but no listing date/price in the workbook; treat it as pending/unknown lifecycle, not a failed listed record.

Assumption audit requirements:
- Treat the workbook as manual seed data, not source of truth.
- Add entity_type so listed REITs, approved-not-listed REITs, pipeline assets, and private deals do not share a false schema.
- Label the 2x pipeline rule as an investment heuristic unless a source proves it is a formal rule.
- Keep regulator path, zoning mapping, and asset eligibility config-driven with source dates.
- Build alias matching for news because ticker-only matching is too weak in China C-REITs.
- Do not create one universal opportunity score in v1; expose component scores.
- Do not build property-level DCF, legal conclusions, live intraday trading, or automated private-deal valuation in v1.

Architecture:
- Create data/creit_master.csv from the workbook.
- Create data/dashboard_data.json with build_time, schema_v, price_asof, summary, records.
- Create scripts/ingest_wind_excel.py, scripts/score_creits.py, scripts/build_data.py.
- Create config/asset_type_map.yaml for asset-type normalization and future zoning/regulator mapping.
- Create tests for row counts, field mapping, lifecycle status, and dashboard JSON contract.
- Create a single-file React index.html similar to etf-dashboard.
- Add source health and alias artifacts: data/creit_source_health.json and data/creit_aliases.json.
- Add online/stat artifacts as adapters are implemented: creit_prices_latest.json, creit_metrics_latest.json, creit_metrics_daily.parquet, creit_distributions.json, creit_company_news.json, creit_structured_events.json, creit_regulatory_events.json.

Dashboard tabs:
1. Market screener.
2. Asset type and zoning.
3. Distribution and reinvestment.
4. REIT stats.
5. Pipeline readiness.
6. Macro and deflation sensitivity.
7. News and regulatory tape.
8. Private and loan-to-own watchlist.
9. Single REIT detail drawer.
10. Source health.

Core fields:
symbol, name_cn, exchange, lifecycle_status, asset_type, issue_announcement_date,
listing_date, originator, financial_advisor, abs_plan_manager, fund_manager,
issue_size_rmb_bn, offer_price_rmb, last_close_rmb, price_asof,
return_since_listing_pct, nav_rmb, premium_discount_to_nav,
distribution_yield_ttm, payout_ratio, retained_cash_for_reinvestment,
zoning_type, regulatory_path, regulatory_stage, pipeline_multiple_of_initial_assets,
pipeline_readiness_score, regulatory_complexity_score, deflation_sensitivity_score,
latest_news, source_url, source_asof, source_confidence, source_freshness.

ETF-dashboard feature parity to include:
- Company/fund/project news flow per REIT, originator, manager, ABS plan manager, and project company.
- Structured event tape for listing approval, registration, listing date, trading halt/resume, distribution, asset injection, refinancing, acquisition, appraisal update.
- Stats panel with NAV, premium/discount, market cap, units outstanding, volume, turnover, distribution yield, latest distribution, asset valuation, occupancy, NOI margin, leverage, and debt maturity.
- Distribution history with ex-date, payment date, distribution per unit, implied yield, and payout ratio.
- Data freshness bar and source-health page.
- Row detail drawer with source audit trail.
- Upcoming event calendar for listing dates, distribution dates, lockup expiries, asset-injection votes, and announcement deadlines.
- Top lists for premium/discount, yield, weak liquidity, pipeline readiness, regulatory complexity, negative news, and deflation sensitivity.

Online data sources to design adapters for:
- SSE/SZSE REIT product pages and disclosure PDFs.
- Fund manager product pages, NAV pages, and distribution announcements.
- Originator/listed-company announcements.
- NDRC and CSRC regulatory notices.
- ChinaBond yield curves, PBOC releases, and National Bureau of Statistics CPI/PPI/PMI data.
- CSI/index-provider data for C-REIT benchmark context.
- Public news/RSS/search feeds where licensing allows; paid/licensed providers can be plugged in later.

Policy/research context to encode as fields and scores:
- C-REITs have a two-regulator/public-path issue; keep regulator path configurable.
- Normal REIT payout framing differs from China reinvestment/pipeline framing.
- Flag whether an originator has roughly 2x asset pipeline before going public.
- Zoning and asset type determine eligibility.
- Prefer simple regulator path; show when another public company has already set precedent.
- Include private alternative / loan-to-own watchlist, including a Hillhouse-style collateralized RMB note case.
- Add macro overlays for low deposit rates, RMB funding costs, and deflation sensitivity.

Acceptance:
- The dashboard works by serving index.html locally.
- All 87 real seed rows are represented.
- Unlisted commercial REITs have clear lifecycle badges.
- Workbook seed prices are visibly labeled stale/as-of 2026-06-10.
- The code is modular enough to replace workbook seed data with live providers later.
- News/regulatory events can be absent without breaking the dashboard; when present, every item shows matched entity, source, date, and confidence.
- Stats fields can be missing while adapters are empty, but the UI must show source freshness and not confuse missing online data with zero.
- Every heuristic score must show its components and source notes.
```

---

## Files expected

| File | Purpose |
|------|---------|
| `README.md` | User/operator overview |
| `index.html` | Static SPA dashboard |
| `config/asset_type_map.yaml` | Asset type, zoning, and regulator mappings |
| `data/creit_master.csv` | Normalized seed universe |
| `data/dashboard_data.json` | Primary dashboard payload |
| `data/creit_prices_latest.json` | Latest market price snapshot |
| `data/creit_metrics_latest.json` | Latest NAV, premium/discount, units, market cap, liquidity, and operating metrics |
| `data/creit_metrics_daily.parquet` | Historical metrics panel for charts and trend stats |
| `data/creit_distributions.json` | Distribution history and calendar |
| `data/creit_company_news.json` | Classified company/fund/project news feed |
| `data/creit_structured_events.json` | Machine-readable listing, distribution, asset-injection, financing, appraisal, halt/resume, and regulatory events |
| `data/creit_regulatory_events.json` | Optional regulatory/event feed |
| `data/creit_source_health.json` | Provider freshness, coverage, and error status |
| `data/creit_aliases.json` | Symbol/name/originator/manager/project aliases for news matching |
| `data/creit_pipeline.json` | Manual/editable future asset pipeline |
| `data/private_deal_watch.json` | Manual/editable private deal and loan-to-own watchlist |
| `scripts/ingest_wind_excel.py` | Workbook normalization |
| `scripts/ingest_exchange_prices.py` | Price, volume, and turnover ingestion |
| `scripts/ingest_nav_distributions.py` | NAV and distribution ingestion |
| `scripts/ingest_announcements.py` | Exchange/fund-manager announcement ingestion |
| `scripts/ingest_news.py` | Company/project news ingestion and classification |
| `scripts/ingest_regulatory_events.py` | NDRC/CSRC/SSE/SZSE regulatory tape |
| `scripts/ingest_macro.py` | Rates, CPI/PPI, and macro overlays |
| `scripts/build_alias_map.py` | Entity alias generation for news/event matching |
| `scripts/source_health.py` | Provider freshness and coverage summaries |
| `scripts/score_creits.py` | Scoring logic |
| `scripts/build_data.py` | Main build pipeline |
| `tests/test_ingest_wind_excel.py` | Workbook ingest coverage |
| `tests/test_lifecycle_status.py` | Listed/pending lifecycle behavior |
| `tests/test_news_alias_matching.py` | News/entity alias matching coverage |
| `tests/test_score_creits.py` | Score component coverage |
| `tests/test_dashboard_data_contract.py` | JSON schema/contract coverage |
| `tests/test_source_health.py` | Freshness and provider failure behavior |

---

## Open decisions

| Decision | Default for v1 |
|----------|----------------|
| Live data provider | Start with workbook seed and pluggable provider interfaces |
| Wind redistribution | Do not commit raw Wind workbook unless license allows it |
| Regulator labels | Config-driven, not hardcoded |
| Commercial REIT treatment | Lifecycle bucket, not missing-data error |
| Hillhouse/private deals | Manual watchlist JSON first |
| Deflation model | Simple score first, richer scenario model later |
