import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "db.sqlite"))
DEAL_THRESHOLD = 0.85   # listings at < 85% of district median are flagged as deals
SCRAPE_HOUR = 3         # 03:00 local time
