from fastapi import APIRouter, BackgroundTasks
from scheduler import run_nightly_scrape

router = APIRouter()


@router.post("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_nightly_scrape)
    return {"status": "scrape started in background"}
