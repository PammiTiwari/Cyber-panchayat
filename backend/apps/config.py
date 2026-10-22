import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "civic-secret-key-iitm-2026-change-in-prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-civic-iitm-secret-key-2026-strong")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    # PyJWT rejects a token whose `iat` is even a fraction of a second ahead of
    # the verifying clock ("The token is not yet valid (iat)"), and its default
    # leeway is zero. That is a real failure, not a theoretical one: a host
    # whose clock steps backwards — an NTP correction, a VM resuming, WSL2
    # resyncing after the Windows host sleeps — invalidates every token it
    # issued in the seconds before the step, and the user is signed out with
    # "Invalid token" moments after signing in. Measured on the dev machine:
    # the wall clock jumped back 1.3s inside a 20s window, which is what made
    # roughly one full pytest run in three fail on a different test each time.
    # A few seconds of leeway absorbs that; it does not weaken `exp`, which
    # is 12 hours away.
    JWT_DECODE_LEEWAY = 10
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB, matches the upload UI's stated limit


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, '..', 'civic.db')}"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    RATELIMIT_ENABLED = False  # a test suite firing dozens of logins/second isn't a brute-force attack


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, '..', 'civic.db')}")


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
