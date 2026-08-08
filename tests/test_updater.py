"""Tests for the update checker: version parsing and GitHub API fetch."""

import json
import urllib.error

import pytest

from rcd2000.updater import parse_version, is_newer, latest_release_tag, API_URL


# ── parse_version ────────────────────────────────────────────────────

def test_parse_simple():
    assert parse_version("v1.2.3") == (1, 2, 3)


def test_parse_without_prefix():
    assert parse_version("1.2.3") == (1, 2, 3)


def test_parse_multi_digit():
    assert parse_version("v1.10.0") == (1, 10, 0)


def test_parse_partial():
    assert parse_version("v1.2") == (1, 2)


def test_parse_garbage():
    assert parse_version("latest") == ()
    assert parse_version("") == ()
    assert parse_version(None) == ()


# ── is_newer ─────────────────────────────────────────────────────────

def test_newer_remote():
    assert is_newer("1.0.1", "v1.1.0") is True
    assert is_newer("1.0.1", "1.0.2") is True


def test_equal_or_older():
    assert is_newer("1.1.0", "1.1.0") is False
    assert is_newer("1.1.0", "1.0.1") is False


def test_unparseable_is_never_newer():
    assert is_newer("1.0.1", "latest") is False
    assert is_newer("1.0.1", "") is False


# ── latest_release_tag (network mocked) ───────────────────────────────

class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def _stub_urlopen(monkeypatch, body=None, error=None):
    def fake_urlopen(req, timeout=4.0):
        if error is not None:
            raise error
        return _FakeResponse(body)
    monkeypatch.setattr("rcd2000.updater.urllib.request.urlopen", fake_urlopen)


def test_latest_release_tag_ok(monkeypatch):
    _stub_urlopen(monkeypatch, json.dumps({"tag_name": "v2.0.0"}).encode())
    assert latest_release_tag() == "v2.0.0"


def test_latest_release_tag_missing_field(monkeypatch):
    _stub_urlopen(monkeypatch, json.dumps({"html_url": "x"}).encode())
    assert latest_release_tag() is None


def test_latest_release_tag_network_error(monkeypatch):
    _stub_urlopen(monkeypatch, error=urllib.error.URLError("offline"))
    assert latest_release_tag() is None


def test_latest_release_tag_http_error(monkeypatch):
    _stub_urlopen(monkeypatch, error=urllib.error.HTTPError(
        API_URL, 403, "rate limited", None, None
    ))
    assert latest_release_tag() is None
