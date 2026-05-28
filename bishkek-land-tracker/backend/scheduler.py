from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import sessionmaker
from db.session import get_engine
from scraper.orchestrator import run_scrape
from scraper.house_kg import scrape as scrape_house_kg
from scraper.lalafo_kg import scrape as scrape_lalafo_kg
from scraper.stroka_kg import scrape as scrape_stroka_kg
from scraper.stroika_kg import scrape as scrape_stroika_kg
from scraper.nbkr import fetch_usd_kgs_rate
from db.models import MacroData
from datetime import date
from config import SCRAPE_HOUR

SCRAPERS = [
    ("house.kg", scrape_house_kg),
    ("lalafo", scrape_lalafo_kg),
    ("stroka", scrape_stroka_kg),
    ("stroika", scrape_stroika_kg),
]


def run_nightly_scrape() -> dict:
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        results = run_scrape(db, SCRAPERS)
        rate = fetch_usd_kgs_rate()
        if rate:
            existing = db.query(MacroData).filter_by(
                recorded_at=date.today(), source="nbkr"
            ).first()
            if not existing:
                db.add(MacroData(recorded_at=date.today(), usd_kgs_rate=rate, source="nbkr"))
                db.commit()
        return results
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_nightly_scrape, "cron", hour=SCRAPE_HOUR, minute=0)
    scheduler.start()
    return scheduler
