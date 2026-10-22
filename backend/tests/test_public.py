from conftest import auth_header
from helpers import subscribe


def test_public_track_unknown_complaint_returns_404(client):
    resp = client.get("/api/track?id=CMP9999")
    assert resp.status_code == 404


def test_public_track_finds_a_real_complaint(client, citizen_token):
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    }).get_json()
    resp = client.get(f"/api/track?id={sr['cmp_id']}")
    assert resp.status_code == 200
    assert "citizen_email" not in resp.get_json()


def test_public_track_shows_evidence_photos_for_a_resolved_complaint(client, admin_token, staff_token, citizen_token, app):
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    }).get_json()
    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]
    client.post("/api/assignments", headers=auth_header(admin_token), json={
        "request_id": sr["id"], "staff_id": staff_id,
    })
    resolved = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
                           json={"status": "resolved", "evidence_urls": ["/api/uploads/ev03_crossing_repainted.jpg"]})
    assert resolved.get_json()["evidence_urls"] == ["/api/uploads/ev03_crossing_repainted.jpg"]

    track = client.get(f"/api/track?id={sr['cmp_id']}").get_json()
    assert track["evidence_urls"] == ["/api/uploads/ev03_crossing_repainted.jpg"]

    feed = client.get("/api/requests/community", headers=auth_header(citizen_token)).get_json()
    mine = next(c for c in feed if c["id"] == sr["id"])
    assert mine["evidence_urls"] == ["/api/uploads/ev03_crossing_repainted.jpg"]

    from apps.models import ServiceRequest
    from apps import db
    with app.app_context():
        row = db.session.get(ServiceRequest, sr["id"])
        assert row.evidence_urls == ["/api/uploads/ev03_crossing_repainted.jpg"]
        assert row.status == "resolved"


def test_public_stats_has_no_auth_requirement(client, citizen_token):
    subscribe(client, citizen_token)
    before = client.get("/api/public-stats").get_json()

    client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    })

    resp = client.get("/api/public-stats")
    assert resp.status_code == 200
    body = resp.get_json()

    # The counts are live, not placeholders: filing one complaint moves the total.
    assert body["total_complaints"] == before["total_complaints"] + 1
    assert body["resolved"] == 0
    assert isinstance(body["departments"], int)

    # Aggregate counts only — a logged-out caller must never see per-complaint
    # detail or anyone's contact details from this endpoint.
    assert "complaints" not in body
    assert "citizen_email" not in body


def test_community_feed_is_citywide_not_scoped_to_the_viewers_ward(client, citizen_token):
    client.post("/api/auth/register", json={
        "name": "Ward Two Citizen", "email": "ward2@test.com", "password": "Citizen@123", "ward": "Ward-2",
    })
    ward2_token = client.post("/api/auth/login", json={"email": "ward2@test.com", "password": "Citizen@123"}).get_json()["token"]
    subscribe(client, ward2_token)
    sr = client.post("/api/requests", headers=auth_header(ward2_token), json={
        "category": "road", "description": "Pothole in Ward-2", "address": "Ward-2 Main Road", "ward": "Ward-2",
    }).get_json()

    client.post("/api/auth/register", json={
        "name": "Ward One Citizen", "email": "ward1@test.com", "password": "Citizen@123", "ward": "Ward-1",
    })
    ward1_token = client.post("/api/auth/login", json={"email": "ward1@test.com", "password": "Citizen@123"}).get_json()["token"]

    feed = client.get("/api/requests/community", headers=auth_header(ward1_token)).get_json()
    assert any(c["id"] == sr["id"] for c in feed)
