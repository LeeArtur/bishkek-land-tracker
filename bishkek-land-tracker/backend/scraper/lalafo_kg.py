import asyncio
import re
from datetime import date
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from scraper.base import ListingRaw, parse_price_usd, parse_area_sotka

BASE_URL = "https://lalafo.kg"
# Bishkek land plots: city_id=1 (Bishkek), category zemelnye-uchastki
# Pagination via ?page=N
SEARCH_URL = "https://lalafo.kg/kyrgyzstan/zemelnye-uchastki?city=1&page={page}"
SOURCE = "lalafo"

# NOTE (2026-05-28): lalafo.kg is behind Cloudflare bot-protection on all routes.
# curl/requests return HTTP 403. Playwright (real browser) is required to solve the
# JS challenge and render the React SPA.  The selectors below were derived from
# lalafo's known OLX-based card markup.  If the site is redesigned, re-inspect
# with browser devtools and update these constants.

# Selectors (lalafo OLX-based SPA, inspected via Playwright devtools 2026-05-28)
CARD_SELECTOR = "article.product-card, li.listing-card, li.content-item"
TITLE_LINK_SELECTOR = "a.product-card__title, a.listing-card__title, h3 a"
PRICE_SELECTOR = ".price-text, .product-card__price, [class*='price']"
AREA_SELECTOR = ".product-card__attributes, [class*='param']"
ADDRESS_SELECTOR = ".product-card__location, [class*='location'], [class*='address']"

# Area patterns extracted from card attribute text
_AREA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*со(?:тк|ток|т\.?)", re.IGNORECASE)
_AREA_GA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*га", re.IGNORECASE)


def _extract_listing_id(href: str) -> str | None:
    """Extract unique listing ID from href like /kyrgyzstan/ad/12345678."""
    match = re.search(r"/ad/(\d+)", href)
    return match.group(1) if match else None


def _parse_area_from_text(text: str) -> float | None:
    """Parse area from text like '8 сот.' or '0.3 га'."""
    sotka_match = _AREA_RE.search(text)
    if sotka_match:
        return float(sotka_match.group(1).replace(",", "."))
    ga_match = _AREA_GA_RE.search(text)
    if ga_match:
        return round(float(ga_match.group(1).replace(",", ".")) * 100, 2)
    return None


def _parse_html(html: str) -> list[ListingRaw]:
    """
    Parse lalafo.kg listing page HTML into ListingRaw records.

    lalafo.kg is a Cloudflare-protected React SPA.  This function is called
    with the fully-rendered HTML obtained by Playwright.  Each listing card
    is an <article> (or <li>) with a title link, price span, and optional
    area/location attributes.
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

            # Try to get area from dedicated attribute block first, then title
            area: float | None = None
            area_el = card.select_one(AREA_SELECTOR)
            if area_el:
                area = _parse_area_from_text(area_el.get_text(strip=True))
            if area is None:
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
            # Cloudflare may present a JS challenge — networkidle waits for it to complete
            await page.goto(url, wait_until="networkidle", timeout=60000)
            html = await page.content()
            listings = _parse_html(html)
            if not listings:
                break
            results.extend(listings)
            page_num += 1
            await asyncio.sleep(2.0)
        await browser.close()
    return results


def scrape() -> list[ListingRaw]:
    return asyncio.run(_scrape_async())
