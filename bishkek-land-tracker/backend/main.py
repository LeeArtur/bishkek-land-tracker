import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.session import get_engine
from db.seed import seed_districts
from sqlalchemy.orm import sessionmaker
from api import districts, listings, trends, recommendations, macro, scrape

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    with sessionmaker(bind=engine)() as db:
        seed_districts(db)
    yield


app = FastAPI(title="Bishkek Land Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(districts.router)
app.include_router(listings.router)
app.include_router(trends.router)
app.include_router(recommendations.router)
app.include_router(macro.router)
app.include_router(scrape.router)
