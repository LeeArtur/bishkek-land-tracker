# Bishkek Land Tracker — Design Spec
_Date: 2026-05-28_

## Overview

A personal web dashboard that scrapes land plot listings from multiple Kyrgyz real estate sites, tracks price changes over time, highlights deals below market average, and provides district-level price trend analytics.

**Scope:** Single user, no authentication, local deployment.

**Geographic scope:** Bishkek city + Chui region (Чуйская область). Scrapers use the sites' own location filters for Bishkek and surrounding areas — no manual geo-filtering needed.

---

## Architecture

### Stack
- **Scraper:** Python + Playwright (handles JS-rendered pages)
- **Database:** SQLite (single file, no server needed)
- **Backend:** FastAPI (REST API)
- **Scheduler:** APScheduler (runs inside FastAPI process, triggers nightly scrape at 03:00)
- **Frontend:** React + Recharts (charts) + Tailwind CSS (styling)

### Data Flow
```
house.kg ─┐
lalafo.kg ─┤
stroka.kg ─┼─► Playwright Scraper ─► SQLite ─► FastAPI REST API ─► React Dashboard
stroika.kg─┘
NBKR API ──────────────────────────────► macro_data table
```

### Project Structure
```
bishkek-land-tracker/
  backend/
    scraper/          # one module per source site
      house_kg.py
      lalafo_kg.py
      stroka_kg.py
      stroika_kg.py
      nbkr.py         # macro data (exchange rate)
    api/
      listings.py     # GET /listings
      trends.py       # GET /trends
      recommendations.py  # GET /recommendations
      districts.py    # GET /districts
    db/
      models.py       # SQLAlchemy models + create_tables()
      seed.py         # seed districts table on first run
    scheduler.py      # APScheduler setup
    main.py           # FastAPI app entry point
  frontend/
    src/
      components/
        SummaryCards.tsx
        TrendChart.tsx
        DealsPanel.tsx
        ListingsTable.tsx
        Filters.tsx
      pages/
        Dashboard.tsx
        Listings.tsx
        Trends.tsx
        Recommendations.tsx
  docker-compose.yml
  .gitignore          # includes .superpowers/
```

---

## Data Sources

### Category 1: Listing Scrapers (Playwright)
| Source | URL | Data |
|--------|-----|------|
| house.kg | house.kg | price, area, district, date, URL |
| lalafo.kg | lalafo.kg/kyrgyzstan/zemelnye-uchastki | price, area, district, date, URL |
| stroka.kg | stroka.kg | price, area, district, date, URL |
| stroika.kg | stroika.kg | price, area, district, date, URL |

Each scraper is an independent Python module with a common interface:
```python
def scrape() -> list[ListingRaw]: ...
```

### Category 2: Contextual Data
| Source | Data | Method |
|--------|------|--------|
| NBKR (nbkr.kg) | USD/KGS exchange rate | XML API, daily |
| bishkek.opendata.kg | City open data | REST API (if available) |

### Category 3: Out of Scope
- **NSC (stat.gov.kg):** PDF reports only, manual import if needed
- **Gosregister (gosreg.gov.kg):** Closed registry, no programmatic access
- **Salam Aleykum Real Estate:** No URL
- **Osh Real Estate:** Different city, out of scope

---

## Database Schema (SQLite)

### `districts`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT | e.g. "Октябрьский" |
| avg_price_per_sotka | REAL | recalculated nightly |
| median_price_per_sotka | REAL | recalculated nightly |
| listing_count | INTEGER | active listings |

### `listings`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| external_id | TEXT UNIQUE | ID from source site |
| source | TEXT | house.kg / lalafo / stroka / stroika |
| title | TEXT | listing headline |
| district_id | INTEGER FK → districts | |
| area_sotka | REAL | area in sotkas |
| current_price_usd | REAL | latest price |
| price_per_sotka | REAL | computed: price / area |
| url | TEXT | original listing URL |
| first_seen | DATE | when first scraped |
| last_seen | DATE | last time seen active |
| is_active | BOOLEAN | still on the site |

### `price_history`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| listing_id | INTEGER FK → listings | |
| price_usd | REAL | price at this point |
| price_per_sotka | REAL | computed |
| recorded_at | DATE | |
| change_pct | REAL | % change vs previous record, NULL if first |

### `macro_data`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| recorded_at | DATE | |
| usd_kgs_rate | REAL | from NBKR |
| source | TEXT | nbkr / opendata |

---

## Nightly Scrape Process

Runs at 03:00 daily via APScheduler:

1. Each scraper fetches all land plot listings for Bishkek/near-Bishkek
2. For each listing:
   - Look up `external_id` in `listings`
   - If new: insert into `listings`, insert first `price_history` record
   - If existing and price changed: update `current_price_usd`, insert new `price_history` record with `change_pct`
   - If existing and no change: update `last_seen` only
3. Mark listings not seen in today's scrape as `is_active = false`
4. Recalculate `median_price_per_sotka` and `avg_price_per_sotka` per district
5. Fetch USD/KGS rate from NBKR and insert into `macro_data`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/listings` | All active listings, supports filters |
| GET | `/listings/{id}/history` | Price history for one listing |
| GET | `/trends` | Median price/sotka per district over time |
| GET | `/recommendations` | Listings ≥15% below district median |
| GET | `/districts` | District list with current stats |
| GET | `/macro` | Latest exchange rate and macro data |
| POST | `/scrape` | Manually trigger a scrape run |

### Filter parameters for `/listings`
- `district_id` — filter by district
- `source` — filter by source site
- `min_price`, `max_price` — USD price range
- `min_area`, `max_area` — area range in sotkas
- `price_changed_today` — boolean, only show listings with price change today

---

## Dashboard UI

### Pages / Tabs
1. **Dashboard** (main) — summary cards, trend chart, top deals panel
2. **All Listings** — full filterable/sortable table
3. **Trends** — expanded district trend charts with period selector
4. **Recommendations** — full list of below-market deals

### Summary Cards
- Total active listings (+ weekly delta)
- Average price/sotka overall (+ monthly % change)
- Listings with price drop today (count)
- Deals below market (count)

### Filter Bar (persists across tabs)
- District dropdown (multi-select)
- Source site checkboxes
- Price range (USD)
- Area range (sotkas)

### Trend Chart
- Line chart (Recharts LineChart)
- X-axis: date, Y-axis: median price/sotka in USD
- One line per district
- Period selector: 30 / 90 / 365 days

### Deals Panel
- Cards showing listings ≥15% below district median
- Shows: district, area, total price, price/sotka, % below median, source
- Threshold configurable in a settings constant (default 15%)

### Listings Table
- Sortable by price, price/sotka, area, date
- Price change column: ↑ green / ↓ red / — neutral
- Clickable row → opens original listing URL

---

## Recommendations Logic

**Deal detection:**
```
is_deal = listing.price_per_sotka < district.median_price_per_sotka × 0.85
```
Threshold (0.85 = 15% below) is a configurable constant.

**Trend signal (per district):**
- `rising` — median price up >3% over last 30 days
- `falling` — median price down >3% over last 30 days
- `stable` — within ±3%

Signals shown as badge on district cards in Trends page.

---

## Non-Functional Requirements

- Runs fully locally (no cloud dependency)
- Backend starts with `uvicorn main:app`
- Frontend starts with `npm run dev` (Vite)
- Both orchestrated via `docker-compose up` for convenience
- SQLite file stored at `backend/data/db.sqlite`
- Scraper respects site robots.txt and adds 1-2s delay between requests
- `.superpowers/` added to `.gitignore`
