"""Small HTTP layer shared by every live provider: timeouts, typed errors, UA, no retries here.

Retries/back-off are the :class:`~nycsim_live.weather.CircuitBreaker`'s job; this module makes exactly
one request per call so failure accounting stays exact. The C++ port maps :class:`HttpError` to a
status enum (no exceptions cross the engine boundary).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Mapping

import requests

log = logging.getLogger("nycsim.live.net")

# api.weather.gov requires a User-Agent that identifies the application. A contact address can be added by
# the operator through NYCSIM_CONTACT (never hard-coded here).
_contact = os.environ.get("NYCSIM_CONTACT", "").strip()
USER_AGENT = f"NYCSim-live/1.0 ({_contact})" if _contact else "NYCSim-live/1.0 (drivable-NYC simulation weather client)"
DEFAULT_TIMEOUT_S = 10.0
CA_BUNDLE = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or True


class HttpError(RuntimeError):
    """Any failure to obtain a 2xx body: network, TLS, timeout, non-2xx status, empty body."""

    def __init__(self, url: str, message: str, status: int | None = None):
        super().__init__(f"{message} [{url}]" if status is None else f"HTTP {status}: {message} [{url}]")
        self.url = url
        self.status = status


@dataclass(frozen=True)
class Response:
    url: str
    status: int
    text: str
    headers: Mapping[str, str]
    elapsed_s: float
    fetched_at: float  # POSIX seconds when the response completed

    def json(self):
        import json

        try:
            return json.loads(self.text)
        except ValueError as e:
            raise HttpError(self.url, f"invalid JSON body: {e}", self.status) from e


_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT})
        _session = s
    return _session


def get(url: str, *, timeout_s: float = DEFAULT_TIMEOUT_S, headers: Mapping[str, str] | None = None, accept: str | None = None) -> Response:
    """One GET. Raises :class:`HttpError` on any problem; never returns a non-2xx or empty body."""
    h = dict(headers or {})
    if accept:
        h["Accept"] = accept
    t0 = time.monotonic()
    try:
        r = _get_session().get(url, timeout=timeout_s, headers=h, verify=CA_BUNDLE)
    except requests.exceptions.Timeout as e:
        raise HttpError(url, f"timeout after {timeout_s:.0f}s") from e
    except requests.exceptions.SSLError as e:
        raise HttpError(url, f"TLS error: {e}") from e
    except requests.exceptions.RequestException as e:
        raise HttpError(url, f"request failed: {e}") from e
    elapsed = time.monotonic() - t0
    if not 200 <= r.status_code < 300:
        raise HttpError(url, r.text[:200].replace("\n", " "), r.status_code)
    if not r.text or not r.text.strip():
        raise HttpError(url, "empty body", r.status_code)
    log.debug("GET %s -> %d (%d bytes, %.2fs)", url, r.status_code, len(r.text), elapsed)
    return Response(url, r.status_code, r.text, dict(r.headers), elapsed, time.time())
