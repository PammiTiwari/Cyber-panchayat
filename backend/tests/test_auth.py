from conftest import auth_header


def test_register_creates_a_citizen(client, app):
    resp = client.post("/api/auth/register", json={
        "name": "Amit Sharma", "email": "amit@test.com", "password": "Citizen@123",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["role"] == "citizen"
    assert "token" in body

    from apps.models import User
    with app.app_context():
        user = User.query.filter_by(email="amit@test.com").first()
        assert user is not None
        assert user.role == "citizen"
        assert user.check_password("Citizen@123")


def test_register_duplicate_email_rejected(client):
    payload = {"name": "Amit Sharma", "email": "amit@test.com", "password": "Citizen@123"}
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_register_rejects_name_with_digits(client):
    resp = client.post("/api/auth/register", json={
        "name": "Amit123", "email": "amit2@test.com", "password": "Citizen@123",
    })
    assert resp.status_code == 400


def test_register_rejects_short_password(client):
    resp = client.post("/api/auth/register", json={
        "name": "Amit Sharma", "email": "amit3@test.com", "password": "abc",
    })
    assert resp.status_code == 400


def test_login_wrong_password_rejected(client, citizen_token):
    resp = client.post("/api/auth/login", json={"email": "citizen@test.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_a_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, citizen_token):
    resp = client.get("/api/auth/me", headers=auth_header(citizen_token))
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "citizen@test.com"


def test_change_password_wrong_current_rejected(client, citizen_token):
    resp = client.put("/api/auth/change-password", headers=auth_header(citizen_token), json={
        "current_password": "not-the-real-one", "new_password": "NewPass@123",
    })
    assert resp.status_code == 400


def test_change_password_then_login_with_new_one(client, citizen_token, app):
    client.put("/api/auth/change-password", headers=auth_header(citizen_token), json={
        "current_password": "Citizen@123", "new_password": "NewPass@123",
    })
    resp = client.post("/api/auth/login", json={"email": "citizen@test.com", "password": "NewPass@123"})
    assert resp.status_code == 200

    from apps.models import User
    with app.app_context():
        user = User.query.filter_by(email="citizen@test.com").first()
        assert user.check_password("NewPass@123")
        assert not user.check_password("Citizen@123")
