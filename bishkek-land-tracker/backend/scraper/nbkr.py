import requests
import xml.etree.ElementTree as ET

NBKR_XML_URL = "https://www.nbkr.kg/XML/daily.xml"


def fetch_usd_kgs_rate() -> float | None:
    """
    Fetches the current USD/KGS rate from NBKR's daily XML feed.
    Returns the rate as a float, or None on failure.
    """
    try:
        resp = requests.get(NBKR_XML_URL, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        for currency in root.findall(".//Currency"):
            if currency.get("ISOCode") == "USD":
                value_el = currency.find("Value")
                if value_el is not None and value_el.text:
                    return float(value_el.text.replace(",", "."))
        return None
    except Exception:
        return None
