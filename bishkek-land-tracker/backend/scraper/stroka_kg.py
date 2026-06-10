import asyncio
import json
import re
from datetime import date
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from scraper.base import ListingRaw, parse_price_usd, parse_area_sotka

BASE_URL = "https://stroka.kg"
# Land plots for sale — listings are rendered client-side; Playwright required
SEARCH_URL = "https://stroka.kg/zemelnye-uchastki"
SOURCE = "stroka"

# NOTE (2026-05-28): stroka.kg is a Next.js 13 App Router SPA (Mantine UI).
# The /zemelnye-uchastki listing page renders cards entirely client-side via
# React Suspense — the SSR HTML contains only Skeleton placeholders.
# Playwright is required to wait for actual listing links.
#
# Individual ad pages at /ad/{uuid} DO embed a JSON-LD <script type="application/ld+json">
# Product schema with price and location — no JS required to parse those.
#
# Scrape strategy:
#   1. Playwright loads /zemelnye-uchastki and waits for card links to appear.
#   2. Collect all /ad/{uuid} hrefs from the rendered page.
#   3. For each ad URL: fetch the static HTML and extract the JSON-LD Product record.
#
# The _parse_html() function operates on individual ad-page HTML (static, no JS).

# CSS selector for ad links once the SPA has rendered the search results
AD_LINK_SELECTOR = "a[href^='/ad/']"

# Area pattern in the product name: "Продается участок, 9 сот." or "8,5 га"
_AREA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*со(?:тк|ток|т\.?)", re.IGNORECASE)
_AREA_GA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*га", re.IGNORECASE)


def _extract_listing_id(href: str) -> str | None:
    """Extract UUID from href like /ad/57d74074-408e-4bac-92b3-6bc35ea3c394."""
    match = re.search(r"/ad/([a-f0-9-]{36})", href)
    return match.group(1) if match else None


def _parse_area_from_text(text: str) -> float | None:
    """Parse area from title or description text."""
    sotka_match = _AREA_RE.search(text)
    if sotka_match:
        return float(sotka_match.group(1).replace(",", "."))
    ga_match = _AREA_GA_RE.search(text)
    if ga_match:
        return round(float(ga_match.group(1).replace(",", ".")) * 100, 2)
    return None


def _parse_html(html: str) -> list[ListingRaw]:
    """
    Parse a single stroka.kg ad-page HTML into a list (0 or 1) of ListingRaw.

    Each ad page at /ad/{uuid} embeds a JSON-LD <script type="application/ld+json">
    Product object.  This function finds that block, extracts price/location/area,
    and returns a list so callers can use the same extend() pattern as other scrapers.

    Also handles a page containing multiple ad cards rendered by Playwright
    (not the normal production path, but makes unit-testing with synthetic HTML easy).
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    today = date.today()

    # ── Strategy 1: JSON-LD Product blocks (individual ad pages) ────────────
    for script_tag in soup.find_all("script", {"type": "application/ld+json"}):
        raw = script_tag.get_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if not isinstance(data, dict) or data.get("@type") != "Product":
            continue

        url = data.get("url", "")
        listing_id = _extract_listing_id(url)
        if not listing_id:
            continue

        title = data.get("name", "")
        if not title:
            continue

        offers = data.get("offers", {})
        price_raw = offers.get("price")
        currency = offers.get("priceCurrency", "KGS")

        if price_raw is None:
            continue

        price_str = f"{price_raw} {currency}"
        price = parse_price_usd(price_str)
        if price is None:
            continue

        # Area: first look in additionalProperty (houses/apts have "Площадь": "X м²")
        # Land listings usually have no additionalProperty — area lives in the title.
        area: float | None = None
        for prop in data.get("additionalProperty", []):
            if prop.get("name") in ("Площадь", "Площадь участка", "Площадь земли"):
                val = str(prop.get("value", ""))
                area = _parse_area_from_text(val) or parse_area_sotka(val)
                break
        if area is None:
            area = _parse_area_from_text(title)

        location = data.get("itemLocation", {}).get("address", {})
        district_name = (
            location.get("addressLocality")
            or location.get("addressRegion")
            or "Другой"
        )

        full_url = BASE_URL + "/ad/" + listing_id

        results.append(ListingRaw(
            external_id=f"{SOURCE}:{listing_id}",
            source=SOURCE,
            title=title,
            district_name=district_name,
            area_sotka=area,
            price_usd=price,
            url=full_url,
            scraped_at=today,
        ))

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

        # Step 1: collect ad URLs from the rendered search/listing page
        search_page = await context.new_page()
        page_num = 1
        ad_urls: list[str] = []

        max_pages = 30
        while page_num <= max_pages:
            url = SEARCH_URL + (f"?page={page_num}" if page_num > 1 else "")
            await search_page.goto(url, wait_until="domcontentloaded", timeout=20000)

            # Wait for at least one ad card link to appear
            try:
                await search_page.wait_for_selector(AD_LINK_SELECTOR, timeout=10000)
            except Exception:
                break  # No more pages

            links = await search_page.eval_on_selector_all(
                AD_LINK_SELECTOR,
                "els => els.map(el => el.getAttribute('href'))",
            )
            new_links = [l for l in links if l and "/ad/" in l]
            if not new_links:
                break
            ad_urls.extend(new_links)
            page_num += 1
            await asyncio.sleep(1.5)

        await search_page.close()

        # Step 2: fetch each ad page and parse JSON-LD (static HTML is sufficient)
        ad_page = await context.new_page()
        seen: set[str] = set()
        for href in ad_urls:
            if href in seen:
                continue
            seen.add(href)
            try:
                full_url = BASE_URL + href if href.startswith("/") else href
                await ad_page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
                html = await ad_page.content()
                listings = _parse_html(html)
                results.extend(listings)
                await asyncio.sleep(0.5)
            except Exception:
                continue

        await browser.close()
    return results


def scrape() -> list[ListingRaw]:
    return asyncio.run(_scrape_async())
