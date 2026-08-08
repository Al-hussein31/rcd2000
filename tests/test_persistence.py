"""Tests for the new Job model, disk persistence, and workbench integration.

The old draft/history persistence (sidebar drafts) is gone; jobs are now
the unit of persistence: a job header plus any number of design items,
stored per-job as JSON files in the AppData location.
"""

import json
import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QStandardPaths

import rcd2000.gui.job as job_mod
from rcd2000.gui.job import Job, DesignItem, JobStore, make_slug
from rcd2000.gui.workbench import Workbench

SAMPLE_HEADER = {
    "company": "ACME Ltd.",
    "job_ref": "FG-2026-001",
    "engineer": "A. Oyenuga",
    "date": "Fri. 07/08/26.",
    "output_file": "",
    "fcu": 30,
    "fy": 460,
    "fyv": 250,
    "soil_pressure": 150.0,
    "max_steel_pct": 6.0,
    "dh": 0.95,
}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def jobs_dir(monkeypatch, tmp_path):
    """Redirect the job store into a temp dir for the test."""
    fake_dir = str(tmp_path / "jobs")
    os.makedirs(fake_dir, exist_ok=True)
    monkeypatch.setattr(job_mod, "_jobs_dir", lambda: fake_dir)
    return fake_dir


def make_job(**kw) -> Job:
    base = dict(slug="test-job", name="Test Job", header=dict(SAMPLE_HEADER))
    base.update(kw)
    return Job(**base)


# ── Model ─────────────────────────────────────────────────────────────

class TestJobModel:
    def test_add_item_assigns_labels(self):
        job = make_job()
        c1 = job.add_item("column")
        c2 = job.add_item("column")
        b1 = job.add_item("beam")
        s1 = job.add_item("slab")
        assert (c1.label, c2.label, b1.label, s1.label) == ("C1", "C2", "B1", "S1")

    def test_next_label_reuses_gaps(self):
        job = make_job()
        job.add_item("column")
        job.add_item("column")
        job.items.pop(0)
        assert job.next_label("column") == "C3"

    def test_remove_item(self):
        job = make_job()
        it = job.add_item("column")
        assert len(job.items) == 1
        job.remove_item(it.uid)
        assert job.items == []

    def test_items_of_and_item_lookup(self):
        job = make_job()
        c = job.add_item("column")
        job.add_item("beam")
        assert job.items_of("column") == [c]
        assert job.item(c.uid) is c
        assert job.item("nope") is None

    def test_to_dict_from_dict_roundtrip(self):
        job = make_job()
        c = job.add_item("column")
        c.state = {"col_type": 2, "load": 2500}
        job.active_type = "beam"
        again = Job.from_dict(job.to_dict())
        assert again.slug == job.slug
        assert again.name == job.name
        assert again.header == job.header
        assert again.active_type == "beam"
        assert len(again.items) == 1
        assert again.items[0].uid == c.uid
        assert again.items[0].state == c.state

    def test_make_slug_sanitises(self):
        assert make_slug("My  Big  Job!")[:7] == "my-big-"


# ── Store ─────────────────────────────────────────────────────────────

class TestJobStore:
    def test_save_load_roundtrip(self, jobs_dir):
        job = make_job()
        c = job.add_item("column")
        c.state = {"col_type": 1, "load": 1200.0}
        path = JobStore.save(job)
        assert os.path.exists(path)

        loaded = JobStore.load(job.slug)
        assert loaded is not None
        assert loaded.header["job_ref"] == "FG-2026-001"
        assert loaded.items[0].state == {"col_type": 1, "load": 1200.0}

    def test_load_missing_returns_none(self, jobs_dir):
        assert JobStore.load("does-not-exist") is None

    def test_corrupt_file_handled_gracefully(self, jobs_dir):
        path = JobStore.path_for("broken")
        with open(path, "w") as f:
            f.write('{"this is not valid json"')
        assert JobStore.load("broken") is None

    def test_delete(self, jobs_dir):
        job = make_job()
        JobStore.save(job)
        assert JobStore.load(job.slug) is not None
        JobStore.delete(job.slug)
        assert JobStore.load(job.slug) is None

    def test_list_jobs_sorted_by_updated(self, jobs_dir):
        a = make_job(slug="aaa", name="A", updated=100.0)
        b = make_job(slug="bbb", name="B", updated=200.0)
        JobStore.save(a)
        JobStore.save(b)
        slugs = [j.slug for j in JobStore.list_jobs()]
        assert slugs == ["bbb", "aaa"]


# ── Workbench integration ─────────────────────────────────────────────

class TestWorkbenchPersistence:
    def test_workbench_syncs_panel_state_into_job(self, app):
        job = make_job()
        wb = Workbench(job)
        wb.add_item("column")
        panel = wb._panels[wb.job.items[0].uid]
        # The column page exposes typical widgets
        page = panel.page
        page.load.setValue(2500)
        page.col_type.setCurrentIndex(2)
        wb._on_state_changed(panel)
        assert wb.job.items[0].state.get("load") == 2500

    def test_restored_job_rebuilds_panels_with_state(self, app):
        job = make_job()
        c = job.add_item("column")
        c.state = {"col_type": 1, "load": 1750.0}
        wb = Workbench(job)
        panel = wb._panels[c.uid]
        assert panel.page.get_state().get("load") == 1750.0

    def test_render_all_reports_contain_header_block(self, app, tmp_path):
        job = make_job()
        job.header["output_file"] = str(tmp_path / "report.txt")
        job.add_item("column")
        job.add_item("beam")
        wb = Workbench(job)
        # Designs must be run before export - undesigned items are skipped
        for panel in wb._panels.values():
            panel.page._on_calculate()
        wb._export_all()
        text = (tmp_path / "report.txt").read_text()
        assert "ACME Ltd." in text
        assert "FG-2026-001" in text
        assert "A. Oyenuga" in text

    def test_export_skips_undesigned_items(self, app, tmp_path):
        job = make_job()
        job.header["output_file"] = str(tmp_path / "report.txt")
        job.add_item("column")      # will be designed
        job.add_item("beam")        # will NOT be designed
        wb = Workbench(job)
        for uid, panel in wb._panels.items():
            if panel.type_key == "column":
                panel.page._on_calculate()
        wb._export_all()
        text = (tmp_path / "report.txt").read_text()
        # only the designed column appears
        assert "COLUMN ANALYSIS" in text
        assert "BEAM ANALYSIS" not in text

    def test_export_with_nothing_designed_writes_no_file(self, app, tmp_path):
        job = make_job()
        job.header["output_file"] = str(tmp_path / "report.txt")
        job.add_item("column")
        wb = Workbench(job)
        wb._export_all()
        assert not (tmp_path / "report.txt").exists()


# ── Forward compatibility ─────────────────────────────────────────────

class TestForwardCompatibility:
    def test_extra_keys_ignored_in_item_dict(self):
        data = {
            "slug": "x",
            "name": "X",
            "header": {},
            "items": [
                {"uid": "u1", "type_key": "column", "label": "C1",
                 "state": {}, "extra_future_key": 1},
            ],
        }
        job = Job.from_dict(data)
        assert len(job.items) == 1
        assert job.items[0].label == "C1"

    def test_missing_fields_get_defaults(self):
        job = Job.from_dict({"slug": "x"})
        assert job.name == "Untitled Job"
        assert job.header == {}
        assert job.items == []
