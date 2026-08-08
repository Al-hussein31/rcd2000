"""User profile settings for RCD2000.

Stored as JSON under the platform AppData location:
    {AppData}/RCD2000/settings.json

Values prefill the New Job header dialog so starting a job is faster;
the user can still override every field per job.
"""

import json
import os
import time
from dataclasses import dataclass, asdict

from PySide6.QtCore import QStandardPaths


def _settings_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not base:
        base = os.path.expanduser("~")
    full = os.path.join(base, "RCD2000")
    os.makedirs(full, exist_ok=True)
    return full


@dataclass
class UserProfile:
    """The engineer's profile, used to prefill new jobs."""

    full_name: str = ""
    company: str = ""
    engineer: str = ""
    job_ref_prefix: str = ""
    default_output_dir: str = ""
    date_format: str = "%a. %d/%m/%y."

    def is_complete(self) -> bool:
        return bool(self.full_name or self.company or self.engineer)


class SettingsStore:
    """JSON persistence for the user profile."""

    _path = None  # overridable in tests

    @staticmethod
    def path() -> str:
        if SettingsStore._path:
            return SettingsStore._path
        return os.path.join(_settings_dir(), "settings.json")

    @staticmethod
    def load() -> UserProfile:
        path = SettingsStore.path()
        if not os.path.exists(path):
            return UserProfile()
        try:
            with open(path) as f:
                data = json.load(f)
            return UserProfile(**{k: data.get(k, "") for k in UserProfile.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError):
            return UserProfile()

    @staticmethod
    def save(profile: UserProfile) -> str:
        path = SettingsStore.path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(profile), f, indent=2)
        return path

    @staticmethod
    def touch_updated(profile: UserProfile) -> UserProfile:
        """Stamp updated time (used by UI saves)."""
        return profile
