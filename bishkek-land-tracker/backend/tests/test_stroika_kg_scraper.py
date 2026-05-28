from pathlib import Path
from scraper.stroika_kg import _parse_html
from scraper.base import ListingRaw

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_parse_html_extracts_listing():
    """
    Fixture is a best-guess placeholder card for stroika.kg.
    NOTE: stroika.kg DNS was unreachable as of 2026-05-28 — update fixture
    and selectors once the site becomes reachable.
    """
    html = (FIXTURE_DIR / "stroika_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    r = results[0]
    assert isinstance(r, ListingRaw)
    assert r.source == "stroika"
    assert r.external_id.startswith("stroika:")
    assert r.price_usd is not None and r.price_usd > 0
    assert r.url.startswith("https://stroika.kg")


def test_parse_html_extracts_area_from_title():
    """Area '6 соток' in the title must be extracted."""
    html = (FIXTURE_DIR / "stroika_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    assert results[0].area_sotka == 6.0


def test_parse_html_extracts_district_from_location():
    """District is the first comma-separated token in .location."""
    html = (FIXTURE_DIR / "stroika_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    assert results[0].district_name == "Свердловский"


def test_parse_html_skips_listings_without_price():
    """A card with no parseable price must be skipped."""
    html = """<html><body>
    <div class="listing-card">
      <h3><a class="title" href="/ad/99999">Участок, 10 сот.</a></h3>
      <span class="price">По договорённости</span>
      <span class="location">Бишкек</span>
    </div>
    </body></html>"""
    results = _parse_html(html)
    assert results == []


def test_parse_html_converts_ga_area():
    """Area '0.15 га' must convert to 15.0 соток."""
    html = """<html><body>
    <div class="listing-card">
      <h3><a class="title" href="/ad/55555">Земельный участок 0.15 га</a></h3>
      <span class="price">$ 12 000</span>
      <span class="location">Первомайский, ул. Весенняя</span>
    </div>
    </body></html>"""
    results = _parse_html(html)
    assert len(results) == 1
    assert results[0].area_sotka == 15.0
