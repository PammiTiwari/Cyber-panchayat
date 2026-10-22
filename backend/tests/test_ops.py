from conftest import auth_header


def test_health_check_needs_no_auth(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_sqlite_foreign_keys_are_enforced(app):
    from apps import db
    from apps.models import ServiceRequest
    import pytest as _pytest
    from sqlalchemy.exc import IntegrityError

    with app.app_context():
        bad = ServiceRequest(
            citizen_id=99999, category="road", title="x",
            description="x", address="x",
        )
        db.session.add(bad)
        with _pytest.raises(IntegrityError):
            db.session.commit()


def test_concurrent_booking_requests_for_the_same_slot_only_one_succeeds():
    import os
    import tempfile
    import threading
    import datetime
    from apps.config import TestingConfig
    from apps import create_app, db
    from apps.models import User, Role

    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    original_uri = TestingConfig.SQLALCHEMY_DATABASE_URI
    TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    try:
        conc_app = create_app("testing")
        with conc_app.app_context():
            admin = User(name="Admin", email="conc-admin@test.com", role=Role.ADMIN)
            admin.set_password("x")
            db.session.add(admin)
            db.session.commit()

        client_a, client_b = conc_app.test_client(), conc_app.test_client()
        admin_token = client_a.post("/api/auth/login",
                                     json={"email": "conc-admin@test.com", "password": "x"}).get_json()["token"]
        facility = client_a.post("/api/facilities", headers=auth_header(admin_token), json={
            "name": "Hall", "facility_type": "hall", "address": "x", "capacity": 50, "fee_per_hour": 100,
        }).get_json()

        for c, email in ((client_a, "conc1@test.com"), (client_b, "conc2@test.com")):
            c.post("/api/auth/register", json={"name": "Citizen", "email": email, "password": "Citizen@123"})
        token_a = client_a.post("/api/auth/login", json={"email": "conc1@test.com", "password": "Citizen@123"}).get_json()["token"]
        token_b = client_b.post("/api/auth/login", json={"email": "conc2@test.com", "password": "Citizen@123"}).get_json()["token"]

        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        payload = {"facility_id": facility["id"], "booking_date": tomorrow,
                   "start_time": "10:00", "end_time": "12:00", "purpose": "Race condition"}

        results = {}

        def book(c, token, key):
            results[key] = c.post("/api/bookings", headers=auth_header(token), json=payload).status_code

        t1 = threading.Thread(target=book, args=(client_a, token_a, "a"))
        t2 = threading.Thread(target=book, args=(client_b, token_b, "b"))
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert sorted(results.values()) == [201, 409], f"expected one success and one conflict, got {results}"

        from apps.models import Booking
        with conc_app.app_context():
            assert Booking.query.filter_by(facility_id=facility["id"]).count() == 1
    finally:
        TestingConfig.SQLALCHEMY_DATABASE_URI = original_uri
        os.unlink(db_path)


def test_concurrent_upvote_double_click_never_500s():
    import os
    import tempfile
    import threading
    from apps.config import TestingConfig
    from apps import create_app, db
    from apps.models import User, Role

    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    original_uri = TestingConfig.SQLALCHEMY_DATABASE_URI
    TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    try:
        conc_app = create_app("testing")
        with conc_app.app_context():
            owner = User(name="Owner", email="upvote-owner@test.com", role=Role.CITIZEN)
            owner.set_password("x")
            voter = User(name="Voter", email="upvote-voter@test.com", role=Role.CITIZEN)
            voter.set_password("x")
            db.session.add_all([owner, voter])
            db.session.commit()

        client_owner, client_voter_a, client_voter_b = conc_app.test_client(), conc_app.test_client(), conc_app.test_client()
        owner_token = client_owner.post("/api/auth/login", json={"email": "upvote-owner@test.com", "password": "x"}).get_json()["token"]
        voter_token = client_voter_a.post("/api/auth/login", json={"email": "upvote-voter@test.com", "password": "x"}).get_json()["token"]

        client_owner.post("/api/subscriptions/subscribe", headers=auth_header(owner_token), json={"method": "upi"})
        sr = client_owner.post("/api/requests", headers=auth_header(owner_token), json={
            "category": "road", "description": "Pothole", "address": "MG Road",
        }).get_json()

        results = {}

        def upvote(c, token, key):
            results[key] = c.post(f"/api/requests/{sr['id']}/upvote", headers=auth_header(token)).status_code

        t1 = threading.Thread(target=upvote, args=(client_voter_a, voter_token, "a"))
        t2 = threading.Thread(target=upvote, args=(client_voter_b, voter_token, "b"))
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert list(results.values()) == [200, 200], f"expected both calls to succeed cleanly, got {results}"
        from apps.models import ComplaintUpvote
        with conc_app.app_context():
            assert ComplaintUpvote.query.filter_by(request_id=sr["id"]).count() == 1
    finally:
        TestingConfig.SQLALCHEMY_DATABASE_URI = original_uri
        os.unlink(db_path)


def test_login_rate_limited_after_repeated_attempts():
    from apps.config import TestingConfig
    from apps import create_app

    original = TestingConfig.RATELIMIT_ENABLED
    TestingConfig.RATELIMIT_ENABLED = True
    try:
        rl_app = create_app("testing")
        local_client = rl_app.test_client()
        for _ in range(10):
            local_client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "wrong"})
        blocked = local_client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "wrong"})
        assert blocked.status_code == 429
    finally:
        TestingConfig.RATELIMIT_ENABLED = original


def test_concurrent_post_like_double_click_never_500s():
    import os
    import tempfile
    import threading
    from apps.config import TestingConfig
    from apps import create_app, db
    from apps.models import User, Role

    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    original_uri = TestingConfig.SQLALCHEMY_DATABASE_URI
    TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    try:
        conc_app = create_app("testing")
        with conc_app.app_context():
            author = User(name="Author", email="post-author@test.com", role=Role.CITIZEN)
            author.set_password("x")
            liker = User(name="Liker", email="post-liker@test.com", role=Role.CITIZEN)
            liker.set_password("x")
            db.session.add_all([author, liker])
            db.session.commit()

        client_author, client_a, client_b = conc_app.test_client(), conc_app.test_client(), conc_app.test_client()
        author_token = client_author.post("/api/auth/login", json={"email": "post-author@test.com", "password": "x"}).get_json()["token"]
        liker_token = client_a.post("/api/auth/login", json={"email": "post-liker@test.com", "password": "x"}).get_json()["token"]

        post = client_author.post("/api/posts", headers=auth_header(author_token), json={"content": "Test post"}).get_json()

        results = {}

        def like(c, token, key):
            results[key] = c.post(f"/api/posts/{post['id']}/like", headers=auth_header(token)).status_code

        t1 = threading.Thread(target=like, args=(client_a, liker_token, "a"))
        t2 = threading.Thread(target=like, args=(client_b, liker_token, "b"))
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert list(results.values()) == [200, 200], f"expected both calls to succeed cleanly, got {results}"

        from apps.models import PostLike
        with conc_app.app_context():
            assert PostLike.query.filter_by(post_id=post["id"]).count() == 1
    finally:
        TestingConfig.SQLALCHEMY_DATABASE_URI = original_uri
        os.unlink(db_path)


def test_concurrent_registration_with_same_email_never_500s():
    import os
    import tempfile
    import threading
    from apps.config import TestingConfig
    from apps import create_app

    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    original_uri = TestingConfig.SQLALCHEMY_DATABASE_URI
    TestingConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    try:
        conc_app = create_app("testing")
        client_a, client_b = conc_app.test_client(), conc_app.test_client()
        payload = {"name": "Race Citizen", "email": "race@test.com", "password": "Citizen@123"}

        results = {}

        def register(c, key):
            results[key] = c.post("/api/auth/register", json=payload).status_code

        t1 = threading.Thread(target=register, args=(client_a, "a"))
        t2 = threading.Thread(target=register, args=(client_b, "b"))
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert sorted(results.values()) == [201, 409], f"expected one success and one conflict, got {results}"

        from apps.models import User
        with conc_app.app_context():
            assert User.query.filter_by(email="race@test.com").count() == 1
    finally:
        TestingConfig.SQLALCHEMY_DATABASE_URI = original_uri
        os.unlink(db_path)
