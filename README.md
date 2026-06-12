# China C-REIT Dashboard

Static dashboard for tracking China public infrastructure REITs, approved commercial C-REITs, pipeline assets, regulatory flow, news, source freshness, and private/loan-to-own watchlist ideas.

The dashboard follows the same broad pattern as the ETF dashboard in the Investing folder:

```text
scripts/build_data.py -> data/dashboard_data.json -> index.html
```

The current build uses `公募reits已发行项目清单.xlsx` as seed data. Workbook prices are labeled as of `2026-06-10`; they are not live prices.

## Run locally

```bash
python scripts/build_data.py
python -m http.server 8000
```

Open `http://localhost:8000`.

## Current data contract

- `data/dashboard_data.json`: primary dashboard payload
- `data/creit_master.csv`: normalized workbook seed
- `data/creit_metrics_latest.json`: seed market/stat fields plus placeholders
- `data/creit_company_news.json`: company/project news feed placeholder
- `data/creit_structured_events.json`: machine-readable event tape placeholder
- `data/creit_regulatory_events.json`: regulatory tape placeholder
- `data/creit_source_health.json`: source freshness and coverage
- `data/private_deal_watch.json`: manual private-deal watchlist

## First-principles rules

- Treat the workbook as a manual seed, not a source of truth.
- Label the 2x pipeline threshold as an investment heuristic unless a source proves otherwise.
- Keep regulator stages, zoning, and asset eligibility config-driven.
- Use entity aliases for news matching; ticker-only matching is too weak.
- Avoid one universal score until there is enough source-backed data.
