"""Tests for job-header defaults flowing into design pages (audit fix #2)."""

import pytest
from PySide6.QtWidgets import QApplication

from rcd2000.gui.design_panel import DesignPanel
from rcd2000.gui.pages.column_page import ColumnPage


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def column_panel(app):
    page = ColumnPage()
    page._build_ui()
    return DesignPanel("column", "TEST COLUMN", page, uid="col-1")


class TestHeaderDefaultsWiring:
    def test_column_page_defaults(self, column_panel):
        # Defaults must match the ColumnDesigner engine defaults so a fresh
        # page designs identically to a bare ColumnDesigner() call.
        page = column_panel.page
        assert page.col_max_steel.value() == 4.0
        assert page.col_dh.value() == 0.85

    def test_header_pushes_max_steel_and_dh(self, column_panel):
        column_panel.apply_header_defaults(
            {"max_steel_pct": 6.0, "dh": 0.95}
        )
        page = column_panel.page
        assert page.col_max_steel.value() == 6.0
        assert page.col_dh.value() == 0.95

    def test_header_ignored_when_missing(self, column_panel):
        column_panel.apply_header_defaults({"fcu": 30})
        page = column_panel.page
        assert page.col_max_steel.value() == 4.0
        assert page.col_dh.value() == 0.85

    def test_values_reach_designer(self, column_panel):
        column_panel.apply_header_defaults(
            {"max_steel_pct": 6.0, "dh": 0.95}
        )
        page = column_panel.page
        page.col_type.setCurrentIndex(0)  # axial
        page.shape.setCurrentIndex(0)     # rectangular
        page.load.setValue(1000)
        page.bx.setValue(300)
        page.by.setValue(300)
        page.depth.setValue(300)
        inp, result = page.calculate()
        # A 300x300 column with 1000kN needs less than 1% steel - verify the
        # design runs and the max steel bound is respected (amax = 6% here).
        assert result.steel_required > 0
        assert result.steel_percent <= 6.0

    def test_state_roundtrip_includes_new_fields(self, column_panel):
        page = column_panel.page
        page.col_max_steel.setValue(5.5)
        page.col_dh.setValue(0.9)
        state = page.get_state()
        fresh = ColumnPage()
        fresh._build_ui()
        fresh.set_state(state)
        assert fresh.col_max_steel.value() == 5.5
        assert fresh.col_dh.value() == 0.9

