from datetime import date
from fastapi.testclient import TestClient
from db.models import District, Listing
from db.session import get_db


def test_recommendations_returns_below_median_listings(db):
    from main import app
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    district = db.query(District).filter_by(name="Ленинский").first()
    district.median_price_per_sotka = 2000.0
    db.commit()

    cheap = Listing(
        external_id="h:cheap", source="house.kg", title="Cheap",
        district_id=district.id, area_sotka=8.0,
        current_price_usd=12000.0, price_per_sotka=1500.0,
        url="https://house.kg/cheap",
        first_seen=date(2026, 5, 28), last_seen=date(2026, 5, 28), is_active=True,
    )
    expensive = Listing(
        external_id="h:exp", source="house.kg", title="Expensive",
        district_id=district.id, area_sotka=8.0,
        current_price_usd=17600.0, price_per_sotka=2200.0,
        url="https://house.kg/exp",
        first_seen=date(2026, 5, 28), last_seen=date(2026, 5, 28), is_active=True,
    )
    db.add_all([cheap, expensive])
    db.commit()

    resp = client.get("/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["external_id"] == "h:cheap"
    assert "discount_pct" in data[0]
