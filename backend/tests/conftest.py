import pytest

from apps import create_app, db
from apps.models import User, Role


@pytest.fixture
def app():
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_token(app, client):
    with app.app_context():
        admin = User(name="Test Admin", email="admin@test.com", role=Role.ADMIN)
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.commit()
    resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "Admin@123"})
    return resp.get_json()["token"]


@pytest.fixture
def citizen_token(client):
    client.post("/api/auth/register", json={
        "name": "Test Citizen", "email": "citizen@test.com", "password": "Citizen@123",
    })
    resp = client.post("/api/auth/login", json={"email": "citizen@test.com", "password": "Citizen@123"})
    return resp.get_json()["token"]


@pytest.fixture
def staff_token(client, admin_token):
    client.post("/api/officers", json={
        "name": "Test Staff", "email": "staff@test.com", "password": "Staff@123",
        "department": "Road Maintenance",
    }, headers=auth_header(admin_token))
    resp = client.post("/api/auth/login", json={"email": "staff@test.com", "password": "Staff@123"})
    return resp.get_json()["token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}
