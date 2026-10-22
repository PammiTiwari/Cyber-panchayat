from conftest import auth_header
from helpers import subscribe


def test_subscribe_then_status_reflects_active(client, citizen_token, app):
    resp = subscribe(client, citizen_token)
    assert resp.status_code == 201
    me = client.get("/api/subscriptions/me", headers=auth_header(citizen_token)).get_json()
    assert me["subscribed"] is True

    from apps.models import Subscription
    with app.app_context():
        row = Subscription.query.filter_by(citizen_id=me["subscription"]["citizen_id"]).first()
        assert row is not None
        assert row.status == "active"


def test_double_subscribe_rejected(client, citizen_token, app):
    subscribe(client, citizen_token)
    resp = subscribe(client, citizen_token)
    assert resp.status_code == 400

    from apps.models import Subscription
    me = client.get("/api/subscriptions/me", headers=auth_header(citizen_token)).get_json()
    with app.app_context():
        assert Subscription.query.filter_by(citizen_id=me["subscription"]["citizen_id"]).count() == 1


def test_staff_and_admin_never_gated_by_subscription(client, staff_token):
    resp = client.post("/api/requests", headers=auth_header(staff_token), json={
        "category": "road", "description": "x", "address": "y",
    })
    assert resp.status_code == 403
    assert "subscription" not in (resp.get_json().get("message") or "").lower()
