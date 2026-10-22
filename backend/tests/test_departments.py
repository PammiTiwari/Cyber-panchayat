from conftest import auth_header


def test_department_with_nonexistent_officer_rejected_cleanly(client, admin_token):
    resp = client.post("/api/departments", headers=auth_header(admin_token),
                        json={"name": "Ghost Dept", "officer_incharge_id": 999999})
    assert resp.status_code == 400


def test_department_officer_must_be_staff_not_citizen(client, admin_token, citizen_token):
    citizen_id = client.get("/api/auth/me", headers=auth_header(citizen_token)).get_json()["id"]
    resp = client.post("/api/departments", headers=auth_header(admin_token),
                        json={"name": "Some Dept", "officer_incharge_id": citizen_id})
    assert resp.status_code == 400


def test_department_with_valid_staff_officer_succeeds(client, admin_token, staff_token, app):
    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]
    resp = client.post("/api/departments", headers=auth_header(admin_token),
                        json={"name": "Real Dept", "officer_incharge_id": staff_id})
    assert resp.status_code == 201
    assert resp.get_json()["officer_incharge_id"] == staff_id

    from apps.models import Department
    with app.app_context():
        row = Department.query.filter_by(name="Real Dept").first()
        assert row is not None
        assert row.officer_incharge_id == staff_id
