from datetime import date, timedelta
from fastapi.testclient import TestClient
from db.models import District, Listing, PriceHistory
from db.session import get_db


def test_get_trends_returns_time_series(db):
    from main import app
    app.dependency_overrides[get_db] = lambda: db

    district = db.query(District).filter_by(name="Октябрьский").first()
    listing = Listing(
        external_id="h:trend1", source="house.kg", title="T",
        district_id=district.id, area_sotka=10.0,
        current_price_usd=20000.0, price_per_sotka=2000.0,
        url="https://house.kg/t1",
        first_seen=date(2026, 4, 1), last_seen=date(2026, 5, 28), is_active=True,
    )
    db.add(listing)
    db.flush()
    for i in range(3):
        db.add(PriceHistory(
            listing_id=listing.id,
            price_usd=20000.0 + i * 1000,
            price_per_sotka=2000.0 + i * 100,
            recorded_at=date(2026, 5, 1) + timedelta(days=i * 10),
            change_pct=None if i == 0 else 5.0,
        ))
    db.commit()

    client = TestClient(app)
    resp = client.get("/trends?days=60")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "date" in data[0]
    assert "district_name" in data[0]
    assert "median_price_per_sotka" in data[0]
