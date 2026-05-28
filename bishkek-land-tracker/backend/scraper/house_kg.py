import asyncio
import re
from datetime import date
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from scraper.base import ListingRaw, parse_price_usd, parse_area_sotka

BASE_URL = "https://house.kg"
# Bishkek land plots: city=1 filters to Bishkek region, page={page} for pagination
SEARCH_URL = "https://house.kg/kupit-uchastok?city=1&page={page}"
SOURCE = "house.kg"

# Selectors discovered by inspecting https://house.kg/kupit-uchastok (2026-05-28)
CARD_SELECTOR = "div.listing"          # container: <div itemscope ... class="listing">
TITLE_LINK_SELECTOR = "p.title a"      # <a href="/details/...">Участок, 4.5 сотки</a>
PRICE_SELECTOR = ".sep.main .price"    # main price: <div class="price">$ 295 000</div>
ADDRESS_SELECTOR = "div.address"       # location: <div class="address">Бишкек, ...</div>

# Area is embedded in the title text: "Участок, 4.5 сотки" — no dedicated element
_AREA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*со(?:тк|ток|т\.)", re.IGNORECASE)
_AREA_GA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*га", re.IGNORECASE)


def _extract_listing_id(href: str) -> str | None:
    """Extract unique ID from href like /details/106097169fcac6736b7f0-59663491."""
    match = re.search(r"/details/([^/?#]+)", href)
    return match.group(1) if match else None


def _parse_area_from_title(title_text: str) -> float | None:
    """
    Parse area from listing title like 'Участок, 4.5 сотки' or 'Участок, 0.2 га'.
    Falls back to None if not found.
    """
    sotka_match = _AREA_RE.search(title_text)
    if sotka_match:
        return float(sotka_match.group(1).replace(",", "."))
    ga_match = _AREA_GA_RE.search(title_text)
    if ga_match:
        return round(float(ga_match.group(1).replace(",", ".")) * 100, 2)
    return None


def _parse_html(html: str) -> list[ListingRaw]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    today = date.today()

    for card in soup.select(CARD_SELECTOR):
        try:
            link_el = card.select_one(TITLE_LINK_SELECTOR)
            price_el = card.select_one(PRICE_SELECTOR)
            address_el = card.select_one(ADDRESS_SELECTOR)

            if not all([link_el, price_el]):
                continue

            href = link_el.get("href", "")
            listing_id = _extract_listing_id(href)
            if not listing_id:
                continue

            title_text = link_el.get_text(strip=True)
            price_text = price_el.get_text(strip=True)
            # Price format: "$ 295 000" — strip the per-sotka suffix if present
            price_main = price_text.split("/")[0].strip()
            price = parse_price_usd(price_main)

            if price is None:
                continue

            area = _parse_area_from_title(title_text)

            district_name = "Другой"
            if address_el:
                # Address format: "Бишкек, Матросова, переулок Елецкий"
                # Strip the map-marker icon text and whitespace
                addr_text = address_el.get_text(strip=True)
                # First token before comma is typically city/district
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
