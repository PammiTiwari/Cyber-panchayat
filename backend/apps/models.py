import json
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

MAX_IMAGES = 3


def _dump_urls(urls):
    if urls is None:
        urls = []
    elif isinstance(urls, str):
        # A bare string would otherwise be iterated character-by-character.
        urls = [urls]
    elif not isinstance(urls, (list, tuple)):
        urls = []
    return json.dumps(list(urls)[:MAX_IMAGES])


def _load_urls(raw):
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return []


class Role:
    CITIZEN = "citizen"
    STAFF = "staff"
    ADMIN = "admin"
    ALL = [CITIZEN, STAFF, ADMIN]

class RequestStatus:
    PENDING = "pending"
    ASSIGNED = "assigned"
    REASSIGNED = "reassigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"
    ON_HOLD_WEATHER = "on_hold_weather"
    ALL = [PENDING, ASSIGNED, REASSIGNED, IN_PROGRESS, RESOLVED, CLOSED, REJECTED, ON_HOLD_WEATHER]

class Priority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    ALL = [LOW, MEDIUM, HIGH, URGENT]

class PostCategory:
    """Categories of a community-feed post.

    Mirrors CATEGORIES in frontend/src/utils/postFilters.js: the create-post
    form and the feed's filter offer exactly ALL, in this order, with GENERAL
    pre-selected. GENERAL leads the list because it is also the fallback
    applied to a post that arrives without a category.

    Scope is the community feed and nothing else. Announcements are a separate
    feature with their own page and publish flow and never appear in the feed,
    so ANNOUNCEMENT_CATEGORY below is deliberately not a member here — keeping
    it out means no dropdown built from this list can ever surface it.

    Separate from ServiceRequest categories / DEPT_MAP below: a post is not a
    complaint and is never routed to a department by its category.
    """
    GENERAL = "general"
    ROAD = "road"
    WATER = "water"
    ELECTRICITY = "electricity"
    SANITATION = "sanitation"
    WASTE = "waste"
    PARKS = "parks"
    MAINTENANCE = "maintenance"

    DEFAULT = GENERAL
    ALL = [GENERAL, ROAD, WATER, ELECTRICITY, SANITATION, WASTE, PARKS, MAINTENANCE]


# Announcements share the posts table but are not a community category: they are
# published and read only through /announcements, and the feed query excludes
# them. Named here so the string isn't scattered as a literal, and kept out of
# PostCategory so the two vocabularies can never be confused for one another.
ANNOUNCEMENT_CATEGORY = "announcement"


class FaqCategory:
    """Sections on the Help and FAQ page.

    Mirrors FAQ_CATEGORIES in frontend/src/data/chatbotFaq.js. An admin picks
    one of these when adding a question, so the ids have to match that file
    exactly. If they drift, a saved question lands in a section the page never
    renders and simply disappears.

    Nothing to do with PostCategory above. That one groups community posts.
    This one groups help articles.
    """
    COMPLAINTS = "complaints"
    PREMIUM = "premium"
    FACILITIES = "facilities"
    COMMUNITY = "community"
    ACCOUNT = "account"
    TROUBLESHOOTING = "troubleshooting"
    STAFF = "staff"
    ADMIN = "admin"

    # The add-a-question form opens on this one, so an admin who does not pick
    # a section still gets a sensible home for the answer.
    DEFAULT = TROUBLESHOOTING
    ALL = [COMPLAINTS, PREMIUM, FACILITIES, COMMUNITY, ACCOUNT, TROUBLESHOOTING, STAFF, ADMIN]


class BookingStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    # The slot's date came and went while the fee was still unpaid — whether
    # the admin never got round to confirming it or the citizen never paid.
    # Distinct from CANCELLED because nobody decided to call it off; it simply
    # ran out of time. Terminal: an expired booking cannot be confirmed, paid
    # for or completed afterwards.
    EXPIRED = "expired"

class PaymentStatus:
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"
    CANCELLED = "cancelled"  # booking was cancelled before this payment was ever made
    REFUND_REQUESTED = "refund_requested"  # citizen asked for money back, awaiting admin review

class SubscriptionStatus:
    ACTIVE = "active"
    CANCELLED = "cancelled"

SUBSCRIPTION_FEE = 100.0  # Rs./month — flat, no GST (a membership fee, not a facility booking)

DEPT_MAP = {
    "road": "Road Maintenance",
    "electricity": "Electricity Department",
    "water": "Water Supply Department",
    "sanitation": "Sanitation Department",
    "waste": "Sanitation Department",
    "parks": "Parks & Public Spaces",
    "complaint": "General Affairs",
    "maintenance": "General Affairs",
    "other": "General Affairs",
}

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    """Naive IST wall-clock — the app serves one Indian locality, and the
    host/WSL clock runs UTC, so timestamps are stored as IST directly and
    serialized with an explicit +05:30 offset in to_dict()."""
    return datetime.now(IST).replace(tzinfo=None)


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text)
    officer_incharge_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=now_ist)
    officer = db.relationship("User", foreign_keys=[officer_incharge_id])

    def to_dict(self):
        return {
            "id": self.id,
            "dept_id": f"DPT{str(self.id).zfill(2)}",
            "name": self.name,
            "description": self.description,
            "officer_incharge_id": self.officer_incharge_id,
            "officer_name": self.officer.name if self.officer else None,
            "officer_phone": self.officer.phone if self.officer else None,
            "created_at": self.created_at.isoformat() + "+05:30",
        }


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.CITIZEN)
    phone = db.Column(db.String(20))
    ward = db.Column(db.String(50))
    department = db.Column(db.String(100))  # for staff: their department name
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)

    service_requests = db.relationship("ServiceRequest", foreign_keys="ServiceRequest.citizen_id", backref="citizen", lazy="dynamic")
    assignments = db.relationship("Assignment", foreign_keys="Assignment.staff_id", backref="staff", lazy="dynamic")
    bookings = db.relationship("Booking", foreign_keys="Booking.citizen_id", backref="citizen", lazy="dynamic")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "officer_id": f"OFF{str(self.id).zfill(2)}",
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "phone": self.phone,
            "ward": self.ward,
            "department": self.department,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() + "+05:30",
        }


class ServiceRequest(db.Model):
    __tablename__ = "service_requests"
    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    address = db.Column(db.String(300), nullable=False)
    ward = db.Column(db.String(50))
    latitude = db.Column(db.Float)   # geotag from the map picker (optional)
    longitude = db.Column(db.Float)
    priority = db.Column(db.String(20), nullable=False, default=Priority.MEDIUM)
    status = db.Column(db.String(30), nullable=False, default=RequestStatus.PENDING)
    admin_notes = db.Column(db.Text)
    _image_urls = db.Column("image_urls", db.Text)
    _evidence_urls = db.Column("evidence_urls", db.Text)
    rating = db.Column(db.Integer)        # 1-5, given by citizen when closing a resolved request
    feedback = db.Column(db.Text)
    pending_funds = db.Column(db.Boolean, nullable=False, default=False)  # admin-tagged: needs budget allocation before work can proceed
    hold_reason = db.Column(db.Text)      # why a request is on_hold_weather (or other admin hold), shown to the citizen
    department_override = db.Column(db.String(100))  # set when admin assigns to an officer outside the category's default department (e.g. citizen miscategorized it)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist, nullable=False)
    resolved_at = db.Column(db.DateTime)
    in_progress_at = db.Column(db.DateTime)  # when status first became in_progress — shown on the citizen timeline
    in_progress_notes = db.Column(db.Text)  # staff's remark at the in_progress step, kept separate from admin_notes so a later step doesn't overwrite it
    # Every in_progress update, not just the last one. in_progress_notes holds
    # only the most recent remark and in_progress_at only the first timestamp,
    # so between them a second update either overwrote the earlier remark or
    # left it dated to a day it was not written on. This keeps each remark
    # beside the moment it was actually made.
    _progress_log = db.Column("progress_log", db.Text)
    resolved_notes = db.Column(db.Text)     # staff's remark at the resolved step
    assignment = db.relationship("Assignment", backref="request", uselist=False, cascade="all, delete-orphan")
    upvotes = db.relationship("ComplaintUpvote", backref="request", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def image_urls(self):
        return _load_urls(self._image_urls)

    @image_urls.setter
    def image_urls(self, value):
        self._image_urls = _dump_urls(value)

    @property
    def progress_log(self):
        """[{"at": iso8601, "note": str|None}, ...] — oldest first."""
        entries = _load_urls(self._progress_log)
        return [e for e in entries if isinstance(e, dict)]

    def add_progress_entry(self, at, note):
        """Appends one in_progress update. A missing remark is stored as None
        rather than skipped, so the timeline can say so instead of hiding a
        step that did happen."""
        entries = self.progress_log
        entries.append({"at": at.isoformat() + "+05:30", "note": note or None})
        self._progress_log = json.dumps(entries)

    @progress_log.setter
    def progress_log(self, value):
        self._progress_log = json.dumps(list(value or []))

    @property
    def evidence_urls(self):
        return _load_urls(self._evidence_urls)

    @evidence_urls.setter
    def evidence_urls(self, value):
        self._evidence_urls = _dump_urls(value)

    def get_department(self):
        return self.department_override or DEPT_MAP.get(self.category, "General Affairs")

    def to_dict(self):
        return {
            "id": self.id,
            "cmp_id": f"CMP{str(self.id).zfill(4)}",
            "citizen_id": self.citizen_id,
            "citizen_name": self.citizen.name if self.citizen else None,
            "citizen_email": self.citizen.email if self.citizen else None,
            "citizen_phone": self.citizen.phone if self.citizen else None,
            "category": self.category,
            "department": self.get_department(),
            "title": self.title,
            "description": self.description,
            "address": self.address,
            "ward": self.ward,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "priority": self.priority,
            "status": self.status,
            "admin_notes": self.admin_notes,
            "image_urls": self.image_urls,
            "evidence_urls": self.evidence_urls,
            "rating": self.rating,
            "feedback": self.feedback,
            "pending_funds": self.pending_funds,
            "hold_reason": self.hold_reason,
            "upvotes_count": self.upvotes.count(),
            "assignment": self.assignment.to_dict() if self.assignment else None,
            "created_at": self.created_at.isoformat() + "+05:30",
            "updated_at": self.updated_at.isoformat() + "+05:30",
            "resolved_at": self.resolved_at.isoformat() + "+05:30" if self.resolved_at else None,
            "in_progress_at": self.in_progress_at.isoformat() + "+05:30" if self.in_progress_at else None,
            "in_progress_notes": self.in_progress_notes,
            "progress_log": self.progress_log,
            "resolved_notes": self.resolved_notes,
        }

    def to_public_dict(self):
        """Safe subset for the unauthenticated public tracking page.
        Excludes citizen name/email/phone (PII) and internal admin_notes/evidence_urls —
        keeps everything about the *complaint* itself (location, description, status,
        assigned department) since that's the point of a public tracking lookup."""
        return {
            "id": self.id,
            "cmp_id": f"CMP{str(self.id).zfill(4)}",
            "category": self.category,
            "department": self.get_department(),
            "title": self.title,
            "description": self.description,
            "address": self.address,
            "ward": self.ward,
            "priority": self.priority,
            "status": self.status,
            "hold_reason": self.hold_reason,
            "pending_funds": self.pending_funds,
            "image_urls": self.image_urls,
            "assignment": self.assignment.to_dict() if self.assignment else None,
            "upvotes_count": self.upvotes.count(),
            "created_at": self.created_at.isoformat() + "+05:30",
            "updated_at": self.updated_at.isoformat() + "+05:30",
            "resolved_at": self.resolved_at.isoformat() + "+05:30" if self.resolved_at else None,
            "progress_log": self.progress_log,
        }


class Assignment(db.Model):
    __tablename__ = "assignments"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), unique=True, nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notes = db.Column(db.Text)
    assigned_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    completed_at = db.Column(db.DateTime)
    assigner = db.relationship("User", foreign_keys=[assigned_by])

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "staff_id": self.staff_id,
            "staff_name": self.staff.name if self.staff else None,
            "staff_department": self.staff.department if self.staff else None,
            "assigned_by": self.assigned_by,
            "notes": self.notes,
            "assigned_at": self.assigned_at.isoformat() + "+05:30",
            "completed_at": self.completed_at.isoformat() + "+05:30" if self.completed_at else None,
        }


class Facility(db.Model):
    __tablename__ = "facilities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    facility_type = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    ward = db.Column(db.String(50))
    capacity = db.Column(db.Integer, nullable=False, default=50)
    description = db.Column(db.Text)
    amenities = db.Column(db.String(500))
    fee_per_hour = db.Column(db.Float, nullable=False, default=0.0)
    _image_urls = db.Column("image_urls", db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    bookings = db.relationship("Booking", backref="facility", lazy="dynamic", cascade="all, delete-orphan")
    ratings = db.relationship("FacilityRating", backref="facility", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def image_urls(self):
        return _load_urls(self._image_urls)

    @image_urls.setter
    def image_urls(self, value):
        self._image_urls = _dump_urls(value)

    def to_dict(self):
        rating_values = [r.rating for r in self.ratings]
        return {
            "id": self.id, "name": self.name, "facility_type": self.facility_type,
            "address": self.address, "ward": self.ward, "capacity": self.capacity,
            "description": self.description, "amenities": self.amenities,
            "fee_per_hour": self.fee_per_hour, "image_urls": self.image_urls, "is_active": self.is_active,
            "created_at": self.created_at.isoformat() + "+05:30",
            "avg_rating": round(sum(rating_values) / len(rating_values), 1) if rating_values else None,
            "rating_count": len(rating_values),
        }


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), nullable=False)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.String(300), nullable=False)
    attendees = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), nullable=False, default=BookingStatus.PENDING)
    fee = db.Column(db.Float, nullable=False, default=0.0)
    admin_notes = db.Column(db.String(500))
    # Who cancelled it: "citizen" (self-cancel) or "admin" (admin/refund-approval
    # path). Null unless status is actually cancelled.
    cancelled_by = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    payment = db.relationship("Payment", backref="booking", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "facility_id": self.facility_id,
            "facility_name": self.facility.name if self.facility else None,
            "facility_type": self.facility.facility_type if self.facility else None,
            "citizen_id": self.citizen_id,
            "citizen_name": self.citizen.name if self.citizen else None,
            "booking_date": self.booking_date.isoformat(),
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
            "purpose": self.purpose, "attendees": self.attendees,
            "status": self.status, "fee": self.fee, "admin_notes": self.admin_notes,
            "cancelled_by": self.cancelled_by,
            "payment": self.payment.to_dict() if self.payment else None,
            "created_at": self.created_at.isoformat() + "+05:30",
        }


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), unique=True, nullable=False)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=PaymentStatus.PENDING)
    method = db.Column(db.String(50), default="online")
    transaction_ref = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    paid_at = db.Column(db.DateTime)
    refund_reason = db.Column(db.Text)  # admin's note when the refund is resolved (approved or rejected)
    refund_request_reason = db.Column(db.Text)  # citizen's stated reason when requesting the refund
    # Kept apart from refund_reason so a rejection survives what comes after
    # it. Both used to share one column, so approving a refund later
    # overwrote the note explaining why it had been turned down first — and
    # the booking could no longer tell you its own history.
    refund_rejected_reason = db.Column(db.Text)
    # The reason is optional, but the rejection itself is a fact. Deriving
    # "was rejected" from the note meant an admin who declined without typing
    # anything left no trace at all — and once the money was refunded later,
    # nothing showed the request had ever been turned down first.
    refund_rejected_at = db.Column(db.DateTime)
    payer = db.relationship("User", foreign_keys=[citizen_id])

    def to_dict(self):
        return {
            "id": self.id, "booking_id": self.booking_id,
            "citizen_id": self.citizen_id,
            "citizen_name": self.payer.name if self.payer else None,
            "amount": self.amount, "status": self.status, "method": self.method,
            "transaction_ref": self.transaction_ref,
            "created_at": self.created_at.isoformat() + "+05:30",
            "paid_at": self.paid_at.isoformat() + "+05:30" if self.paid_at else None,
            "refund_reason": self.refund_reason,
            "refund_request_reason": self.refund_request_reason,
            "refund_rejected_reason": self.refund_rejected_reason,
            "refund_rejected_at": self.refund_rejected_at.isoformat() + "+05:30" if self.refund_rejected_at else None,
        }


class FacilityRating(db.Model):
    """A citizen's 1-5 star rating of a facility, given after a completed
    booking. One rating per (facility, citizen) — a repeat booking edits the
    same row rather than adding a second one, matching how the facility's
    average is expected to work (one voice per citizen, not one per visit)."""
    __tablename__ = "facility_ratings"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), nullable=False)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"))
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist, nullable=False)
    citizen = db.relationship("User", foreign_keys=[citizen_id])
    __table_args__ = (db.UniqueConstraint("facility_id", "citizen_id", name="uq_facility_rating_citizen"),)

    def to_dict(self):
        return {
            "id": self.id, "facility_id": self.facility_id, "booking_id": self.booking_id,
            "citizen_id": self.citizen_id, "citizen_name": self.citizen.name if self.citizen else None,
            "rating": self.rating, "comment": self.comment,
            "created_at": self.created_at.isoformat() + "+05:30",
            "updated_at": self.updated_at.isoformat() + "+05:30",
        }


class FacilityFavorite(db.Model):
    """A facility a citizen saved to come back to.

    Just the link between a person and a facility, with no state of its own. A
    favourite is either there or it is not, which is why the API toggles it with
    a single call rather than separate add and remove ones.

    Sits next to FacilityRating above but answers a different question. A rating
    is a judgement made after using a facility; a favourite is an intention to
    use it. A citizen can favourite somewhere they have never booked, and can
    rate somewhere they would never save.
    """
    __tablename__ = "facility_favorites"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), nullable=False, index=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    citizen = db.relationship("User", foreign_keys=[citizen_id])
    facility = db.relationship("Facility", foreign_keys=[facility_id])
    # Favouriting twice is the same as favouriting once. Named to match the
    # convention FacilityRating set just above.
    __table_args__ = (db.UniqueConstraint("facility_id", "citizen_id", name="uq_facility_favorite_citizen"),)

    def to_dict(self):
        return {
            "id": self.id,
            "facility_id": self.facility_id,
            "citizen_id": self.citizen_id,
            "facility_name": self.facility.name if self.facility else None,
            "created_at": self.created_at.isoformat() + "+05:30",
        }


class Subscription(db.Model):
    """One row per citizen — the recurring membership itself. Actual money
    changes hands via SubscriptionPayment, one per billing cycle (like a
    Booking having many months instead of just one). Simple pay-per-month:
    one payment buys exactly one month, starting the day it's paid. There is
    no auto-renewal and no manual "cancel" — access just runs out at
    next_billing_date, and the citizen subscribes again whenever they want
    back in (see _sync_subscription_billing)."""
    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=SubscriptionStatus.ACTIVE)
    started_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    next_billing_date = db.Column(db.Date, nullable=False)  # when the current paid month runs out
    payment_method = db.Column(db.String(50))  # how the most recent month was paid: upi/card/netbanking/online
    subscriber = db.relationship("User", foreign_keys=[citizen_id])
    payments = db.relationship("SubscriptionPayment", backref="subscription",
                                lazy="dynamic", cascade="all, delete-orphan",
                                order_by="SubscriptionPayment.id.desc()")
    events = db.relationship("SubscriptionEvent", backref="subscription",
                              lazy="dynamic", cascade="all, delete-orphan",
                              order_by="SubscriptionEvent.occurred_at.desc()")

    def to_dict(self):
        latest = self.payments.first()
        return {
            "id": self.id,
            "citizen_id": self.citizen_id,
            "citizen_name": self.subscriber.name if self.subscriber else None,
            "citizen_email": self.subscriber.email if self.subscriber else None,
            "status": self.status,
            "monthly_fee": SUBSCRIPTION_FEE,
            "started_at": self.started_at.isoformat() + "+05:30",
            "next_billing_date": self.next_billing_date.isoformat(),
            "payment_method": self.payment_method,
            "latest_payment_status": latest.status if latest else None,
        }


class SubscriptionEvent(db.Model):
    """One row per expiry or rejoin — the full history, not just the latest of
    each, so admin can see every lapse-and-return cycle a citizen has been
    through, not only the most recent one."""
    __tablename__ = "subscription_events"
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"), nullable=False)
    event_type = db.Column(db.String(20), nullable=False)  # "expired" or "rejoined"
    occurred_at = db.Column(db.DateTime, default=now_ist, nullable=False)

    def to_dict(self):
        return {"type": self.event_type, "at": self.occurred_at.isoformat() + "+05:30"}


class SubscriptionPayment(db.Model):
    """One invoice-able charge for a single billing cycle of a Subscription."""
    __tablename__ = "subscription_payments"
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"), nullable=False)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=SUBSCRIPTION_FEE)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=PaymentStatus.PENDING)
    method = db.Column(db.String(50))
    transaction_ref = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    paid_at = db.Column(db.DateTime)
    payer = db.relationship("User", foreign_keys=[citizen_id])

    def to_dict(self):
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "citizen_id": self.citizen_id,
            "citizen_name": self.payer.name if self.payer else None,
            "amount": self.amount,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "status": self.status,
            "method": self.method,
            "transaction_ref": self.transaction_ref,
            "created_at": self.created_at.isoformat() + "+05:30",
            "paid_at": self.paid_at.isoformat() + "+05:30" if self.paid_at else None,
        }


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notif_type = db.Column(db.String(50), default="info")
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id, "title": self.title,
            "message": self.message, "notif_type": self.notif_type,
            "is_read": self.is_read, "created_at": self.created_at.isoformat() + "+05:30",
        }


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    # Not nullable: the create-post form always submits a category (it opens on
    # General and offers no blank option), and the API coerces a
    # missing one to DEFAULT, so a post with no category is not a state the
    # product can reach.
    category = db.Column(db.String(50), nullable=False, default=PostCategory.DEFAULT)
    # Both optional, and the form treats them that way: location is trimmed and
    # omitted when blank rather than stored as an empty string, and ward is left
    # unset when it can't be parsed from the location.
    location = db.Column(db.String(200))
    ward = db.Column(db.String(50))
    # What civic topic an announcement is about (reuses PostCategory's values —
    # general/road/water/etc.). Distinct from `category`, which stays the fixed
    # "announcement" sentinel that routes a post to the Announcements page
    # instead of the community feed; this is just a topic tag shown on it.
    # Optional and only meaningful on announcements, so regular community posts
    # (which already carry their topic in `category`) leave it unset.
    topic = db.Column(db.String(50))
    _image_urls = db.Column("image_urls", db.Text)
    # Not nullable: the feed's "Officials only" / "Citizens only" filter splits
    # every post on this flag, so NULL would belong to neither side.
    is_official = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    author = db.relationship("User", foreign_keys=[citizen_id])
    comments = db.relationship("PostComment", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    likes = db.relationship("PostLike", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def image_urls(self):
        return _load_urls(self._image_urls)

    @image_urls.setter
    def image_urls(self, value):
        self._image_urls = _dump_urls(value)

    def to_dict(self, current_user_id=None):
        return {
            "id": self.id, "citizen_id": self.citizen_id,
            "author_name": self.author.name if self.author else None,
            "author_role": self.author.role if self.author else None,
            "author_department": self.author.department if self.author else None,
            "title": self.title, "content": self.content,
            "category": self.category, "location": self.location,
            "ward": self.ward, "topic": self.topic, "image_urls": self.image_urls,
            "is_official": self.is_official,
            "likes_count": self.likes.count(),
            "comments_count": self.comments.count(),
            "liked_by_me": self.likes.filter_by(user_id=current_user_id).count() > 0 if current_user_id else False,
            "created_at": self.created_at.isoformat() + "+05:30",
        }


class PostComment(db.Model):
    __tablename__ = "post_comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # Matches Post: the UI badges a comment as official or not, never neither.
    is_official = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    author = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id, "post_id": self.post_id, "user_id": self.user_id,
            "author_name": self.author.name if self.author else None,
            "author_role": self.author.role if self.author else None,
            "author_department": self.author.department if self.author else None,
            "content": self.content, "is_official": self.is_official,
            "created_at": self.created_at.isoformat() + "+05:30",
        }


class FaqEntry(db.Model):
    """A help article an admin wrote from the Help and FAQ page.

    The help that ships with the app lives in frontend/src/data/chatbotFaq.js
    and is not in the database. This table is only for questions an admin adds
    afterwards, which is why there is no seed data for it.

    The page shows both together. Added questions are keyed as "custom-<id>" in
    the browser so they can never collide with, and quietly replace, a built-in
    answer.
    """
    __tablename__ = "faq_entries"
    id = db.Column(db.Integer, primary_key=True)
    # 200 matches the maxlength on the question field in the add form, so a
    # question that types fine cannot be rejected or cut short on save.
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default=FaqCategory.DEFAULT)
    # Only an admin can add one, enforced server side and not just by hiding the
    # form. Kept so the page can show who wrote an answer.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist, nullable=False)
    author = db.relationship("User", foreign_keys=[author_id])

    def to_dict(self):
        # Shape matches what the mock API returns today, so swapping the mock
        # for this needs no change on the page.
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category,
            "author_name": self.author.name if self.author else None,
            "created_at": self.created_at.isoformat() + "+05:30",
            # Sent so the page can tell an edited answer from an original one.
            # Equal to created_at until the entry is actually edited.
            "updated_at": self.updated_at.isoformat() + "+05:30",
        }


class FaqFeedback(db.Model):
    """One reader's answer to "Was this helpful?" on one help article.

    Admins are never shown the question. They see the running count of these
    instead, since they are the ones who act on it.

    article_id is deliberately NOT a foreign key. Most help articles ship in
    frontend/src/data/chatbotFaq.js and have no row in this database, so this
    stores the article key the page uses: "cit-file" for built-in help, or
    "custom-<id>" for a question an admin added (see FaqEntry above).
    """
    __tablename__ = "faq_feedback"
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.String(80), nullable=False, index=True)
    helpful = db.Column(db.Boolean, nullable=False)
    # Required, even though the Help page itself is public. An anonymous answer
    # has nothing to key on, so the constraint below could not cap it and the
    # same person could answer as often as they liked. A count an admin cannot
    # trust is worse than a smaller one they can, so signed-out readers are not
    # asked at all and the column stays NOT NULL.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=now_ist, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist, nullable=False)
    voter = db.relationship("User", foreign_keys=[user_id])
    # One answer per reader per article. Changing your mind updates the existing
    # row rather than adding a second. Now that user_id cannot be NULL, this
    # holds for every row with no exceptions.
    __table_args__ = (db.UniqueConstraint("article_id", "user_id"),)

    def to_dict(self):
        return {
            "id": self.id,
            "article_id": self.article_id,
            "helpful": self.helpful,
            "user_id": self.user_id,
            "user_role": self.voter.role if self.voter else None,
            "created_at": self.created_at.isoformat() + "+05:30",
        }


class PostLike(db.Model):
    __tablename__ = "post_likes"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("post_id", "user_id"),)


class ComplaintUpvote(db.Model):
    """'Me too' upvotes on a complaint — lets a citizen flag that they're
    facing the same issue, without needing to file a duplicate complaint."""
    __tablename__ = "complaint_upvotes"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("request_id", "user_id"),)
