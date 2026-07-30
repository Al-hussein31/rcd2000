"""Tests for draft autosave, disk persistence, and startup recovery."""

import json
import os
import pytest
from PySide6.QtWidgets import QApplication

import rcd2000.gui.app as app_mod
from rcd2000.gui.app import MainWindow, MODULES


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, monkeypatch, tmp_path):
    """Create a MainWindow with a redirected state file."""
    fake_path = str(tmp_path / "rcd2000_state.json")
    monkeypatch.setattr(app_mod, "_persist_path", lambda: fake_path)
    w = MainWindow()
    w._test_state_path = fake_path
    yield w
    w.close()


class TestDraftAutosave:
    def test_draft_saved_on_page_switch(self, window):
        page = window.pages[0]
        page.col_type.setCurrentIndex(2)
        page.load.setValue(2500)
        state = page.get_state()

        window.sidebar_list.setCurrentRow(1)

        assert "Column Design" in window._drafts
        assert window._drafts["Column Design"] == state

    def test_draft_restored_on_page_return(self, window):
        page0 = window.pages[0]
        page0.col_type.setCurrentIndex(2)
        page0.load.setValue(2500)
        state = page0.get_state()

        window.sidebar_list.setCurrentRow(1)
        window.sidebar_list.setCurrentRow(0)

        assert page0.get_state() == state

    def test_draft_survives_across_instances(self, window, monkeypatch, tmp_path):
        page = window.pages[0]
        page.col_type.setCurrentIndex(2)
        page.shape.setCurrentIndex(1)
        page.load.setValue(2500)
        state = page.get_state()

        window._save_draft(0)
        window._write_state()

        fake_path = str(tmp_path / "rcd2000_state.json")
        monkeypatch.setattr(app_mod, "_persist_path", lambda: fake_path)
        window2 = MainWindow()
        page2 = window2.pages[0]
        assert page2.get_state() == state


class TestDiskPersistence:
    def test_history_serialized_to_disk(self, window):
        page = window.pages[0]
        page.col_type.setCurrentIndex(2)
        page.load.setValue(2500)
        page._on_calculate()

        window._write_state()

        fake_path = window._test_state_path
        with open(fake_path) as f:
            disk = json.load(f)

        assert len(disk["history"]) == 1
        assert disk["history"][0]["module"] == "Column Design"
        assert "input" in disk["history"][0]
        assert "result" in disk["history"][0]
        # ColumnInput.col_type = currentIndex() + 1 (normalized by calc engine)
        assert disk["history"][0]["input"]["col_type"] == 3

    def test_corrupt_file_handled_gracefully(self, window, monkeypatch, tmp_path):
        fake_path = str(tmp_path / "rcd2000_state.json")
        monkeypatch.setattr(app_mod, "_persist_path", lambda: fake_path)
        with open(fake_path, "w") as f:
            f.write('{"this is not valid json"')

        window2 = MainWindow()
        assert window2._drafts == {}
        assert window2._history == []

    def test_last_page_restored(self, window):
        # Switch to SlabPage (index 2) so _last_active_page gets updated
        window.sidebar_list.setCurrentRow(2)
        page = window.pages[2]
        page.s_depth.setValue(200)
        window._save_draft(2)
        window._write_state()

        fake_path = window._test_state_path
        with open(fake_path) as f:
            disk = json.load(f)
        assert disk["last_page"] == 2

        window2 = MainWindow()
        assert window2._last_active_page == 2
        page2 = window2.pages[2]
        assert page2.get_state() == page.get_state()


class TestDynamicGrids:
    def test_beam_member_grid_round_trip(self, window):
        beam = window.pages[1]
        beam.n_members.setValue(3)
        for w in beam._member_widgets:
            w[1].setValue(7.5)
            w[2].setValue(300)
            w[3].setValue(15)
            w[4].setValue(8)
            w[5].setValue(3.0)

        state = beam.get_state()
        assert len(state["members"]) == 3

        window._save_draft(1)
        window.sidebar_list.setCurrentRow(0)
        window.sidebar_list.setCurrentRow(1)

        assert beam.get_state() == state

    def test_slab_span_grid_round_trip(self, window):
        slab = window.pages[2]
        slab.cont_nspan.setValue(4)
        for w in slab._cont_span_widgets:
            w[0].setValue(5.0)
            w[1].setValue(15.0)

        state = slab.get_state()
        assert len(state["cont_spans"]) == 4

        window._save_draft(2)
        window.sidebar_list.setCurrentRow(0)
        window.sidebar_list.setCurrentRow(2)

        assert slab.get_state() == state

    def test_continuous_beam_member_grid_round_trip(self, window):
        cb = window.pages[5]
        cb.cb_nm.setValue(2)
        for w in cb._cb_member_widgets:
            w[1].setValue(6.0)
            w[2].setValue(0.005)
            w[3].setValue(1.2)
            w[4].setValue(18.0)
            w[5].setValue(12.0)
            w[6].setValue(6.0)
            w[7].setValue(3.0)

        state = cb.get_state()
        assert len(state["members"]) == 2

        window._save_draft(5)
        window.sidebar_list.setCurrentRow(0)
        window.sidebar_list.setCurrentRow(5)

        assert cb.get_state() == state


class TestForwardCompatibility:
    def test_extra_keys_ignored(self, window):
        page = window.pages[0]
        state = page.get_state()
        state["_nonexistent_key"] = 42
        page.set_state(state)

    def test_missing_keys_ignored(self, window):
        page = window.pages[0]
        state = page.get_state()
        del state["load"]
        page.set_state(state)