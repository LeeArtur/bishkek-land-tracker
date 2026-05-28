import pytest
from datetime import date
from fastapi.testclient import TestClient
from db.models import District, Listing, PriceHistory
from db.session import get_db


def _make_app(db_session):
    from main import app
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


@pytest.fixture
def client(db):
    district = db.query(District).filter_by(name="Ленинский").first()
    listing = Listing(
        external_id="house.kg:100",
        source="house.kg",
        title="Тестовый участок",
        district_id=district.id,
        area_sotka=8.0,
        current_price_usd=12000.0,
        price_per_sotka=1500.0,
        url="https://house.kg/100",
        first_seen=date(2026, 5, 1),
        last_seen=date(2026, 5, 28),
        is_active=True,
    )
    db.add(listing)
    db.flush()
    db.add(PriceHistory(
        listing_id=listing.id, price_usd=12000.0,
        price_per_sotka=1500.0, recorded_at=date(2026, 5, 28), change_pct=None
    ))
    db.commit()
    return _make_app(db)


def test_get_districts_returns_list(client):
    resp = client.get("/districts")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = [d["name"] for d in data]
    assert "Ленинский" in names


def test_get_listings_returns_active(client):
    resp = client.get("/listings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["external_id"] == "house.kg:100"


def test_get_listings_filter_by_nonexistent_district(client):
    resp = client.get("/listings?district_id=999")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_listing_history(client, db):
    listing = db.query(Listing).filter_by(external_id="house.kg:100").first()
    resp = client.get(f"/listings/{listing.id}/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["price_usd"] == 12000.0
