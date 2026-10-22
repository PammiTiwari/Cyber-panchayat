from conftest import auth_header
from helpers import create_facility, make_booking, subscribe


def test_category_filter_only_returns_matching_types(client, admin_token, staff_token, citizen_token):
    subscribe(client, citizen_token)
    facility = create_facility(client, admin_token).get_json()
    make_booking(client, citizen_token, facility["id"])

    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    }).get_json()

    all_notifs = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()
    assert all_notifs["total"] >= 2

    bookings_only = client.get("/api/notifications?category=bookings", headers=auth_header(admin_token)).get_json()
    assert bookings_only["total"] >= 1
    assert all(n["notif_type"] == "booking" for n in bookings_only["notifications"])

    payments_only = client.get("/api/notifications?category=payments", headers=auth_header(admin_token)).get_json()
    assert all(n["notif_type"] in ("payment", "refund", "subscription") for n in payments_only["notifications"])
    assert not any(n["notif_type"] == "booking" for n in payments_only["notifications"])


def test_unread_count_ignores_the_active_category_filter(client, admin_token, staff_token, citizen_token):
    subscribe(client, citizen_token)
    facility = create_facility(client, admin_token).get_json()
    make_booking(client, citizen_token, facility["id"])
    client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    })

    full = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()
    narrowed = client.get("/api/notifications?category=bookings", headers=auth_header(admin_token)).get_json()
    assert narrowed["unread_count"] == full["unread_count"]


def test_pagination_limits_page_size_and_reports_total(client, admin_token, citizen_token):
    subscribe(client, citizen_token)
    for i in range(3):
        client.post("/api/requests", headers=auth_header(citizen_token), json={
            "category": "road", "description": f"Pothole {i}", "address": "MG Road",
        })

    page1 = client.get("/api/notifications?page=1&limit=2", headers=auth_header(admin_token)).get_json()
    assert len(page1["notifications"]) == 2
    assert page1["total"] >= 3

    page2 = client.get("/api/notifications?page=2&limit=2", headers=auth_header(admin_token)).get_json()
    assert page1["notifications"][0]["id"] != page2["notifications"][0]["id"]


def test_archive_removes_a_notification(client, admin_token, citizen_token, app):
    subscribe(client, citizen_token)
    client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    })
    before = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()
    target = before["notifications"][0]["id"]

    resp = client.put(f"/api/notifications/{target}/archive", headers=auth_header(admin_token))
    assert resp.status_code == 200

    after = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()
    assert after["total"] == before["total"] - 1
    assert all(n["id"] != target for n in after["notifications"])

    from apps.models import Notification
    from apps import db
    with app.app_context():
        assert db.session.get(Notification, target) is None


def test_cannot_archive_someone_elses_notification(client, admin_token, citizen_token):
    subscribe(client, citizen_token)
    client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    })
    admin_notifs = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()
    target = admin_notifs["notifications"][0]["id"]

    resp = client.put(f"/api/notifications/{target}/archive", headers=auth_header(citizen_token))
    assert resp.status_code == 403


def test_archive_unknown_notification_returns_404(client, admin_token):
    resp = client.put("/api/notifications/999999/archive", headers=auth_header(admin_token))
    assert resp.status_code == 404


def test_clear_all_only_empties_the_callers_own_notifications(client, admin_token, citizen_token, app):
    facility = create_facility(client, admin_token).get_json()
    booking = make_booking(client, citizen_token, facility["id"]).get_json()
    client.put(f"/api/bookings/{booking['id']}/status", headers=auth_header(admin_token), json={"status": "confirmed"})

    assert client.get("/api/notifications", headers=auth_header(citizen_token)).get_json()["total"] >= 1
    admin_before = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["total"]
    assert admin_before >= 1

    resp = client.post("/api/notifications/clear-all", headers=auth_header(citizen_token))
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Cleared"

    assert client.get("/api/notifications", headers=auth_header(citizen_token)).get_json()["total"] == 0
    assert client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["total"] == admin_before

    from apps.models import Notification, User
    with app.app_context():
        citizen = User.query.filter_by(email="citizen@test.com").first()
        admin = User.query.filter_by(email="admin@test.com").first()
        assert Notification.query.filter_by(user_id=citizen.id).count() == 0
        assert Notification.query.filter_by(user_id=admin.id).count() == admin_before
