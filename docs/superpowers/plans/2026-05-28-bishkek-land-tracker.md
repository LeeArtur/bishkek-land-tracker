# Bishkek Land Tracker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web dashboard that scrapes land plot listings from 4 Kyrgyz real estate sites, tracks price history, and surfaces below-market deals and district price trends.

**Architecture:** Python FastAPI backend with SQLite storage, Playwright-based scrapers running nightly via APScheduler, and a React + Recharts frontend served by Vite. Scrapers split into a pure HTML-parsing layer (testable with BS4) and a Playwright orchestration layer.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, BeautifulSoup4, Playwright, APScheduler, httpx, pytest; React 18, TypeScript, Vite, Tailwind CSS v3, Recharts, Vitest

**Spec:** `docs/superpowers/specs/2026-05-28-bishkek-land-tracker-design.md`

---

## File Map

```
bishkek-land-tracker/
  backend/
    config.py                        # constants: DB_PATH, DEAL_THRESHOLD, SCRAPE_HOUR
    main.py                          # FastAPI app, CORS, router includes, lifespan
    scheduler.py                     # APScheduler nightly job
    db/
      __init__.py
      models.py                      # SQLAlchemy 2.0 ORM models + create_tables()
      session.py                     # get_engine(), get_db() dependency
      seed.py                        # seed Bishkek districts on first run
    scraper/
      __init__.py
      base.py                        # ListingRaw dataclass, common helpers
      orchestrator.py                # upsert_listing(), mark_inactive(), recalculate_districts(), run_scrape()
      house_kg.py                    # _parse_html() + scrape()
      lalafo_kg.py
      stroka_kg.py
      stroika_kg.py
      nbkr.py                        # fetch_usd_kgs_rate()
    api/
      __init__.py
      districts.py                   # GET /districts
      listings.py                    # GET /listings, GET /listings/{id}/history
      trends.py                      # GET /trends
      recommendations.py             # GET /recommendations
      macro.py                       # GET /macro
      scrape.py                      # POST /scrape
    tests/
      conftest.py                    # in-memory SQLite engine + seeded session fixture
      test_models.py
      test_orchestrator.py
      test_api_listings.py
      test_api_trends.py
      test_api_recommendations.py
      test_house_kg_scraper.py
      test_lalafo_kg_scraper.py
      test_stroka_kg_scraper.py
      test_stroika_kg_scraper.py
    requirements.txt
  frontend/
    src/
      types.ts                       # shared TypeScript interfaces
      api/
        client.ts                    # typed fetch wrappers for all endpoints
      context/
        FilterContext.tsx            # global filter state + provider
      components/
        Nav.tsx
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
      App.tsx                        # router + layout
      main.tsx
    index.html
    package.json
    vite.config.ts
    tailwind.config.js
    postcss.config.js
    tsconfig.json
  docker-compose.yml
  .gitignore
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `bishkek-land-tracker/.gitignore`
- Create: `bishkek-land-tracker/backend/requirements.txt`
- Create: `bishkek-land-tracker/docker-compose.yml`

- [ ] **Step 1: Create root directory and .gitignore**

```bash
mkdir -p bishkek-land-tracker/backend/tests
mkdir -p bishkek-land-tracker/backend/db
mkdir -p bishkek-land-tracker/backend/scraper
mkdir -p bishkek-land-tracker/backend/api
mkdir -p bishkek-land-tracker/frontend
```

Write `bishkek-land-tracker/.gitignore`:
```
__pycache__/
*.pyc
*.pyo
.venv/
backend/data/
.env
node_modules/
dist/
.superpowers/
```

- [ ] **Step 2: Write requirements.txt**

Write `bishkek-land-tracker/backend/requirements.txt`:
```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.30
playwright==1.44.0
beautifulsoup4==4.12.3
apscheduler==3.10.4
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.7
requests==2.32.3
```

- [ ] **Step 3: Write docker-compose.yml**

Write `bishkek-land-tracker/docker-compose.yml`:
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
    command: npm run dev -- --host
```

Write `bishkek-land-tracker/backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium --with-deps
COPY . .
RUN mkdir -p data
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create Python package stubs**

Create empty `__init__.py` in each package:
```bash
touch bishkek-land-tracker/backend/db/__init__.py
touch bishkek-land-tracker/backend/scraper/__init__.py
touch bishkek-land-tracker/backend/api/__init__.py
```

- [ ] **Step 5: Commit**

```bash
cd bishkek-land-tracker
git add .
git commit -m "feat: project scaffolding"
```

---

## Task 2: Database Models

**Files:**
- Create: `backend/config.py`
- Create: `backend/db/models.py`
- Create: `backend/db/session.py`
- Create: `backend/db/seed.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write config.py**

Write `backend/config.py`:
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "db.sqlite"))
DEAL_THRESHOLD = 0.85   # listings at < 85% of district median are flagged as deals
SCRAPE_HOUR = 3         # 03:00 local time
```

- [ ] **Step 2: Write db/models.py**

Write `backend/db/models.py`:
```python
from datetime import date
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, Date, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    avg_price_per_sotka: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    median_price_per_sotka: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    listing_count: Mapped[int] = mapped_column(Integer, default=0)

    listings: Mapped[list["Listing"]] = relationship(back_populates="district")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), nullable=False)
    area_sotka: Mapped[float] = mapped_column(Float, nullable=False)
    current_price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_sotka: Mapped[float] = mapped_column(Float, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    first_seen: Mapped[date] = mapped_column(Date, nullable=False)
    last_seen: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    district: Mapped["District"] = relationship(back_populates="listings")
    history: Mapped[list["PriceHistory"]] = relationship(back_populates="listing")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False)
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_sotka: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)
    change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    listing: Mapped["Listing"] = relationship(back_populates="history")


class MacroData(Base):
    __tablename__ = "macro_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)
    usd_kgs_rate: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)


def create_tables(engine) -> None:
    Base.metadata.create_all(engine)
```

- [ ] **Step 3: Write db/session.py**

Write `backend/db/session.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import DB_PATH
from db.models import create_tables

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
        create_tables(_engine)
    return _engine


def get_db():
    SessionLocal = sessionmaker(bind=get_engine())
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Write db/seed.py**

Write `backend/db/seed.py`:
```python
from sqlalchemy.orm import Session
from db.models import District

BISHKEK_DISTRICTS = [
    "Октябрьский",
    "Ленинский",
    "Свердловский",
    "Первомайский",
    "Чуйская область",
    "Другой",
]


def seed_districts(db: Session) -> None:
    for name in BISHKEK_DISTRICTS:
        if not db.query(District).filter_by(name=name).first():
            db.add(District(name=name))
    db.commit()
```

- [ ] **Step 5: Write failing test**

Write `backend/tests/conftest.py`:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, create_tables
from db.seed import seed_districts


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    create_tables(e)
    return e


@pytest.fixture
def db(engine):
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    seed_districts(session)
    yield session
    session.close()
```

Write `backend/tests/test_models.py`:
```python
from datetime import date
from db.models import District, Listing, PriceHistory, MacroData


def test_seed_creates_districts(db):
    districts = db.query(District).all()
    names = [d.name for d in districts]
    assert "Октябрьский" in names
    assert "Ленинский" in names
    assert len(districts) == 6


def test_listing_relates_to_district(db):
    district = db.query(District).filter_by(name="Ленинский").first()
    listing = Listing(
        external_id="house.kg:001",
        source="house.kg",
        title="Участок 8 соток",
        district_id=district.id,
        area_sotka=8.0,
        current_price_usd=12000.0,
        price_per_sotka=1500.0,
        url="https://house.kg/listing/001",
        first_seen=date(2026, 5, 28),
        last_seen=date(2026, 5, 28),
        is_active=True,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    assert listing.district.name == "Ленинский"


def test_price_history_links_to_listing(db):
    district = db.query(District).filter_by(name="Ленинский").first()
    listing = Listing(
        external_id="house.kg:002",
        source="house.kg",
        title="Участок",
        district_id=district.id,
        area_sotka=6.0,
        current_price_usd=10000.0,
        price_per_sotka=1666.67,
        url="https://house.kg/002",
        first_seen=date(2026, 5, 1),
        last_seen=date(2026, 5, 28),
        is_active=True,
    )
    db.add(listing)
    db.flush()
    ph = PriceHistory(
        listing_id=listing.id,
        price_usd=10000.0,
        price_per_sotka=1666.67,
        recorded_at=date(2026, 5, 28),
        change_pct=None,
    )
    db.add(ph)
    db.commit()
    assert listing.history[0].change_pct is None
```

- [ ] **Step 6: Run tests to verify they fail (models don't exist yet)**

```bash
cd backend && python -m pytest tests/test_models.py -v
```
Expected: FAIL — ImportError or assertion errors.

- [ ] **Step 7: Run tests to verify they pass (models already written in Step 2)**

```bash
cd backend && python -m pytest tests/test_models.py -v
```
Expected: 3 PASSED

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: DB models, session, seed"
```

---

## Task 3: Scraper Base Types

**Files:**
- Create: `backend/scraper/base.py`

- [ ] **Step 1: Write the base types**

Write `backend/scraper/base.py`:
```python
import re
from dataclasses import dataclass
from datetime import date


@dataclass
class ListingRaw:
    external_id: str      # format: "source_name:site_listing_id"
    source: str           # "house.kg" | "lalafo" | "stroka" | "stroika"
    title: str
    district_name: str    # matched against districts table by name
    area_sotka: float
    price_usd: float
    url: str
    scraped_at: date


def parse_price_usd(text: str, usd_kgs_rate: float = 87.0) -> float | None:
    """
    Parse price string like '15 000 $', '15000$', '1 500 000 сом', '1500000 KGS'.
    Converts KGS to USD using usd_kgs_rate if no $ found.
    Returns None if parsing fails.
    """
    text = text.strip().replace("\xa0", " ").replace(" ", "")
    usd_match = re.search(r"([\d]+)", text.replace(",", ""))
    if not usd_match:
        return None
    amount = float(usd_match.group(1))
    if "$" in text or "USD" in text.upper():
        return amount
    if "сом" in text.lower() or "kgs" in text.lower() or "som" in text.lower():
        return round(amount / usd_kgs_rate, 2)
    return amount


def parse_area_sotka(text: str) -> float | None:
    """
    Parse area string like '8 соток', '8 сот.', '8 сотки', '0.08 га'.
    Converts га to сотки (1 га = 100 соток).
    Returns None if parsing fails.
    """
    text = text.strip().lower().replace("\xa0", " ")
    match = re.search(r"([\d]+[.,]?[\d]*)", text.replace(" ", ""))
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    if "га" in text or "га" in text:
        return round(value * 100, 2)
    return value
```

- [ ] **Step 2: Write failing test**

Write `backend/tests/test_scraper_base.py`:
```python
from scraper.base import parse_price_usd, parse_area_sotka


def test_parse_price_usd_dollar_sign():
    assert parse_price_usd("15 000 $") == 15000.0


def test_parse_price_usd_no_spaces():
    assert parse_price_usd("15000$") == 15000.0


def test_parse_price_usd_kgs():
    result = parse_price_usd("1 305 000 сом", usd_kgs_rate=87.0)
    assert result == round(1305000 / 87.0, 2)


def test_parse_price_usd_returns_none_on_garbage():
    assert parse_price_usd("Цена по договорённости") is None


def test_parse_area_sotka_basic():
    assert parse_area_sotka("8 соток") == 8.0


def test_parse_area_sotka_abbreviation():
    assert parse_area_sotka("8 сот.") == 8.0


def test_parse_area_sotka_ga():
    assert parse_area_sotka("0.08 га") == 8.0


def test_parse_area_sotka_none_on_garbage():
    assert parse_area_sotka("площадь не указана") is None
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_scraper_base.py -v
```
Expected: FAIL — ImportError.

- [ ] **Step 4: Run test after writing base.py**

```bash
cd backend && python -m pytest tests/test_scraper_base.py -v
```
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/scraper/base.py backend/tests/test_scraper_base.py
git commit -m "feat: scraper base types and price/area parsers"
```

---

## Task 4: Orchestrator

**Files:**
- Create: `backend/scraper/orchestrator.py`
- Create: `backend/tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

Write `backend/tests/test_orchestrator.py`:
```python
from datetime import date
from db.models import Listing, PriceHistory, District
from scraper.base import ListingRaw
from scraper.orchestrator import upsert_listing, mark_inactive, recalculate_districts


def _make_raw(external_id="house.kg:001", price=12000.0, area=8.0, district="Ленинский"):
    return ListingRaw(
        external_id=external_id,
        source="house.kg",
        title="Участок",
        district_name=district,
        area_sotka=area,
        price_usd=price,
        url=f"https://house.kg/{external_id}",
        scraped_at=date(2026, 5, 28),
    )


def test_upsert_new_listing_creates_record(db):
    raw = _make_raw()
    upsert_listing(db, raw, date(2026, 5, 28))
    listing = db.query(Listing).filter_by(external_id="house.kg:001").first()
    assert listing is not None
    assert listing.current_price_usd == 12000.0
    assert listing.price_per_sotka == 1500.0
    assert listing.is_active is True


def test_upsert_new_listing_creates_price_history(db):
    raw = _make_raw()
    upsert_listing(db, raw, date(2026, 5, 28))
    listing = db.query(Listing).filter_by(external_id="house.kg:001").first()
    assert len(listing.history) == 1
    assert listing.history[0].change_pct is None


def test_upsert_existing_no_change_does_not_add_history(db):
    raw = _make_raw()
    upsert_listing(db, raw, date(2026, 5, 27))
    upsert_listing(db, raw, date(2026, 5, 28))
    listing = db.query(Listing).filter_by(external_id="house.kg:001").first()
    assert len(listing.history) == 1
    assert listing.last_seen == date(2026, 5, 28)


def test_upsert_price_change_adds_history_with_pct(db):
    upsert_listing(db, _make_raw(price=12000.0), date(2026, 5, 27))
    upsert_listing(db, _make_raw(price=10000.0), date(2026, 5, 28))
    listing = db.query(Listing).filter_by(external_id="house.kg:001").first()
    assert listing.current_price_usd == 10000.0
    assert len(listing.history) == 2
    last_record = max(listing.history, key=lambda h: h.recorded_at)
    assert round(last_record.change_pct, 2) == round(((10000 - 12000) / 12000) * 100, 2)


def test_mark_inactive_removes_missing_listings(db):
    upsert_listing(db, _make_raw("house.kg:001"), date(2026, 5, 28))
    upsert_listing(db, _make_raw("house.kg:002"), date(2026, 5, 28))
    mark_inactive(db, seen_external_ids={"house.kg:001"}, today=date(2026, 5, 29))
    l1 = db.query(Listing).filter_by(external_id="house.kg:001").first()
    l2 = db.query(Listing).filter_by(external_id="house.kg:002").first()
    assert l1.is_active is True
    assert l2.is_active is False


def test_recalculate_districts_sets_median(db):
    for ext_id, price in [("h:1", 10000.0), ("h:2", 14000.0), ("h:3", 18000.0)]:
        upsert_listing(db, _make_raw(ext_id, price=price, area=10.0, district="Октябрьский"), date(2026, 5, 28))
    recalculate_districts(db)
    d = db.query(District).filter_by(name="Октябрьский").first()
    assert d.median_price_per_sotka == 1400.0
    assert d.listing_count == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_orchestrator.py -v
```
Expected: FAIL — ImportError (orchestrator not written).

- [ ] **Step 3: Write orchestrator.py**

Write `backend/scraper/orchestrator.py`:
```python
import statistics
from datetime import date
from sqlalchemy.orm import Session
from db.models import District, Listing, PriceHistory
from scraper.base import ListingRaw


def _get_or_create_district(db: Session, name: str) -> District:
    district = db.query(District).filter_by(name=name).first()
    if not district:
        district = District(name=name)
        db.add(district)
        db.flush()
    return district


def upsert_listing(db: Session, raw: ListingRaw, today: date) -> None:
    district = _get_or_create_district(db, raw.district_name)
    price_per_sotka = raw.price_usd / raw.area_sotka if raw.area_sotka > 0 else 0.0

    existing = db.query(Listing).filter_by(external_id=raw.external_id).first()

    if not existing:
        listing = Listing(
            external_id=raw.external_id,
            source=raw.source,
            title=raw.title,
            district_id=district.id,
            area_sotka=raw.area_sotka,
            current_price_usd=raw.price_usd,
            price_per_sotka=price_per_sotka,
            url=raw.url,
            first_seen=today,
            last_seen=today,
            is_active=True,
        )
        db.add(listing)
        db.flush()
        db.add(PriceHistory(
            listing_id=listing.id,
            price_usd=raw.price_usd,
            price_per_sotka=price_per_sotka,
            recorded_at=today,
            change_pct=None,
        ))
    else:
        existing.last_seen = today
        existing.is_active = True
        if existing.current_price_usd != raw.price_usd:
            change_pct = ((raw.price_usd - existing.current_price_usd) / existing.current_price_usd) * 100
            existing.current_price_usd = raw.price_usd
            existing.price_per_sotka = price_per_sotka
            db.add(PriceHistory(
                listing_id=existing.id,
                price_usd=raw.price_usd,
                price_per_sotka=price_per_sotka,
                recorded_at=today,
                change_pct=change_pct,
            ))

    db.commit()


def mark_inactive(db: Session, seen_external_ids: set, today: date) -> None:
    active = db.query(Listing).filter_by(is_active=True).all()
    for listing in active:
        if listing.external_id not in seen_external_ids:
            listing.is_active = False
    db.commit()


def recalculate_districts(db: Session) -> None:
    districts = db.query(District).all()
    for district in districts:
        prices = [
            l.price_per_sotka
            for l in db.query(Listing).filter_by(district_id=district.id, is_active=True).all()
            if l.price_per_sotka > 0
        ]
        if prices:
            district.avg_price_per_sotka = sum(prices) / len(prices)
            district.median_price_per_sotka = statistics.median(prices)
            district.listing_count = len(prices)
        else:
            district.listing_count = 0
    db.commit()


def run_scrape(db: Session, scrapers: list) -> dict:
    """
    scrapers: list of (name: str, fn: () -> list[ListingRaw])
    Returns dict of {source_name: {count, error}}
    """
    today = date.today()
    seen_external_ids: set = set()
    results = {}

    for name, scraper_fn in scrapers:
        try:
            raw_listings = scraper_fn()
            for raw in raw_listings:
                upsert_listing(db, raw, today)
                seen_external_ids.add(raw.external_id)
            results[name] = {"count": len(raw_listings), "error": None}
        except Exception as e:
            results[name] = {"count": 0, "error": str(e)}

    mark_inactive(db, seen_external_ids, today)
    recalculate_districts(db)
    return results
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_orchestrator.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/scraper/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat: scraper orchestrator with upsert and district recalculation"
```

---

## Task 5: house.kg Scraper

**Files:**
- Create: `backend/scraper/house_kg.py`
- Create: `backend/tests/test_house_kg_scraper.py`
- Create: `backend/tests/fixtures/house_kg_card.html`

- [ ] **Step 1: Inspect the site (manual)**

Open https://house.kg, navigate to земельные участки → Бишкек. In DevTools (F12 → Elements):
1. Find the CSS selector for a single listing card (e.g. `.item`, `.listing-card`, `.object-item`)
2. Find price element selector within the card
3. Find area element selector
4. Find district/location element selector
5. Find the listing URL (usually the `<a>` wrapping the card or a title link)
6. Find the listing ID (usually in the `href` or a `data-id` attribute)
7. Find the "next page" button selector to detect end of pagination
8. Note the base URL structure for land plots in Bishkek

Copy one card's raw HTML into `backend/tests/fixtures/house_kg_card.html`.

- [ ] **Step 2: Write the fixture file**

Based on your inspection in Step 1, write the actual HTML of one listing card into:
`backend/tests/fixtures/house_kg_card.html`

Example structure (update selectors after inspection):
```html
<div class="object-item">
  <a class="object-title" href="/ru/listing/12345">Участок 8 соток, Ленинский район</a>
  <span class="object-price">15 000 $</span>
  <div class="object-params">
    <span class="area">8 соток</span>
    <span class="location">Ленинский район, Бишкек</span>
  </div>
</div>
```

- [ ] **Step 3: Write failing test**

Write `backend/tests/test_house_kg_scraper.py`:
```python
from pathlib import Path
from scraper.house_kg import _parse_html
from scraper.base import ListingRaw

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_parse_html_extracts_listing():
    html = (FIXTURE_DIR / "house_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    r = results[0]
    assert isinstance(r, ListingRaw)
    assert r.source == "house.kg"
    assert r.external_id.startswith("house.kg:")
    assert r.price_usd > 0
    assert r.area_sotka > 0
    assert r.district_name != ""
    assert r.url.startswith("https://house.kg")


def test_parse_html_skips_listings_without_price():
    html = """<div class="object-item">
      <a class="object-title" href="/ru/listing/99999">Участок без цены</a>
      <span class="object-price">Договорная</span>
      <div class="object-params">
        <span class="area">5 соток</span>
        <span class="location">Ленинский</span>
      </div>
    </div>"""
    results = _parse_html(html)
    assert results == []
```

- [ ] **Step 4: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_house_kg_scraper.py -v
```
Expected: FAIL — ImportError.

- [ ] **Step 5: Write house_kg.py**

Write `backend/scraper/house_kg.py` — replace CSS selectors with the ones you found in Step 1:
```python
import asyncio
import re
from datetime import date
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from scraper.base import ListingRaw, parse_price_usd, parse_area_sotka

BASE_URL = "https://house.kg"
SEARCH_URL = "https://house.kg/ru/search?deal_type=2&object_type=5&city_id=1&page={page}"
SOURCE = "house.kg"

# CSS selectors — verify these match the live site after inspection
CARD_SELECTOR = ".object-item"          # update after inspection
TITLE_LINK_SELECTOR = ".object-title"   # <a> tag with href and text
PRICE_SELECTOR = ".object-price"
AREA_SELECTOR = ".object-params .area"
LOCATION_SELECTOR = ".object-params .location"


def _extract_listing_id(href: str) -> str | None:
    match = re.search(r"/(\d+)(?:/|$)", href)
    return match.group(1) if match else None


def _parse_html(html: str) -> list[ListingRaw]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    today = date.today()

    for card in soup.select(CARD_SELECTOR):
        try:
            link_el = card.select_one(TITLE_LINK_SELECTOR)
            price_el = card.select_one(PRICE_SELECTOR)
            area_el = card.select_one(AREA_SELECTOR)
            location_el = card.select_one(LOCATION_SELECTOR)

            if not all([link_el, price_el, area_el, location_el]):
                continue

            href = link_el.get("href", "")
            listing_id = _extract_listing_id(href)
            if not listing_id:
                continue

            price = parse_price_usd(price_el.get_text())
            area = parse_area_sotka(area_el.get_text())

            if price is None or area is None or area == 0:
                continue

            location_text = location_el.get_text(strip=True)
            district_name = location_text.split(",")[0].strip()

            results.append(ListingRaw(
                external_id=f"{SOURCE}:{listing_id}",
                source=SOURCE,
                title=link_el.get_text(strip=True),
                district_name=district_name,
                area_sotka=area,
                price_usd=price,
                url=BASE_URL + href if href.startswith("/") else href,
                scraped_at=today,
            ))
        except Exception:
            continue

    return results


async def _scrape_async() -> list[ListingRaw]:
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page_num = 1
        while True:
            url = SEARCH_URL.format(page=page_num)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
            listings = _parse_html(html)
            if not listings:
                break
            results.extend(listings)
            page_num += 1
            await asyncio.sleep(1.5)
        await browser.close()
    return results


def scrape() -> list[ListingRaw]:
    return asyncio.run(_scrape_async())
```

- [ ] **Step 6: Update selectors from inspection**

Open the fixture HTML you saved. Confirm the selectors in `CARD_SELECTOR`, `TITLE_LINK_SELECTOR`, `PRICE_SELECTOR`, `AREA_SELECTOR`, `LOCATION_SELECTOR` match your fixture.

Also update `SEARCH_URL` to match the actual URL pattern for земельные участки в Бишкеке.

- [ ] **Step 7: Run tests**

```bash
cd backend && python -m pytest tests/test_house_kg_scraper.py -v
```
Expected: 2 PASSED

- [ ] **Step 8: Integration smoke test (manual)**

```bash
cd backend && python -c "from scraper.house_kg import scrape; r = scrape(); print(len(r), 'listings'); print(r[0])"
```
Expected: prints listing count > 0 and a valid ListingRaw.

- [ ] **Step 9: Commit**

```bash
git add backend/scraper/house_kg.py backend/tests/test_house_kg_scraper.py backend/tests/fixtures/
git commit -m "feat: house.kg scraper with HTML parser"
```

---

## Task 6: lalafo.kg Scraper

**Files:**
- Create: `backend/scraper/lalafo_kg.py`
- Create: `backend/tests/test_lalafo_kg_scraper.py`
- Create: `backend/tests/fixtures/lalafo_kg_card.html`

Follow the exact same steps as Task 5. Key differences:

- [ ] **Step 1: Inspect https://lalafo.kg/kyrgyzstan/zemelnye-uchastki**

Find selectors for: card container, title link, price, area, location. Copy one card HTML to `fixtures/lalafo_kg_card.html`.

- [ ] **Step 2: Write test** (`test_lalafo_kg_scraper.py`)

Same structure as `test_house_kg_scraper.py` but import from `scraper.lalafo_kg` and use the lalafo fixture.

- [ ] **Step 3: Write scraper**

Write `backend/scraper/lalafo_kg.py`:
```python
import asyncio
import re
from datetime import date
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from scraper.base import ListingRaw, parse_price_usd, parse_area_sotka

BASE_URL = "https://lalafo.kg"
SEARCH_URL = "https://lalafo.kg/kyrgyzstan/zemelnye-uchastki?page={page}"
SOURCE = "lalafo"

# Update these after inspecting the live site
CARD_SELECTOR = ".ad-tile"
TITLE_LINK_SELECTOR = ".ad-tile-title a"
PRICE_SELECTOR = ".ad-tile-price"
AREA_SELECTOR = ".ad-tile-params .area"
LOCATION_SELECTOR = ".ad-tile-params .location"


def _extract_listing_id(href: str) -> str | None:
    match = re.search(r"/(\d+)(?:-|/|$)", href)
    return match.group(1) if match else None


def _parse_html(html: str) -> list[ListingRaw]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    today = date.today()

    for card in soup.select(CARD_SELECTOR):
        try:
            link_el = card.select_one(TITLE_LINK_SELECTOR)
            price_el = card.select_one(PRICE_SELECTOR)
            area_el = card.select_one(AREA_SELECTOR)
            location_el = card.select_one(LOCATION_SELECTOR)

            if not all([link_el, price_el, area_el]):
                continue

            href = link_el.get("href", "")
            listing_id = _extract_listing_id(href)
            if not listing_id:
                continue

            price = parse_price_usd(price_el.get_text())
            area = parse_area_sotka(area_el.get_text())

            if price is None or area is None or area == 0:
                continue

            district_name = location_el.get_text(strip=True).split(",")[0] if location_el else "Другой"

            results.append(ListingRaw(
                external_id=f"{SOURCE}:{listing_id}",
                source=SOURCE,
                title=link_el.get_text(strip=True),
                district_name=district_name,
                area_sotka=area,
                price_usd=price,
                url=BASE_URL + href if href.startswith("/") else href,
                scraped_at=today,
            ))
        except Exception:
            continue

    return results


async def _scrape_async() -> list[ListingRaw]:
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page_num = 1
        while True:
            await page.goto(SEARCH_URL.format(page=page_num), wait_until="networkidle", timeout=30000)
            html = await page.content()
            listings = _parse_html(html)
            if not listings:
                break
            results.extend(listings)
            page_num += 1
            await asyncio.sleep(1.5)
        await browser.close()
    return results


def scrape() -> list[ListingRaw]:
    return asyncio.run(_scrape_async())
```

- [ ] **Step 4: Run tests, then integration smoke test, then commit**

```bash
cd backend && python -m pytest tests/test_lalafo_kg_scraper.py -v
git add backend/scraper/lalafo_kg.py backend/tests/test_lalafo_kg_scraper.py backend/tests/fixtures/lalafo_kg_card.html
git commit -m "feat: lalafo.kg scraper"
```

---

## Task 7: stroka.kg Scraper

**Files:**
- Create: `backend/scraper/stroka_kg.py`
- Create: `backend/tests/test_stroka_kg_scraper.py`
- Create: `backend/tests/fixtures/stroka_kg_card.html`

- [ ] **Step 1: Inspect https://stroka.kg — find land plot listings for Bishkek**

Copy one card HTML to `fixtures/stroka_kg_card.html`.

- [ ] **Step 2: Write test and scraper**

Same pattern as Tasks 5-6. Use `SOURCE = "stroka"` and `BASE_URL = "https://stroka.kg"`.

- [ ] **Step 3: Run tests, smoke test, commit**

```bash
python -m pytest tests/test_stroka_kg_scraper.py -v
git add backend/scraper/stroka_kg.py backend/tests/test_stroka_kg_scraper.py backend/tests/fixtures/stroka_kg_card.html
git commit -m "feat: stroka.kg scraper"
```

---

## Task 8: stroika.kg Scraper

**Files:**
- Create: `backend/scraper/stroika_kg.py`
- Create: `backend/tests/test_stroika_kg_scraper.py`
- Create: `backend/tests/fixtures/stroika_kg_card.html`

- [ ] **Step 1: Inspect https://stroika.kg — find land plot listings for Bishkek**

Copy one card HTML to `fixtures/stroika_kg_card.html`.

- [ ] **Step 2: Write test and scraper**

Same pattern as Tasks 5-7. Use `SOURCE = "stroika"` and `BASE_URL = "https://stroika.kg"`.

- [ ] **Step 3: Run tests, smoke test, commit**

```bash
python -m pytest tests/test_stroika_kg_scraper.py -v
git add backend/scraper/stroika_kg.py backend/tests/test_stroika_kg_scraper.py backend/tests/fixtures/stroika_kg_card.html
git commit -m "feat: stroika.kg scraper"
```

---

## Task 9: NBKR Exchange Rate

**Files:**
- Create: `backend/scraper/nbkr.py`

- [ ] **Step 1: Write the scraper**

NBKR provides exchange rates via XML at `https://www.nbkr.kg/XML/daily.xml`.

Write `backend/scraper/nbkr.py`:
```python
import requests
import xml.etree.ElementTree as ET


NBKR_XML_URL = "https://www.nbkr.kg/XML/daily.xml"


def fetch_usd_kgs_rate() -> float | None:
    """
    Fetches the current USD/KGS rate from NBKR's daily XML feed.
    Returns the rate as a float, or None on failure.
    """
    try:
        resp = requests.get(NBKR_XML_URL, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        for currency in root.findall(".//Currency"):
            if currency.get("ISOCode") == "USD":
                value_el = currency.find("Value")
                if value_el is not None and value_el.text:
                    return float(value_el.text.replace(",", "."))
        return None
    except Exception:
        return None
```

- [ ] **Step 2: Manual test**

```bash
cd backend && python -c "from scraper.nbkr import fetch_usd_kgs_rate; print(fetch_usd_kgs_rate())"
```
Expected: prints a float like `87.42`.

- [ ] **Step 3: Commit**

```bash
git add backend/scraper/nbkr.py
git commit -m "feat: NBKR USD/KGS rate fetcher"
```

---

## Task 10: FastAPI Main App + Scheduler

**Files:**
- Create: `backend/scheduler.py`
- Create: `backend/main.py`

- [ ] **Step 1: Write scheduler.py**

Write `backend/scheduler.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from db.session import get_engine
from sqlalchemy.orm import sessionmaker
from scraper.orchestrator import run_scrape
from scraper.house_kg import scrape as scrape_house_kg
from scraper.lalafo_kg import scrape as scrape_lalafo_kg
from scraper.stroka_kg import scrape as scrape_stroka_kg
from scraper.stroika_kg import scrape as scrape_stroika_kg
from scraper.nbkr import fetch_usd_kgs_rate
from db.models import MacroData
from datetime import date
from config import SCRAPE_HOUR

SCRAPERS = [
    ("house.kg", scrape_house_kg),
    ("lalafo", scrape_lalafo_kg),
    ("stroka", scrape_stroka_kg),
    ("stroika", scrape_stroika_kg),
]


def run_nightly_scrape():
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        run_scrape(db, SCRAPERS)
        rate = fetch_usd_kgs_rate()
        if rate:
            db.add(MacroData(recorded_at=date.today(), usd_kgs_rate=rate, source="nbkr"))
            db.commit()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_nightly_scrape, "cron", hour=SCRAPE_HOUR, minute=0)
    scheduler.start()
    return scheduler
```

- [ ] **Step 2: Write main.py**

Write `backend/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.session import get_engine
from db.seed import seed_districts
from db.models import create_tables
from sqlalchemy.orm import sessionmaker
from scheduler import start_scheduler
from api import districts, listings, trends, recommendations, macro, scrape


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    create_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        seed_districts(db)
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(title="Bishkek Land Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(districts.router)
app.include_router(listings.router)
app.include_router(trends.router)
app.include_router(recommendations.router)
app.include_router(macro.router)
app.include_router(scrape.router)
```

- [ ] **Step 3: Verify server starts**

```bash
cd backend && uvicorn main:app --reload
```
Expected: server starts on http://localhost:8000, no errors. Open http://localhost:8000/docs.

- [ ] **Step 4: Commit**

```bash
git add backend/scheduler.py backend/main.py
git commit -m "feat: FastAPI app with scheduler and CORS"
```

---

## Task 11: API — /districts and /listings

**Files:**
- Create: `backend/api/districts.py`
- Create: `backend/api/listings.py`
- Create: `backend/tests/test_api_listings.py`

- [ ] **Step 1: Write failing tests**

Write `backend/tests/test_api_listings.py`:
```python
import pytest
from fastapi.testclient import TestClient
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, create_tables, District, Listing, PriceHistory
from db.seed import seed_districts
from db.session import get_db


def _make_app(db_session):
    from main import app
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


@pytest.fixture
def client(db):
    district = db.query(District).filter_by(name="Ленинский").first()
    listing = Listing(
        external_id="house.kg:100",
        source="house.kg",
        title="Тестовый участок",
        district_id=district.id,
        area_sotka=8.0,
        current_price_usd=12000.0,
        price_per_sotka=1500.0,
        url="https://house.kg/100",
        first_seen=date(2026, 5, 1),
        last_seen=date(2026, 5, 28),
        is_active=True,
    )
    db.add(listing)
    db.flush()
    db.add(PriceHistory(
        listing_id=listing.id, price_usd=12000.0,
        price_per_sotka=1500.0, recorded_at=date(2026, 5, 28), change_pct=None
    ))
    db.commit()
    return _make_app(db)


def test_get_districts_returns_list(client):
    resp = client.get("/districts")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = [d["name"] for d in data]
    assert "Ленинский" in names


def test_get_listings_returns_active(client):
    resp = client.get("/listings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["external_id"] == "house.kg:100"


def test_get_listings_filter_by_district(client, db):
    resp = client.get("/listings?district_id=999")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_listing_history(client, db):
    listing = db.query(Listing).filter_by(external_id="house.kg:100").first()
    resp = client.get(f"/listings/{listing.id}/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["price_usd"] == 12000.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_api_listings.py -v
```
Expected: FAIL

- [ ] **Step 3: Write api/districts.py**

Write `backend/api/districts.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import District

router = APIRouter()


@router.get("/districts")
def get_districts(db: Session = Depends(get_db)):
    districts = db.query(District).order_by(District.name).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "avg_price_per_sotka": d.avg_price_per_sotka,
            "median_price_per_sotka": d.median_price_per_sotka,
            "listing_count": d.listing_count,
        }
        for d in districts
    ]
```

- [ ] **Step 4: Write api/listings.py**

Write `backend/api/listings.py`:
```python
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Listing, PriceHistory

router = APIRouter()


def _listing_to_dict(l: Listing, price_changed_today: bool = False, change_pct_today: float | None = None) -> dict:
    return {
        "id": l.id,
        "external_id": l.external_id,
        "source": l.source,
        "title": l.title,
        "district_id": l.district_id,
        "district_name": l.district.name if l.district else "",
        "area_sotka": l.area_sotka,
        "current_price_usd": l.current_price_usd,
        "price_per_sotka": l.price_per_sotka,
        "url": l.url,
        "first_seen": str(l.first_seen),
        "last_seen": str(l.last_seen),
        "is_active": l.is_active,
        "price_changed_today": price_changed_today,
        "change_pct_today": change_pct_today,
    }


@router.get("/listings")
def get_listings(
    db: Session = Depends(get_db),
    district_id: int | None = Query(None),
    source: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    min_area: float | None = Query(None),
    max_area: float | None = Query(None),
    price_changed_today: bool = Query(False),
):
    today = date.today()
    today_changes = {
        ph.listing_id: ph.change_pct
        for ph in db.query(PriceHistory).filter(
            PriceHistory.recorded_at == today,
            PriceHistory.change_pct != None,
        ).all()
    }

    q = db.query(Listing).filter_by(is_active=True)
    if district_id is not None:
        q = q.filter(Listing.district_id == district_id)
    if source:
        q = q.filter(Listing.source == source)
    if min_price is not None:
        q = q.filter(Listing.current_price_usd >= min_price)
    if max_price is not None:
        q = q.filter(Listing.current_price_usd <= max_price)
    if min_area is not None:
        q = q.filter(Listing.area_sotka >= min_area)
    if max_area is not None:
        q = q.filter(Listing.area_sotka <= max_area)
    if price_changed_today:
        q = q.filter(Listing.id.in_(today_changes.keys()))

    listings = q.order_by(Listing.price_per_sotka).all()
    return [
        _listing_to_dict(l, l.id in today_changes, today_changes.get(l.id))
        for l in listings
    ]


@router.get("/listings/{listing_id}/history")
def get_listing_history(listing_id: int, db: Session = Depends(get_db)):
    history = (
        db.query(PriceHistory)
        .filter_by(listing_id=listing_id)
        .order_by(PriceHistory.recorded_at)
        .all()
    )
    return [
        {
            "price_usd": h.price_usd,
            "price_per_sotka": h.price_per_sotka,
            "recorded_at": str(h.recorded_at),
            "change_pct": h.change_pct,
        }
        for h in history
    ]
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_api_listings.py -v
```
Expected: 4 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/api/districts.py backend/api/listings.py backend/tests/test_api_listings.py
git commit -m "feat: /districts and /listings API endpoints"
```

---

## Task 12: API — /trends

**Files:**
- Create: `backend/api/trends.py`
- Create: `backend/tests/test_api_trends.py`

- [ ] **Step 1: Write failing test**

Write `backend/tests/test_api_trends.py`:
```python
from datetime import date, timedelta
from fastapi.testclient import TestClient
from db.models import District, Listing, PriceHistory
from db.session import get_db


def test_get_trends_returns_time_series(db):
    from main import app
    app.dependency_overrides[get_db] = lambda: db

    district = db.query(District).filter_by(name="Октябрьский").first()
    listing = Listing(
        external_id="h:trend1", source="house.kg", title="T",
        district_id=district.id, area_sotka=10.0,
        current_price_usd=20000.0, price_per_sotka=2000.0,
        url="https://house.kg/t1",
        first_seen=date(2026, 4, 1), last_seen=date(2026, 5, 28), is_active=True,
    )
    db.add(listing)
    db.flush()
    for i in range(3):
        db.add(PriceHistory(
            listing_id=listing.id,
            price_usd=20000.0 + i * 1000,
            price_per_sotka=2000.0 + i * 100,
            recorded_at=date(2026, 5, 1) + timedelta(days=i * 10),
            change_pct=None if i == 0 else 5.0,
        ))
    db.commit()

    client = TestClient(app)
    resp = client.get("/trends?days=60")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "date" in data[0]
    assert "district_name" in data[0]
    assert "median_price_per_sotka" in data[0]
```

- [ ] **Step 2: Write api/trends.py**

Write `backend/api/trends.py`:
```python
from datetime import date, timedelta
from collections import defaultdict
import statistics
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import PriceHistory, Listing, District

router = APIRouter()


@router.get("/trends")
def get_trends(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=365),
):
    since = date.today() - timedelta(days=days)

    rows = (
        db.query(PriceHistory, Listing, District)
        .join(Listing, PriceHistory.listing_id == Listing.id)
        .join(District, Listing.district_id == District.id)
        .filter(PriceHistory.recorded_at >= since)
        .all()
    )

    # Group by (date, district_id) → list of price_per_sotka values
    buckets: dict[tuple, list[float]] = defaultdict(list)
    district_names: dict[int, str] = {}
    for ph, listing, district in rows:
        key = (str(ph.recorded_at), district.id)
        buckets[key].append(ph.price_per_sotka)
        district_names[district.id] = district.name

    result = []
    for (recorded_at, district_id), prices in sorted(buckets.items()):
        result.append({
            "date": recorded_at,
            "district_id": district_id,
            "district_name": district_names[district_id],
            "median_price_per_sotka": round(statistics.median(prices), 2),
            "sample_count": len(prices),
        })

    return result
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_api_trends.py -v
```
Expected: PASSED

- [ ] **Step 4: Commit**

```bash
git add backend/api/trends.py backend/tests/test_api_trends.py
git commit -m "feat: /trends API endpoint"
```

---

## Task 13: API — /recommendations, /macro, /scrape

**Files:**
- Create: `backend/api/recommendations.py`
- Create: `backend/api/macro.py`
- Create: `backend/api/scrape.py`
- Create: `backend/tests/test_api_recommendations.py`

- [ ] **Step 1: Write failing test**

Write `backend/tests/test_api_recommendations.py`:
```python
from datetime import date
from fastapi.testclient import TestClient
from db.models import District, Listing
from db.session import get_db


def test_recommendations_returns_below_median_listings(db):
    from main import app
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    district = db.query(District).filter_by(name="Ленинский").first()
    district.median_price_per_sotka = 2000.0
    db.commit()

    # cheap listing: 1500/sotka < 2000 * 0.85 = 1700
    cheap = Listing(
        external_id="h:cheap", source="house.kg", title="Cheap",
        district_id=district.id, area_sotka=8.0,
        current_price_usd=12000.0, price_per_sotka=1500.0,
        url="https://house.kg/cheap",
        first_seen=date(2026, 5, 28), last_seen=date(2026, 5, 28), is_active=True,
    )
    # expensive listing: 2200/sotka > 1700 — not a deal
    expensive = Listing(
        external_id="h:exp", source="house.kg", title="Expensive",
        district_id=district.id, area_sotka=8.0,
        current_price_usd=17600.0, price_per_sotka=2200.0,
        url="https://house.kg/exp",
        first_seen=date(2026, 5, 28), last_seen=date(2026, 5, 28), is_active=True,
    )
    db.add_all([cheap, expensive])
    db.commit()

    resp = client.get("/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["external_id"] == "h:cheap"
    assert "discount_pct" in data[0]
```

- [ ] **Step 2: Write api/recommendations.py**

Write `backend/api/recommendations.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Listing, District
from config import DEAL_THRESHOLD

router = APIRouter()


@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    districts = {d.id: d for d in db.query(District).all()}
    listings = db.query(Listing).filter_by(is_active=True).all()

    deals = []
    for l in listings:
        district = districts.get(l.district_id)
        if not district or not district.median_price_per_sotka:
            continue
        threshold = district.median_price_per_sotka * DEAL_THRESHOLD
        if l.price_per_sotka < threshold:
            discount_pct = round(
                (1 - l.price_per_sotka / district.median_price_per_sotka) * 100, 1
            )
            deals.append({
                "id": l.id,
                "external_id": l.external_id,
                "source": l.source,
                "title": l.title,
                "district_id": l.district_id,
                "district_name": district.name,
                "area_sotka": l.area_sotka,
                "current_price_usd": l.current_price_usd,
                "price_per_sotka": l.price_per_sotka,
                "median_price_per_sotka": district.median_price_per_sotka,
                "discount_pct": discount_pct,
                "url": l.url,
                "last_seen": str(l.last_seen),
            })

    return sorted(deals, key=lambda d: d["discount_pct"], reverse=True)
```

- [ ] **Step 3: Write api/macro.py**

Write `backend/api/macro.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import MacroData

router = APIRouter()


@router.get("/macro")
def get_macro(db: Session = Depends(get_db)):
    latest = db.query(MacroData).order_by(MacroData.recorded_at.desc()).first()
    if not latest:
        return None
    return {
        "recorded_at": str(latest.recorded_at),
        "usd_kgs_rate": latest.usd_kgs_rate,
        "source": latest.source,
    }
```

- [ ] **Step 4: Write api/scrape.py**

Write `backend/api/scrape.py`:
```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from db.session import get_db
from scheduler import run_nightly_scrape

router = APIRouter()


@router.post("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_nightly_scrape)
    return {"status": "scrape started in background"}
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_api_recommendations.py -v
```
Expected: PASSED

- [ ] **Step 6: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASSED

- [ ] **Step 7: Commit**

```bash
git add backend/api/
git commit -m "feat: /recommendations, /macro, /scrape API endpoints"
```

---

## Task 14: Frontend Scaffold

**Files:**
- Create: `frontend/` (Vite project)
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Scaffold Vite + React + TypeScript project**

```bash
cd bishkek-land-tracker
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install recharts tailwindcss postcss autoprefixer
npm install -D @types/recharts
npx tailwindcss init -p
```

- [ ] **Step 3: Configure Tailwind**

Write `frontend/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Write `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Configure Vite proxy**

Write `frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

- [ ] **Step 5: Verify dev server starts**

```bash
cd frontend && npm run dev
```
Expected: Vite dev server running at http://localhost:5173, default React page visible.

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: Vite + React + Tailwind frontend scaffold"
```

---

## Task 15: TypeScript Types + API Client

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Write types.ts**

Write `frontend/src/types.ts`:
```ts
export interface District {
  id: number
  name: string
  avg_price_per_sotka: number | null
  median_price_per_sotka: number | null
  listing_count: number
}

export interface Listing {
  id: number
  external_id: string
  source: string
  title: string
  district_id: number
  district_name: string
  area_sotka: number
  current_price_usd: number
  price_per_sotka: number
  url: string
  first_seen: string
  last_seen: string
  is_active: boolean
  price_changed_today: boolean
  change_pct_today: number | null
}

export interface PriceHistoryEntry {
  price_usd: number
  price_per_sotka: number
  recorded_at: string
  change_pct: number | null
}

export interface TrendPoint {
  date: string
  district_id: number
  district_name: string
  median_price_per_sotka: number
  sample_count: number
}

export interface Deal extends Listing {
  median_price_per_sotka: number
  discount_pct: number
}

export interface MacroData {
  recorded_at: string
  usd_kgs_rate: number
  source: string
}

export interface Filters {
  district_ids: number[]
  sources: string[]
  min_price: number | null
  max_price: number | null
  min_area: number | null
  max_area: number | null
  price_changed_today: boolean
}
```

- [ ] **Step 2: Write api/client.ts**

Write `frontend/src/api/client.ts`:
```ts
import type { District, Listing, PriceHistoryEntry, TrendPoint, Deal, MacroData, Filters } from '../types'

const BASE = '/api'

async function get<T>(path: string, params?: Record<string, string | number | boolean | null | undefined>): Promise<T> {
  const url = new URL(path, window.location.origin)
  url.pathname = BASE + path
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined) url.searchParams.set(k, String(v))
    })
  }
  const res = await fetch(url.pathname + url.search)
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  getDistricts: () => get<District[]>('/districts'),

  getListings: (filters: Partial<Filters>) =>
    get<Listing[]>('/listings', {
      district_id: filters.district_ids?.length === 1 ? filters.district_ids[0] : undefined,
      source: filters.sources?.length === 1 ? filters.sources[0] : undefined,
      min_price: filters.min_price ?? undefined,
      max_price: filters.max_price ?? undefined,
      min_area: filters.min_area ?? undefined,
      max_area: filters.max_area ?? undefined,
      price_changed_today: filters.price_changed_today || undefined,
    }),

  getListingHistory: (id: number) =>
    get<PriceHistoryEntry[]>(`/listings/${id}/history`),

  getTrends: (days: number = 30) =>
    get<TrendPoint[]>('/trends', { days }),

  getRecommendations: () => get<Deal[]>('/recommendations'),

  getMacro: () => get<MacroData | null>('/macro'),

  triggerScrape: () =>
    fetch(BASE + '/scrape', { method: 'POST' }).then(r => r.json()),
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/
git commit -m "feat: TS types and API client"
```

---

## Task 16: Filter Context

**Files:**
- Create: `frontend/src/context/FilterContext.tsx`

- [ ] **Step 1: Write FilterContext.tsx**

Write `frontend/src/context/FilterContext.tsx`:
```tsx
import { createContext, useContext, useState, ReactNode } from 'react'
import type { Filters } from '../types'

const DEFAULT_FILTERS: Filters = {
  district_ids: [],
  sources: [],
  min_price: null,
  max_price: null,
  min_area: null,
  max_area: null,
  price_changed_today: false,
}

interface FilterContextValue {
  filters: Filters
  setFilters: (f: Partial<Filters>) => void
  resetFilters: () => void
}

const FilterContext = createContext<FilterContextValue | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, setFiltersState] = useState<Filters>(DEFAULT_FILTERS)

  const setFilters = (patch: Partial<Filters>) =>
    setFiltersState(prev => ({ ...prev, ...patch }))

  const resetFilters = () => setFiltersState(DEFAULT_FILTERS)

  return (
    <FilterContext.Provider value={{ filters, setFilters, resetFilters }}>
      {children}
    </FilterContext.Provider>
  )
}

export function useFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error('useFilters must be used within FilterProvider')
  return ctx
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/context/
git commit -m "feat: FilterContext global state"
```

---

## Task 17: SummaryCards Component

**Files:**
- Create: `frontend/src/components/SummaryCards.tsx`

- [ ] **Step 1: Write SummaryCards.tsx**

Write `frontend/src/components/SummaryCards.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Listing, Deal } from '../types'

interface Stats {
  totalListings: number
  weeklyDelta: number
  avgPricePerSotka: number
  monthlyPricePct: number | null
  priceDropsToday: number
  dealsCount: number
}

function StatCard({ label, value, sub, subColor }: {
  label: string
  value: string
  sub: string
  subColor?: string
}) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border-l-4 border-blue-500 flex-1 min-w-[160px]">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className={`text-xs mt-1 ${subColor ?? 'text-gray-400'}`}>{sub}</div>
    </div>
  )
}

export function SummaryCards() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    Promise.all([
      api.getListings({}),
      api.getListings({ price_changed_today: true }),
      api.getRecommendations(),
    ]).then(([all, changed, deals]: [Listing[], Listing[], Deal[]]) => {
      const prices = all.map(l => l.price_per_sotka).filter(p => p > 0)
      const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0
      setStats({
        totalListings: all.length,
        weeklyDelta: 0,
        avgPricePerSotka: Math.round(avg),
        monthlyPricePct: null,
        priceDropsToday: changed.filter(l => (l.change_pct_today ?? 0) < 0).length,
        dealsCount: deals.length,
      })
    })
  }, [])

  if (!stats) return <div className="flex gap-3 animate-pulse">{[1,2,3,4].map(i => (
    <div key={i} className="flex-1 h-20 bg-gray-800 rounded-xl" />
  ))}</div>

  return (
    <div className="flex gap-3 flex-wrap">
      <StatCard
        label="Всего объявлений"
        value={stats.totalListings.toLocaleString()}
        sub={stats.weeklyDelta > 0 ? `↑ +${stats.weeklyDelta} за неделю` : 'нет данных'}
        subColor="text-green-400"
      />
      <StatCard
        label="Средняя цена / сотка"
        value={`$${stats.avgPricePerSotka.toLocaleString()}`}
        sub={stats.monthlyPricePct !== null
          ? `${stats.monthlyPricePct > 0 ? '↑' : '↓'} ${stats.monthlyPricePct}% за месяц`
          : 'нет истории'}
        subColor={stats.monthlyPricePct && stats.monthlyPricePct < 0 ? 'text-red-400' : 'text-gray-400'}
      />
      <StatCard
        label="Снижение цен сегодня"
        value={String(stats.priceDropsToday)}
        sub="объявлений снизили цену"
      />
      <StatCard
        label="Выгодных сделок"
        value={String(stats.dealsCount)}
        sub="ниже среднего на 15%+"
      />
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/SummaryCards.tsx
git commit -m "feat: SummaryCards component"
```

---

## Task 18: TrendChart Component

**Files:**
- Create: `frontend/src/components/TrendChart.tsx`

- [ ] **Step 1: Write TrendChart.tsx**

Write `frontend/src/components/TrendChart.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../api/client'
import type { TrendPoint } from '../types'

const DISTRICT_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#fb923c']

type Period = 30 | 90 | 365

interface ChartRow {
  date: string
  [districtName: string]: number | string
}

export function TrendChart() {
  const [period, setPeriod] = useState<Period>(30)
  const [data, setData] = useState<ChartRow[]>([])
  const [districts, setDistricts] = useState<string[]>([])

  useEffect(() => {
    api.getTrends(period).then((points: TrendPoint[]) => {
      const dateMap: Record<string, ChartRow> = {}
      const districtSet = new Set<string>()

      for (const p of points) {
        if (!dateMap[p.date]) dateMap[p.date] = { date: p.date }
        dateMap[p.date][p.district_name] = p.median_price_per_sotka
        districtSet.add(p.district_name)
      }

      setData(Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date)))
      setDistricts([...districtSet])
    })
  }, [period])

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-gray-400 text-sm">Тренд средней цены / сотка по районам</h3>
        <div className="flex gap-1">
          {([30, 90, 365] as Period[]).map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`text-xs px-2 py-1 rounded ${period === p ? 'bg-blue-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
            >
              {p === 365 ? '1 год' : `${p} дн`}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#4b5563' }} />
          <YAxis tick={{ fontSize: 10, fill: '#4b5563' }} tickFormatter={v => `$${v}`} />
          <Tooltip
            contentStyle={{ background: '#111827', border: '1px solid #1f2937', fontSize: 12 }}
            formatter={(v: number) => [`$${v.toLocaleString()}`, '']}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {districts.map((name, i) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              stroke={DISTRICT_COLORS[i % DISTRICT_COLORS.length]}
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TrendChart.tsx
git commit -m "feat: TrendChart with period selector"
```

---

## Task 19: DealsPanel Component

**Files:**
- Create: `frontend/src/components/DealsPanel.tsx`

- [ ] **Step 1: Write DealsPanel.tsx**

Write `frontend/src/components/DealsPanel.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Deal } from '../types'

function DealCard({ deal }: { deal: Deal }) {
  return (
    <a
      href={deal.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-green-950 border-l-2 border-green-400 rounded-lg p-3 hover:bg-green-900 transition-colors"
    >
      <div className="text-sm text-white font-medium mb-1 truncate">{deal.district_name}, {deal.area_sotka} соток</div>
      <div className="text-lg font-bold text-green-400">${deal.current_price_usd.toLocaleString()}</div>
      <div className="text-xs text-gray-400">${deal.price_per_sotka.toLocaleString()}/сотка · среднее ${deal.median_price_per_sotka.toLocaleString()}</div>
      <div className="text-xs text-green-400 mt-1">-{deal.discount_pct}% от среднего · {deal.source}</div>
    </a>
  )
}

interface Props {
  limit?: number
  showAll?: boolean
}

export function DealsPanel({ limit = 3, showAll = false }: Props) {
  const [deals, setDeals] = useState<Deal[]>([])

  useEffect(() => {
    api.getRecommendations().then(setDeals)
  }, [])

  const visible = showAll ? deals : deals.slice(0, limit)

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="text-sm text-gray-400 mb-1">⭐ Выгодные сделки</div>
      <div className="text-xs text-gray-600 mb-3">Ниже средней цены района на 15%+</div>
      <div className="flex flex-col gap-2">
        {visible.map(d => <DealCard key={d.id} deal={d} />)}
        {deals.length === 0 && <div className="text-xs text-gray-600">Выгодных сделок пока нет</div>}
      </div>
      {!showAll && deals.length > limit && (
        <div className="text-xs text-blue-400 mt-3 text-center">
          Все {deals.length} рекомендаций →
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/DealsPanel.tsx
git commit -m "feat: DealsPanel component"
```

---

## Task 20: ListingsTable Component

**Files:**
- Create: `frontend/src/components/ListingsTable.tsx`

- [ ] **Step 1: Write ListingsTable.tsx**

Write `frontend/src/components/ListingsTable.tsx`:
```tsx
import { useState } from 'react'
import type { Listing } from '../types'

type SortKey = 'current_price_usd' | 'price_per_sotka' | 'area_sotka' | 'last_seen'

function PriceChangeCell({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-gray-600">—</span>
  return pct < 0
    ? <span className="text-red-400">↓ {Math.abs(pct).toFixed(1)}%</span>
    : <span className="text-green-400">↑ {pct.toFixed(1)}%</span>
}

interface Props {
  listings: Listing[]
  loading?: boolean
}

export function ListingsTable({ listings, loading }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('price_per_sotka')
  const [sortAsc, setSortAsc] = useState(true)

  const sorted = [...listings].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey]
    if (typeof av === 'string' && typeof bv === 'string') {
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av)
    }
    return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(a => !a)
    else { setSortKey(key); setSortAsc(true) }
  }

  const SortTh = ({ label, k }: { label: string; k: SortKey }) => (
    <th
      className="px-3 py-2 text-left text-xs text-gray-500 cursor-pointer hover:text-gray-300 select-none"
      onClick={() => toggleSort(k)}
    >
      {label} {sortKey === k ? (sortAsc ? '↑' : '↓') : ''}
    </th>
  )

  if (loading) return <div className="h-40 bg-gray-800 animate-pulse rounded-xl" />

  return (
    <div className="bg-gray-900 rounded-xl overflow-hidden">
      <div className="px-4 py-3 text-sm text-gray-400">📋 Объявления</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-800">
            <tr>
              <th className="px-3 py-2 text-left text-xs text-gray-500">Район</th>
              <SortTh label="Площадь" k="area_sotka" />
              <SortTh label="Цена $" k="current_price_usd" />
              <SortTh label="$/сотка" k="price_per_sotka" />
              <th className="px-3 py-2 text-left text-xs text-gray-500">Изменение</th>
              <th className="px-3 py-2 text-left text-xs text-gray-500">Источник</th>
              <SortTh label="Дата" k="last_seen" />
            </tr>
          </thead>
          <tbody>
            {sorted.map(l => (
              <tr
                key={l.id}
                className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer"
                onClick={() => window.open(l.url, '_blank')}
              >
                <td className="px-3 py-2 text-gray-300">{l.district_name}</td>
                <td className="px-3 py-2 text-gray-300">{l.area_sotka} сот.</td>
                <td className="px-3 py-2 font-semibold text-white">${l.current_price_usd.toLocaleString()}</td>
                <td className="px-3 py-2 text-gray-300">${l.price_per_sotka.toLocaleString()}</td>
                <td className="px-3 py-2"><PriceChangeCell pct={l.change_pct_today} /></td>
                <td className="px-3 py-2 text-blue-400">{l.source}</td>
                <td className="px-3 py-2 text-gray-600 text-xs">{l.last_seen}</td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-600">Нет данных</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ListingsTable.tsx
git commit -m "feat: ListingsTable with sort"
```

---

## Task 21: Filters Component

**Files:**
- Create: `frontend/src/components/Filters.tsx`

- [ ] **Step 1: Write Filters.tsx**

Write `frontend/src/components/Filters.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { useFilters } from '../context/FilterContext'
import { api } from '../api/client'
import type { District } from '../types'

const SOURCES = ['house.kg', 'lalafo', 'stroka', 'stroika']

export function Filters() {
  const { filters, setFilters, resetFilters } = useFilters()
  const [districts, setDistricts] = useState<District[]>([])

  useEffect(() => { api.getDistricts().then(setDistricts) }, [])

  return (
    <div className="flex flex-wrap gap-3 items-center bg-gray-900 px-4 py-3 rounded-xl">
      <span className="text-xs text-gray-500">Фильтры:</span>

      <select
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 text-sm"
        value={filters.district_ids[0] ?? ''}
        onChange={e => setFilters({ district_ids: e.target.value ? [Number(e.target.value)] : [] })}
      >
        <option value="">Все районы</option>
        {districts.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
      </select>

      <select
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 text-sm"
        value={filters.sources[0] ?? ''}
        onChange={e => setFilters({ sources: e.target.value ? [e.target.value] : [] })}
      >
        <option value="">Все источники</option>
        {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
      </select>

      <input
        type="number"
        placeholder="Цена от $"
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 text-sm w-28"
        value={filters.min_price ?? ''}
        onChange={e => setFilters({ min_price: e.target.value ? Number(e.target.value) : null })}
      />

      <input
        type="number"
        placeholder="Цена до $"
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 text-sm w-28"
        value={filters.max_price ?? ''}
        onChange={e => setFilters({ max_price: e.target.value ? Number(e.target.value) : null })}
      />

      <input
        type="number"
        placeholder="Соток от"
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 text-sm w-24"
        value={filters.min_area ?? ''}
        onChange={e => setFilters({ min_area: e.target.value ? Number(e.target.value) : null })}
      />

      <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
        <input
          type="checkbox"
          checked={filters.price_changed_today}
          onChange={e => setFilters({ price_changed_today: e.target.checked })}
          className="accent-blue-500"
        />
        Изменение цены сегодня
      </label>

      <button
        onClick={resetFilters}
        className="text-xs text-gray-500 hover:text-gray-300 ml-auto"
      >
        Сбросить
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Filters.tsx
git commit -m "feat: Filters component"
```

---

## Task 22: Dashboard Page

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Write Dashboard.tsx**

Write `frontend/src/pages/Dashboard.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { SummaryCards } from '../components/SummaryCards'
import { TrendChart } from '../components/TrendChart'
import { DealsPanel } from '../components/DealsPanel'
import { Filters } from '../components/Filters'
import { useFilters } from '../context/FilterContext'
import { api } from '../api/client'
import type { Listing, MacroData } from '../types'

export function Dashboard() {
  const { filters } = useFilters()
  const [listings, setListings] = useState<Listing[]>([])
  const [macro, setMacro] = useState<MacroData | null>(null)
  const [scraping, setScraping] = useState(false)

  useEffect(() => {
    api.getListings(filters).then(setListings)
  }, [filters])

  useEffect(() => {
    api.getMacro().then(setMacro)
  }, [])

  const handleScrape = () => {
    setScraping(true)
    api.triggerScrape().finally(() => setTimeout(() => setScraping(false), 3000))
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="text-xs text-gray-500">
          {macro ? `Курс USD/KGS: ${macro.usd_kgs_rate} · обновлено ${macro.recorded_at}` : ''}
        </div>
        <button
          onClick={handleScrape}
          disabled={scraping}
          className="text-xs bg-green-900 hover:bg-green-800 text-green-300 px-3 py-1.5 rounded-lg disabled:opacity-50"
        >
          {scraping ? '⏳ Парсинг...' : '🔄 Обновить данные'}
        </button>
      </div>

      <SummaryCards />
      <Filters />

      <div className="flex gap-4">
        <div className="flex-2 min-w-0" style={{ flex: 2 }}>
          <TrendChart />
        </div>
        <div className="flex-1 min-w-0" style={{ flex: 1 }}>
          <DealsPanel limit={3} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: Dashboard page"
```

---

## Task 23: Listings, Trends, Recommendations Pages

**Files:**
- Create: `frontend/src/pages/Listings.tsx`
- Create: `frontend/src/pages/Trends.tsx`
- Create: `frontend/src/pages/Recommendations.tsx`

- [ ] **Step 1: Write Listings.tsx**

Write `frontend/src/pages/Listings.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { Filters } from '../components/Filters'
import { ListingsTable } from '../components/ListingsTable'
import { useFilters } from '../context/FilterContext'
import { api } from '../api/client'
import type { Listing } from '../types'

export function Listings() {
  const { filters } = useFilters()
  const [listings, setListings] = useState<Listing[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.getListings(filters).then(data => { setListings(data); setLoading(false) })
  }, [filters])

  return (
    <div className="space-y-4">
      <Filters />
      <div className="text-xs text-gray-500">{listings.length} объявлений</div>
      <ListingsTable listings={listings} loading={loading} />
    </div>
  )
}
```

- [ ] **Step 2: Write Trends.tsx**

Write `frontend/src/pages/Trends.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { District } from '../types'
import { TrendChart } from '../components/TrendChart'

export function Trends() {
  const [districts, setDistricts] = useState<District[]>([])

  useEffect(() => { api.getDistricts().then(setDistricts) }, [])

  return (
    <div className="space-y-4">
      <TrendChart />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {districts.filter(d => d.listing_count > 0).map(d => {
          return (
            <div key={d.id} className="bg-gray-900 rounded-xl p-4">
              <div className="text-sm font-medium text-white mb-2">{d.name}</div>
              <div className="text-xs text-gray-400">Медиана: <span className="text-white">${d.median_price_per_sotka?.toLocaleString() ?? '—'}/сотка</span></div>
              <div className="text-xs text-gray-400">Среднее: <span className="text-white">${d.avg_price_per_sotka?.toLocaleString() ?? '—'}/сотка</span></div>
              <div className="text-xs text-gray-500 mt-1">{d.listing_count} объявлений</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Write Recommendations.tsx**

Write `frontend/src/pages/Recommendations.tsx`:
```tsx
import { DealsPanel } from '../components/DealsPanel'

export function Recommendations() {
  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-400">
        Объявления с ценой за сотку на 15%+ ниже медианной по своему району.
      </div>
      <DealsPanel showAll />
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/
git commit -m "feat: Listings, Trends, Recommendations pages"
```

---

## Task 24: Nav + App Router

**Files:**
- Create: `frontend/src/components/Nav.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Write Nav.tsx**

Write `frontend/src/components/Nav.tsx`:
```tsx
interface NavProps {
  active: string
  onNavigate: (page: string) => void
}

const PAGES = [
  { id: 'dashboard', label: '📊 Дашборд' },
  { id: 'listings', label: '📋 Объявления' },
  { id: 'trends', label: '📈 Тренды' },
  { id: 'recommendations', label: '⭐ Рекомендации' },
]

export function Nav({ active, onNavigate }: NavProps) {
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center justify-between">
      <div className="flex gap-4">
        {PAGES.map(p => (
          <button
            key={p.id}
            onClick={() => onNavigate(p.id)}
            className={`text-sm transition-colors ${
              active === p.id
                ? 'text-blue-400 border-b-2 border-blue-400 pb-0.5'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="text-xs text-gray-600">Bishkek Land Tracker</div>
    </nav>
  )
}
```

- [ ] **Step 2: Write App.tsx**

Write `frontend/src/App.tsx`:
```tsx
import { useState } from 'react'
import { FilterProvider } from './context/FilterContext'
import { Nav } from './components/Nav'
import { Dashboard } from './pages/Dashboard'
import { Listings } from './pages/Listings'
import { Trends } from './pages/Trends'
import { Recommendations } from './pages/Recommendations'

const PAGES: Record<string, React.ReactNode> = {
  dashboard: <Dashboard />,
  listings: <Listings />,
  trends: <Trends />,
  recommendations: <Recommendations />,
}

export default function App() {
  const [page, setPage] = useState('dashboard')

  return (
    <FilterProvider>
      <div className="min-h-screen bg-gray-950 text-white">
        <Nav active={page} onNavigate={setPage} />
        <main className="max-w-7xl mx-auto px-4 py-6">
          {PAGES[page]}
        </main>
      </div>
    </FilterProvider>
  )
}
```

- [ ] **Step 3: Write main.tsx**

Write `frontend/src/main.tsx`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 4: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Start both servers and verify**

Terminal 1:
```bash
cd backend && uvicorn main:app --reload
```

Terminal 2:
```bash
cd frontend && npm run dev
```

Open http://localhost:5173. Verify:
- All 4 nav tabs render without errors
- Summary cards load (show 0s if no data — that's fine)
- Trend chart renders empty state
- Deals panel shows "нет данных"
- Listings table renders empty

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: Nav, App router, complete frontend"
```

---

## Task 25: End-to-End Smoke Test + Final Cleanup

**Files:**
- No new files — manual verification

- [ ] **Step 1: Run the full backend test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASSED, no failures.

- [ ] **Step 2: Trigger a scrape and verify data flows through**

With both servers running:
```bash
curl -X POST http://localhost:8000/scrape
```

Wait ~2 minutes (Playwright scraping takes time). Then:
```bash
curl http://localhost:8000/listings | python -m json.tool | head -50
curl http://localhost:8000/districts | python -m json.tool
```
Expected: listings array with real data, districts with updated `listing_count`.

- [ ] **Step 3: Verify dashboard shows real data**

Open http://localhost:5173:
- SummaryCards show real listing counts and prices
- TrendChart still shows empty (needs 2+ days of data for trends)
- DealsPanel shows deals if any listings are ≥15% below median

- [ ] **Step 4: Add .gitignore entries and final commit**

Verify `bishkek-land-tracker/.gitignore` includes:
```
backend/data/
.superpowers/
__pycache__/
*.pyc
.venv/
node_modules/
dist/
```

```bash
git add .
git commit -m "feat: complete Bishkek Land Tracker MVP"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ 4 scraper sources (house.kg, lalafo, stroka, stroika) — Tasks 5-8
- ✅ NBKR exchange rate — Task 9
- ✅ SQLite schema (districts, listings, price_history, macro_data) — Task 2
- ✅ Nightly scrape with APScheduler — Task 10
- ✅ Upsert logic + price change tracking — Task 4
- ✅ mark_inactive when listing disappears — Task 4
- ✅ Recalculate district medians nightly — Task 4
- ✅ All 7 API endpoints — Tasks 11-13
- ✅ Deal detection (15% below median) — Task 13
- ✅ Trend signals per district — Task 22 (Trends page shows district cards)
- ✅ Dashboard with SummaryCards, TrendChart, DealsPanel — Tasks 17-22
- ✅ Listings table with sort + price change indicators — Task 20
- ✅ Filters (district, source, price range, area, price_changed_today) — Task 21
- ✅ Manual scrape trigger button — Task 22
- ✅ docker-compose — Task 1
