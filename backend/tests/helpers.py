import datetime

from conftest import auth_header


def subscribe(client, token):
    return client.post("/api/subscriptions/subscribe", headers=auth_header(token), json={"method": "upi"})


def create_facility(client, admin_token, **overrides):
    payload = {"name": "Community Hall", "facility_type": "hall", "address": "Ward-1",
               "capacity": 100, "fee_per_hour": 200}
    payload.update(overrides)
    return client.post("/api/facilities", headers=auth_header(admin_token), json=payload)


def make_booking(client, citizen_token, facility_id, **overrides):
    payload = {
        "facility_id": facility_id,
        "booking_date": (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
        "start_time": "10:00", "end_time": "12:00", "purpose": "Meeting",
    }
    payload.update(overrides)
    return client.post("/api/bookings", headers=auth_header(citizen_token), json=payload)
