from conftest import auth_header


def test_officer_created_with_uppercase_email_can_log_in(client, admin_token, app):
    resp = client.post("/api/officers", headers=auth_header(admin_token), json={
        "name": "Rajesh Kumar", "email": "Rajesh.Kumar@Civic.Gov",
        "password": "Staff@123", "department": "Road Maintenance",
    })
    assert resp.status_code == 201
    assert resp.get_json()["email"] == "rajesh.kumar@civic.gov"

    login = client.post("/api/auth/login", json={
        "email": "Rajesh.Kumar@Civic.Gov", "password": "Staff@123",
    })
    assert login.status_code == 200

    from apps.models import User
    with app.app_context():
        assert User.query.filter_by(email="rajesh.kumar@civic.gov").first() is not None
        assert User.query.filter_by(email="Rajesh.Kumar@Civic.Gov").first() is None


def test_officer_email_uniqueness_is_case_insensitive(client, admin_token, app):
    client.post("/api/officers", headers=auth_header(admin_token), json={
        "name": "Priya Singh", "email": "priya@civic.gov", "password": "Staff@123",
    })
    dup = client.post("/api/officers", headers=auth_header(admin_token), json={
        "name": "Priya S.", "email": "PRIYA@Civic.Gov", "password": "Staff@123",
    })
    assert dup.status_code == 409

    from apps.models import User
    with app.app_context():
        assert User.query.filter_by(email="priya@civic.gov").count() == 1
