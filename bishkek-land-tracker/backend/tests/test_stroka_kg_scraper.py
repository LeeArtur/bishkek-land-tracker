from pathlib import Path
from scraper.stroka_kg import _parse_html
from scraper.base import ListingRaw

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_parse_html_extracts_listing():
    """Fixture is a real stroka.kg ad page with JSON-LD Product schema."""
    html = (FIXTURE_DIR / "stroka_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, ListingRaw)
    assert r.source == "stroka"
    assert r.external_id == "stroka:57d74074-408e-4bac-92b3-6bc35ea3c394"
    assert r.price_usd is not None and r.price_usd > 0
    assert r.url == "https://stroka.kg/ad/57d74074-408e-4bac-92b3-6bc35ea3c394"


def test_parse_html_extracts_area_from_title():
    """Land plot title '9 сот.' must be parsed into area_sotka=9.0."""
    html = (FIXTURE_DIR / "stroka_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) == 1
    assert results[0].area_sotka == 9.0


def test_parse_html_extracts_district_from_location():
    """addressLocality from JSON-LD must become district_name."""
    html = (FIXTURE_DIR / "stroka_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) == 1
    assert results[0].district_name == "с. Кок-Джар"


def test_parse_html_converts_kgs_price():
    """Price 31 500 000 KGS / 87 ≈ 362 069 USD."""
    html = (FIXTURE_DIR / "stroka_kg_card.html").read_text()
    results = _parse_html(html)
    assert len(results) == 1
    r = results[0]
    assert r.price_usd is not None
    # Allow ±1 USD for floating-point rounding
    assert abs(r.price_usd - round(31_500_000 / 87.0, 2)) <= 1.0


def test_parse_html_skips_listings_without_price():
    """JSON-LD without an offers.price must be skipped."""
    html = """<!DOCTYPE html><html><head>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Участок, 5 сот.",
      "url": "https://stroka.kg/ad/aaaabbbb-cccc-dddd-eeee-ffffffffffff",
      "offers": {
        "@type": "Offer",
        "priceCurrency": "KGS"
      },
      "additionalProperty": [],
      "itemLocation": {
        "@type": "Place",
        "address": {
          "@type": "PostalAddress",
          "addressLocality": "Бишкек"
        }
      }
    }
    </script>
    </head><body></body></html>"""
    results = _parse_html(html)
    assert results == []


def test_parse_html_handles_ga_area():
    """Area expressed as '0.15 га' should convert to 15.0 соток."""
    html = """<!DOCTYPE html><html><head>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Продается участок, 0.15 га",
      "url": "https://stroka.kg/ad/12345678-0000-0000-0000-000000000001",
      "offers": {
        "@type": "Offer",
        "price": 1500000,
        "priceCurrency": "KGS"
      },
      "additionalProperty": [],
      "itemLocation": {
        "@type": "Place",
        "address": {
          "@type": "PostalAddress",
          "addressLocality": "Ленинский",
          "addressRegion": "Бишкек"
        }
      }
    }
    </script>
    </head><body></body></html>"""
    results = _parse_html(html)
    assert len(results) == 1
    assert results[0].area_sotka == 15.0
