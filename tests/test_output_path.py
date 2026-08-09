"""Tests for the job header dialog output-file path validation and the
solid default-folder resolution (Documents/RCD2000_output)."""

import os

import pytest
from PySide6.QtWidgets import QApplication

from rcd2000.gui.job_header_dialog import (
    check_output_path, default_output_dir, resolve_output_path,
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


# ── Resolution rule (pure function, injectable base dir) ────────────────


def test_resolve_empty_text_is_empty():
    assert resolve_output_path("") == ""
    assert resolve_output_path("   ") == ""


def test_resolve_bare_name_joins_default_folder(tmp_path):
    resolved = resolve_output_path("job1.txt", base_dir=tmp_path)
    assert resolved == str(tmp_path / "job1.txt")


def test_resolve_relative_path_joins_default_folder(tmp_path):
    resolved = resolve_output_path("jobs/floor1.txt", base_dir=tmp_path)
    assert resolved == str(tmp_path / "jobs" / "floor1.txt")


def test_resolve_absolute_path_is_honored(tmp_path):
    target = tmp_path / "elsewhere" / "report.txt"
    assert resolve_output_path(str(target), base_dir=tmp_path) == str(target)


def test_resolve_tilde_is_expanded_before_join(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    resolved = resolve_output_path("~/my_designs/job1.txt", base_dir=tmp_path)
    assert resolved == str(tmp_path / "my_designs" / "job1.txt")


def test_resolve_default_base_dir_is_documents(tmp_path, monkeypatch):
    # Without an injected base dir, bare names must land in the real
    # Documents-based default folder - never the process CWD.
    resolved = resolve_output_path("job1.txt")
    assert os.path.isabs(resolved)
    assert resolved.endswith(
        os.path.join(default_output_dir().name, "job1.txt")
    )


def test_check_output_path_accepts_bare_name(tmp_path):
    # A bare name resolves under the (auto-created) default folder, so it
    # must always be valid - the old "missing folder" error no longer
    # applies to plain names.
    ok, msg = check_output_path("job1.txt", base_dir=tmp_path)
    assert ok, msg


def test_check_output_path_empty_is_valid():
    # The output file is optional - empty must never block creation.
    ok, msg = check_output_path("")
    assert ok and not msg
    ok, msg = check_output_path("   ")
    assert ok and not msg


def test_check_output_path_existing_folder_is_valid(tmp_path):
    ok, msg = check_output_path(str(tmp_path / "report.txt"))
    assert ok, msg


def test_check_output_path_tilde_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    (tmp_path / "designs").mkdir()
    ok, msg = check_output_path("~/designs/job1.txt")
    assert ok, msg


def test_check_output_path_file_as_parent_is_invalid(tmp_path):
    # Parent is a file, not a folder - cannot write into it.
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    ok, msg = check_output_path(str(blocker / "report.txt"))
    assert not ok


def test_check_output_path_still_rejects_bad_absolute(tmp_path):
    ok, msg = check_output_path(str(tmp_path / "nope" / "job1.txt"))
    assert not ok
    assert "does not exist" in msg


def test_default_output_dir_is_documents_subfolder():
    # The default folder is Qt's real Documents location + RCD2000_output
    # (QStandardPaths does not honour $HOME, so no monkeypatch here).
    from PySide6.QtCore import QStandardPaths
    docs = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    folder = default_output_dir()
    assert folder.name == "RCD2000_output"
    assert folder.is_dir()
    assert str(folder) == os.path.join(docs, "RCD2000_output")


# ── Split-field dialog behavior (offscreen) ─────────────────────────────

def _new_dialog(existing=None):
    from rcd2000.gui.job_header_dialog import JobHeaderDialog
    dlg = JobHeaderDialog(existing=existing or {})
    return dlg


def test_dialog_prefills_default_folder_when_no_stored_path(qapp):
    dlg = _new_dialog()
    assert dlg._folder.text().endswith("RCD2000_output")
    assert dlg.output_file.text() == ""


def test_dialog_header_resolves_bare_name_to_default_folder(qapp):
    dlg = _new_dialog()
    dlg.output_file.setText("job1.txt")
    h = dlg.header()
    assert os.path.isabs(h["output_file"])
    assert h["output_file"].endswith(
        os.path.join("RCD2000_output", "job1.txt")
    )


def test_dialog_splits_stored_full_path_back_into_fields(qapp, tmp_path):
    stored = str(tmp_path / "custom" / "report.txt")
    dlg = _new_dialog(existing={"output_file": stored})
    assert dlg._folder.text().endswith("custom")
    assert dlg.output_file.text() == "report.txt"
    # Round-trip: header() keeps the full absolute path.
    h = dlg.header()
    assert os.path.abspath(os.path.expanduser(h["output_file"])) == stored


def test_dialog_default_button_resets_folder(qapp):
    dlg = _new_dialog()
    dlg._folder.setText("/tmp/somewhere")
    dlg._reset_output_folder()
    assert dlg._folder.text().endswith("RCD2000_output")


def test_dialog_validation_marks_bad_absolute_path(qapp, tmp_path):
    dlg = _new_dialog()
    dlg._folder.setText(str(tmp_path))
    dlg.output_file.setText("sub/nope.txt")  # folder tmp/sub does not exist
    dlg._validate_output_path()
    # Dialog is never shown in tests, so probe explicit show/hide state
    # relative to the dialog (isVisibleTo ignores hidden ancestors).
    assert dlg._output_error.isVisibleTo(dlg)
    assert "does not exist" in dlg._output_error.text()
    # A good path clears the error label again.
    dlg.output_file.setText("ok.txt")
    dlg._validate_output_path()
    assert not dlg._output_error.isVisibleTo(dlg)
