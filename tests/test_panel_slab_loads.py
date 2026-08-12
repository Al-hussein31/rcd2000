"""Panel (cantilever / simply supported) slab point-load editor tests.

Covers the multi-load PointLoadsEditor on the single-panel slab path:
loads flowing into the engine input, per-load validation messages, and
state round-trip persistence.
"""

import pytest
from PySide6.QtWidgets import QApplication

from rcd2000.gui.pages.slab_page import SlabPage


@pytest.fixture(scope="module")
def app():
    """One QApplication for the whole module."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def page(app):
    p = SlabPage()
    p._build_ui()
    p.slab_type.setCurrentIndex(1)  # Simply Supported
    p.s_span.setValue(5.5)
    p.s_depth.setValue(200)
    p.gk.setValue(12.0)
    p.qk.setValue(6.5)
    return p


class TestPanelPointLoads:
    def test_loads_flow_into_input(self, page):
        page.panel_pl_editor.set_value([(50.0, 2.0), (30.0, 4.0)])
        inp, _ = page.calculate()
        assert inp.npl == 2
        assert inp.point_loads == [(50.0, 2.0), (30.0, 4.0)]

    def test_no_loads_by_default(self, page):
        inp, _ = page.calculate()
        assert inp.npl == 0
        assert inp.point_loads == []

    def test_validation_marks_each_load(self, page):
        # Load 2 distance exceeds the 5.5 m panel span -> per-load message
        page.panel_pl_editor.set_value([(50.0, 2.0), (30.0, 6.0)])
        errs = page.validate()
        assert len(errs) == 1
        assert "Panel point load 2" in errs[0]
        # Only the offending row's distance spin is marked
        assert len(page._error_widgets) == 1

    def test_validation_marks_both_loads(self, page):
        page.panel_pl_editor.set_value([(80.0, 8.0), (30.0, 6.0)])
        errs = page.validate()
        assert len(errs) == 2
        assert "load 1" in errs[0]
        assert "load 2" in errs[1]
        assert len(page._error_widgets) == 2

    def test_validation_passes_valid_loads(self, page):
        page.panel_pl_editor.set_value([(50.0, 2.0), (30.0, 4.0)])
        assert page.validate() == []

    def test_round_trip(self, page):
        page.panel_pl_editor.set_value([(50.0, 2.0), (30.0, 4.0)])
        state1 = page.get_state()
        fresh = SlabPage()
        fresh._build_ui()
        fresh.set_state(state1)
        assert fresh.get_state() == state1
        # Editor contents restored on the fresh page
        assert fresh.panel_pl_editor.all_loads() == [
            (50.0, 2.0), (30.0, 4.0)
        ]