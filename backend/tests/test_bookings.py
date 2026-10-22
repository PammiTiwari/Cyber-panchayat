from conftest import auth_header
from helpers import create_facility, make_booking


def test_booking_double_slot_rejected(client, admin_token, citizen_token, app):
    facility = create_facility(client, admin_token).get_json()
    first = make_booking(client, citizen_token, facility["id"])
    assert first.status_code == 201
    second = make_booking(client, citizen_token, facility["id"])
    assert second.status_code == 409

    from apps.models import Booking
    with app.app_context():
        assert Booking.query.filter_by(facility_id=facility["id"]).count() == 1


def test_booking_over_capacity_rejected(client, admin_token, citizen_token):
    facility = create_facility(client, admin_token, capacity=5).get_json()
    resp = make_booking(client, citizen_token, facility["id"], attendees=6)
    assert resp.status_code == 400


def test_citizen_can_cancel_own_pending_booking(client, admin_token, citizen_token, app):
    facility = create_facility(client, admin_token).get_json()
    booking = make_booking(client, citizen_token, facility["id"]).get_json()
    resp = client.delete(f"/api/bookings/{booking['id']}", headers=auth_header(citizen_token))
    assert resp.status_code == 200
    updated = client.get(f"/api/bookings/{booking['id']}", headers=auth_header(citizen_token)).get_json()
    assert updated["status"] == "cancelled"
    assert updated["cancelled_by"] == "citizen"

    from apps.models import Booking
    from apps import db
    with app.app_context():
        row = db.session.get(Booking, booking["id"])
        assert row.status == "cancelled"
        assert row.cancelled_by == "citizen"


def test_admin_cannot_use_the_citizen_self_cancel_endpoint(client, admin_token, citizen_token):
    facility = create_facility(client, admin_token).get_json()
    booking = make_booking(client, citizen_token, facility["id"]).get_json()
    resp = client.delete(f"/api/bookings/{booking['id']}", headers=auth_header(admin_token))
    assert resp.status_code == 403


def test_paid_booking_cannot_be_self_cancelled(client, admin_token, citizen_token, app):
    facility = create_facility(client, admin_token).get_json()
    booking = make_booking(client, citizen_token, facility["id"]).get_json()
    payment_id = booking["payment"]["id"]
    client.put(f"/api/bookings/{booking['id']}/status", headers=auth_header(admin_token),
               json={"status": "confirmed"})
    client.post(f"/api/payments/{payment_id}/pay", headers=auth_header(citizen_token), json={"method": "upi"})

    resp = client.delete(f"/api/bookings/{booking['id']}", headers=auth_header(citizen_token))
    assert resp.status_code == 400

    refund = client.put(f"/api/bookings/{booking['id']}/request-refund", headers=auth_header(citizen_token),
                         json={"reason": "Change of plans"})
    assert refund.status_code == 200
    assert refund.get_json()["payment"]["status"] == "refund_requested"

    from apps.models import Booking, Payment
    from apps import db
    with app.app_context():
        assert db.session.get(Booking, booking["id"]).status != "cancelled"
        assert db.session.get(Payment, payment_id).status == "refund_requested"
        assert db.session.get(Payment, payment_id).refund_request_reason == "Change of plans"
