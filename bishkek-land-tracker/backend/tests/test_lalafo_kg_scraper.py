from pathlib import Path
from scraper.lalafo_kg import _parse_html
from scraper.base import ListingRaw

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_parse_html_extracts_listing():
    """Fixture contains two lalafo.kg product-card articles; both should parse."""
    html = (FIXTURE_DIR / "lalafo_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    r = results[0]
    assert isinstance(r, ListingRaw)
    assert r.source == "lalafo"
    assert r.external_id.startswith("lalafo:")
    assert r.price_usd is not None and r.price_usd > 0
    assert r.url.startswith("https://lalafo.kg")


def test_parse_html_extracts_area_from_attributes():
    """Area '8 сот.' in the product-card__attributes block must be extracted."""
    html = (FIXTURE_DIR / "lalafo_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    r = results[0]
    assert r.area_sotka == 8.0


def test_parse_html_extracts_district_from_location():
    """District is the first comma-separated token in product-card__location."""
    html = (FIXTURE_DIR / "lalafo_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    r = results[0]
    assert r.district_name == "Ленинский"


def test_parse_html_converts_kgs_price():
    """Second fixture card has KGS price (3 500 000 сом); must convert to USD."""
    html = (FIXTURE_DIR / "lalafo_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 2
    r = results[1]
    # 3 500 000 сом / 87 ≈ 40 230 USD
    assert r.price_usd is not None and r.price_usd > 0
    assert r.external_id == "lalafo:84519002"


def test_parse_html_skips_listings_without_price():
    """A card with an unparseable price (e.g., 'Договорная') must be skipped."""
    html = """<html><body>
    <article class="product-card">
      <a class="product-card__title" href="/kyrgyzstan/ad/99999">
        Участок, 5 сот.
      </a>
      <div class="product-card__price">
        <span class="price-text">Договорная</span>
      </div>
      <div class="product-card__location">Бишкек</div>
    </article>
    </body></html>"""
    results = _parse_html(html)
    assert results == []
