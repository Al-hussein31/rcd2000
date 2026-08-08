"""Update checking - tell the user when a newer RCD2000 is released.

The GitHub Releases API is the source of truth (the repo is public).
Pure logic only - no Qt - so it is easy to unit test; the GUI wraps it
in a background thread.

Design notes (from desktop-app update UX):
  * Check once per app start, never in a loop - the unauthenticated
    GitHub API allows ~60 requests/hour.
  * All failures are silent: an update check must never disturb the
    user, and it is a check-then-notify system - nothing is ever
    downloaded or executed automatically.
"""

import json
import urllib.request

#: Public GitHub repo used for release lookups.
REPO = "Al-hussein31/rcd2000"

#: Latest-release endpoint (unauthenticated, rate-limited).
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

#: Releases page - where the banner's "Get Update" button sends the user.
RELEASES_URL = f"https://github.com/{REPO}/releases"

_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "rcd2000-update-check",
}


def parse_version(tag: str) -> tuple:
    """'v1.2.3' or '1.2.3' -> (1, 2, 3).  Returns () when unparseable."""
    t = (tag or "").strip().lstrip("vV")
    parts = []
    for piece in t.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            break
    return tuple(parts)


def is_newer(local: str, remote: str) -> bool:
    """True when *remote* denotes a newer version than *local*."""
    a, b = parse_version(local), parse_version(remote)
    if not a or not b:
        return False
    return b > a


def latest_release_tag(timeout: float = 4.0) -> str | None:
    """Latest release tag name from GitHub, or None on any failure.

    Failures (offline, rate limit, API change) return None silently -
    an update check must never disturb the user or the app.
    """
    try:
        req = urllib.request.Request(API_URL, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("tag_name")
    except Exception:
        return None
