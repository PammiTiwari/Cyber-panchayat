from conftest import auth_header
from helpers import create_facility, make_booking


def test_only_admin_can_create_a_facility(client, citizen_token):
    resp = create_facility(client, citizen_token)
    assert resp.status_code == 403


def test_facility_fee_below_minimum_rejected(client, admin_token):
    resp = create_facility(client, admin_token, fee_per_hour=10)
    assert resp.status_code == 400


def test_facility_favorite_toggle(client, admin_token, citizen_token, app):
    facility = create_facility(client, admin_token).get_json()

    fav_on = client.post("/api/facilities/favorites", headers=auth_header(citizen_token),
                          json={"facility_id": facility["id"]})
    assert fav_on.status_code == 200
    assert fav_on.get_json()["favourited"] is True
    assert facility["id"] in client.get("/api/facilities/favorites", headers=auth_header(citizen_token)).get_json()

    from apps.models import FacilityFavorite
    with app.app_context():
        assert FacilityFavorite.query.filter_by(facility_id=facility["id"]).first() is not None

    fav_off = client.post("/api/facilities/favorites", headers=auth_header(citizen_token),
                           json={"facility_id": facility["id"]})
    assert fav_off.get_json()["favourited"] is False
    assert facility["id"] not in client.get("/api/facilities/favorites", headers=auth_header(citizen_token)).get_json()

    with app.app_context():
        assert FacilityFavorite.query.filter_by(facility_id=facility["id"]).first() is None


def test_favorite_unknown_facility_returns_404(client, citizen_token):
    resp = client.post("/api/facilities/favorites", headers=auth_header(citizen_token), json={"facility_id": 9999})
    assert resp.status_code == 404


def test_cannot_rate_a_facility_without_a_completed_booking(client, admin_token, citizen_token):
    facility = create_facility(client, admin_token).get_json()
    resp = client.post(f"/api/facilities/{facility['id']}/ratings", headers=auth_header(citizen_token),
                        json={"rating": 5})
    assert resp.status_code == 400


def test_rating_after_completed_booking_ties_to_that_booking(client, admin_token, citizen_token, app):
    facility = create_facility(client, admin_token).get_json()
    booking = make_booking(client, citizen_token, facility["id"]).get_json()
    client.put(f"/api/bookings/{booking['id']}/status", headers=auth_header(admin_token), json={"status": "confirmed"})
    client.post(f"/api/payments/{booking['payment']['id']}/pay", headers=auth_header(citizen_token), json={"method": "upi"})
    client.put(f"/api/bookings/{booking['id']}/status", headers=auth_header(admin_token), json={"status": "completed"})

    resp = client.post(f"/api/facilities/{facility['id']}/ratings", headers=auth_header(citizen_token),
                        json={"rating": 4, "comment": "Good hall"})
    assert resp.status_code == 201
    assert resp.get_json()["booking_id"] == booking["id"]

    from apps.models import FacilityRating
    with app.app_context():
        row = FacilityRating.query.filter_by(facility_id=facility["id"]).first()
        assert row is not None
        assert row.booking_id == booking["id"]
        assert row.rating == 4


def test_favorites_detail_returns_full_records_and_drops_deactivated(client, admin_token, citizen_token, app):
    hall = create_facility(client, admin_token).get_json()
    park = create_facility(client, admin_token, name="Riverside Park", facility_type="park").get_json()
    for f in (hall, park):
        client.post("/api/facilities/favorites", headers=auth_header(citizen_token),
                    json={"facility_id": f["id"]})

    detail = client.get("/api/facilities/favorites/detail", headers=auth_header(citizen_token))
    assert detail.status_code == 200
    body = detail.get_json()
    assert {f["id"] for f in body} == {hall["id"], park["id"]}
    assert {f["name"] for f in body} == {"Community Hall", "Riverside Park"}

    client.put(f"/api/facilities/{hall['id']}", headers=auth_header(admin_token),
               json={"is_active": False})

    after = client.get("/api/facilities/favorites/detail", headers=auth_header(citizen_token)).get_json()
    assert [f["id"] for f in after] == [park["id"]]

    from apps.models import FacilityFavorite
    with app.app_context():
        assert FacilityFavorite.query.filter_by(facility_id=hall["id"]).first() is not None


def test_facility_ratings_summary_reports_average_and_distribution(client, admin_token, citizen_token, app):
    facility = create_facility(client, admin_token).get_json()
    booking = make_booking(client, citizen_token, facility["id"]).get_json()
    client.put(f"/api/bookings/{booking['id']}/status", headers=auth_header(admin_token), json={"status": "confirmed"})
    client.post(f"/api/payments/{booking['payment']['id']}/pay", headers=auth_header(citizen_token), json={"method": "upi"})
    client.put(f"/api/bookings/{booking['id']}/status", headers=auth_header(admin_token), json={"status": "completed"})
    client.post(f"/api/facilities/{facility['id']}/ratings", headers=auth_header(citizen_token),
                json={"rating": 4, "comment": "Good hall"})

    resp = client.get(f"/api/facilities/{facility['id']}/ratings", headers=auth_header(citizen_token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["avg"] == 4.0
    assert body["count"] == 1
    assert body["distribution"]["4"] == 1
    assert len(body["ratings"]) == 1

    from apps.models import FacilityRating
    with app.app_context():
        rows = FacilityRating.query.filter_by(facility_id=facility["id"]).all()
        assert len(rows) == 1
        assert rows[0].rating == 4
