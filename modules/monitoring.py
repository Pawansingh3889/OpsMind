"""Error monitoring with Sentry.

Set SENTRY_DSN environment variable to enable.
If not set, monitoring is disabled (no-op).
"""
import logging
import os

log = logging.getLogger("monitoring")

def init_sentry():
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        log.info("Sentry disabled (no SENTRY_DSN set)")
        return
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1, environment=os.getenv("ENVIRONMENT", "development"))
        log.info("Sentry initialized")
    except ImportError:
        log.warning("sentry-sdk not installed, monitoring disabled")

def capture_exception(e):
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
    except (ImportError, Exception):
        pass

def capture_message(msg, level="info"):
    try:
        import sentry_sdk
        sentry_sdk.capture_message(msg, level=level)
    except (ImportError, Exception):
        pass
