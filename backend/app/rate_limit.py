"""Single shared rate limiter instance, imported by every router. Rate limiting
is disabled only for the automated test suite (RATE_LIMIT_ENABLED=false, set
in tests/conftest.py) so tests aren't flaky against real per-IP limits — it is
always on in local dev and production."""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMITING_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() != "false"

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"], enabled=RATE_LIMITING_ENABLED)
