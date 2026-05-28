from sqlalchemy.orm import Session
from db.models import District

BISHKEK_DISTRICTS = [
    "Октябрьский",
    "Ленинский",
    "Свердловский",
    "Первомайский",
    "Чуйская область",
    "Другой",
]


def seed_districts(db: Session) -> None:
    for name in BISHKEK_DISTRICTS:
        if not db.query(District).filter_by(name=name).first():
            db.add(District(name=name))
    db.commit()
