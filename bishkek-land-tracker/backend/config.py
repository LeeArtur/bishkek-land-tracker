import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # fallback to SQLite for local dev without .env
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{DATA_DIR / 'db.sqlite'}"
DEAL_THRESHOLD = 0.85   # listings at < 85% of district median are flagged as deals
SCRAPE_HOUR = 3         # 03:00 local time

# Keywords in listing titles that indicate non-residential land (industrial/agricultural).
# Listings matching any of these are excluded from recommendations.
_NON_RESIDENTIAL_KEYWORDS = [
    "производств", "сельхоз", "с/х", "фермер", "кфх",
    "коммерч", "под завод", "промышленн", "под склад",
    "под базу", "производственная", "животновод",
]

def is_residential(title: str) -> bool:
    """Return False if the listing title indicates non-residential/agricultural land."""
    lower = title.lower()
    return not any(kw in lower for kw in _NON_RESIDENTIAL_KEYWORDS)
