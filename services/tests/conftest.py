"""Pytest configuration for the live services: import path and fixture loaders.

Every test in this directory is **offline**: it reads recorded provider responses from
``services/tests/fixtures/`` (captured live from the real endpoints, see
``docs/verification/live/REPORT.md`` for the capture times) and never touches the network. A test that
needs a clock supplies its own; a test that writes state writes into ``tmp_path``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SERVICES_DIR = Path(__file__).resolve().parents[1]
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_json(name: str):
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


class FakeFetch:
    """Stand-in for :func:`nycsim_live.net.get` that serves recorded bodies by URL substring.

    ``routes`` maps a substring of the URL to either a body (str) or an exception to raise. Every call is
    recorded in ``calls`` so tests can assert the provider order and the circuit-breaker skipping.
    """

    def __init__(self, routes: dict[str, object]):
        self.routes = routes
        self.calls: list[str] = []

    def __call__(self, url: str, *, timeout_s: float = 10.0, headers=None, accept: str | None = None):
        from nycsim_live import net

        self.calls.append(url)
        for key, body in self.routes.items():
            if key in url:
                if isinstance(body, BaseException):
                    raise body
                if callable(body):
                    body = body(url)
                return net.Response(url, 200, body if isinstance(body, str) else json.dumps(body), {}, 0.01, 0.0)
        raise net.HttpError(url, "no route in FakeFetch", 404)
