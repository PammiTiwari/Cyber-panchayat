import logging
import os

from dotenv import load_dotenv

# Secrets are read from two places, and neither is ever committed:
#
#   1. backend/.env — the conventional per-checkout spot, and the one the
#      README documents. Listed in backend/.gitignore, so it stays local.
#   2. ~/.cyber_panchayat.env — outside the repo altogether, so a stray
#      `git add -A` cannot reach it at all.
#
# backend/.env is loaded first and wins on conflict: load_dotenv does not
# overwrite a variable that is already set, so whichever file is read first
# takes precedence. A key placed deliberately inside this checkout should
# beat a machine-wide default — that is the whole point of putting it there.
# Anyone with only the home file is unaffected; it still fills in whatever
# backend/.env did not define.
#
# Must run before `from .config import config_map` below — config.py reads
# os.environ at class-definition time (import time), so this has to already
# be loaded into the process environment by then or those values never see it.
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
load_dotenv(os.path.join(os.path.expanduser("~"), ".cyber_panchayat.env"))

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_restful import Api
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import config_map

db = SQLAlchemy()
jwt = JWTManager()
# In-memory storage is fine for a single-process deployment; scaling to
# multiple app instances needs a shared store, so RATELIMIT_STORAGE_URI lets
# ops point this at Redis (e.g. "redis://...") without a code change.
limiter = Limiter(key_func=get_remote_address,
                   storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
                   default_limits=["200 per minute"])


# SQLite does not enforce FOREIGN KEY constraints unless a connection turns
# it on explicitly — every relationship in models.py (citizen_id, staff_id,
# facility_id, ...) is silently unenforced without this, so a bad id could
# be written and only fail later, confusingly, wherever it's first read back
# and joined. Postgres/MySQL (a real DATABASE_URL in production) enforce
# this by default, so the listener is a no-op there.
#
# journal_mode=WAL + busy_timeout fix a real bug: SQLite's default rollback-
# journal mode only allows one writer at a time and, under Flask's
# multi-threaded dev server, a second thread's write attempt arriving while
# another thread's transaction is mid-flight doesn't just wait — it can fail
# outright with "attempt to write a readonly database" (a well-known SQLite
# quirk, confirmed here by repeatedly hitting POST /requests/<id>/upvote and
# seeing roughly 1 in 3 calls 500). WAL mode lets reads and a single write
# proceed concurrently instead of colliding, and busy_timeout makes a
# genuinely blocked writer retry for up to 5s instead of erroring instantly.
@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def create_app(env="development"):
    app = Flask(__name__)
    app.config.from_object(config_map.get(env, config_map["development"]))

    if env == "production":
        # The dev/testing defaults in config.py are checked into source
        # control, so anyone who can read this repo can forge a JWT (e.g. an
        # admin token) for a deployment still running on them. Refuse to
        # boot rather than silently serve real users on a forgeable secret —
        # a crash at startup is loud and cheap to fix; a forged admin
        # session in front of real users is neither.
        missing = [name for name in ("SECRET_KEY", "JWT_SECRET_KEY") if not os.environ.get(name)]
        if missing:
            raise RuntimeError(
                f"Refusing to start in production without {', '.join(missing)} set in the "
                f"environment — the checked-in default is public and unsafe for real users."
            )

    if not app.debug:
        logging.basicConfig(level=logging.INFO,
                             format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db.init_app(app)
    jwt.init_app(app)

    limiter.init_app(app)

    # Frontend runs on a separate origin (Vite dev server / static host), so
    # every /api/* route needs CORS, not just a specific one. Defaults to "*"
    # for local development; a real deployment should set CORS_ORIGINS to
    # its actual frontend domain(s) — a wildcard also disallows cookies/
    # credentialed requests under CORS, which this app doesn't use (auth is
    # a Bearer token), but it's still far more open than a live site needs.
    origins_env = os.environ.get("CORS_ORIGINS", "*")
    origins = [o.strip() for o in origins_env.split(",")] if origins_env != "*" else "*"
    CORS(app, resources={r"/api/*": {
        "origins": origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False,
        "max_age": 3600
    }})

    # LoginResource refuses a disabled account, but that only covers the
    # moment of signing in — a token handed out before the account was
    # disabled stays valid until it expires (12 hours). So an officer
    # deactivated mid-shift could carry on resolving complaints all day on
    # the session they already had open. Checking on every request closes
    # that window, and is the one place that catches every endpoint.
    @app.before_request
    def _reject_disabled_accounts():
        from flask import request
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        from .models import User

        # Skip JWT validation for OPTIONS (CORS preflight) requests
        if request.method == "OPTIONS":
            return None

        try:
            verify_jwt_in_request(optional=True)
        except Exception:
            # Missing/expired/malformed token — the JWT error handlers below
            # already answer those; nothing for this check to add.
            return None
        identity = get_jwt_identity()
        if not identity:
            return None
        user = db.session.get(User, int(identity))
        if user and not user.is_active:
            return jsonify({"message": "This account has been disabled. Contact admin."}), 403
        return None

    # Flask-RESTful swallows anything a resource raises that is not an
    # HTTPException and answers 500 itself. flask-jwt-extended reports a
    # missing or bad token by raising, so its @jwt.*_loader handlers below
    # never got a chance and every unauthenticated call returned 500 — which
    # the frontend reads as "the server broke" rather than "log in again".
    #
    # Only auth failures are handed back to Flask. Turning on
    # PROPAGATE_EXCEPTIONS instead would do it for *every* exception, which
    # also breaks the deliberate IntegrityError handling behind concurrent
    # double-clicks (see test_ops.py) — those must keep reaching their own
    # except blocks rather than escaping as a 500.
    class _AuthAwareApi(Api):
        def error_router(self, original_handler, e):
            if isinstance(e, (JWTExtendedException, PyJWTError)):
                return original_handler(e)
            return super().error_router(original_handler, e)

    api = _AuthAwareApi(app, prefix="/api")

    # Importing api.py pulls in models.py too, registering every model on
    # db.Model's metadata before create_all() below runs.
    from . import api as api_module
    api_module.register_resources(api)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"message": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"message": "Method not allowed"}), 405

    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify({"message": "File is too large — max 5MB"}), 413

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error")
        return jsonify({"message": "Internal server error"}), 500

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"message": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"message": "Invalid token"}), 401

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"message": "Authorization token required"}), 401

    # Unauthenticated on purpose — a load balancer or uptime monitor needs to
    # reach this without a token, and it deliberately never touches the DB so
    # it still answers (proving the process itself is alive) even if the
    # database is the thing that's down.
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # No demo seeding here: the schema is created, but the rows come from the
    # civic.db that ships alongside this checkout. A brand-new database will
    # therefore come up empty — create the first admin through /auth/register
    # (then promote it) or restore a copy of civic.db.
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            # A real deployment runs several worker processes (e.g. `gunicorn
            # -w 2`), each importing this module and reaching create_all() at
            # boot. On the very first boot, before any table exists, two
            # workers can both decide a table is missing and both try to
            # create it — one wins, the other hits "table already exists".
            # create_all() is otherwise idempotent (its checkfirst logic
            # already skips tables that exist), so once any single worker
            # has won that race the schema is correct; a loser worker should
            # log and continue rather than crash-loop the whole process.
            app.logger.warning("db.create_all() failed — likely a concurrent "
                                "table-creation race between workers at first boot", exc_info=True)

    return app
