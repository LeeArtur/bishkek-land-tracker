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
    assert r.price_usd is not None and r.price_usd > 0
    assert r.url.startswith("https://house.kg")


def test_parse_html_extracts_area_from_title():
    html = (FIXTURE_DIR / "house_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    r = results[0]
    # Fixture card title is "Участок, 4.5 сотки"
    assert r.area_sotka == 4.5


def test_parse_html_extracts_district_from_address():
    html = (FIXTURE_DIR / "house_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) >= 1
    r = results[0]
    # Fixture card address is "Бишкек, Матросова, переулок Елецкий"
    assert r.district_name == "Бишкек"


def test_parse_html_skips_listings_without_price():
    # Build minimal HTML with a listing card that has no parseable price
    html = """<html><body>
    <div class="listing">
      <div class="main-wrapper">
        <div class="right-info">
          <div class="top-info">
            <div class="left-side">
              <p class="title">
                <a href="/details/99999testid-00000000">Участок, 6 соток</a>
              </p>
              <div class="address">Бишкек, ул. Тестовая</div>
            </div>
            <div class="right-side">
              <div class="listing-prices-block">
                <div class="sep main">
                  <div class="price">Договорная</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </body></html>"""
    results = _parse_html(html)
    assert results == []
