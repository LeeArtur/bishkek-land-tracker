import asyncio
import re
from datetime import date
import httpx
from bs4 import BeautifulSoup
from scraper.base import ListingRaw, parse_price_usd

BASE_URL = "https://house.kg"
# Bishkek land plots with красная книга (document=6), Chui region (region=1), Bishkek city (town=2)
SEARCH_URL = "https://house.kg/kupit-uchastok?region=1&town=2&document=6&sort_by=upped_at+desc&page={page}"
SOURCE = "house.kg"
MAX_PAGES = 50
CONCURRENCY = 8  # parallel page fetches

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

_AREA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*со(?:тк|ток|т\.)", re.IGNORECASE)
_AREA_GA_RE = re.compile(r"([\d]+[.,]?[\d]*)\s*га", re.IGNORECASE)


def _extract_listing_id(href: str) -> str | None:
    match = re.search(r"/details/([^/?#]+)", href)
    return match.group(1) if match else None


def _parse_area_from_title(title_text: str) -> float | None:
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

    for card in soup.select("div.listing"):
        try:
            link_el = card.select_one("p.title a")
            price_el = card.select_one(".sep.main .price")
            address_el = card.select_one("div.address")

            if not link_el or not price_el:
                continue

            href = link_el.get("href", "")
            listing_id = _extract_listing_id(href)
            if not listing_id:
                continue

            title_text = link_el.get_text(strip=True)
            price_main = price_el.get_text(strip=True).split("/")[0].strip()
            price = parse_price_usd(price_main)
            if price is None:
                continue

            area = _parse_area_from_title(title_text)

            district_name = "Другой"
            if address_el:
                addr_text = address_el.get_text(strip=True)
                parts = [p.strip() for p in addr_text.split(",")]
                if len(parts) >= 2 and parts[0].lower() in ("бишкек", "bishkek"):
                    district_name = parts[1] or "Бишкек"
                elif parts:
                    district_name = parts[0] or "Другой"

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


async def _fetch_page(client: httpx.AsyncClient, page_num: int) -> list[ListingRaw]:
    url = SEARCH_URL.format(page=page_num)
    r = await client.get(url, timeout=15)
    r.raise_for_status()
    return _parse_html(r.text)


async def _scrape_async() -> list[ListingRaw]:
    # Step 1: fetch page 1 to check how many pages exist
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        first_page = await _fetch_page(client, 1)
        if not first_page:
            return []

        results = list(first_page)
        print(f"house.kg page 1: +{len(first_page)} listings ({len(results)} total)")

        # Step 2: fetch remaining pages in parallel batches
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def fetch_with_sem(page_num: int) -> tuple[int, list[ListingRaw]]:
            async with semaphore:
                listings = await _fetch_page(client, page_num)
                return page_num, listings

        page_num = 2
        while page_num <= MAX_PAGES:
            batch = range(page_num, min(page_num + CONCURRENCY, MAX_PAGES + 1))
            tasks = [fetch_with_sem(p) for p in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            got_any = False
            for item in sorted(batch_results, key=lambda x: x[0] if isinstance(x, tuple) else 0):
                if isinstance(item, Exception):
                    continue
                p, listings = item
                if not listings:
                    continue
                got_any = True
                results.extend(listings)
                print(f"house.kg page {p}: +{len(listings)} listings ({len(results)} total)")

            if not got_any:
                break
            page_num += len(batch)

    return results


def scrape() -> list[ListingRaw]:
    return asyncio.run(_scrape_async())
