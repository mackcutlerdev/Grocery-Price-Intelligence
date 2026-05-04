# BC Grocery Price Intelligence

A data pipeline that scrapes weekly grocery prices from major BC retail banners, normalizes them for honest comparison, and surfaces pricing trends through interactive dashboards. Designed as a sibling project to [GroceryGenie](#), the price intelligence layer that powers smart shopping list decisions.

> **Status:** v1 in development. Targeting BC banners only.

---

## Table of Contents

1. [Why this exists](#why-this-exists)
2. [What it does](#what-it-does)
3. [Tech stack](#tech-stack)
4. [Architecture](#architecture)
5. [Data model](#data-model)
6. [Project structure](#project-structure)
7. [Setup](#setup)
8. [Build order — how to actually do this](#build-order)
9. [The dashboard](#the-dashboard)
10. [Things that will go wrong](#things-that-will-go-wrong)
11. [Stretch goals](#stretch-goals)
12. [Resume framing](#resume-framing)

---

## Why this exists

Canadian grocery prices have been a moving target. Headline inflation numbers paper over significant variance between banners — Save-On-Foods, Real Canadian Superstore, and Walmart Canada compete for the same BC shopper but price very differently across categories. This project quantifies that variance from the *consumer* side, using publicly available flyer and online-store data, and makes the patterns inspectable.

Practical purpose: feed pricing data into GroceryGenie so the shopping-list feature can answer "where is this basket cheapest this week?" rather than just "here's a list of things you're missing."

---

## What it does

- **Scrapes** weekly prices for ~50 staple items across 3 BC grocery banners
- **Normalizes** prices to per-100g / per-L / per-unit so 1.89L and 2L milk aren't compared as equals
- **Stores** price history in Postgres, indexed for time-series queries
- **Analyzes** banner-level basket inflation, sale-price behavior, and cross-banner price spread
- **Forecasts** 4-week-ahead basket index with confidence intervals (Prophet)
- **Visualizes** all of the above in a Power BI dashboard, with a Tableau Public mirror for shareable links

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Scraping | Python 3.11 + Playwright | Modern grocery sites are JS-rendered; BeautifulSoup alone won't reach the prices |
| Storage | PostgreSQL (Supabase free tier) | Already on resume; free hosted Postgres saves a deploy step |
| ETL / analysis | Pandas, NumPy | Standard, already on resume |
| Forecasting | Prophet | 20 lines of Python for a defensible ML bullet; ARIMA fallback if Prophet's deps misbehave |
| Dashboard (primary) | Power BI Desktop | Higher BC employer demand, Microsoft-ecosystem fit |
| Dashboard (mirror) | Tableau Public | Free shareable URL — recruiter-clickable from resume |
| Orchestration | GitHub Actions (weekly cron) | Free, version-controlled, signals CI/CD competence |
| Config | `.env` + `pydantic-settings` | Keep DB creds out of the repo |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (weekly cron)                   │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
       ┌────────▼────────┐          ┌────────▼────────┐
       │  scraper:       │          │  scraper:       │
       │  save_on_foods  │   ...    │  superstore     │
       │  (Playwright)   │          │  (Playwright)   │
       └────────┬────────┘          └────────┬────────┘
                │                             │
                └──────────────┬──────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  normalizer.py      │
                    │  (unit conversion,  │
                    │   alias resolution) │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Postgres           │
                    │  (Supabase)         │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────▼─────┐   ┌─────▼──────┐   ┌─────▼──────┐
       │ analysis/  │   │ forecast/  │   │ Power BI   │
       │ notebooks  │   │ prophet.py │   │ DirectQuery│
       └────────────┘   └────────────┘   └────────────┘
```

Each scraper is independent. One banner's site failing does not break the pipeline for the others — failed runs log and skip; the next week's run picks up.

---

## Data model

### `banners`
The retail banners being tracked. Stored at the *banner* level, not parent company level, because Loblaws and No Frills price differently by design even though both are Loblaw Companies.

| Column | Type | Notes |
|---|---|---|
| `banner_id` | serial PK | |
| `banner_name` | text | "Save-On-Foods", "Real Canadian Superstore", "Walmart Canada" |
| `parent_company` | text | "Pattison", "Loblaw", "Walmart" — for secondary analysis |
| `province` | text | "BC" for v1 |

### `products`
The canonical product list: your hand-curated basket of ~50 staples.

| Column | Type | Notes |
|---|---|---|
| `product_id` | serial PK | |
| `canonical_name` | text | "2% milk, 2L" |
| `category` | text | "dairy", "produce", "pantry", "meat", "bakery", etc. |
| `size_value` | numeric | 2 |
| `size_unit` | text | "L" |

### `product_aliases`
The mapping table: *the part that will eat the most of your time*. Each canonical product needs to be mapped, by hand, to whatever each banner calls it.

| Column | Type | Notes |
|---|---|---|
| `alias_id` | serial PK | |
| `product_id` | int FK | → products |
| `banner_id` | int FK | → banners |
| `banner_sku` | text nullable | their internal product code if you can find it |
| `banner_product_name` | text | "Lucerne 2% Milk 2L" — what THEY call it |
| `scrape_url` | text | direct URL to that product's page if applicable |

### `price_observations`
The fact table. Append-only. One row per (product, banner, week).

| Column | Type | Notes |
|---|---|---|
| `observation_id` | bigserial PK | |
| `product_id` | int FK | |
| `banner_id` | int FK | |
| `observed_at` | timestamptz | when scraped |
| `regular_price` | numeric(10,2) | shelf price |
| `sale_price` | numeric(10,2) nullable | promo price if on sale |
| `is_on_sale` | bool | |
| `unit_price` | numeric(10,4) | computed: price / normalized size |
| `unit_type` | text | "per_100g", "per_L", "per_kg", "per_unit" |
| `raw_payload` | jsonb | the original scraped record — keep it, you'll thank yourself |

**Index on `(product_id, banner_id, observed_at DESC)`.** Every query you write will use this.

---

## Project structure

```
grocery-price-intelligence/
├── README.md
├── pyproject.toml
├── .env.example
├── .github/
│   └── workflows/
│       └── weekly-scrape.yml
├── src/
│   ├── scrapers/
│   │   ├── base.py                  # abstract Scraper class
│   │   ├── save_on_foods.py
│   │   ├── superstore.py
│   │   └── walmart.py
│   ├── normalize/
│   │   ├── units.py                 # ml→L, g→kg, etc.
│   │   └── aliases.py               # banner SKU → canonical product
│   ├── db/
│   │   ├── schema.sql
│   │   ├── models.py                # SQLAlchemy or pydantic
│   │   └── seed_products.py         # populate the basket
│   ├── analysis/
│   │   ├── basket_index.py
│   │   ├── inflation_by_category.py
│   │   └── price_spread.py
│   ├── forecast/
│   │   └── prophet_basket.py
│   └── cli.py                       # `python -m src.cli scrape --banner=all`
├── notebooks/
│   ├── 01_exploratory.ipynb
│   ├── 02_basket_analysis.ipynb
│   └── 03_forecast_demo.ipynb
├── dashboards/
│   ├── grocery_intelligence.pbix    # Power BI
│   └── tableau_public_link.md       # URL + screenshot
└── data/
    └── basket_v1.csv                # seed data for the 50-item basket
```

---

## Setup

### Prerequisites
- Python 3.11+
- A free Supabase project (or any Postgres 14+)
- Power BI Desktop (Windows; or use a VM/Parallels on Mac)
- A Tableau Public account (free)

### Install
```bash
git clone <repo>
cd grocery-price-intelligence
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env  # then fill in DB creds
```

### Initialize DB
```bash
psql $DATABASE_URL -f src/db/schema.sql
python -m src.db.seed_products data/basket_v1.csv
```

### First scrape
```bash
python -m src.cli scrape --banner=save_on_foods --dry-run
# inspect output, then drop --dry-run when satisfied
```

---

## Build order

Don't try to build this top-down. Build it in slices, getting end-to-end working as fast as possible, then deepening.

### Week 1: vertical slice (one banner, one product)
- [ ] Set up repo, venv, Supabase project, schema applied
- [ ] Hand-define a 5-item basket (just 5 to start — milk, bread, eggs, bananas, butter)
- [ ] Manually map those 5 items to one banner (Save-On-Foods is the easiest to scrape)
- [ ] Write `save_on_foods.py` scraper that pulls those 5 prices
- [ ] Insert into `price_observations`
- [ ] Run it three times over three days, confirm you have time-series data

**Goal: end-to-end working with trivial scope.** Don't expand until this works.

### Week 2: expand horizontally
- [ ] Expand basket to 50 items
- [ ] Add Superstore scraper (this will be harder than Save-On's)
- [ ] Add Walmart Canada scraper
- [ ] Build the alias-mapping spreadsheet, this is grunt work, budget 3-4 hours
- [ ] Implement unit normalization (`normalize/units.py`)

### Week 3: analysis + dashboard
- [ ] Notebooks for basket index, category inflation, price spread
- [ ] Build Power BI dashboard with 4-5 views (see [The dashboard](#the-dashboard))
- [ ] Mirror the headline view to Tableau Public
- [ ] Write up findings paragraph for the README

### Week 4: automation + ML + polish
- [ ] GitHub Actions weekly cron
- [ ] Prophet forecast on the basket index
- [ ] Add forecast view to dashboard
- [ ] README polish, screenshot the dashboard, record a 60-second Loom

**Realistic total: 20-30 focused hours.** The scrapers will eat more time than you expect; the dashboard will eat less.

Then in interviews you can talk about:
- The product-aliasing problem (mature engineering judgment — you knew the exact-matching tarpit and chose pragmatism)
- Why banner-level not parent-level (domain understanding — retail banners price independently by design)
- Why you picked Power BI over Tableau (BC market awareness)
- One concrete insight from the data ("Over 12 weeks, dairy at Banner X rose Y% vs Banner Z's W%…")

That last one is the thing that makes the project feel real instead of academic. **Always have a finding ready.**
