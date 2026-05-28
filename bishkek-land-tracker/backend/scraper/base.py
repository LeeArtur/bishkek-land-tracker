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
    if "га" in text:
        return round(value * 100, 2)
    return value
