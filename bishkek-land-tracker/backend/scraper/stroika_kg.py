import asyncio
import re
from datetime import date
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from scraper.base import ListingRaw, parse_price_usd, parse_area_sotka

BASE_URL = "https://stroika.kg"
SEARCH_URL = "https://stroika.kg/zemelnye-uchastki?page={page}"
SOURCE = "stroika"

# NOTE (2026-05-28): stroika.kg DNS does not resolve — the domain is unreachable
# (curl returns "Could not resolve host: stroika.kg").  The scraper is implemented
# based on the typical Bishkek classifieds site structure observed on similar
# portals (house.kg / stroka.kg).  Once the domain becomes reachable, the
# selectors should be verified and updated via browser devtools inspection.
#
# Expected card structure (best-guess from similar KG real-estate portals):
#   <div class="listing-card"> or <article class="ad-card">
#     <a class="title" href="/ad/12345">Участок, 8 сот.</a>
#     <span class="price">25 000 $</span>
#     <span class="location">Бишкек, Ленинский р-н</span>
#   </div>

CARD_SELECTOR = (
    "div.listing-card, article.ad-card, div.property-card, "
    "div.item-card, article.item"
)
TITLE_LINK_SELECTOR = "a.title, h2 a, h3 a, .card-title a"
PRICE_SELECTOR = ".price, .cost, span.price-text, [class*='price']"
ADDRESS_SELECTOR = ".location, .address, [class*='location'], [class*='address']"

_AREA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*со(?:тк|ток|т\.?)", re.IGNORECASE)
_AREA_GA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*га", re.IGNORECASE)


def _extract_listing_id(href: str) -> str | None:
    """Extract ID from href like /ad/12345 or /listing/12345."""
    match = re.search(r"/(?:ad|listing|property|object)/([^/?#]+)", href)
    return match.group(1) if match else None


def _parse_area_from_text(text: str) -> float | None:
    """Parse area from title or attribute text."""
    sotka_match = _AREA_RE.search(text)
    if sotka_match:
        return float(sotka_match.group(1).replace(",", "."))
    ga_match = _AREA_GA_RE.search(text)
    if ga_match:
        return round(float(ga_match.group(1).replace(",", ".")) * 100, 2)
    return None


def _parse_html(html: str) -> list[ListingRaw]:
    """
    Parse stroika.kg listing-page HTML into ListingRaw records.

    NOTE: stroika.kg is currently unreachable (DNS failure as of 2026-05-28).
    Selectors are best-guesses.  Re-inspect when the site becomes available.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    today = date.today()

    for card in soup.select(CARD_SELECTOR):
        try:
            link_el = card.select_one(TITLE_LINK_SELECTOR)
            price_el = card.select_one(PRICE_SELECTOR)

            if not all([link_el, price_el]):
                continue

            href = link_el.get("href", "")
            listing_id = _extract_listing_id(href)
            if not listing_id:
                continue

            title_text = link_el.get_text(strip=True)
            price_text = price_el.get_text(strip=True)
            price_main = price_text.split("/")[0].strip()
            price = parse_price_usd(price_main)

            if price is None:
                continue

            area = _parse_area_from_text(title_text)

            district_name = "Другой"
            addr_el = card.select_one(ADDRESS_SELECTOR)
            if addr_el:
                addr_text = addr_el.get_text(strip=True)
                district_name = addr_text.split(",")[0].strip() or "Другой"

            full_url = BASE_URL + href if href.startswith("/") else href

            results.append(ListingRaw(
                external_id=f"{SOURCE}:{listing_id}",
                source=SOURCE,
                title=title_text,
                district_name=district_name,
                area_sotka=area,
                price_usd=price,
                url=full_url,
                scraped_at=today,
            ))
        except Exception:
            continue

    return results


async def _scrape_async() -> list[ListingRaw]:
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ru-RU",
        )
        page = await context.new_page()
        page_num = 1
        while True:
            url = SEARCH_URL.format(page=page_num)
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                break  # Domain unreachable or timeout
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
