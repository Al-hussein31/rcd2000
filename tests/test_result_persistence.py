"""Persistent results + stale-state tests.

Results survive re-opening a job (stored as a JSON payload in the item
state) and any input edit after a design blurs the results, disables the
Save/PDF buttons and flags the panel OUTDATED until Design is re-run.
"""

import pytest
from PySide6.QtWidgets import QApplication

from rcd2000.gui.job import Job, DesignItem
from rcd2000.gui.design_panel import DesignPanel
from rcd2000.gui.pages.column_page import ColumnPage
from rcd2000.gui.workbench import Workbench


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _designed_column(app):
    """Return a ColumnPage with a valid 400x400 @ 800 kN design run.

    Mirrors the panel's wiring (the panel would call these on build).
    """
    p = ColumnPage()          # __init__ builds the UI exactly once
    p.shape.setCurrentIndex(0)
    p.bx.setValue(400)
    p.by.setValue(400)
    p.load.setValue(800)
    p._on_calculate()
    assert p._last_result is not None
    p._wire_dirty_inputs()    # what DesignPanel does in production
    return p


# ── Payload roundtrip ─────────────────────────────────────────────────

def test_payload_roundtrip_restores_results(app):
    p = _designed_column(app)
    payload = p.result_payload()
    assert payload is not None
    assert payload["stale"] is False

    p2 = ColumnPage()
    p2._build_ui()
    p2.restore_result(payload)
    # Same design values, no engine re-run required.
    assert p2._last_input == p._last_input
    assert p2._last_result == p._last_result
    assert p2._result_widgets, "results table must be rebuilt"
    assert p2.save_btn.isVisibleTo(p2)
    assert p2.save_btn.isEnabled()
    assert p2._results_placeholder.isHidden() or not p2._results_placeholder.isVisibleTo(p2)


def test_payload_is_json_serializable(app):
    import json
    p = _designed_column(app)
    payload = p.result_payload()
    json.dumps(payload)  # must not raise


def test_restore_result_none_is_safe(app):
    p = ColumnPage()
    p.restore_result(None)
    assert p._last_result is None


def test_result_payload_none_when_undesigned(app):
    p = ColumnPage()
    assert p.result_payload() is None


# ── Stale state on input edit ─────────────────────────────────────────

def test_input_edit_blurs_results_and_disables_save(app):
    p = _designed_column(app)
    assert not p._stale
    p.load.setValue(900)  # user edits a value
    assert p._stale is True
    assert p._stale_banner.isVisibleTo(p)
    assert not p.save_btn.isEnabled()
    assert not p.pdf_btn.isEnabled()
    for w in p._result_widgets:
        assert not w.isEnabled()
        assert w.graphicsEffect() is not None  # blurred

    # Redesign clears the stale state and re-enables everything.
    p._on_calculate()
    assert not p._stale
    assert p.save_btn.isEnabled()
    assert p.pdf_btn.isEnabled()
    assert not p._stale_banner.isVisibleTo(p)


def test_stale_flag_persists_in_payload(app):
    p = _designed_column(app)
    p.load.setValue(900)
    assert p.result_payload()["stale"] is True

    p2 = ColumnPage()
    p2._build_ui()
    p2.restore_result(p.result_payload())
    assert p2._stale is True          # still outdated after re-entry
    assert not p2.save_btn.isEnabled()
    assert p2._stale_banner.isVisibleTo(p2)


def test_edit_before_any_design_is_harmless(app):
    p = ColumnPage()
    p.load.setValue(500)  # no results yet - nothing to invalidate
    assert not p._stale


# ── Panel level ───────────────────────────────────────────────────────

def test_panel_restore_marks_designed(app):
    p = _designed_column(app)
    panel = DesignPanel("column", "C1", p, "u1")
    assert panel.is_designed()
    assert not panel.is_stale()


def test_panel_stale_badge(app):
    p = _designed_column(app)
    panel = DesignPanel("column", "C1", p, "u1")
    p.load.setValue(900)
    assert panel.is_stale()
    assert panel.badge.text() == "OUTDATED"


# ── Workbench end-to-end: reopen shows results, export skips stale ────

def _job_with_designed_column(tmp_path):
    p = ColumnPage()
    p.shape.setCurrentIndex(0)
    p.bx.setValue(400)
    p.by.setValue(400)
    p.load.setValue(800)
    p._on_calculate()
    state = p.get_state()
    state["_result"] = p.result_payload()
    item = DesignItem(uid="c1", type_key="column", label="C1", state=state)
    return Job(
        slug="test-job",
        name="Test Job",
        header={"output_file": str(tmp_path / "out.txt")},
        items=[item],
    )


def test_workbench_restores_results_on_open(app, tmp_path):
    job = _job_with_designed_column(tmp_path)
    wb = Workbench(job)
    panel = wb._panels.get("c1")
    assert panel is not None
    assert panel.is_designed(), "results must survive re-opening the job"
    assert not panel.is_stale()
    assert panel.page._result_widgets


def test_export_all_skips_outdated_designs(app, tmp_path):
    job = _job_with_designed_column(tmp_path)
    wb = Workbench(job)
    messages = []
    wb.status_message.connect(lambda msg, err: messages.append(msg))
    assert wb._panels["c1"].page._dirty_wired
    # Edit an input: the stored design is now outdated.
    wb._panels["c1"].page.load.setValue(1200)
    wb._export_all()
    assert messages and "outdated" in messages[-1]
    out = tmp_path / "out.txt"
    assert not out.exists(), "stale design must NOT be exported"

    # Redesign, then export succeeds.
    wb._panels["c1"].page._on_calculate()
    wb._export_all()
    assert out.exists()
    assert "Reports written" in messages[-1]


def test_app_save_path_preserves_results(app, tmp_path):
    """Regression: the app's save loop used to strip the result payload.

    app._save_current_job re-synced state with panel.get_state() only,
    dropping the stored results, so re-opening a job lost them.  The
    payload must survive the exact save + reload cycle the app performs.
    """
    from rcd2000.gui.job import Job, DesignItem, JobStore
    p = ColumnPage()
    p.shape.setCurrentIndex(0)
    p.bx.setValue(400)
    p.by.setValue(400)
    p.load.setValue(800)
    p._on_calculate()
    state = p.get_state()
    state["_result"] = p.result_payload()
    job = Job(slug="save-path-reg", name="Reg",
              items=[DesignItem(uid="c1", type_key="column",
                                label="C1", state=state)])

    # Workbench as the app would build it, then the app's save routine.
    wb = Workbench(job)
    wb.sync_all_to_job()
    path = JobStore.save(job)

    # Re-open from disk, exactly like _open_job -> _replace_workbench.
    job2 = JobStore.load("save-path-reg")
    wb2 = Workbench(job2)
    panel = wb2._panels["c1"]
    assert panel.is_designed(), "results must survive the app save/reload"
    assert not panel.is_stale()
    assert panel.page._result_widgets

    import os
    os.remove(path)
