"""Tests for the job header dialog output-file path validation."""

import os

import pytest

from rcd2000.gui.job_header_dialog import check_output_path


def test_empty_is_valid():
    # The output file is optional - empty must never block creation.
    ok, msg = check_output_path("")
    assert ok and not msg
    ok, msg = check_output_path("   ")
    assert ok and not msg


def test_existing_writable_folder_is_valid(tmp_path):
    ok, msg = check_output_path(str(tmp_path / "report.txt"))
    assert ok, msg


def test_missing_folder_is_invalid(tmp_path):
    missing = tmp_path / "no_such_dir" / "report.txt"
    ok, msg = check_output_path(str(missing))
    assert not ok
    assert "does not exist" in msg


def test_tilde_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("USERPROFILE", raising=False)
    (tmp_path / "designs").mkdir()
    ok, msg = check_output_path("~/designs/job1.txt")
    assert ok, msg


def test_file_as_parent_is_invalid(tmp_path):
    # Parent is a file, not a folder - cannot write into it.
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    ok, msg = check_output_path(str(blocker / "report.txt"))
    assert not ok
