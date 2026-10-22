from conftest import auth_header
from helpers import subscribe


def test_filing_a_complaint_without_subscription_is_blocked(client, citizen_token):
    resp = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole on main road", "address": "MG Road",
    })
    assert resp.status_code == 403


def test_filing_a_complaint_with_subscription_succeeds(client, citizen_token, app):
    subscribe(client, citizen_token)
    resp = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole on main road", "address": "MG Road",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "pending"
    assert body["department"] == "Road Maintenance"

    from apps.models import ServiceRequest
    from apps import db
    with app.app_context():
        row = db.session.get(ServiceRequest, body["id"])
        assert row is not None
        assert row.description == "Pothole on main road"
        assert row.status == "pending"


def test_filing_a_complaint_with_invalid_category_rejected(client, citizen_token):
    subscribe(client, citizen_token)
    resp = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "not-a-real-category", "description": "x", "address": "y",
    })
    assert resp.status_code == 400


def test_citizen_cannot_view_another_citizens_complaint(client, citizen_token):
    subscribe(client, citizen_token)
    created = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    }).get_json()

    client.post("/api/auth/register", json={
        "name": "Other Citizen", "email": "other@test.com", "password": "Citizen@123",
    })
    other_token = client.post("/api/auth/login", json={
        "email": "other@test.com", "password": "Citizen@123",
    }).get_json()["token"]

    resp = client.get(f"/api/requests/{created['id']}", headers=auth_header(other_token))
    assert resp.status_code == 403


def test_full_complaint_lifecycle_assign_progress_resolve_close(client, admin_token, staff_token, citizen_token, app):
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    }).get_json()

    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]

    assign = client.post("/api/assignments", headers=auth_header(admin_token), json={
        "request_id": sr["id"], "staff_id": staff_id,
    })
    assert assign.status_code == 201
    assert client.get(f"/api/requests/{sr['id']}", headers=auth_header(admin_token)).get_json()["status"] == "assigned"

    prog = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
                       json={"status": "in_progress"})
    assert prog.status_code == 200

    resolved = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
                           json={"status": "resolved", "admin_notes": "Fixed"})
    assert resolved.status_code == 200

    closed = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(citizen_token),
                         json={"status": "closed", "rating": 5, "feedback": "Great work"})
    assert closed.status_code == 200
    body = closed.get_json()
    assert body["status"] == "closed"
    assert body["rating"] == 5

    from apps.models import Assignment, ServiceRequest
    from apps import db
    with app.app_context():
        row = db.session.get(ServiceRequest, sr["id"])
        assert row.status == "closed"
        assert row.rating == 5
        assert row.feedback == "Great work"
        assert Assignment.query.filter_by(request_id=sr["id"], staff_id=staff_id).first() is not None


def test_staff_cannot_jump_straight_to_resolved_status_others_than_allowed(client, admin_token, staff_token, citizen_token):
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    }).get_json()
    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]
    client.post("/api/assignments", headers=auth_header(admin_token), json={
        "request_id": sr["id"], "staff_id": staff_id,
    })
    resp = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
                       json={"status": "pending"})
    assert resp.status_code == 400


def test_citizen_can_only_close_a_resolved_complaint(client, admin_token, staff_token, citizen_token):
    """Reopening was removed — close is the only move a citizen has on a
    resolved complaint, and nothing else may be forced through."""
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    }).get_json()
    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]
    client.post("/api/assignments", headers=auth_header(admin_token), json={
        "request_id": sr["id"], "staff_id": staff_id,
    })
    client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
               json={"status": "resolved"})

    # "reopened" is not a status any more
    gone = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(citizen_token),
                      json={"status": "reopened"})
    assert gone.status_code == 400

    # nor can the citizen push it back into the work queue by another name
    back = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(citizen_token),
                      json={"status": "in_progress"})
    assert back.status_code == 400

    ok = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(citizen_token),
                    json={"status": "closed", "rating": 4})
    assert ok.status_code == 200
    assert ok.get_json()["status"] == "closed"


def test_only_admin_can_reject_a_complaint(client, staff_token, citizen_token):
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Road",
    }).get_json()
    resp = client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
                       json={"status": "rejected", "admin_notes": "Duplicate"})
    assert resp.status_code == 403


def test_similar_complaint_search_ignores_unrelated_complaints_in_the_same_ward(client, citizen_token):
    subscribe(client, citizen_token)
    client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Streetlight pole is bent and leaning dangerously over the footpath",
        "title": "Bent streetlight pole", "address": "MG Road", "ward": "Ward-1",
    })
    resp = client.post("/api/requests/similar", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Large pothole has formed after the recent rain near the market",
        "title": "Pothole near market", "ward": "Ward-1",
    })
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_similar_complaint_search_still_finds_a_genuine_reworded_duplicate(client, citizen_token):
    subscribe(client, citizen_token)
    client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "There is a big dangerous pothole on MG Road near the bus stop",
        "title": "Big pothole on MG Road", "address": "MG Road", "ward": "Ward-1",
    })
    resp = client.post("/api/requests/similar", headers=auth_header(citizen_token), json={
        "category": "road",
        "description": "A deep pothole has formed on MG Road near the bus stop, very dangerous for vehicles",
        "title": "Deep pothole near MG Road causing issues", "ward": "Ward-1",
    })
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1
