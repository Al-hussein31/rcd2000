"""Job model + persistence for the RCD2000 multi-design workbench.

A *job* is the unit of work: one project (company, job reference,
designer, date, output file) holding any number of design items of any
type.  This mirrors the original RCD2000 programs, where each program
accepted an array of designs under a single job header.

Jobs are stored as JSON files under the platform AppData location:
    {AppData}/RCD2000/jobs/{slug}.json
"""

import json
import os
import re
import time
import logging
from dataclasses import dataclass, field, asdict

from PySide6.QtCore import QStandardPaths

from rcd2000.gui.modules import MODULE_BY_KEY, LABEL_PREFIX

JOB_DIR_NAME = "jobs"


def _jobs_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not base:
        base = os.path.expanduser("~")
    full = os.path.join(base, "RCD2000", JOB_DIR_NAME)
    os.makedirs(full, exist_ok=True)
    return full


def make_slug(name: str) -> str:
    """Sanitise a job name into a filesystem-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip().lower()).strip("-")
    if not slug:
        slug = "job"
    return f"{slug}-{int(time.time())}"


# ── Model ────────────────────────────────────────────────────────────

@dataclass
class DesignItem:
    """One design being worked on (a beam, a column, a slab …)."""

    uid: str
    type_key: str
    label: str
    state: dict = field(default_factory=dict)
    created: float = field(default_factory=time.time)

    @property
    def module_name(self) -> str:
        entry = MODULE_BY_KEY.get(self.type_key)
        return entry[0] if entry else self.type_key


@dataclass
class Job:
    """A project: header info + a list of design items."""

    slug: str
    name: str = "Untitled Job"
    header: dict = field(default_factory=dict)
    items: list = field(default_factory=list)  # list[DesignItem]
    active_type: str = "column"
    note: str = ""
    time_spent: float = 0.0            # seconds spent working on this job
    last_opened: float = 0.0
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)

    # ── helpers ─────────────────────────────────────────────────────

    def items_of(self, type_key: str) -> list:
        return [it for it in self.items if it.type_key == type_key]

    def item(self, uid: str):
        for it in self.items:
            if it.uid == uid:
                return it
        return None

    def next_label(self, type_key: str) -> str:
        prefix = LABEL_PREFIX.get(type_key, "D")
        existing = self.items_of(type_key)
        nums = []
        for it in existing:
            m = re.fullmatch(rf"{prefix}(\d+)", it.label)
            if m:
                nums.append(int(m.group(1)))
        n = (max(nums) + 1) if nums else 1
        return f"{prefix}{n}"

    def add_item(self, type_key: str) -> DesignItem:
        uid = f"{type_key}-{int(time.time() * 1000)}"
        it = DesignItem(uid=uid, type_key=type_key, label=self.next_label(type_key))
        self.items.append(it)
        self.updated = time.time()
        return it

    def remove_item(self, uid: str) -> None:
        self.items = [it for it in self.items if it.uid != uid]
        self.updated = time.time()

    # ── (de)serialisation ───────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "header": self.header,
            "items": [asdict(it) for it in self.items],
            "active_type": self.active_type,
            "note": self.note,
            "time_spent": self.time_spent,
            "last_opened": self.last_opened,
            "created": self.created,
            "updated": self.updated,
        }

    @staticmethod
    def from_dict(data: dict) -> "Job":
        items = []
        for it in data.get("items", []):
            # Forward-compat: ignore unknown keys (future versions may
            # add fields) instead of crashing on load.
            fields = {k: it[k] for k in DesignItem.__dataclass_fields__ if k in it}
            items.append(DesignItem(**fields))
        return Job(
            slug=data.get("slug", make_slug(data.get("name", "job"))),
            name=data.get("name", "Untitled Job"),
            header=data.get("header", {}),
            items=items,
            active_type=data.get("active_type", "column"),
            note=data.get("note", ""),
            time_spent=data.get("time_spent", 0.0),
            last_opened=data.get("last_opened", 0.0),
            created=data.get("created", time.time()),
            updated=data.get("updated", time.time()),
        )

    def add_time(self, seconds: float):
        """Accumulate active editing time for history display."""
        if seconds > 0:
            self.time_spent += seconds

    def duration_text(self) -> str:
        """Human-readable time worked, e.g. '1h 24m' or '6m'."""
        total = int(self.time_spent)
        h, rem = divmod(total, 3600)
        m = rem // 60
        if h:
            return f"{h}h {m}m"
        return f"{m}m"


# ── Store ────────────────────────────────────────────────────────────

class JobStore:
    """Filesystem persistence for jobs."""

    @staticmethod
    def path_for(slug: str) -> str:
        return os.path.join(_jobs_dir(), f"{slug}.json")

    @staticmethod
    def save(job: Job) -> str:
        job.updated = time.time()
        path = JobStore.path_for(job.slug)
        with open(path, "w") as f:
            json.dump(job.to_dict(), f, indent=2)
        return path

    @staticmethod
    def load(slug: str) -> Job | None:
        path = JobStore.path_for(slug)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return Job.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            logging.error("Job file corrupt - ignoring: %s", path, exc_info=True)
            return None

    @staticmethod
    def delete(slug: str) -> None:
        path = JobStore.path_for(slug)
        if os.path.exists(path):
            os.remove(path)

    @staticmethod
    def list_jobs() -> list[Job]:
        """Return all saved jobs, most-recently-updated first."""
        jobs = []
        for fname in os.listdir(_jobs_dir()):
            if not fname.endswith(".json"):
                continue
            job = JobStore.load(fname[:-5])
            if job is not None:
                jobs.append(job)
        jobs.sort(key=lambda j: j.updated, reverse=True)
        return jobs
