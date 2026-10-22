from conftest import auth_header
from helpers import subscribe


def test_disabled_account_cannot_act_on_an_existing_token(client, admin_token, staff_token, citizen_token, app):
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Marg",
    }).get_json()
    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]
    client.post("/api/assignments", headers=auth_header(admin_token),
                json={"request_id": sr["id"], "staff_id": staff_id})

    assert client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
                      json={"status": "in_progress"}).status_code == 200

    client.delete(f"/api/officers/{staff_id}", headers=auth_header(admin_token))

    from apps.models import User
    from apps import db
    with app.app_context():
        assert db.session.get(User, staff_id).is_active is False

    assert client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
                      json={"status": "resolved"}).status_code == 403
    assert client.get("/api/auth/me", headers=auth_header(staff_token)).status_code == 403

    client.put(f"/api/officers/{staff_id}", headers=auth_header(admin_token), json={"is_active": True})
    assert client.get("/api/auth/me", headers=auth_header(staff_token)).status_code == 200
    with app.app_context():
        assert db.session.get(User, staff_id).is_active is True


def test_department_with_officers_cannot_be_deleted(client, admin_token, staff_token, app):
    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]
    dept = client.post("/api/departments", headers=auth_header(admin_token), json={
        "name": "Road Maintenance", "officer_incharge_id": staff_id,
    }).get_json()

    blocked = client.delete(f"/api/departments/{dept['id']}", headers=auth_header(admin_token))
    assert blocked.status_code == 400
    assert "officer" in blocked.get_json()["message"].lower()

    from apps.models import Department
    from apps import db
    with app.app_context():
        assert db.session.get(Department, dept["id"]) is not None

    client.put(f"/api/officers/{staff_id}", headers=auth_header(admin_token),
               json={"department": "Parks & Public Spaces"})
    assert client.delete(f"/api/departments/{dept['id']}", headers=auth_header(admin_token)).status_code == 200
    with app.app_context():
        assert db.session.get(Department, dept["id"]) is None


def test_finished_complaints_cannot_be_upvoted(client, admin_token, staff_token, citizen_token, app):
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Marg",
    }).get_json()

    client.post("/api/auth/register", json={
        "name": "Other Citizen", "email": "other@test.com", "password": "Citizen@123",
    })
    other = client.post("/api/auth/login", json={
        "email": "other@test.com", "password": "Citizen@123",
    }).get_json()["token"]

    assert client.post(f"/api/requests/{sr['id']}/upvote", headers=auth_header(other)).status_code == 200

    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]
    client.post("/api/assignments", headers=auth_header(admin_token),
                json={"request_id": sr["id"], "staff_id": staff_id})
    client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
               json={"status": "resolved"})

    off = client.post(f"/api/requests/{sr['id']}/upvote", headers=auth_header(other))
    assert off.status_code == 200
    assert off.get_json()["upvoted"] is False

    again = client.post(f"/api/requests/{sr['id']}/upvote", headers=auth_header(other))
    assert again.status_code == 400
    assert "resolved" in again.get_json()["message"]

    from apps.models import ComplaintUpvote
    with app.app_context():
        assert ComplaintUpvote.query.filter_by(request_id=sr["id"]).count() == 0


def test_rejected_complaints_cannot_be_upvoted(client, admin_token, citizen_token):
    subscribe(client, citizen_token)
    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Marg",
    }).get_json()
    client.post("/api/auth/register", json={
        "name": "Third Citizen", "email": "third@test.com", "password": "Citizen@123",
    })
    other = client.post("/api/auth/login", json={
        "email": "third@test.com", "password": "Citizen@123",
    }).get_json()["token"]

    client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(admin_token),
               json={"status": "rejected", "admin_notes": "Duplicate report"})

    resp = client.post(f"/api/requests/{sr['id']}/upvote", headers=auth_header(other))
    assert resp.status_code == 400
