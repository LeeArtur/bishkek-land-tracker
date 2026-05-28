from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DB_PATH
from db.models import create_tables

_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            connect_args={"check_same_thread": False},
        )
        create_tables(_engine)
        _SessionLocal = sessionmaker(bind=_engine)
    return _engine


def get_db():
    db = _SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
