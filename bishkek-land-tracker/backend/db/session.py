from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import DB_PATH
from db.models import create_tables

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
        create_tables(_engine)
    return _engine


def get_db():
    SessionLocal = sessionmaker(bind=get_engine())
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
