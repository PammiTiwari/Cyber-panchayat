import os
import uuid
import json
from datetime import datetime, date, time, timezone, timedelta
from flask import request, current_app, send_from_directory
from flask_restful import Resource
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from werkzeug.utils import secure_filename
from rapidfuzz import fuzz
from sqlalchemy.exc import IntegrityError
from . import db, limiter
from .models import (now_ist,
    User, ServiceRequest, Assignment, Facility, Booking, Payment, Notification,
    Post, PostComment, PostLike, ComplaintUpvote, Department, FacilityRating,
    FacilityFavorite, FaqEntry, FaqFeedback,
    Subscription, SubscriptionPayment, SubscriptionEvent,
    Role, RequestStatus, Priority, BookingStatus, PaymentStatus, DEPT_MAP,
    SubscriptionStatus, SUBSCRIPTION_FEE, FaqCategory
)

import re

# ── Error response helper ─────────────────────────────────────────────────────
def error_response(message, error_code, status_code=400):
    """Standardized error response with message, error_code, and status."""
    return {
        "message": message,
        "error_code": error_code,
        "status": status_code
    }, status_code

# ── Input validators (shared) ─────────────────────────────────────────────────
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s.'-]{1,79}$")   # letters/spaces only, no digits
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")                    # 10-digit Indian mobile

def _validate_person(data, require_password=True):
    """Common checks for any human account (register / officer create).
    Returns an error tuple or None."""
    name = (data.get("name") or "").strip()
    if not NAME_RE.match(name):
        return error_response("Please enter a valid name — letters only, numbers are not a name", "INVALID_NAME")
    email = (data.get("email") or "").lower().strip()
    if not EMAIL_RE.match(email):
        return error_response("Please enter a valid email address", "INVALID_EMAIL")
    if require_password and len(data.get("password") or "") < 6:
        return error_response("Password must be at least 6 characters", "PASSWORD_TOO_SHORT")
    phone = (data.get("phone") or "").strip()
    if phone and not PHONE_RE.match(phone):
        return error_response("Phone must be a valid 10-digit mobile number", "INVALID_PHONE")
    return None


# Weighted "how similar overall" scoring for duplicate-complaint detection.
# Category is the only hard filter (a road complaint is never a match for an
# electricity one). Ward and geo-proximity are supporting signals that ADD to
# a combined score built on top of the fuzzy text score — not gates on their
# own — so a strong text match still surfaces even when the ward field
# doesn't match (wards are self-picked and boundaries are fuzzy), while a
# same-ward same-spot report with weak wording can still clear the bar
# because the signals corroborate each other.
# Bug fix: SIMILAR_SCORE_THRESHOLD was 0.45. Measured fuzz.token_set_ratio
# across 28 pairs of genuinely UNRELATED sample complaints (different
# categories of issue, just ordinary sentence phrasing) and got scores
# ranging 0.36-0.57 (median 0.44) from coincidental wording overlap alone
# ("near my house", "has been", etc.) — 39% of those pairs already exceeded
# 0.45 on text alone, before any ward/geo bonus. A real duplicate (same
# issue, reworded) scored ~0.81 in comparison. That means the old threshold
# was silently derailing a large fraction of ordinary, unrelated submissions
# into the duplicate-review panel — and if a citizen didn't notice the
# "proceed anyway" option there, their complaint would sit as an unsaved
# draft (30s autosave) instead of the one they meant to file. 0.65 sits
# cleanly above the unrelated-pairs range and below the real-duplicate
# score, so it only fires on genuine overlap.
SIMILAR_SCORE_THRESHOLD = 0.65   # combined score (0-1) needed to surface as "similar"
WARD_BONUS = 0.2                 # same ward — on its own, below the threshold
GEO_BONUS_MAX = 0.2              # proximity, decaying to 0 by PROXIMITY_M — on its own, also below the threshold
PROXIMITY_M = 300               # metres at which the geo bonus decays to zero

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _delete_unreferenced_uploads(urls):
    """Remove uploaded photos that nothing points at any more.

    Call this *after* committing the delete of whatever owned them, so the
    row being removed no longer counts as a reference. Without it, deleting a
    complaint or a post left its photos sitting in uploads/ forever.

    Reference-counted rather than deleted outright, because the same file is
    legitimately shared: a community post about an issue reuses the photo
    from the complaint it illustrates, and a citizen can attach a URL that is
    already on another record. Deleting on the first owner's removal would
    leave the others showing a broken image.

    Only ever touches plain filenames inside uploads/, so a crafted URL like
    "/api/uploads/../../apps/api.py" cannot reach anything outside it.
    """
    if not urls:
        return
    upload_folder = os.path.abspath(os.environ.get("UPLOAD_FOLDER") or os.path.join(os.path.dirname(__file__), "..", "uploads"))
    for url in {u for u in urls if u}:
        if "/uploads/" not in url:
            continue
        name = os.path.basename(url.split("?")[0])
        if not name or name in (".", ".."):
            continue
        still_referenced = (
            ServiceRequest.query.filter(ServiceRequest._image_urls.like(f"%{name}%")).count()
            or ServiceRequest.query.filter(ServiceRequest._evidence_urls.like(f"%{name}%")).count()
            or Post.query.filter(Post._image_urls.like(f"%{name}%")).count()
            or Facility.query.filter(Facility._image_urls.like(f"%{name}%")).count()
        )
        if still_referenced:
            continue
        path = os.path.abspath(os.path.join(upload_folder, name))
        if os.path.dirname(path) != upload_folder:
            continue
        try:
            os.remove(path)
        except OSError:
            # Already gone, or never written — nothing left to clean up.
            pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _current_user():
    uid = int(get_jwt_identity())
    return db.session.get(User, uid)


def _require_role(*roles):
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user or user.role not in roles:
        return error_response("Forbidden: insufficient role", "INSUFFICIENT_ROLE", 403)
    return None


def _require_active_subscription(user):
    """Citizen-only paywall: filing a new complaint requires an active Premium
    subscription — the community feed stays free for everyone per the
    original plan. Simple pay-per-month, no auto-renewal — the moment the
    paid month runs out, access stops until they subscribe again. Staff/admin
    are never gated (they don't hold subscriptions). This only blocks *new*
    activity — complaints made while subscribed stay fully valid and visible
    even after the subscription later lapses."""
    if user.role != Role.CITIZEN:
        return None
    sub = Subscription.query.filter_by(citizen_id=user.id, status=SubscriptionStatus.ACTIVE).first()
    if not sub:
        return error_response(f"An active Cyber Panchayat Premium subscription (Rs.{SUBSCRIPTION_FEE:.0f}/month) is required for this action.", "SUBSCRIPTION_REQUIRED", 403)
    # Flips access off the moment the paid period ends — no grace period.
    _sync_subscription_billing(sub)
    if sub.status != SubscriptionStatus.ACTIVE:
        return error_response(f"An active Cyber Panchayat Premium subscription (Rs.{SUBSCRIPTION_FEE:.0f}/month) is required for this action.", "SUBSCRIPTION_EXPIRED", 403)
    return None


# The frontend's Notifications page groups the finer-grained notif_type
# values above into 3 broad tabs — this is the one place that mapping is
# defined, so the tabs and this dict can never drift apart from each other.
NOTIF_CATEGORY_MAP = {
    "complaints": ["request", "status", "warning", "info", "assignment"],
    "bookings": ["booking"],
    "payments": ["payment", "refund", "subscription"],
}


def _notify(user_id, title, message, notif_type="info"):
    n = Notification(user_id=user_id, title=title, message=message, notif_type=notif_type)
    db.session.add(n)


def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def _haversine_m(lat1, lng1, lat2, lng2):
    """Great-circle distance in metres between two lat/lng points."""
    import math
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _geo_score(lat, lng, r_lat, r_lng):
    """0-1, linearly decaying to 0 at PROXIMITY_M — a graded signal rather
    than an in/out cutoff, so "practically the same spot" counts for more
    than "just inside the radius"."""
    if lat is None or lng is None or r_lat is None or r_lng is None:
        return 0.0
    d = _haversine_m(lat, lng, r_lat, r_lng)
    return max(0.0, 1 - d / PROXIMITY_M)


def _find_similar(category, ward, title, description, lat=None, lng=None, limit=5):
    """Open complaints in the same category that look like duplicates. Category
    is the only hard filter here; ward match and geo-proximity are supporting
    signals that add to a combined score on top of the fuzzy text score,
    rather than gating results on their own — see the constants above."""
    # Only genuinely open complaints are worth backing — resolved/closed ones
    # are already done, not a duplicate to "+1". "assigned"/"reassigned" are
    # open too (an officer just hasn't started work yet, or the request is
    # mid-handoff) — only resolved/closed/rejected are excluded.
    q = ServiceRequest.query.filter(
        ServiceRequest.category == category,
        ServiceRequest.status.in_([
            RequestStatus.PENDING, RequestStatus.ASSIGNED, RequestStatus.REASSIGNED,
            RequestStatus.IN_PROGRESS, RequestStatus.ON_HOLD_WEATHER,
        ]),
    )
    candidates = q.order_by(ServiceRequest.created_at.desc()).limit(50).all()
    new_text = f"{title or ''} {description}".strip()
    scored = []
    for r in candidates:
        existing_text = f"{r.title or ''} {r.description or ''}".strip()
        text_score = max(
            fuzz.token_set_ratio(title, r.title or "") if title else 0,
            fuzz.token_set_ratio(new_text, existing_text),
        ) / 100
        ward_score = 1 if (ward and r.ward == ward) else 0
        combined = text_score + WARD_BONUS * ward_score + GEO_BONUS_MAX * _geo_score(lat, lng, r.latitude, r.longitude)
        if combined >= SIMILAR_SCORE_THRESHOLD:
            scored.append((combined, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]


def _parse_time(s):
    return datetime.strptime(s, "%H:%M").time()


def _lock_facility_for_booking(facility_id):
    """Serializes concurrent booking attempts against the same facility so
    the conflict check right after this can't race another request's insert
    — two people hitting "book" on the same visible slot at the same instant
    otherwise both pass the check before either has committed. No schema
    change needed: this is a query-time lock, not a constraint.

    SQLite has no row-level locking, so `with_for_update()` is a silent no-op
    there — BEGIN IMMEDIATE is used instead, which grabs the single
    file-level write lock immediately rather than only at the first write
    statement, so a second concurrent request blocks here until the first
    one commits. On a real multi-user database (Postgres, via DATABASE_URL)
    the row lock below does the equivalent job.
    """
    if db.engine.dialect.name == "sqlite":
        db.session.execute(db.text("BEGIN IMMEDIATE"))
    else:
        db.session.query(Facility).filter_by(id=facility_id).with_for_update().first()


def _booking_conflicts(facility_id, booking_date, start_time, end_time, exclude_id=None):
    q = Booking.query.filter(
        Booking.facility_id == facility_id,
        Booking.booking_date == booking_date,
        Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    )
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)
    return q.first() is not None


def _calculate_fee(facility, start_time, end_time):
    start_dt = datetime.combine(date.today(), start_time)
    end_dt = datetime.combine(date.today(), end_time)
    hours = (end_dt - start_dt).seconds / 3600
    return round(facility.fee_per_hour * hours, 2)


def _add_month(d):
    """Calendar-month add with day-overflow clamped (Jan 31 -> Feb 28)."""
    import calendar
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=min(d.day, 31))
    last_day = calendar.monthrange(d.year, d.month + 1)[1]
    return d.replace(month=d.month + 1, day=min(d.day, last_day))


def _sync_subscription_billing(sub):
    """Simple pay-per-month, no auto-renewal: once the paid period's end date
    passes, access just expires — there's no auto-charge, no manual "cancel"
    step. The citizen subscribes again whenever they want back in, and that
    starts a brand new period from that day. There's no payment-gateway
    webhook or cron job in this app, so this expiry check is brought up to
    date lazily, right before it's read (on /subscriptions/me or the admin
    list) — the same wall-clock date would produce the same result whether
    checked here or by a real scheduler."""
    if sub.status != SubscriptionStatus.ACTIVE:
        return
    today = now_ist().date()
    if sub.next_billing_date <= today:
        sub.status = SubscriptionStatus.CANCELLED
        db.session.add(SubscriptionEvent(subscription_id=sub.id, event_type="expired"))
        db.session.commit()


def _expire_stale_bookings(bookings):
    """Marks bookings whose date has passed while the fee was never paid.

    Same lazy approach as _sync_subscription_billing above: there is no cron
    in this app, so the check is brought up to date right before the rows are
    read. A booking only expires if money was actually owed and never came in
    — a free booking (no payment row) is left alone, since there was nothing
    to pay and the citizen can still mark it complete.

    The unpaid payment is closed off as `cancelled`, exactly as it would be if
    the booking had been cancelled: no money moved either way.
    """
    today = now_ist().date()
    changed = False
    for b in bookings:
        if b.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            continue
        if b.booking_date >= today:
            continue
        if not b.payment or b.payment.status != PaymentStatus.PENDING:
            continue
        b.status = BookingStatus.EXPIRED
        b.payment.status = PaymentStatus.CANCELLED
        changed = True
        _notify(b.citizen_id, "Booking Expired",
                f"{b.facility.name} on {b.booking_date.isoformat()} expired unpaid. "
                f"You were not charged.", "booking")
    if changed:
        db.session.commit()
    return bookings


# ── API Info ───────────────────────────────────────────────────────────────────

class APIInfoResource(Resource):
    def get(self):
        """Public API information endpoint — returns metadata about this API."""
        return {
            "name": "Cyber Panchayat API",
            "version": "1.0.0",
            "status": "operational",
            "description": "Civic services management system API for complaints, facility bookings, and community engagement",
            "documentation": "https://github.com/SakshiAgarwal142/MAY2026-Team-009",
            "endpoints": {
                "auth": ["/auth/register", "/auth/login", "/auth/me", "/auth/change-password"],
                "requests": ["/requests", "/requests/<id>", "/requests/<id>/status", "/requests/<id>/upvote"],
                "facilities": ["/facilities", "/facilities/<id>", "/facilities/<id>/ratings"],
                "bookings": ["/bookings", "/bookings/<id>", "/bookings/<id>/status"],
                "payments": ["/payments", "/payments/<id>/pay"],
                "subscriptions": ["/subscriptions/me", "/subscriptions/subscribe"],
                "notifications": ["/notifications", "/notifications/<id>/read"],
                "admin": ["/admin/users", "/admin/staff", "/departments", "/officers"],
                "public": ["/track", "/public-stats", "/health"],
            },
            "base_url": "http://localhost:5001/api/v1",
        }, 200


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterResource(Resource):
    # A real internet-facing signup form gets hit by bots trying to mass-
    # create accounts; this doesn't stop that outright but slows it to a
    # crawl per source IP.
    decorators = [limiter.limit("10 per hour")]

    def post(self):
        """Public self-registration — always creates a CITIZEN account;
        staff/admin accounts can only be created by an Admin via the
        Officer management flow."""
        data = request.get_json() or {}
        required = ["name", "email", "password"]
        missing = [f for f in required if not str(data.get(f) or "").strip()]
        if missing:
            return {"message": f"Missing fields: {', '.join(missing)}"}, 400

        invalid = _validate_person(data)
        if invalid:
            return invalid

        if User.query.filter_by(email=data["email"].lower().strip()).first():
            return {"message": "Email already registered"}, 409

        # Public self-registration only ever creates citizens — staff/admin
        # accounts must be created by an Admin via the Officer management flow.
        user = User(
            name=data["name"].strip(),
            email=data["email"].lower().strip(),
            role=Role.CITIZEN,
            phone=data.get("phone", ""),
            ward=data.get("ward", ""),
        )
        user.set_password(data["password"])
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            # A double-submitted signup form (fast double-click, or a retried
            # request) racing the check above — without this, the second
            # request 500s instead of getting the same clean 409 the first
            # slower request would have gotten.
            db.session.rollback()
            return {"message": "Email already registered"}, 409
        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
        return {"token": token, "user": user.to_dict()}, 201


class LoginResource(Resource):
    # Login has no account-lockout mechanism, so this is the only thing
    # standing between a real deployment and someone scripting password
    # guesses against a known email — a per-IP cap makes that impractically
    # slow without punishing a genuine user who mistypes their password a
    # few times.
    decorators = [limiter.limit("10 per minute")]

    def post(self):
        """Public. Email+password login. A disabled account gets a clear
        403 rather than the generic 401 an unknown email or wrong password
        gets."""
        data = request.get_json() or {}
        email = data.get("email", "").lower().strip()
        password = data.get("password", "")
        if not email or not password:
            return error_response("Email and password required", "MISSING_CREDENTIALS", 400)

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return error_response("Invalid credentials", "INVALID_CREDENTIALS", 401)
        if not user.is_active:
            return error_response("Account disabled. Contact admin.", "ACCOUNT_DISABLED", 403)

        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
        return {"token": token, "user": user.to_dict()}, 200


class MeResource(Resource):
    @jwt_required()
    def get(self):
        """The signed-in user's own profile."""
        user = _current_user()
        if not user:
            return error_response("User not found", "USER_NOT_FOUND", 404)
        return user.to_dict(), 200

    @jwt_required()
    def put(self):
        """Update the signed-in user's own name/phone/ward — not the
        password (see ChangePasswordResource) or role (admin-only, via
        AdminUserResource)."""
        user = _current_user()
        data = request.get_json() or {}
        if "name" in data and not NAME_RE.match((data["name"] or "").strip()):
            return error_response("Please enter a valid name — letters only, numbers are not a name", "INVALID_NAME")
        if data.get("phone") and not PHONE_RE.match(data["phone"].strip()):
            return error_response("Phone must be a valid 10-digit mobile number", "INVALID_PHONE")
        for field in ["name", "phone", "ward"]:
            if field in data:
                setattr(user, field, data[field].strip() if isinstance(data[field], str) else data[field])
        db.session.commit()
        return user.to_dict(), 200


class ChangePasswordResource(Resource):
    """Self-service password change — separate from MeResource so a wrong
    current password only ever fails this, never the profile fields update."""
    @jwt_required()
    def put(self):
        user = _current_user()
        data = request.get_json() or {}
        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")
        if not user.check_password(current_password):
            return error_response("Current password is incorrect", "PASSWORD_MISMATCH")
        if len(new_password) < 6:
            return error_response("New password must be at least 6 characters", "PASSWORD_TOO_SHORT")
        user.set_password(new_password)
        db.session.commit()
        return {"message": "Password updated"}, 200


# ── Service Requests ──────────────────────────────────────────────────────────

VALID_CATEGORIES = ["complaint", "road", "water", "electricity", "sanitation", "waste", "parks", "maintenance", "other"]

class RequestListResource(Resource):
    @jwt_required()
    def get(self):
        """Role-scoped complaint list: a citizen sees only their own, staff
        see only complaints assigned to them, and admin sees everything.
        Supports status/category/ward/pending_funds filters and an optional
        ?sort=upvotes to surface the most-backed complaints first."""
        user = _current_user()
        status_filter = request.args.get("status")
        category_filter = request.args.get("category")
        ward_filter = request.args.get("ward")
        pending_funds_filter = request.args.get("pending_funds")
        sort_by = request.args.get("sort")  # "upvotes" to surface the most-backed complaints first

        if user.role == Role.CITIZEN:
            q = ServiceRequest.query.filter_by(citizen_id=user.id)
        elif user.role == Role.STAFF:
            q = ServiceRequest.query.join(Assignment).filter(Assignment.staff_id == user.id)
        else:
            q = ServiceRequest.query

        if status_filter:
            q = q.filter_by(status=status_filter)
        if category_filter:
            q = q.filter_by(category=category_filter)
        if ward_filter:
            q = q.filter_by(ward=ward_filter)
        if pending_funds_filter is not None:
            q = q.filter_by(pending_funds=(pending_funds_filter.lower() == "true"))

        requests_list = q.order_by(ServiceRequest.created_at.desc()).all()
        if sort_by == "upvotes":
            requests_list.sort(key=lambda r: r.upvotes.count(), reverse=True)
        return [r.to_dict() for r in requests_list], 200

    @jwt_required()
    def post(self):
        """Citizen-only, requires an active subscription. Files a new
        complaint and notifies every admin."""
        user = _current_user()
        err = _require_role(Role.CITIZEN)
        if err:
            return err
        err = _require_active_subscription(user)
        if err:
            return err

        data = request.get_json() or {}
        required = ["category", "description", "address"]
        missing = [f for f in required if not str(data.get(f) or "").strip()]
        if missing:
            return {"message": f"Missing: {', '.join(missing)}"}, 400

        if data["category"] not in VALID_CATEGORIES:
            return {"message": "Invalid category"}, 400

        priority = data.get("priority", Priority.MEDIUM)
        if priority not in Priority.ALL:
            priority = Priority.MEDIUM

        title = data.get("title") or f"{data['category'].title()} issue at {data['address'][:50]}"

        try:
            lat = float(data["latitude"]) if data.get("latitude") is not None else None
            lng = float(data["longitude"]) if data.get("longitude") is not None else None
        except (TypeError, ValueError):
            lat = lng = None

        sr = ServiceRequest(
            citizen_id=user.id,
            category=data["category"],
            title=title.strip(),
            description=data["description"].strip(),
            address=data["address"].strip(),
            ward=data.get("ward", user.ward or ""),
            latitude=lat,
            longitude=lng,
            priority=priority,
            image_urls=data.get("image_urls") or [],
        )
        db.session.add(sr)

        # notify all admins
        admins = User.query.filter_by(role=Role.ADMIN).all()
        for admin in admins:
            _notify(admin.id, "New Service Request",
                    f"{user.name} submitted a {data['category']} request: {title}", "request")

        db.session.commit()
        return sr.to_dict(), 201


class RequestResource(Resource):
    @jwt_required()
    def get(self, request_id):
        """One complaint's full detail — a citizen only their own, staff
        only if it's assigned to them."""
        user = _current_user()
        sr = db.session.get(ServiceRequest, request_id)
        if not sr:
            return error_response(f"Service request {request_id} not found", "REQUEST_NOT_FOUND", 404)
        if user.role == Role.CITIZEN and sr.citizen_id != user.id:
            return error_response("You do not have access to this request", "REQUEST_ACCESS_DENIED", 403)
        if user.role == Role.STAFF and (not sr.assignment or sr.assignment.staff_id != user.id):
            return error_response("You are not assigned to this request", "REQUEST_NOT_ASSIGNED", 403)
        return sr.to_dict(), 200

    @jwt_required()
    def put(self, request_id):
        """Edit a complaint's own fields — a citizen only while it's still
        pending, staff only if it's assigned to them."""
        user = _current_user()
        sr = db.session.get(ServiceRequest, request_id)
        if not sr:
            return error_response(f"Service request {request_id} not found", "REQUEST_NOT_FOUND", 404)

        if user.role == Role.CITIZEN:
            if sr.citizen_id != user.id:
                return error_response("You do not have access to this request", "REQUEST_ACCESS_DENIED", 403)
            if sr.status not in [RequestStatus.PENDING]:
                return error_response("Cannot edit a request that has been picked up", "REQUEST_NOT_EDITABLE")
        if user.role == Role.STAFF and (not sr.assignment or sr.assignment.staff_id != user.id):
            return error_response("You are not assigned to this request", "REQUEST_NOT_ASSIGNED", 403)

        data = request.get_json() or {}
        if "priority" in data and data["priority"] not in Priority.ALL:
            return error_response("Invalid priority value", "INVALID_PRIORITY")
        for field in ["title", "description", "address"]:
            if field in data and not str(data[field] or "").strip():
                return error_response(f"{field.title()} cannot be blank", "BLANK_FIELD")
        editable = ["title", "description", "address", "ward", "priority", "admin_notes"]
        for field in editable:
            if field in data:
                if user.role == Role.CITIZEN and field == "admin_notes":
                    continue
                setattr(sr, field, data[field].strip() if isinstance(data[field], str) else data[field])

        sr.updated_at = now_ist()
        db.session.commit()
        return sr.to_dict(), 200

    @jwt_required()
    def delete(self, request_id):
        """Delete a complaint — a citizen only their own pending one; admin
        can't delete a resolved/closed one, it's part of the public
        accountability record."""
        user = _current_user()
        sr = db.session.get(ServiceRequest, request_id)
        if not sr:
            return error_response(f"Service request {request_id} not found", "REQUEST_NOT_FOUND", 404)
        if user.role == Role.CITIZEN:
            if sr.citizen_id != user.id or sr.status != RequestStatus.PENDING:
                return error_response("Cannot delete this request", "REQUEST_NOT_DELETABLE", 403)
        elif user.role == Role.STAFF:
            return error_response("Staff members cannot delete requests", "DELETE_NOT_ALLOWED", 403)
        elif user.role == Role.ADMIN and sr.status in [RequestStatus.RESOLVED, RequestStatus.CLOSED]:
            return error_response("Cannot delete a resolved/closed request — it's part of the public accountability record", "REQUEST_IMMUTABLE")

        # Captured before the delete; cleaned up after the commit, once the
        # row is gone and can no longer count as a reference to its own files.
        attached = list(sr.image_urls or []) + list(sr.evidence_urls or [])
        db.session.delete(sr)
        db.session.commit()
        _delete_unreferenced_uploads(attached)
        return {"message": "Request deleted"}, 200


class RequestStatusResource(Resource):
    @jwt_required()
    def put(self, request_id):
        """Transitions a complaint's status — which moves are legal depends
        on the current status and the caller's role (staff progress,
        citizen close/rate, admin assign/reject/hold)."""
        user = _current_user()
        sr = db.session.get(ServiceRequest, request_id)
        if not sr:
            return error_response(f"Service request {request_id} not found", "REQUEST_NOT_FOUND", 404)
        data = request.get_json() or {}
        new_status = data.get("status")

        if not new_status or new_status not in RequestStatus.ALL:
            return error_response(f"Invalid status: {new_status}", "INVALID_STATUS")

        if new_status == RequestStatus.ON_HOLD_WEATHER and user.role != Role.ADMIN:
            return {"message": "Only an admin can place a request on hold"}, 403

        if new_status == RequestStatus.REJECTED:
            if user.role != Role.ADMIN:
                return {"message": "Only an admin can reject a request"}, 403
            if sr.status != RequestStatus.PENDING:
                return {"message": "Only a pending (unassigned) request can be rejected"}, 400
            if not (data.get("admin_notes") or "").strip():
                return {"message": "A reason is required to reject a request"}, 400

        if user.role == Role.CITIZEN:
            if sr.citizen_id != user.id:
                return {"message": "Forbidden"}, 403
            if sr.status != RequestStatus.RESOLVED or new_status != RequestStatus.CLOSED:
                return {"message": "Citizens can only close a resolved request"}, 400
            rating = data.get("rating")
            if rating is not None and (not isinstance(rating, int) or rating < 1 or rating > 5):
                return {"message": "Rating must be an integer from 1 to 5"}, 400

        if user.role == Role.ADMIN:
            # An admin may correct a mistake, but not invent history. A
            # complaint that was never assigned has had no work done on it, so
            # it cannot be declared finished — that produced a timeline with
            # "Resolved" ticked and no officer, no start, no evidence behind it.
            if new_status in (RequestStatus.RESOLVED, RequestStatus.CLOSED) and not sr.assignment:
                return {"message": "Assign this request to an officer before marking it "
                                   "resolved — there is no work behind it otherwise"}, 400
            # Closing is the citizen's last word, including their rating.
            # Pulling it back into the queue is reopening by another name, and
            # reopening was deliberately removed from this app.
            if sr.status == RequestStatus.CLOSED and new_status != RequestStatus.CLOSED:
                return {"message": "The citizen has closed this request — it cannot be "
                                   "moved back"}, 400

        if user.role == Role.STAFF:
            if not sr.assignment or sr.assignment.staff_id != user.id:
                return {"message": "Not your assignment"}, 403
            if sr.status == RequestStatus.CLOSED:
                return {"message": "Citizen has closed this request — it can no longer be changed"}, 400
            if sr.status == RequestStatus.ON_HOLD_WEATHER:
                return {"message": "This request is on hold for weather restrictions — an admin needs to resume it first"}, 400
            if sr.status == RequestStatus.RESOLVED:
                return {"message": "This request is already resolved — no further updates until the citizen closes it"}, 400
            if sr.status == RequestStatus.REJECTED:
                return {"message": "This request was rejected and can no longer be updated"}, 400
            allowed = [RequestStatus.IN_PROGRESS, RequestStatus.RESOLVED]
            if new_status not in allowed:
                return {"message": "Staff can only mark in_progress or resolved"}, 400

        old_status = sr.status
        sr.status = new_status
        if new_status == RequestStatus.IN_PROGRESS and not sr.in_progress_at:
            sr.in_progress_at = now_ist()
        # Each step keeps its own remark so a later status change doesn't erase
        # an earlier one — the citizen timeline shows all of them at once.
        if new_status == RequestStatus.IN_PROGRESS and data.get("admin_notes"):
            sr.in_progress_notes = data["admin_notes"]
        # One entry per in_progress update, each carrying its own timestamp.
        # in_progress_at deliberately stays at the first one — that is when the
        # work started — so without this an officer's later remark was shown
        # under a date it was not written on, and the remark it replaced was
        # gone entirely.
        if new_status == RequestStatus.IN_PROGRESS:
            sr.add_progress_entry(now_ist(), (data.get("admin_notes") or "").strip() or None)
        if new_status == RequestStatus.RESOLVED and data.get("admin_notes"):
            sr.resolved_notes = data["admin_notes"]
        if data.get("admin_notes"):
            sr.admin_notes = data["admin_notes"]
        # Evidence photos are proof-of-completion — only accepted the moment a request is being resolved.
        if data.get("evidence_urls") and new_status == RequestStatus.RESOLVED:
            sr.evidence_urls = data["evidence_urls"]

        if new_status == RequestStatus.ON_HOLD_WEATHER:
            sr.hold_reason = (data.get("hold_reason") or "").strip() or "Work is paused due to weather restrictions and will resume once conditions allow."
        elif old_status == RequestStatus.ON_HOLD_WEATHER:
            sr.hold_reason = None

        if new_status == RequestStatus.CLOSED and user.role == Role.CITIZEN:
            if data.get("rating") is not None:
                sr.rating = data["rating"]
            if data.get("feedback"):
                sr.feedback = data["feedback"].strip()

        # resolved_at is when the work was finished, not when the citizen got
        # round to confirming it. Stamping it again on close overwrote the
        # officer's actual completion time with the closing time, and the
        # citizen's timeline then showed the wrong date for "Resolved".
        if new_status == RequestStatus.RESOLVED and not sr.resolved_at:
            sr.resolved_at = now_ist()
        if new_status in [RequestStatus.RESOLVED, RequestStatus.CLOSED] and sr.assignment \
                and not sr.assignment.completed_at:
            sr.assignment.completed_at = now_ist()

        sr.updated_at = now_ist()

        if new_status == RequestStatus.REJECTED:
            reason = data.get("admin_notes", "").strip()
            msg = f"Your request '{sr.title}' was rejected." + (f" Reason: {reason}" if reason else "")
            _notify(sr.citizen_id, "Request Rejected", msg, "status")
        elif new_status == RequestStatus.ON_HOLD_WEATHER:
            msg = f"Your request '{sr.title}' has been put on hold. {sr.hold_reason}"
            _notify(sr.citizen_id, "Request On Hold — Weather Restrictions", msg, "warning")
            if sr.assignment:
                _notify(sr.assignment.staff_id, "Request On Hold", msg, "warning")
        elif old_status == RequestStatus.ON_HOLD_WEATHER:
            msg = f"Work on your request '{sr.title}' has resumed."
            _notify(sr.citizen_id, "Request Resumed", msg, "info")
            if sr.assignment:
                _notify(sr.assignment.staff_id, "Request Resumed", msg, "info")
        else:
            _notify(sr.citizen_id, "Request Status Updated",
                    f"Your request '{sr.title}' status changed from {old_status} to {new_status}.",
                    "status")

        # Everyone who "+1"'d this complaint backed it as their own issue too —
        # they should hear it's resolved, not just the citizen who filed it.
        if new_status == RequestStatus.RESOLVED and old_status != new_status:
            cmp_id = f"CMP{str(sr.id).zfill(4)}"
            for upvote in ComplaintUpvote.query.filter_by(request_id=sr.id).all():
                if upvote.user_id == sr.citizen_id:
                    continue  # already covered by the notification above
                _notify(upvote.user_id, "A Complaint You Backed Was Resolved",
                        f"{cmp_id} ('{sr.title}'), which you upvoted, has been marked resolved.",
                        "status")

        db.session.commit()
        return sr.to_dict(), 200


class RequestBudgetTagResource(Resource):
    """Admin/ward-member toggle for flagging a verified complaint as 'Pending Funds',
    so it can be compiled into a list for the next budget allocation meeting."""
    @jwt_required()
    def put(self, request_id):
        err = _require_role(Role.ADMIN)
        if err:
            return err
        sr = db.session.get(ServiceRequest, request_id)
        if not sr:
            return {"message": "Not found"}, 404
        data = request.get_json() or {}
        if "pending_funds" not in data:
            return {"message": "Missing: pending_funds"}, 400
        sr.pending_funds = bool(data["pending_funds"])
        sr.updated_at = now_ist()
        db.session.commit()
        return sr.to_dict(), 200


# ── Complaint community visibility & upvotes ──────────────────────────────────

class RequestSimilarResource(Resource):
    """Looks for existing open complaints that might be the same issue, so a
    citizen can upvote/"me too" an existing one instead of filing a duplicate.
    Uses to_public_dict() — this runs before the complaint is even submitted,
    so the citizen is looking at other citizens' complaints; no PII exposure."""
    @jwt_required()
    def post(self):
        user = _current_user()
        data = request.get_json() or {}
        category = data.get("category")
        description = (data.get("description") or "").strip()
        ward = data.get("ward")
        title = (data.get("title") or "").strip()
        if not category or not description:
            return [], 200
        try:
            lat = float(data["latitude"]) if data.get("latitude") is not None else None
            lng = float(data["longitude"]) if data.get("longitude") is not None else None
        except (TypeError, ValueError):
            lat = lng = None
        matches = _find_similar(category, ward, title, description, lat, lng)
        upvoted_ids = {u.request_id for u in ComplaintUpvote.query.filter_by(user_id=user.id)}
        result = []
        for m in matches:
            d = m.to_public_dict()
            # to_public_dict() omits evidence_urls (paired with admin_notes as
            # "internal" there) — but it's resolution-proof photos, not PII, and
            # the frontend's SimilarComplaints card is built to show them.
            d["evidence_urls"] = m.evidence_urls
            d["upvoted_by_me"] = m.id in upvoted_ids
            d["is_own"] = m.citizen_id == user.id
            result.append(d)
        return result, 200


class RequestUpvoteResource(Resource):
    """'Me too' toggle — lets a citizen flag they're facing the same issue
    without filing a duplicate complaint. A citizen can't upvote their own
    complaint — that isn't another person corroborating the issue."""
    @jwt_required()
    def post(self, request_id):
        user = _current_user()
        sr = db.session.get(ServiceRequest, request_id)
        if not sr:
            return {"message": "Not found"}, 404
        if sr.citizen_id == user.id:
            return {"message": "You can't upvote your own complaint"}, 403
        # "Me too" only means something while the issue is still live. The
        # complaints page already hides the button once a request is done,
        # and _find_similar only ever offers open ones to back — but the rule
        # lived only in the UI, so a direct API call could still add votes to
        # a complaint that was already resolved, closed or rejected.
        existing = ComplaintUpvote.query.filter_by(request_id=request_id, user_id=user.id).first()
        if sr.status in (RequestStatus.RESOLVED, RequestStatus.CLOSED, RequestStatus.REJECTED) and not existing:
            return {"message": f"This complaint is already {sr.status} — there's nothing left to back"}, 400
        if existing:
            # Removing a vote stays allowed whatever the status, so a citizen
            # is never stuck with a vote they can't take back.
            db.session.delete(existing)
            db.session.commit()
            return {"upvoted": False, "upvotes_count": ComplaintUpvote.query.filter_by(request_id=request_id).count()}, 200
        db.session.add(ComplaintUpvote(request_id=request_id, user_id=user.id))
        try:
            db.session.commit()
        except IntegrityError:
            # A concurrent double-click (or a retried request) raced us to
            # add the same upvote — same fix as FacilityFavoriteListResource.
            db.session.rollback()
        return {"upvoted": True, "upvotes_count": ComplaintUpvote.query.filter_by(request_id=request_id).count()}, 200


class RequestCommunityResource(Resource):
    """Read-only feed backing the citizen "All Complaints" page — city-wide,
    not scoped to the viewer's ward. AllComplaints.vue already has its own
    "All Wards"/per-ward filter dropdown built for narrowing this down
    client-side (it expects to receive every complaint and filter locally),
    so silently pre-filtering to the viewer's own ward here meant a citizen
    could never actually see complaints from any other ward — even
    explicitly selecting "All Wards" in the UI couldn't undo a restriction
    the backend had already applied before the data ever arrived.
    Uses to_public_dict() — never exposes another citizen's name/email/phone,
    same privacy bar as the public tracking endpoint (see to_public_dict)."""
    @jwt_required()
    def get(self):
        user = _current_user()
        complaints = ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).limit(50).all()
        upvoted_ids = {u.request_id for u in ComplaintUpvote.query.filter_by(user_id=user.id)}
        result = []
        for c in complaints:
            d = c.to_public_dict()
            # See RequestSimilarResource above — evidence_urls is proof-of-completion,
            # not PII, and AllComplaints.vue is built to show it here.
            d["evidence_urls"] = c.evidence_urls
            d["upvoted_by_me"] = c.id in upvoted_ids
            d["is_own"] = c.citizen_id == user.id
            result.append(d)
        return result, 200


# ── Assignments ───────────────────────────────────────────────────────────────

class AssignmentListResource(Resource):
    @jwt_required()
    def get(self):
        """Staff/admin only. Staff see only their own assignments, admin
        sees every assignment."""
        user = _current_user()
        if user.role == Role.CITIZEN:
            return {"message": "Forbidden"}, 403
        if user.role == Role.STAFF:
            assignments = Assignment.query.filter_by(staff_id=user.id).all()
        else:
            assignments = Assignment.query.all()
        return [a.to_dict() for a in assignments], 200

    @jwt_required()
    def post(self):
        """Admin-only. Assigns (or reassigns) a complaint to an active
        staff member and notifies everyone involved."""
        err = _require_role(Role.ADMIN)
        if err:
            return err

        admin = _current_user()
        data = request.get_json() or {}
        required = ["request_id", "staff_id"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return {"message": f"Missing: {', '.join(missing)}"}, 400

        sr = db.session.get(ServiceRequest, data["request_id"])
        if not sr:
            return {"message": "Request not found"}, 404
        if sr.status in [RequestStatus.RESOLVED, RequestStatus.CLOSED, RequestStatus.REJECTED]:
            return {"message": "Cannot assign a completed/closed request"}, 400

        staff = db.session.get(User, data["staff_id"])
        if not staff or staff.role != Role.STAFF:
            return {"message": "Invalid staff member"}, 400
        if not staff.is_active:
            return {"message": "Cannot assign to a deactivated officer"}, 400
        # An admin can deliberately assign across departments to correct a
        # miscategorized complaint — the chosen officer's department then
        # becomes the request's department of record going forward.
        if staff.department != sr.get_department():
            sr.department_override = staff.department

        # Assignment.request_id is unique=True — there is always at most one
        # assignment per request, so a re-assignment must UPDATE that row in
        # place rather than delete-then-insert. SQLAlchemy's unit of work
        # flushes INSERTs before DELETEs in the same commit, so a delete+
        # insert pair against a unique column trips the constraint while
        # both rows briefly coexist (IntegrityError on request_id).
        if sr.assignment:
            prev_staff_id = sr.assignment.staff_id
            assignment = sr.assignment
            assignment.staff_id = staff.id
            assignment.assigned_by = admin.id
            assignment.notes = data.get("notes", "")
            assignment.assigned_at = now_ist()
            assignment.completed_at = None
            sr.status = RequestStatus.REASSIGNED
            # Reassigning hands the request to a different officer — any
            # progress the previous officer logged shouldn't linger and read
            # as if the new officer already started work.
            sr.in_progress_at = None
            sr.in_progress_notes = None
            sr.progress_log = []
            sr.admin_notes = data.get("notes") or f"Reassigned to {staff.name} ({staff.department})"
            sr.updated_at = now_ist()

            if prev_staff_id != staff.id:
                _notify(prev_staff_id, "Request Reassigned",
                        f"Request '{sr.title}' has been reassigned to another officer.", "assignment")
            _notify(staff.id, "New Assignment",
                    f"You've been assigned request: '{sr.title}' (Priority: {sr.priority})", "assignment")
            _notify(sr.citizen_id, "Request Reassigned",
                    f"Your request '{sr.title}' has been reassigned to a different officer.", "status")

            db.session.commit()
            return assignment.to_dict(), 200

        assignment = Assignment(
            request_id=sr.id,
            staff_id=staff.id,
            assigned_by=admin.id,
            notes=data.get("notes", ""),
        )
        db.session.add(assignment)
        sr.status = RequestStatus.ASSIGNED
        sr.admin_notes = data.get("notes") or f"Assigned to {staff.name} ({staff.department})"
        sr.updated_at = now_ist()

        _notify(staff.id, "New Assignment",
                f"You've been assigned request: '{sr.title}' (Priority: {sr.priority})", "assignment")
        _notify(sr.citizen_id, "Request Assigned",
                f"Your request '{sr.title}' has been assigned to a staff member.", "status")

        try:
            db.session.commit()
        except IntegrityError:
            # Two admins assigning the same never-before-assigned request at
            # the same moment both pass the `sr.assignment` check above (it's
            # still None for both); Assignment.request_id is unique, so the
            # second commit trips that constraint instead of creating two
            # assignments for one request.
            db.session.rollback()
            return {"message": "This request was just assigned by someone else — refresh and try again"}, 409
        return assignment.to_dict(), 201


class AssignmentResource(Resource):
    @jwt_required()
    def put(self, assignment_id):
        """Admin-only. Reassigns an existing assignment to a different
        officer and/or updates its notes."""
        err = _require_role(Role.ADMIN)
        if err:
            return err

        assignment = db.session.get(Assignment, assignment_id)
        if not assignment:
            return {"message": "Not found"}, 404
        data = request.get_json() or {}
        if "staff_id" in data:
            staff = db.session.get(User, data["staff_id"])
            if not staff or staff.role != Role.STAFF:
                return {"message": "Invalid staff member"}, 400
            if not staff.is_active:
                return {"message": "Cannot assign to a deactivated officer"}, 400
            if staff.department != assignment.request.get_department():
                assignment.request.department_override = staff.department
            assignment.staff_id = staff.id
        if "notes" in data:
            assignment.notes = data["notes"]
        db.session.commit()
        return assignment.to_dict(), 200


# ── Facilities ────────────────────────────────────────────────────────────────

class FacilityListResource(Resource):
    @jwt_required()
    def get(self):
        """Citizens only see active facilities by default; staff/admin can
        pass ?active=false to include disabled ones too — the same endpoint
        backs both the public browse page and the admin management
        table."""
        active_only = request.args.get("active", "true").lower() == "true"
        user = _current_user()
        q = Facility.query
        if active_only and user.role == Role.CITIZEN:
            q = q.filter_by(is_active=True)
        facilities = q.order_by(Facility.name).all()
        return [f.to_dict() for f in facilities], 200

    @jwt_required()
    def post(self):
        """Admin-only. Creates a new bookable facility."""
        err = _require_role(Role.ADMIN)
        if err:
            return err

        data = request.get_json() or {}
        required = ["name", "facility_type", "address", "capacity"]
        missing = [f for f in required if f not in data]
        if missing:
            return {"message": f"Missing: {', '.join(missing)}"}, 400

        try:
            capacity = int(data["capacity"])
            fee_per_hour = float(data.get("fee_per_hour", 0))
        except (TypeError, ValueError):
            return {"message": "Capacity and fee per hour must be numbers"}, 400
        if capacity < 1 or capacity > 100000:
            return {"message": "Capacity must be between 1 and 100000"}, 400
        if fee_per_hour < 50:
            return {"message": "Fee per hour must be at least ₹50 — facilities can't be listed for free"}, 400
        if not data["name"].strip() or not data["address"].strip():
            return {"message": "Name and address cannot be blank"}, 400

        facility = Facility(
            name=data["name"].strip(),
            facility_type=data["facility_type"].strip(),
            address=data["address"].strip(),
            ward=data.get("ward", ""),
            capacity=capacity,
            description=data.get("description", ""),
            amenities=data.get("amenities", ""),
            fee_per_hour=fee_per_hour,
            image_urls=data.get("image_urls") or [],
        )
        db.session.add(facility)
        db.session.commit()
        return facility.to_dict(), 201


class FacilityResource(Resource):
    @jwt_required()
    def get(self, facility_id):
        """One facility's full detail."""
        f = db.session.get(Facility, facility_id)
        if not f:
            return {"message": "Not found"}, 404
        return f.to_dict(), 200

    @jwt_required()
    def put(self, facility_id):
        """Admin-only. Updates a facility's fields."""
        err = _require_role(Role.ADMIN)
        if err:
            return err

        f = db.session.get(Facility, facility_id)
        if not f:
            return {"message": "Not found"}, 404
        data = request.get_json() or {}
        if "capacity" in data:
            try:
                data["capacity"] = int(data["capacity"])
            except (TypeError, ValueError):
                return {"message": "Capacity must be a number"}, 400
            if data["capacity"] < 1 or data["capacity"] > 100000:
                return {"message": "Capacity must be between 1 and 100000"}, 400
        if "fee_per_hour" in data:
            try:
                data["fee_per_hour"] = float(data["fee_per_hour"])
            except (TypeError, ValueError):
                return {"message": "Fee per hour must be a number"}, 400
            if data["fee_per_hour"] < 50:
                return {"message": "Fee per hour must be at least ₹50 — facilities can't be listed for free"}, 400
        for field in ["name", "facility_type", "address"]:
            if field in data and not str(data[field] or "").strip():
                return {"message": f"{field.replace('_', ' ').title()} cannot be blank"}, 400
        for field in ["name", "facility_type", "address", "ward", "capacity",
                      "description", "amenities", "fee_per_hour", "image_urls", "is_active"]:
            if field in data:
                setattr(f, field, data[field])
        db.session.commit()
        return f.to_dict(), 200

    @jwt_required()
    def delete(self, facility_id):
        """Admin-only. Deletes a facility with no booking history at all —
        one with any bookings must be deactivated instead."""
        err = _require_role(Role.ADMIN)
        if err:
            return err

        f = db.session.get(Facility, facility_id)
        if not f:
            return {"message": "Not found"}, 404
        # Bookings (and their payments) cascade-delete with the facility, which would
        # silently wipe citizens' payment/transaction history. Block deletion entirely
        # if the facility has ANY booking history, not just active ones — admin should
        # deactivate instead to preserve records.
        total_bookings = f.bookings.count()
        if total_bookings > 0:
            return {"message": "Cannot delete a facility with existing bookings — deactivate it instead to preserve booking/payment history"}, 400

        db.session.delete(f)
        db.session.commit()
        return {"message": "Facility deleted"}, 200


class FacilityAvailabilityResource(Resource):
    @jwt_required()
    def get(self, facility_id):
        """Already-booked time slots for a facility on a given ?date=, so
        the booking form can grey them out."""
        booking_date_str = request.args.get("date")
        if not booking_date_str:
            return {"message": "Date required"}, 400

        try:
            booking_date = _parse_date(booking_date_str)
        except ValueError:
            return {"message": "Invalid date format. Use YYYY-MM-DD"}, 400

        bookings = Booking.query.filter(
            Booking.facility_id == facility_id,
            Booking.booking_date == booking_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        ).all()

        return {
            "facility_id": facility_id,
            "date": booking_date_str,
            "booked_slots": [
                {"start": b.start_time.strftime("%H:%M"), "end": b.end_time.strftime("%H:%M"), "status": b.status}
                for b in bookings
            ]
        }, 200


class FacilityRatingResource(Resource):
    @jwt_required()
    def get(self, facility_id):
        """A facility's ratings, average and 1-5 star distribution."""
        facility = db.session.get(Facility, facility_id)
        if not facility:
            return {"message": "Facility not found"}, 404
        ratings = FacilityRating.query.filter_by(facility_id=facility_id).order_by(FacilityRating.updated_at.desc()).all()
        values = [r.rating for r in ratings]
        distribution = {str(n): 0 for n in range(1, 6)}
        for v in values:
            distribution[str(v)] += 1
        return {
            "ratings": [r.to_dict() for r in ratings],
            "avg": round(sum(values) / len(values), 1) if values else None,
            "count": len(values),
            "distribution": distribution,
        }, 200

    @jwt_required()
    def post(self, facility_id):
        """Citizen-only. Rates a facility 1-5 — gated on having actually
        completed a booking there."""
        user = _current_user()
        err = _require_role(Role.CITIZEN)
        if err:
            return err
        facility = db.session.get(Facility, facility_id)
        if not facility:
            return {"message": "Facility not found"}, 404

        data = request.get_json() or {}
        rating = data.get("rating")
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return {"message": "Rating must be an integer from 1 to 5"}, 400
        comment = (data.get("comment") or "").strip() or None

        # Gate rating on having actually completed a booking there — otherwise
        # there's nothing for the citizen to be reviewing. booking_id is taken
        # from this lookup, not the request body: trusting a client-supplied
        # id here would let a bad/other-citizen's id through as a foreign key
        # the server never actually checked.
        has_completed = Booking.query.filter_by(
            facility_id=facility_id, citizen_id=user.id, status=BookingStatus.COMPLETED
        ).first()
        if not has_completed:
            return {"message": "You can only rate a facility after completing a booking there"}, 400

        existing = FacilityRating.query.filter_by(facility_id=facility_id, citizen_id=user.id).first()
        if existing:
            existing.rating = rating
            existing.comment = comment
            existing.booking_id = has_completed.id
            db.session.commit()
            return existing.to_dict(), 200

        fr = FacilityRating(facility_id=facility_id, citizen_id=user.id, booking_id=has_completed.id, rating=rating, comment=comment)
        db.session.add(fr)
        try:
            db.session.commit()
        except IntegrityError:
            # A double-submitted rating form racing itself.
            db.session.rollback()
            existing = FacilityRating.query.filter_by(facility_id=facility_id, citizen_id=user.id).first()
            return existing.to_dict(), 200
        return fr.to_dict(), 201


# ── Facility Favourites ───────────────────────────────────────────────────────

class FacilityFavoriteListResource(Resource):
    """A citizen's saved-for-later facilities. Always scoped to the signed-in
    user — a favourite is personal, so its owner comes from the session, never
    from the caller."""
    @jwt_required()
    def get(self):
        user = _current_user()
        ids = [f.facility_id for f in FacilityFavorite.query.filter_by(citizen_id=user.id).all()]
        return ids, 200

    @jwt_required()
    def post(self):
        user = _current_user()
        data = request.get_json() or {}
        try:
            facility_id = int(data.get("facility_id"))
        except (TypeError, ValueError):
            return {"message": "Invalid facility_id"}, 400
        if not db.session.get(Facility, facility_id):
            return {"message": "That facility does not exist"}, 404

        # One endpoint that toggles rather than separate add/remove calls, so
        # two open tabs can't drift out of sync with each other.
        existing = FacilityFavorite.query.filter_by(citizen_id=user.id, facility_id=facility_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return {"facility_id": facility_id, "favourited": False}, 200

        db.session.add(FacilityFavorite(citizen_id=user.id, facility_id=facility_id))
        try:
            db.session.commit()
        except IntegrityError:
            # A concurrent double-click raced us to add the same favourite.
            db.session.rollback()
            return {"facility_id": facility_id, "favourited": True}, 200
        return {"facility_id": facility_id, "favourited": True}, 200


class FacilityFavoriteDetailResource(Resource):
    """Full facility records for the citizen's favourites, so the dashboard
    doesn't have to fetch every facility and filter client side. Only active
    facilities are returned — a favourited-then-deactivated facility should
    quietly drop off the list rather than surface as bookable."""
    @jwt_required()
    def get(self):
        user = _current_user()
        ids = [f.facility_id for f in FacilityFavorite.query.filter_by(citizen_id=user.id).all()]
        if not ids:
            return [], 200
        facilities = Facility.query.filter(Facility.id.in_(ids), Facility.is_active.is_(True)).all()
        return [f.to_dict() for f in facilities], 200


# ── Bookings ──────────────────────────────────────────────────────────────────

class BookingListResource(Resource):
    @jwt_required()
    def get(self):
        """Staff can't book facilities, so this is citizen/admin only. A
        citizen sees only their own bookings, admin sees every booking;
        both can filter by ?status=."""
        user = _current_user()
        if user.role == Role.STAFF:
            return {"message": "Forbidden"}, 403
        status_filter = request.args.get("status")

        if user.role == Role.CITIZEN:
            q = Booking.query.filter_by(citizen_id=user.id)
        else:
            q = Booking.query

        # Bring expiry up to date before the status filter is applied, so a
        # booking that just lapsed is filtered as "expired" and not as the
        # "pending" it was a moment ago.
        _expire_stale_bookings(
            (Booking.query.filter_by(citizen_id=user.id) if user.role == Role.CITIZEN
             else Booking.query).all())

        if status_filter:
            q = q.filter_by(status=status_filter)

        bookings = q.order_by(Booking.created_at.desc()).all()
        return [b.to_dict() for b in bookings], 200

    @jwt_required()
    def post(self):
        """Citizen-only. Books a facility time slot after checking capacity,
        operating hours (06:00-22:00) and slot conflicts, and creates a
        pending Payment if the facility has a fee."""
        user = _current_user()
        err = _require_role(Role.CITIZEN)
        if err:
            return err

        data = request.get_json() or {}
        required = ["facility_id", "booking_date", "start_time", "end_time", "purpose"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return {"message": f"Missing: {', '.join(missing)}"}, 400

        facility = db.session.get(Facility, data["facility_id"])
        if not facility or not facility.is_active:
            return {"message": "Facility not found or inactive"}, 404

        try:
            booking_date = _parse_date(data["booking_date"])
            start_time = _parse_time(data["start_time"])
            end_time = _parse_time(data["end_time"])
        except ValueError:
            return {"message": "Invalid date/time format. Use YYYY-MM-DD and HH:MM"}, 400

        if booking_date < date.today():
            return {"message": "Cannot book for a past date"}, 400

        if booking_date == now_ist().date() and start_time <= now_ist().time():
            return {"message": "Cannot book a time slot that has already passed today"}, 400

        if start_time >= end_time:
            return {"message": "Start time must be before end time"}, 400

        start_hour = start_time.hour
        end_hour = end_time.hour + (1 if end_time.minute > 0 else 0)
        if start_hour < 6 or end_hour > 22:
            return {"message": "Bookings allowed only between 06:00 and 22:00"}, 400

        try:
            attendees = int(data.get("attendees", 1))
        except (TypeError, ValueError):
            return {"message": "Attendees must be a number"}, 400
        if attendees < 1:
            return {"message": "Attendees must be at least 1"}, 400
        if attendees > facility.capacity:
            return {"message": f"Attendees exceed facility capacity of {facility.capacity}"}, 400

        _lock_facility_for_booking(facility.id)
        if _booking_conflicts(facility.id, booking_date, start_time, end_time):
            db.session.rollback()  # release the lock taken above before returning
            return {"message": "This time slot is already booked"}, 409

        fee = _calculate_fee(facility, start_time, end_time)

        booking = Booking(
            facility_id=facility.id,
            citizen_id=user.id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            purpose=data["purpose"].strip(),
            attendees=attendees,
            fee=fee,
        )
        db.session.add(booking)

        if fee > 0:
            payment = Payment(
                booking_id=None,
                citizen_id=user.id,
                amount=fee,
            )
            db.session.flush()
            payment.booking_id = booking.id
            db.session.add(payment)

        admins = User.query.filter_by(role=Role.ADMIN).all()
        for admin in admins:
            _notify(admin.id, "New Facility Booking",
                    f"{user.name} has requested to book {facility.name} on {booking_date}", "booking")

        db.session.commit()
        return booking.to_dict(), 201


class BookingResource(Resource):
    @jwt_required()
    def get(self, booking_id):
        """One booking's detail — a citizen only their own."""
        user = _current_user()
        b = db.session.get(Booking, booking_id)
        if not b:
            return {"message": "Not found"}, 404
        if user.role == Role.CITIZEN and b.citizen_id != user.id:
            return {"message": "Forbidden"}, 403
        _expire_stale_bookings([b])
        return b.to_dict(), 200

    @jwt_required()
    def delete(self, booking_id):
        """Citizen self-cancel for their own pending, unpaid booking (see
        BookingRequestRefundResource for a paid one)."""
        user = _current_user()
        b = db.session.get(Booking, booking_id)
        if not b:
            return {"message": "Not found"}, 404

        # Citizen self-service only — admin cancellation goes through
        # BookingStatusResource instead, which correctly records cancelled_by
        # as "admin" and applies the same paid/refund handling below. Without
        # this being citizen-only, an admin hitting this endpoint would both
        # mislabel cancelled_by as "citizen" and skip the "paid bookings need
        # a refund request" guard a couple lines down.
        if user.role != Role.CITIZEN:
            return {"message": "Forbidden"}, 403
        if b.citizen_id != user.id:
            return {"message": "Forbidden"}, 403
        _expire_stale_bookings([b])
        if b.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
            article = "An" if b.status[0] in "aeiou" else "A"
            return {"message": f"{article} {b.status} booking can no longer be cancelled"}, 400
        if b.payment and b.payment.status in (PaymentStatus.PAID, PaymentStatus.REFUND_REQUESTED):
            return {"message": "A paid booking cannot be self-cancelled — request a refund instead"}, 400

        b.status = BookingStatus.CANCELLED
        b.cancelled_by = Role.CITIZEN
        # A PAID (or refund-requested) payment already returned 400 above, so
        # whatever's left here is at most PENDING — cancelling the booking
        # cancels that unpaid invoice too rather than leaving it dangling.
        if b.payment and b.payment.status == PaymentStatus.PENDING:
            b.payment.status = PaymentStatus.CANCELLED
        _notify(b.citizen_id, "Booking Cancelled",
                    f"Your booking for {b.facility.name} on {b.booking_date} was cancelled.", "booking")

        db.session.commit()
        return {"message": "Booking cancelled"}, 200


class BookingStatusResource(Resource):
    @jwt_required()
    def put(self, booking_id):
        """Admin/staff move a booking's status forward (confirm/reject/
        cancel), with the same paid/refund handling BookingResource.delete
        applies for a citizen's own cancel."""
        err = _require_role(Role.ADMIN, Role.STAFF)
        if err:
            return err

        b = db.session.get(Booking, booking_id)
        if not b:
            return {"message": "Not found"}, 404
        data = request.get_json() or {}
        new_status = data.get("status")

        valid_statuses = [BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CANCELLED, BookingStatus.COMPLETED]
        if new_status not in valid_statuses:
            return {"message": "Invalid status"}, 400
        # An unpaid booking whose date has gone is already over — confirming it
        # now would invite the citizen to pay for a slot they never got.
        _expire_stale_bookings([b])
        if b.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED,
                        BookingStatus.EXPIRED]:
            article = "An" if b.status[0] in "aeiou" else "A"
            return {"message": f"{article} {b.status} booking can no longer be changed"}, 400

        user = _current_user()
        if user.role == Role.STAFF and new_status not in [BookingStatus.COMPLETED]:
            return {"message": "Staff can only mark bookings as completed"}, 403

        b.status = new_status
        if data.get("admin_notes"):
            b.admin_notes = data["admin_notes"]
        if new_status == BookingStatus.CANCELLED:
            b.cancelled_by = Role.ADMIN

        if new_status == BookingStatus.CANCELLED and b.payment and b.payment.status in (PaymentStatus.PAID, PaymentStatus.REFUND_REQUESTED):
            b.payment.status = PaymentStatus.REFUNDED
            b.payment.refund_reason = (data.get("refund_reason") or "").strip() or None
            _notify(b.citizen_id, "Booking Cancelled & Refund Initiated",
                    f"Your booking for {b.facility.name} was cancelled. Refund of Rs.{b.fee} initiated.", "refund")
        elif new_status == BookingStatus.CANCELLED and b.payment and b.payment.status == PaymentStatus.PENDING:
            b.payment.status = PaymentStatus.CANCELLED
            _notify(b.citizen_id, "Booking Cancelled",
                    f"Your booking for {b.facility.name} on {b.booking_date} was cancelled.", "booking")
        else:
            status_msgs = {
                BookingStatus.CONFIRMED: f"Your booking for {b.facility.name} on {b.booking_date} is confirmed!",
                BookingStatus.CANCELLED: f"Your booking for {b.facility.name} on {b.booking_date} was cancelled.",
                BookingStatus.COMPLETED: f"Your booking for {b.facility.name} is marked as completed.",
            }
            if new_status in status_msgs:
                _notify(b.citizen_id, f"Booking {new_status.title()}", status_msgs[new_status], "booking")

        db.session.commit()
        return b.to_dict(), 200


class BookingCompleteResource(Resource):
    """Citizen self-service: mark their own confirmed booking as completed
    once the date has passed, so they can then rate the facility. Distinct
    from BookingStatusResource, which is the admin/staff status-change path."""
    @jwt_required()
    def put(self, booking_id):
        user = _current_user()
        err = _require_role(Role.CITIZEN)
        if err:
            return err
        b = db.session.get(Booking, booking_id)
        if not b:
            return {"message": "Not found"}, 404
        if b.citizen_id != user.id:
            return {"message": "Forbidden"}, 403
        _expire_stale_bookings([b])
        if b.status != BookingStatus.CONFIRMED:
            return {"message": f"Only a confirmed booking can be marked complete (current status: {b.status})"}, 400
        if b.payment and b.payment.status != PaymentStatus.PAID:
            return {"message": "This booking can't be marked complete right now"}, 400
        if b.booking_date > now_ist().date():
            return {"message": "This booking hasn't happened yet"}, 400
        b.status = BookingStatus.COMPLETED
        db.session.commit()
        return b.to_dict(), 200


class BookingRequestRefundResource(Resource):
    """Citizen self-service: ask for money back on an already-paid booking,
    with a reason (e.g. the facility turned out to be unavailable). This does
    not refund anything by itself — it only flags the payment for admin
    review, who then approves (BookingStatusResource, status=cancelled) or
    rejects (BookingRejectRefundResource) it."""
    @jwt_required()
    def put(self, booking_id):
        user = _current_user()
        err = _require_role(Role.CITIZEN)
        if err:
            return err
        b = db.session.get(Booking, booking_id)
        if not b:
            return {"message": "Not found"}, 404
        if b.citizen_id != user.id:
            return {"message": "Forbidden"}, 403
        if not b.payment or b.payment.status != PaymentStatus.PAID:
            return {"message": "Only a paid booking can have a refund requested"}, 400
        if b.status == BookingStatus.COMPLETED:
            return {"message": "A completed booking is no longer eligible for a refund"}, 400

        data = request.get_json() or {}
        reason = (data.get("reason") or "").strip()
        if not reason:
            return {"message": "Please tell us why you're requesting a refund"}, 400

        b.payment.status = PaymentStatus.REFUND_REQUESTED
        b.payment.refund_request_reason = reason
        admins = User.query.filter_by(role=Role.ADMIN).all()
        for admin in admins:
            _notify(admin.id, "Refund Requested",
                    f"{user.name} requested a refund for {b.facility.name} (Rs.{b.payment.amount}).", "refund")
        db.session.commit()
        return b.to_dict(), 200


class BookingRejectRefundResource(Resource):
    """Admin declines a citizen's refund request — the payment goes back to
    'paid' exactly as it was, no money moves."""
    @jwt_required()
    def put(self, booking_id):
        err = _require_role(Role.ADMIN)
        if err:
            return err
        b = db.session.get(Booking, booking_id)
        if not b:
            return {"message": "Not found"}, 404
        if not b.payment or b.payment.status != PaymentStatus.REFUND_REQUESTED:
            return {"message": "This booking has no pending refund request"}, 400

        data = request.get_json() or {}
        note = (data.get("reason") or "").strip()
        b.payment.status = PaymentStatus.PAID
        b.payment.refund_reason = note or None
        # Recorded on their own, so a refund granted later for some other
        # reason cannot erase that this request was turned down first. The
        # timestamp is what marks the rejection — the note is optional and an
        # admin who declines without typing one must still leave a trace.
        b.payment.refund_rejected_reason = note or None
        b.payment.refund_rejected_at = now_ist()
        msg = f"Your refund request for {b.facility.name} was declined."
        if note:
            msg += f' Note: "{note}"'
        _notify(b.citizen_id, "Refund Request Declined", msg, "refund")
        db.session.commit()
        return b.to_dict(), 200


# ── Payments ──────────────────────────────────────────────────────────────────

class PaymentListResource(Resource):
    @jwt_required()
    def get(self):
        """Citizen/admin only. A citizen sees only their own booking
        payments, admin sees every payment."""
        user = _current_user()
        if user.role == Role.STAFF:
            return {"message": "Forbidden"}, 403
        if user.role == Role.CITIZEN:
            payments = Payment.query.filter_by(citizen_id=user.id).all()
        else:
            payments = Payment.query.all()
        return [p.to_dict() for p in payments], 200


class PaymentPayResource(Resource):
    @jwt_required()
    def post(self, payment_id):
        """Marks a pending booking payment as paid — the app's stand-in for
        a real payment gateway, no actual processing happens."""
        user = _current_user()
        if user.role == Role.STAFF:
            return {"message": "Forbidden"}, 403
        payment = db.session.get(Payment, payment_id)
        if not payment:
            return {"message": "Not found"}, 404

        if payment.citizen_id != user.id and user.role == Role.CITIZEN:
            return {"message": "Forbidden"}, 403

        booking = payment.booking
        if booking:
            # The slot may have lapsed since this page was loaded.
            _expire_stale_bookings([booking])

        if payment.status != PaymentStatus.PENDING:
            return {"message": f"Payment is already {payment.status}"}, 400

        if booking and booking.status == BookingStatus.EXPIRED:
            return {"message": "This booking expired unpaid. Please book a new slot."}, 400
        if booking and booking.status != BookingStatus.CONFIRMED:
            return {"message": "This booking must be confirmed by admin before you can pay"}, 400

        data = request.get_json() or {}
        method = data.get("method", "online")
        if method not in ["online", "upi", "card", "netbanking"]:
            return {"message": "Invalid payment method"}, 400

        import uuid
        payment.status = PaymentStatus.PAID
        payment.method = method
        payment.transaction_ref = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        payment.paid_at = now_ist()

        if booking:
            _notify(booking.citizen_id, "Payment Successful",
                    f"Payment of Rs.{payment.amount} for {booking.facility.name} received.", "payment")

            admins = User.query.filter_by(role=Role.ADMIN).all()
            for admin in admins:
                _notify(admin.id, "Payment Received",
                        f"{user.name} paid Rs.{payment.amount} for {booking.facility.name}", "payment")

        db.session.commit()
        return payment.to_dict(), 200


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationListResource(Resource):
    @jwt_required()
    def get(self):
        """The signed-in user's own notification feed, paginated and
        optionally filtered by category via ?category=. unread_count is
        always computed across *all* categories, not just the current
        filter, so the bell badge stays correct no matter which tab is
        open."""
        user = _current_user()
        q = Notification.query.filter_by(user_id=user.id)

        category = request.args.get("category", "all")
        if category != "all":
            types = NOTIF_CATEGORY_MAP.get(category)
            if types:
                q = q.filter(Notification.notif_type.in_(types))

        # unread_count always reflects *every* notification the user has
        # (not just the current category/page), so the bell badge stays
        # correct regardless of which tab is currently open.
        unread = Notification.query.filter_by(user_id=user.id, is_read=False).count()
        total = q.count()

        try:
            page = max(1, int(request.args.get("page", 1)))
            limit = max(1, min(50, int(request.args.get("limit", 10))))
        except (TypeError, ValueError):
            page, limit = 1, 10

        notifications = q.order_by(Notification.created_at.desc())\
            .offset((page - 1) * limit).limit(limit).all()
        return {
            "notifications": [n.to_dict() for n in notifications],
            "unread_count": unread,
            "total": total,
        }, 200


class NotificationReadResource(Resource):
    @jwt_required()
    def put(self, notif_id):
        """Marks one of the signed-in user's own notifications as read —
        notif_id=0 is a sentinel that marks all of them read at once."""
        user = _current_user()
        if notif_id == 0:
            Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
        else:
            n = db.session.get(Notification, notif_id)
            if not n:
                return {"message": "Not found"}, 404
            if n.user_id != user.id:
                return {"message": "Forbidden"}, 403
            n.is_read = True
        db.session.commit()
        return {"message": "Marked as read"}, 200


class NotificationArchiveResource(Resource):
    """Dismiss a notification from the Notifications page. Unlike a complaint
    or booking, a notification isn't part of any accountability record — it's
    just a transient alert — so "archive" here means an outright delete
    rather than a soft-deleted/hidden row."""
    @jwt_required()
    def put(self, notif_id):
        user = _current_user()
        n = db.session.get(Notification, notif_id)
        if not n:
            return {"message": "Not found"}, 404
        if n.user_id != user.id:
            return {"message": "Forbidden"}, 403
        db.session.delete(n)
        db.session.commit()
        return {"message": "Archived"}, 200


class NotificationClearAllResource(Resource):
    """Bulk version of NotificationArchiveResource — "Clear All" in the bell
    dropdown/Notifications page. This route never existed on the real
    backend at all (the frontend was built against it, but nothing ever
    implemented it), so every "Clear All" click 404'd silently."""
    @jwt_required()
    def post(self):
        user = _current_user()
        Notification.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return {"message": "Cleared"}, 200


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardResource(Resource):
    @jwt_required()
    def get(self):
        """Role-dependent summary counts: a citizen gets their own request/
        booking/payment tallies, staff get their assigned-request breakdown
        plus their 5 most recent, and an admin gets platform-wide totals
        across requests, bookings, users, payments, subscriptions and
        facilities."""
        user = _current_user()

        if user.role == Role.CITIZEN:
            my_requests = ServiceRequest.query.filter_by(citizen_id=user.id)
            my_bookings = Booking.query.filter_by(citizen_id=user.id)
            pending_payments = Payment.query.filter_by(citizen_id=user.id, status=PaymentStatus.PENDING).count()
            return {
                "requests": {
                    "total": my_requests.count(),
                    "pending": my_requests.filter_by(status=RequestStatus.PENDING).count(),
                    "in_progress": my_requests.filter(ServiceRequest.status.in_(
                        [RequestStatus.ASSIGNED, RequestStatus.REASSIGNED, RequestStatus.IN_PROGRESS])).count(),
                    "on_hold_weather": my_requests.filter_by(status=RequestStatus.ON_HOLD_WEATHER).count(),
                    "resolved": my_requests.filter_by(status=RequestStatus.RESOLVED).count(),
                },
                "bookings": {
                    "total": my_bookings.count(),
                    "pending": my_bookings.filter_by(status=BookingStatus.PENDING).count(),
                    "confirmed": my_bookings.filter_by(status=BookingStatus.CONFIRMED).count(),
                },
                "pending_payments": pending_payments,
                "unread_notifications": Notification.query.filter_by(user_id=user.id, is_read=False).count(),
            }, 200

        elif user.role == Role.STAFF:
            my_assignments = Assignment.query.filter_by(staff_id=user.id)
            assigned_ids = [a.request_id for a in my_assignments.all()]
            my_requests = ServiceRequest.query.filter(ServiceRequest.id.in_(assigned_ids))
            return {
                "assignments": {
                    "total": my_assignments.count(),
                    "active": my_requests.filter(ServiceRequest.status.in_(
                        [RequestStatus.ASSIGNED, RequestStatus.REASSIGNED, RequestStatus.IN_PROGRESS, RequestStatus.ON_HOLD_WEATHER])).count(),
                    "pending": my_requests.filter(ServiceRequest.status.in_(
                        [RequestStatus.ASSIGNED, RequestStatus.REASSIGNED, RequestStatus.ON_HOLD_WEATHER])).count(),
                    "in_progress": my_requests.filter_by(status=RequestStatus.IN_PROGRESS).count(),
                    "resolved": my_requests.filter_by(status=RequestStatus.RESOLVED).count(),
                },
                "recent": [r.to_dict() for r in my_requests.order_by(ServiceRequest.created_at.desc()).limit(5).all()],
                "unread_notifications": Notification.query.filter_by(user_id=user.id, is_read=False).count(),
            }, 200

        else:  # admin
            return {
                "requests": {
                    "total": ServiceRequest.query.count(),
                    "pending": ServiceRequest.query.filter_by(status=RequestStatus.PENDING).count(),
                    "assigned": ServiceRequest.query.filter_by(status=RequestStatus.ASSIGNED).count(),
                    "reassigned": ServiceRequest.query.filter_by(status=RequestStatus.REASSIGNED).count(),
                    "in_progress": ServiceRequest.query.filter_by(status=RequestStatus.IN_PROGRESS).count(),
                    "resolved": ServiceRequest.query.filter_by(status=RequestStatus.RESOLVED).count(),
                    "closed": ServiceRequest.query.filter_by(status=RequestStatus.CLOSED).count(),
                    "on_hold_weather": ServiceRequest.query.filter_by(status=RequestStatus.ON_HOLD_WEATHER).count(),
                    "pending_funds": ServiceRequest.query.filter_by(pending_funds=True).count(),
                },
                "bookings": {
                    "total": Booking.query.count(),
                    "pending": Booking.query.filter_by(status=BookingStatus.PENDING).count(),
                    "confirmed": Booking.query.filter_by(status=BookingStatus.CONFIRMED).count(),
                },
                "users": {
                    "total": User.query.count(),
                    "citizens": User.query.filter_by(role=Role.CITIZEN).count(),
                    "staff": User.query.filter_by(role=Role.STAFF).count(),
                },
                "payments": {
                    "collected": db.session.query(db.func.sum(Payment.amount))
                        .filter_by(status=PaymentStatus.PAID).scalar() or 0,
                    "pending": Payment.query.filter_by(status=PaymentStatus.PENDING).count(),
                },
                "subscriptions": {
                    "active": Subscription.query.filter_by(status=SubscriptionStatus.ACTIVE).count(),
                    "monthly_recurring_revenue": Subscription.query.filter_by(
                        status=SubscriptionStatus.ACTIVE).count() * SUBSCRIPTION_FEE,
                    "total_collected": db.session.query(db.func.sum(SubscriptionPayment.amount))
                        .filter_by(status=PaymentStatus.PAID).scalar() or 0,
                },
                "facilities": {
                    "total": Facility.query.count(),
                    "active": Facility.query.filter_by(is_active=True).count(),
                },
                "unread_notifications": Notification.query.filter_by(user_id=user.id, is_read=False).count(),
            }, 200


# ── Admin: Users ──────────────────────────────────────────────────────────────

class AdminUserListResource(Resource):
    @jwt_required()
    def get(self):
        """Admin-only. Every user account, optionally filtered to one role
        via ?role=, newest first — drives the admin's user-management
        table."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        role_filter = request.args.get("role")
        q = User.query
        if role_filter:
            q = q.filter_by(role=role_filter)
        users = q.order_by(User.created_at.desc()).all()
        return [u.to_dict() for u in users], 200


class AdminUserResource(Resource):
    @jwt_required()
    def put(self, user_id):
        """Admin-only. Updates a user's role/is_active/ward — not for
        creating staff accounts, that goes through Manage Officers
        instead."""
        err = _require_role(Role.ADMIN)
        if err:
            return err

        user = db.session.get(User, user_id)
        if not user:
            return {"message": "Not found"}, 404
        data = request.get_json() or {}
        caller = _current_user()

        # An admin who demotes or disables themselves is locked out the moment
        # the change commits, and the only way back in is editing the database
        # by hand. Same for the last remaining admin, whoever makes the change.
        losing_admin = (
            ("role" in data and data["role"] in Role.ALL and data["role"] != Role.ADMIN)
            or ("is_active" in data and not bool(data["is_active"]))
        )
        if losing_admin and user.role == Role.ADMIN:
            if user.id == caller.id:
                return {"message": "You cannot remove your own admin access — "
                                   "ask another admin to do it"}, 400
            others = User.query.filter(
                User.role == Role.ADMIN, User.is_active.is_(True), User.id != user.id
            ).count()
            if others == 0:
                return {"message": "This is the last active admin — promote another "
                                   "admin first, or the system would be left "
                                   "with nobody who can administer it"}, 400

        if "role" in data:
            if data["role"] == Role.STAFF:
                return {"message": "Use Manage Officers to create staff accounts (requires a department)"}, 400
            if data["role"] in Role.ALL:
                user.role = data["role"]
        if "is_active" in data:
            user.is_active = bool(data["is_active"])
        if "ward" in data:
            user.ward = data["ward"]

        db.session.commit()
        return user.to_dict(), 200


class StaffListResource(Resource):
    @jwt_required()
    def get(self):
        """Admin-only. Active officers only (is_active=True) — the pool a
        department's officer_incharge_id or an assignment's staff_id can be
        picked from, unlike OfficerListResource which also lists disabled
        ones."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        staff = User.query.filter_by(role=Role.STAFF, is_active=True).all()
        return [u.to_dict() for u in staff], 200


# ── Departments ───────────────────────────────────────────────────────────────

def _validate_officer_incharge(officer_id):
    """Returns an error tuple or None. Guards Department.officer_incharge_id
    against a nonexistent or wrong-role id — previously unvalidated, this
    could silently write a dangling reference (SQLite doesn't enforce
    foreign keys unless a connection turns it on, see apps/__init__.py), and
    now that it does, the same bad input would otherwise surface as a raw,
    unhandled IntegrityError/500 instead of a clean 400."""
    if not officer_id:
        return None
    officer = db.session.get(User, officer_id)
    if not officer or officer.role != Role.STAFF:
        return {"message": "officer_incharge_id must be an existing staff member"}, 400
    return None


class DepartmentListResource(Resource):
    def get(self):
        """Public — no login required. Every department in id order, used
        to populate the department dropdown on both the complaint form and
        the admin screens."""
        depts = Department.query.order_by(Department.id).all()
        return [d.to_dict() for d in depts], 200

    @jwt_required()
    def post(self):
        """Admin-only. Creates a new department."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        if not name:
            return {"message": "Name required"}, 400
        if Department.query.filter(db.func.lower(Department.name) == name.lower()).first():
            return {"message": "Department already exists"}, 409
        invalid = _validate_officer_incharge(data.get("officer_incharge_id"))
        if invalid:
            return invalid
        dept = Department(
            name=name,
            description=data.get("description", ""),
            officer_incharge_id=data.get("officer_incharge_id") or None,
        )
        db.session.add(dept)
        try:
            db.session.commit()
        except IntegrityError:
            # Two admins racing to create the same department name.
            db.session.rollback()
            return {"message": "Department already exists"}, 409
        return dept.to_dict(), 201


class DepartmentResource(Resource):
    @jwt_required()
    def put(self, dept_id):
        """Admin-only. Updates a department's name/description/officer in
        charge."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        dept = db.session.get(Department, dept_id)
        if not dept:
            return {"message": "Not found"}, 404
        data = request.get_json() or {}
        if "name" in data:
            new_name = (data["name"] or "").strip()
            if not new_name:
                return {"message": "Name cannot be blank"}, 400
            clash = Department.query.filter(
                db.func.lower(Department.name) == new_name.lower(),
                Department.id != dept.id,
            ).first()
            if clash:
                return {"message": "A department with this name already exists"}, 409
            dept.name = new_name
        if "description" in data:
            dept.description = data["description"]
        if "officer_incharge_id" in data:
            invalid = _validate_officer_incharge(data["officer_incharge_id"])
            if invalid:
                return invalid
            dept.officer_incharge_id = data["officer_incharge_id"] or None
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {"message": "A department with this name already exists"}, 409
        return dept.to_dict(), 200

    @jwt_required()
    def delete(self, dept_id):
        """Admin-only. Deletes a department that has no active officers
        still assigned to it — reassign them first."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        dept = db.session.get(Department, dept_id)
        if not dept:
            return {"message": "Not found"}, 404
        # Officers carry their department as a plain name, so deleting the
        # department out from under them left officers filed against one that
        # no longer exists — and complaints in that category kept routing to
        # it. Same guard as deleting a facility that still has bookings:
        # reassign the people first, then the department can go.
        staffed = User.query.filter_by(role=Role.STAFF, department=dept.name, is_active=True).count()
        if staffed:
            return {"message": f"{staffed} officer(s) still belong to this department — "
                               f"move them to another department first"}, 400
        db.session.delete(dept)
        db.session.commit()
        return {"message": "Deleted"}, 200


# ── Officers ──────────────────────────────────────────────────────────────────

class OfficerListResource(Resource):
    @jwt_required()
    def get(self):
        """Admin-only. Every officer account regardless of is_active — the
        Manage Officers screen needs to show disabled accounts too, unlike
        StaffListResource which only lists active ones."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        officers = User.query.filter_by(role=Role.STAFF).order_by(User.id).all()
        return [u.to_dict() for u in officers], 200

    @jwt_required()
    def post(self):
        """Admin-only. Creates a new officer (staff) account."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        data = request.get_json() or {}
        if not data.get("email") or not data.get("name") or not data.get("password"):
            return {"message": "Name, email and password required"}, 400
        invalid = _validate_person(data)
        if invalid:
            return invalid
        # Bug fix: this used to compare the raw, un-normalized email — unlike
        # RegisterResource, which always lower-cases/strips first. Login
        # always lower-cases the input before looking the user up, so an
        # officer created with any uppercase in their email (very plausible
        # — an admin typing "Rajesh.Kumar@Civic.Gov") could never log in
        # again with that same email, not even typed exactly as entered here.
        email = data["email"].lower().strip()
        if User.query.filter_by(email=email).first():
            return {"message": "Email already in use"}, 409
        u = User(
            name=data["name"], email=email, role=Role.STAFF,
            phone=data.get("phone", ""), ward=data.get("ward", ""),
            department=data.get("department", ""),
        )
        u.set_password(data["password"])
        db.session.add(u)
        try:
            db.session.commit()
        except IntegrityError:
            # Two admins (or a double-submitted form) racing to create the
            # same officer email — same fix as everywhere else in this file.
            db.session.rollback()
            return {"message": "Email already in use"}, 409
        return u.to_dict(), 201


class OfficerResource(Resource):
    @jwt_required()
    def put(self, officer_id):
        """Admin-only. Updates an officer's profile fields and/or
        is_active."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        u = db.session.get(User, officer_id)
        if not u or u.role != Role.STAFF:
            return {"message": "Not found"}, 404
        data = request.get_json() or {}
        if "name" in data and not NAME_RE.match((data["name"] or "").strip()):
            return {"message": "Please enter a valid name — letters only, numbers are not a name"}, 400
        if data.get("phone") and not PHONE_RE.match(data["phone"].strip()):
            return {"message": "Phone must be a valid 10-digit mobile number"}, 400
        for field in ["name", "phone", "department"]:
            if field in data:
                setattr(u, field, (data[field] or "").strip() if isinstance(data[field], str) else data[field])
        if data.get("is_active") is not None:
            u.is_active = data["is_active"]
        db.session.commit()
        return u.to_dict(), 200

    @jwt_required()
    def delete(self, officer_id):
        """Admin-only. Soft-deletes an officer by setting is_active=False —
        never a hard delete, so their assignment history stays intact."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        u = db.session.get(User, officer_id)
        if not u or u.role != Role.STAFF:
            return {"message": "Not found"}, 404
        u.is_active = False
        open_count = (
            ServiceRequest.query.join(Assignment)
            .filter(Assignment.staff_id == u.id,
                    ServiceRequest.status.in_([RequestStatus.ASSIGNED, RequestStatus.REASSIGNED, RequestStatus.IN_PROGRESS]))
            .count()
        )
        db.session.commit()
        msg = "Officer deactivated"
        if open_count:
            msg += f". They had {open_count} open complaint(s) — reassign them from Manage Complaints."
        return {"message": msg, "open_complaints": open_count}, 200


# ── Public Track ──────────────────────────────────────────────────────────────

class PublicTrackResource(Resource):
    def get(self):
        """Public — no login required. Looks up one complaint by its
        tracking ID (?id=), for the citizen tracker page."""
        cmp_id = request.args.get("id", "").strip().upper()
        if not cmp_id:
            return {"message": "Provide complaint ID"}, 400
        try:
            req_id = int(cmp_id.replace("CMP", "").lstrip("0") or "0")
        except ValueError:
            return {"message": "Invalid ID format"}, 400
        if req_id <= 0 or req_id > 2**31:
            return {"message": "Complaint not found"}, 404
        r = db.session.get(ServiceRequest, req_id)
        if not r:
            return {"message": "Complaint not found"}, 404
        d = r.to_public_dict()
        # See RequestSimilarResource above — evidence_urls is proof-of-completion,
        # not PII, and TrackResultCard.vue is built to show it here.
        d["evidence_urls"] = r.evidence_urls
        return d, 200


class PublicStatsResource(Resource):
    """Aggregate counts only (no PII, no per-complaint detail) for the
    logged-out landing page's stats section."""
    def get(self):
        admin = User.query.filter_by(role=Role.ADMIN).first()
        return {
            "total_complaints": ServiceRequest.query.count(),
            "resolved": ServiceRequest.query.filter(ServiceRequest.status.in_(
                [RequestStatus.RESOLVED, RequestStatus.CLOSED])).count(),
            "in_progress": ServiceRequest.query.filter(ServiceRequest.status.in_(
                [RequestStatus.ASSIGNED, RequestStatus.REASSIGNED, RequestStatus.IN_PROGRESS,
                 RequestStatus.ON_HOLD_WEATHER])).count(),
            "departments": Department.query.count(),
            "admin_email": admin.email if admin else None,
            "admin_phone": admin.phone if admin else None,
        }, 200


# ── Reports ───────────────────────────────────────────────────────────────────

class ReportsResource(Resource):
    @jwt_required()
    def get(self):
        """Admin-only. Aggregated complaint stats over a date range
        (?from=/?to=, defaults to the last 14 days, capped at 60 days) —
        powers the admin reporting charts."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        from datetime import timedelta

        today = now_ist().date()
        from_str = request.args.get("from")
        to_str = request.args.get("to")
        try:
            range_to = datetime.strptime(to_str, "%Y-%m-%d").date() if to_str else today
        except ValueError:
            range_to = today
        try:
            range_from = datetime.strptime(from_str, "%Y-%m-%d").date() if from_str else range_to - timedelta(days=13)
        except ValueError:
            range_from = range_to - timedelta(days=13)
        if range_from > range_to:
            range_from, range_to = range_to, range_from
        # cap the chart window so a huge range doesn't render hundreds of bars
        if (range_to - range_from).days > 60:
            range_from = range_to - timedelta(days=60)

        all_requests = ServiceRequest.query.filter(
            ServiceRequest.created_at >= datetime.combine(range_from, datetime.min.time()),
            ServiceRequest.created_at < datetime.combine(range_to + timedelta(days=1), datetime.min.time()),
        ).all()

        days = []
        span = (range_to - range_from).days
        for i in range(span + 1):
            d = range_from + timedelta(days=i)
            count = sum(1 for r in all_requests if r.created_at.date() == d)
            days.append({"date": d.strftime("%d %b"), "count": count})

        # The real departments always get a row, even in a quiet window, so a
        # department is never silently missing from the comparison. DEPT_MAP can
        # also route a category to a name with no Department row behind it (the
        # "General Affairs" catch-all) — that only earns a row when complaints
        # actually landed there, instead of showing a permanent empty 0/0 bar.
        dept_names = {d.name for d in Department.query.all()}
        dept_names |= {DEPT_MAP[r.category] for r in all_requests if r.category in DEPT_MAP}
        dept_names = sorted(dept_names)
        dept_perf = []
        for dept_name in dept_names:
            cats = [c for c, d in DEPT_MAP.items() if d == dept_name]
            total = sum(1 for r in all_requests if r.category in cats)
            resolved = sum(1 for r in all_requests if r.category in cats and r.status in ["resolved", "closed"])
            pct = round((resolved / total * 100) if total > 0 else 0)
            dept_perf.append({"name": dept_name, "total": total, "resolved": resolved, "pct": pct})
        return {
            "complaints_over_time": days,
            "department_performance": dept_perf,
            "total": len(all_requests),
            "by_status": {
                "pending": sum(1 for r in all_requests if r.status == "pending"),
                "in_progress": sum(1 for r in all_requests if r.status in ["assigned", "reassigned", "in_progress", "on_hold_weather"]),
                "resolved": sum(1 for r in all_requests if r.status == "resolved"),
                "closed": sum(1 for r in all_requests if r.status == "closed"),
            }
        }, 200


# ── Community Posts ───────────────────────────────────────────────────────────

class PostListResource(Resource):
    @jwt_required()
    def get(self):
        """The community feed, optionally filtered by ?category= and
        ?ward=. When no category is given, announcement posts are excluded
        from the general feed — they only ever show on the dedicated
        Announcements page."""
        user = _current_user()
        category = request.args.get("category")
        ward = request.args.get("ward")
        q = Post.query
        if category:
            q = q.filter_by(category=category)
        else:
            # The general community feed never mixes in official announcements —
            # those only ever show on the dedicated Announcements page.
            q = q.filter(Post.category != "announcement")
        if ward:
            q = q.filter_by(ward=ward)
        posts = q.order_by(Post.created_at.desc()).all()
        return [p.to_dict(user.id) for p in posts], 200

    @jwt_required()
    def post(self):
        """Creates a community post — only an admin's post can carry the
        "announcement" category, everyone else's falls back to "general"."""
        user = _current_user()
        data = request.get_json() or {}
        content = (data.get("content") or "").strip()
        if not content:
            return {"message": "Content required"}, 400
        # Only an admin can publish an official announcement — everyone else's
        # posts land in the regular community feed, announcement or not.
        category = data.get("category", "general")
        if category == "announcement" and user.role != Role.ADMIN:
            category = "general"
        post = Post(
            citizen_id=user.id,
            title=(data.get("title") or "").strip(),
            content=content,
            category=category,
            location=data.get("location", ""),
            ward=data.get("ward", user.ward or ""),
            topic=data.get("topic") or None,
            image_urls=data.get("image_urls") or [],
            is_official=user.role in ["staff", "admin"],
        )
        db.session.add(post)
        db.session.commit()
        return post.to_dict(user.id), 201

    @jwt_required()
    def delete(self):
        """Admin-only. Deletes a post by ?post_id= query param (see
        PostResourceItem.delete for the citizen/admin-by-owner path
        version)."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        post_id = request.args.get("post_id")
        if not post_id:
            return {"message": "post_id required"}, 400
        try:
            post_id = int(post_id)
        except ValueError:
            return {"message": "post_id must be a number"}, 400
        p = db.session.get(Post, post_id)
        if not p:
            return {"message": "Not found"}, 404
        attached = list(p.image_urls or [])
        db.session.delete(p)
        db.session.commit()
        _delete_unreferenced_uploads(attached)
        return {"message": "Deleted"}, 200


class PostResourceItem(Resource):
    @jwt_required()
    def delete(self, post_id):
        """Deletes a post — its own author or an admin."""
        user = _current_user()
        p = db.session.get(Post, post_id)
        if not p:
            return {"message": "Not found"}, 404
        if user.role != Role.ADMIN and p.citizen_id != user.id:
            return {"message": "Forbidden"}, 403
        attached = list(p.image_urls or [])
        db.session.delete(p)
        db.session.commit()
        _delete_unreferenced_uploads(attached)
        return {"message": "Deleted"}, 200


class PostLikeResource(Resource):
    @jwt_required()
    def post(self, post_id):
        """Toggles the signed-in user's like on a post — liked if it wasn't,
        unliked if it already was."""
        user = _current_user()
        if not db.session.get(Post, post_id):
            return {"message": "Post not found"}, 404
        existing = PostLike.query.filter_by(post_id=post_id, user_id=user.id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return {"liked": False}, 200
        like = PostLike(post_id=post_id, user_id=user.id)
        db.session.add(like)
        try:
            db.session.commit()
        except IntegrityError:
            # A double-click racing itself — same fix as the complaint
            # upvote and facility favourite toggles.
            db.session.rollback()
        return {"liked": True}, 200


class PostCommentListResource(Resource):
    @jwt_required()
    def get(self, post_id):
        """All comments on one post, oldest first — no extra permission
        check beyond being signed in, since any signed-in resident can read
        a public post's comment thread."""
        comments = PostComment.query.filter_by(post_id=post_id).order_by(PostComment.created_at).all()
        return [c.to_dict() for c in comments], 200

    @jwt_required()
    def post(self, post_id):
        """Adds a comment to a post."""
        user = _current_user()
        if not db.session.get(Post, post_id):
            return {"message": "Post not found"}, 404
        data = request.get_json() or {}
        content = (data.get("content") or "").strip()
        if not content:
            return {"message": "Content required"}, 400
        comment = PostComment(
            post_id=post_id,
            user_id=user.id,
            content=content,
            is_official=user.role in ["staff", "admin"],
        )
        db.session.add(comment)
        db.session.commit()
        return comment.to_dict(), 201


class PostCommentResource(Resource):
    @jwt_required()
    def delete(self, post_id, comment_id):
        """Deletes a comment — its own author or an admin."""
        user = _current_user()
        c = PostComment.query.filter_by(id=comment_id, post_id=post_id).first()
        if not c:
            return {"message": "Not found"}, 404
        if not (user.role == Role.ADMIN or c.user_id == user.id):
            return {"message": "You can only delete your own comments"}, 403
        db.session.delete(c)
        db.session.commit()
        return {"success": True}, 200


# ── Help & FAQ (admin-authored) ───────────────────────────────────────────────
# The help content that ships with the app lives in the frontend's own data
# file and is never stored here. This is only for questions an admin adds
# afterwards from the Help and FAQ page — and the page itself is public, so
# browsing these needs no login.

class FaqListResource(Resource):
    def get(self):
        """Public — no login required. Every FAQ entry, newest first; the
        Help & FAQ page's own list."""
        entries = FaqEntry.query.order_by(FaqEntry.created_at.desc()).all()
        return [e.to_dict() for e in entries], 200

    @jwt_required()
    def post(self):
        """Admin-only. Adds a new FAQ entry."""
        user = _current_user()
        err = _require_role(Role.ADMIN)
        if err:
            return err
        data = request.get_json() or {}
        question = (data.get("question") or "").strip()
        answer = (data.get("answer") or "").strip()
        if not question or not answer:
            return {"message": "Please fill in both the question and the answer"}, 400
        category = data.get("category") or FaqCategory.DEFAULT
        if category not in FaqCategory.ALL:
            category = FaqCategory.DEFAULT
        entry = FaqEntry(question=question, answer=answer, category=category, author_id=user.id)
        db.session.add(entry)
        db.session.commit()
        return entry.to_dict(), 201


class FaqResource(Resource):
    @jwt_required()
    def put(self, faq_id):
        """Admin-only. Edits an FAQ entry in place.

        Deleting and re-adding was the only way to fix an answer before this,
        and that changes the entry's id. The 'Was this helpful?' counts are
        keyed on "custom-<id>" (see FaqFeedback), so the old counts were
        orphaned and the rewritten answer started from zero — which is exactly
        the signal an admin needs to judge whether the rewrite helped.

        Editing keeps the id, so the counts follow the answer. Note that means
        votes cast on the previous wording are still counted; updated_at is
        returned so the page can show when the text last changed.

        Partial: any of question, answer and category may be sent on their own.
        """
        err = _require_role(Role.ADMIN)
        if err:
            return err
        entry = db.session.get(FaqEntry, faq_id)
        if not entry:
            return {"message": "Not found"}, 404

        data = request.get_json() or {}
        # Present-but-blank is a mistake worth rejecting; absent just means
        # "leave this one alone".
        if "question" in data:
            question = (data.get("question") or "").strip()
            if not question:
                return {"message": "Please fill in both the question and the answer"}, 400
            entry.question = question
        if "answer" in data:
            answer = (data.get("answer") or "").strip()
            if not answer:
                return {"message": "Please fill in both the question and the answer"}, 400
            entry.answer = answer
        if "category" in data:
            category = data.get("category") or FaqCategory.DEFAULT
            # Same fallback as the add form: an unknown section would land the
            # question somewhere the page never renders.
            entry.category = category if category in FaqCategory.ALL else FaqCategory.DEFAULT

        db.session.commit()
        return entry.to_dict(), 200

    @jwt_required()
    def delete(self, faq_id):
        """Admin-only. Deletes an FAQ entry."""
        err = _require_role(Role.ADMIN)
        if err:
            return err
        entry = db.session.get(FaqEntry, faq_id)
        if not entry:
            return {"message": "Not found"}, 404
        db.session.delete(entry)
        db.session.commit()
        return {"success": True}, 200


class FaqFeedbackResource(Resource):
    """'Was this helpful?' on one help article. Signed-in readers only — an
    anonymous answer can't be capped at one per person, so it would let the
    count be inflated at will.

    Uses optional JWT rather than @jwt_required() on purpose: the Help and
    FAQ page itself is public, and a hard 401 here would trip the frontend's
    "session expired" handler and bounce an anonymous visitor to /login —
    a rude thing to do to someone quietly reading the help. A 403 lets the
    page show an inline "please log in" message instead."""
    @jwt_required(optional=True)
    def post(self):
        user = _current_user() if get_jwt_identity() else None
        if not user:
            return {"message": "Please log in to answer this"}, 403
        data = request.get_json() or {}
        article_id = (data.get("article_id") or "").strip()
        if not article_id:
            return {"message": "Which article is this about?"}, 400
        helpful = data.get("helpful") is True

        existing = FaqFeedback.query.filter_by(article_id=article_id, user_id=user.id).first()
        if existing:
            existing.helpful = helpful
        else:
            db.session.add(FaqFeedback(article_id=article_id, helpful=helpful, user_id=user.id))
        try:
            db.session.commit()
        except IntegrityError:
            # Two votes on the same article racing each other.
            db.session.rollback()
        return {"success": True}, 200

    @jwt_required()
    def get(self):
        err = _require_role(Role.ADMIN)
        if err:
            return err
        tally = {}
        for v in FaqFeedback.query.all():
            bucket = tally.setdefault(v.article_id, {"yes": 0, "no": 0})
            bucket["yes" if v.helpful else "no"] += 1
        return tally, 200


# ── Image Upload ──────────────────────────────────────────────────────────────

class UploadResource(Resource):
    @jwt_required()
    def post(self):
        """Saves an uploaded file to uploads/ under a random filename and
        returns its URL — used for complaint/facility/post photos."""
        if "file" not in request.files:
            return {"message": "No file provided"}, 400
        file = request.files["file"]
        if file.filename == "" or not _allowed_file(file.filename):
            return {"message": "Invalid file type"}, 400
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_folder = os.environ.get("UPLOAD_FOLDER") or os.path.join(os.path.dirname(__file__), "..", "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        return {"url": f"/api/uploads/{filename}"}, 201


class UploadServeResource(Resource):
    def get(self, filename):
        """Serves a previously uploaded file straight from the uploads/
        folder by filename — the actual bytes behind every /uploads/...
        URL that UploadResource hands back."""
        upload_folder = os.environ.get("UPLOAD_FOLDER") or os.path.join(os.path.dirname(__file__), "..", "uploads")
        return send_from_directory(os.path.abspath(upload_folder), filename)


# ── AI Category Suggestion (Gemini) ──────────────────────────────────────────

class AISuggestResource(Resource):
    @jwt_required()
    def post(self):
        """Suggests a complaint category from a free-text description via
        Gemini, falling back to keyword matching if no GEMINI_API_KEY is
        configured."""
        data = request.get_json() or {}
        description = data.get("description", "").strip()
        if not description:
            return {"category": "", "message": "No description provided"}, 400

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            # Fallback: simple keyword matching if no API key
            desc_lower = description.lower()
            if any(w in desc_lower for w in ["road", "pothole", "footpath", "speed", "manhole"]):
                return {"category": "road", "confidence": "keyword_match"}
            if any(w in desc_lower for w in ["light", "electric", "power", "wire", "pole"]):
                return {"category": "electricity", "confidence": "keyword_match"}
            if any(w in desc_lower for w in ["water", "pipe", "leak", "drainage", "flood"]):
                return {"category": "water", "confidence": "keyword_match"}
            if any(w in desc_lower for w in ["garbage", "trash", "waste", "dirty", "sanit"]):
                return {"category": "sanitation", "confidence": "keyword_match"}
            if any(w in desc_lower for w in ["park", "playground", "bench", "garden", "tree", "swing", "slide"]):
                return {"category": "parks", "confidence": "keyword_match"}
            return {"category": "other", "confidence": "keyword_match"}

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = (
                f"You are a civic complaint classifier. Classify this complaint into exactly one category.\n"
                f"Categories: road, water, electricity, sanitation, waste, parks, maintenance, other\n"
                f"Complaint: \"{description}\"\n"
                f"Reply with only the category word, nothing else."
            )
            result = model.generate_content(prompt)
            category = result.text.strip().lower().split()[0]
            valid = {"road", "water", "electricity", "sanitation", "waste", "parks", "maintenance", "other"}
            if category not in valid:
                category = "other"
            return {"category": category, "confidence": "ai"}
        except Exception as e:
            return {"category": "other", "confidence": "error", "message": str(e)}


class AIExtractFromImageResource(Resource):
    """Reads a photo of a handwritten/printed complaint note and extracts
    structured fields (category, title, description, address, priority) using
    Gemini's vision model, so a citizen can fill the complaint form just by
    photographing a paper note instead of typing everything out."""
    @jwt_required()
    def post(self):
        if "file" not in request.files:
            return {"message": "No file provided"}, 400
        file = request.files["file"]
        if file.filename == "" or not _allowed_file(file.filename):
            return {"message": "Invalid file type"}, 400

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return {"message": "AI scanning isn't configured on this server (no GEMINI_API_KEY)."}, 503

        image_bytes = file.read()
        mime_type = file.mimetype or "image/jpeg"

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = (
                "This image is a photo of a handwritten or printed note describing a civic complaint "
                "(e.g. a broken streetlight, pothole, water leak). Read it and extract the details.\n"
                "Reply with ONLY a JSON object, no other text, in exactly this shape:\n"
                '{"category": "...", "title": "...", "description": "...", "address": "...", "priority": "..."}\n'
                "- category must be exactly one of: road, water, electricity, sanitation, waste, parks, maintenance, complaint, other\n"
                "- priority must be exactly one of: low, medium, high, urgent\n"
                "- title: a short summary (under 10 words)\n"
                "- description: the full complaint detail in your own words, based on what's written\n"
                "- address: the location/address mentioned in the note, or an empty string if none is mentioned\n"
                "If the image doesn't look like a complaint note at all, still do your best with whatever text is visible."
            )
            result = model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": image_bytes},
            ])
            raw = result.text.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").lstrip("json").strip()
            extracted = json.loads(raw)
        except json.JSONDecodeError:
            return {"message": "Could not read structured details from that image. Try a clearer photo, or fill the form manually."}, 422
        except Exception as e:
            return {"message": f"AI scan failed: {e}"}, 502

        category = str(extracted.get("category", "")).strip().lower()
        if category not in VALID_CATEGORIES:
            category = "other"
        priority = str(extracted.get("priority", "")).strip().lower()
        if priority not in Priority.ALL:
            priority = Priority.MEDIUM

        # The scan is read for its text and then dropped — deliberately not
        # written to uploads/. It's a photo of a paper complaint, not evidence
        # of the actual issue, so NewRequest.vue never attaches it to the
        # complaint (see the comment there); saving it anyway just left a file
        # in uploads/ that nothing ever referenced, one per scan, forever.
        # A citizen who does want a photo on the complaint adds it through
        # Upload Photos, which goes to UploadResource.
        return {
            "category": category,
            "title": str(extracted.get("title", "")).strip()[:200],
            "description": str(extracted.get("description", "")).strip(),
            "address": str(extracted.get("address", "")).strip(),
            "priority": priority,
        }, 200


# ── Booking Invoice ───────────────────────────────────────────────────────────

class BookingInvoiceResource(Resource):
    @jwt_required()
    def get(self, booking_id):
        """A booking's downloadable invoice details."""
        user = _current_user()
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return {"message": "Booking not found"}, 404
        if user.role == Role.STAFF:
            return {"message": "Access denied"}, 403
        if user.role == Role.CITIZEN and booking.citizen_id != user.id:
            return {"message": "Access denied"}, 403

        # Calculate hours and total
        start = datetime.combine(booking.booking_date, booking.start_time)
        end = datetime.combine(booking.booking_date, booking.end_time)
        hours = (end - start).seconds / 3600
        fee_per_hour = booking.facility.fee_per_hour if booking.facility else 0
        total = round(fee_per_hour * hours, 2)

        return {
            "invoice_number": f"INV-{booking.id:05d}",
            "booking_id": booking.id,
            "citizen_name": booking.citizen.name if booking.citizen else "",
            "citizen_phone": booking.citizen.phone if booking.citizen else "",
            "facility_name": booking.facility.name if booking.facility else "",
            "facility_address": booking.facility.address if booking.facility else "",
            "booking_date": booking.booking_date.isoformat(),
            "start_time": booking.start_time.strftime("%H:%M"),
            "end_time": booking.end_time.strftime("%H:%M"),
            "hours": hours,
            "purpose": booking.purpose,
            "attendees": booking.attendees,
            "fee_per_hour": fee_per_hour,
            "total": total,
            "payment_status": booking.payment.status if booking.payment else "free",
            "payment_method": booking.payment.method if booking.payment else None,
            "paid_at": booking.payment.paid_at.isoformat() + "+05:30" if booking.payment and booking.payment.paid_at else None,
            "transaction_ref": booking.payment.transaction_ref if booking.payment else None,
            "issued_at": now_ist().strftime("%d %b %Y, %I:%M %p"),
        }


# ── Subscriptions (Cyber Panchayat Premium — recurring monthly membership) ────
# One Subscription row per citizen; one SubscriptionPayment per billing cycle.
# There's no payment gateway or cron in this app, so each cycle's invoice is
# generated lazily by _sync_subscription_billing() the next time the
# subscription is read (see that function's docstring for why that's fine).

class SubscriptionMeResource(Resource):
    @jwt_required()
    def get(self):
        """Citizen-only. The signed-in citizen's own Premium subscription
        status and next billing info — returns subscribed: false with no
        error if they've never subscribed at all."""
        err = _require_role(Role.CITIZEN)
        if err:
            return err
        user = _current_user()
        sub = Subscription.query.filter_by(citizen_id=user.id).first()
        if not sub:
            return {"subscribed": False, "subscription": None, "monthly_fee": SUBSCRIPTION_FEE}, 200
        _sync_subscription_billing(sub)
        return {
            "subscribed": sub.status == SubscriptionStatus.ACTIVE,
            "subscription": sub.to_dict(),
            "monthly_fee": SUBSCRIPTION_FEE,
        }, 200


class SubscriptionSubscribeResource(Resource):
    @jwt_required()
    def post(self):
        """Citizen-only. Starts (or resumes) a monthly Premium subscription
        and generates the first cycle's payment record."""
        err = _require_role(Role.CITIZEN)
        if err:
            return err
        user = _current_user()
        sub = Subscription.query.filter_by(citizen_id=user.id).first()
        if sub and sub.status == SubscriptionStatus.ACTIVE:
            return {"message": "You already have an active subscription"}, 400

        data = request.get_json() or {}
        method = data.get("method", "upi")
        if method not in ["online", "upi", "card", "netbanking"]:
            method = "upi"

        today = now_ist().date()
        period_end = _add_month(today)
        if sub:
            # started_at is deliberately left untouched on a resubscribe — it's
            # the citizen's original join date. A fresh period always starts
            # from today, however long they were away — simple pay-per-month,
            # no makeup billing for the time they missed. Logged as a
            # "rejoined" event so admin can see every lapse-and-return.
            sub.status = SubscriptionStatus.ACTIVE
            sub.next_billing_date = period_end
            sub.payment_method = method
            db.session.add(SubscriptionEvent(subscription_id=sub.id, event_type="rejoined"))
        else:
            sub = Subscription(citizen_id=user.id, next_billing_date=period_end, payment_method=method)
            db.session.add(sub)
            try:
                db.session.flush()
            except IntegrityError:
                # A concurrent double-submit raced us to create this citizen's
                # (unique) Subscription row first — treat it the same as the
                # already-subscribed check above instead of a raw 500.
                db.session.rollback()
                return {"message": "You already have an active subscription"}, 400

        # Guards a concurrent double-submit from creating two invoices for the same cycle.
        payment = SubscriptionPayment.query.filter_by(subscription_id=sub.id, period_start=today).first()
        if not payment:
            payment = SubscriptionPayment(
                subscription_id=sub.id, citizen_id=user.id, amount=SUBSCRIPTION_FEE,
                period_start=today, period_end=period_end,
                status=PaymentStatus.PAID, method=method,
                transaction_ref=f"SUB-TXN-{uuid.uuid4().hex[:10].upper()}", paid_at=now_ist(),
            )
            db.session.add(payment)

        admins = User.query.filter_by(role=Role.ADMIN).all()
        for admin in admins:
            _notify(admin.id, "New Premium Subscriber",
                    f"{user.name} subscribed to Cyber Panchayat Premium (Rs.{SUBSCRIPTION_FEE:.0f}/month).",
                    "subscription")

        db.session.commit()
        return {"subscription": sub.to_dict(), "payment": payment.to_dict()}, 201


class SubscriptionPaymentsListResource(Resource):
    @jwt_required()
    def get(self):
        """Citizen-only. The signed-in citizen's own subscription
        payment/billing history, most recent period first; an empty list if
        they've never subscribed."""
        err = _require_role(Role.CITIZEN)
        if err:
            return err
        user = _current_user()
        sub = Subscription.query.filter_by(citizen_id=user.id).first()
        if not sub:
            return [], 200
        _sync_subscription_billing(sub)
        payments = sub.payments.order_by(SubscriptionPayment.period_start.desc()).all()
        return [p.to_dict() for p in payments], 200


class SubscriptionInvoiceResource(Resource):
    @jwt_required()
    def get(self, payment_id):
        """A subscription billing cycle's downloadable invoice details —
        the payer or an admin only."""
        user = _current_user()
        payment = db.session.get(SubscriptionPayment, payment_id)
        if not payment:
            return {"message": "Not found"}, 404
        if user.role == Role.STAFF:
            return {"message": "Access denied"}, 403
        if user.role == Role.CITIZEN and payment.citizen_id != user.id:
            return {"message": "Access denied"}, 403

        return {
            "invoice_number": f"SUB-INV-{payment.id:05d}",
            "payment_id": payment.id,
            "citizen_name": payment.payer.name if payment.payer else "",
            "citizen_email": payment.payer.email if payment.payer else "",
            "plan": "Cyber Panchayat Premium Membership",
            "period_start": payment.period_start.isoformat(),
            "period_end": payment.period_end.isoformat(),
            "amount": payment.amount,
            "status": payment.status,
            "method": payment.method,
            "transaction_ref": payment.transaction_ref,
            "paid_at": payment.paid_at.isoformat() + "+05:30" if payment.paid_at else None,
            "issued_at": now_ist().strftime("%d %b %Y, %I:%M %p"),
        }, 200


def _subscription_with_history(sub):
    """A subscription dict with its full billing history + expire/rejoin
    event log attached — shared by the admin list and the detail page so
    both return the exact same shape."""
    d = sub.to_dict()
    d["payments"] = [p.to_dict() for p in
                      sub.payments.order_by(SubscriptionPayment.period_start.desc()).all()]
    d["history"] = [e.to_dict() for e in sub.events.all()]
    return d


class SubscriptionListResource(Resource):
    """Admin visibility: every citizen's subscription status + revenue stats."""
    @jwt_required()
    def get(self):
        err = _require_role(Role.ADMIN)
        if err:
            return err
        subs = Subscription.query.order_by(Subscription.started_at.desc()).all()
        for sub in subs:
            _sync_subscription_billing(sub)
        active_count = sum(1 for s in subs if s.status == SubscriptionStatus.ACTIVE)
        total_collected = db.session.query(db.func.sum(SubscriptionPayment.amount)) \
            .filter_by(status=PaymentStatus.PAID).scalar() or 0
        pending_count = SubscriptionPayment.query.filter_by(status=PaymentStatus.PENDING).count()

        return {
            "subscriptions": [_subscription_with_history(s) for s in subs],
            "stats": {
                "active": active_count,
                "cancelled": len(subs) - active_count,
                "monthly_recurring_revenue": active_count * SUBSCRIPTION_FEE,
                "total_collected": total_collected,
                "pending_payments": pending_count,
            },
        }, 200


class SubscriptionDetailResource(Resource):
    """Admin visibility: one citizen's full subscription record — status,
    lifetime billing, and the complete expire/rejoin event history. Backs the
    Subscription Detail page reached from the "View" action on Manage
    Subscriptions."""
    @jwt_required()
    def get(self, sub_id):
        err = _require_role(Role.ADMIN)
        if err:
            return err
        sub = db.session.get(Subscription, sub_id)
        if not sub:
            return {"message": "Subscription not found"}, 404
        _sync_subscription_billing(sub)
        return _subscription_with_history(sub), 200


# ── Register all resources ────────────────────────────────────────────────────

def register_resources(api):
    # API Info
    api.add_resource(APIInfoResource, "/")

    # Auth
    api.add_resource(RegisterResource, "/auth/register")
    api.add_resource(LoginResource, "/auth/login")
    api.add_resource(MeResource, "/auth/me")
    api.add_resource(ChangePasswordResource, "/auth/change-password")

    # Requests
    api.add_resource(RequestListResource, "/requests")
    api.add_resource(RequestResource, "/requests/<int:request_id>")
    api.add_resource(RequestStatusResource, "/requests/<int:request_id>/status")
    api.add_resource(RequestBudgetTagResource, "/requests/<int:request_id>/budget-tag")
    api.add_resource(RequestCommunityResource, "/requests/community")
    api.add_resource(RequestSimilarResource, "/requests/similar")
    api.add_resource(RequestUpvoteResource, "/requests/<int:request_id>/upvote")

    # Assignments
    api.add_resource(AssignmentListResource, "/assignments")
    api.add_resource(AssignmentResource, "/assignments/<int:assignment_id>")

    # Facilities
    api.add_resource(FacilityListResource, "/facilities")
    api.add_resource(FacilityResource, "/facilities/<int:facility_id>")
    api.add_resource(FacilityAvailabilityResource, "/facilities/<int:facility_id>/availability")
    api.add_resource(FacilityRatingResource, "/facilities/<int:facility_id>/ratings")
    api.add_resource(FacilityFavoriteListResource, "/facilities/favorites")
    api.add_resource(FacilityFavoriteDetailResource, "/facilities/favorites/detail")

    # Bookings
    api.add_resource(BookingListResource, "/bookings")
    api.add_resource(BookingResource, "/bookings/<int:booking_id>")
    api.add_resource(BookingStatusResource, "/bookings/<int:booking_id>/status")
    api.add_resource(BookingCompleteResource, "/bookings/<int:booking_id>/complete")
    api.add_resource(BookingRequestRefundResource, "/bookings/<int:booking_id>/request-refund")
    api.add_resource(BookingRejectRefundResource, "/bookings/<int:booking_id>/reject-refund")

    # Payments
    api.add_resource(PaymentListResource, "/payments")
    api.add_resource(PaymentPayResource, "/payments/<int:payment_id>/pay")

    # Subscriptions (Cyber Panchayat Premium)
    api.add_resource(SubscriptionMeResource, "/subscriptions/me")
    api.add_resource(SubscriptionSubscribeResource, "/subscriptions/subscribe")
    api.add_resource(SubscriptionPaymentsListResource, "/subscriptions/payments")
    api.add_resource(SubscriptionInvoiceResource, "/subscriptions/payments/<int:payment_id>/invoice")
    api.add_resource(SubscriptionListResource, "/admin/subscriptions")
    api.add_resource(SubscriptionDetailResource, "/admin/subscriptions/<int:sub_id>")

    # Notifications
    api.add_resource(NotificationListResource, "/notifications")
    api.add_resource(NotificationReadResource, "/notifications/<int:notif_id>/read")
    api.add_resource(NotificationArchiveResource, "/notifications/<int:notif_id>/archive")
    api.add_resource(NotificationClearAllResource, "/notifications/clear-all")

    # Dashboard
    api.add_resource(DashboardResource, "/dashboard")

    # Admin Users
    api.add_resource(AdminUserListResource, "/admin/users")
    api.add_resource(AdminUserResource, "/admin/users/<int:user_id>")
    api.add_resource(StaffListResource, "/admin/staff")

    # Departments
    api.add_resource(DepartmentListResource, "/departments")
    api.add_resource(DepartmentResource, "/departments/<int:dept_id>")

    # Officers
    api.add_resource(OfficerListResource, "/officers")
    api.add_resource(OfficerResource, "/officers/<int:officer_id>")

    # Public Track
    api.add_resource(PublicTrackResource, "/track")
    api.add_resource(PublicStatsResource, "/public-stats")

    # Reports
    api.add_resource(ReportsResource, "/reports")

    # Community Posts
    api.add_resource(PostListResource, "/posts")
    api.add_resource(PostResourceItem, "/posts/<int:post_id>")
    api.add_resource(PostLikeResource, "/posts/<int:post_id>/like")
    api.add_resource(PostCommentListResource, "/posts/<int:post_id>/comments")
    api.add_resource(PostCommentResource, "/posts/<int:post_id>/comments/<int:comment_id>")

    # Help & FAQ
    api.add_resource(FaqListResource, "/faqs")
    api.add_resource(FaqResource, "/faqs/<int:faq_id>")
    api.add_resource(FaqFeedbackResource, "/faqs/feedback")

    # File Upload
    api.add_resource(UploadResource, "/upload")
    api.add_resource(UploadServeResource, "/uploads/<string:filename>")

    # AI
    api.add_resource(AISuggestResource, "/ai/suggest")
    api.add_resource(AIExtractFromImageResource, "/ai/extract-from-image")

    # Invoice
    api.add_resource(BookingInvoiceResource, "/bookings/<int:booking_id>/invoice")
