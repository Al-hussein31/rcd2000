"""Tests for audit fix #8 - circular depth==dia enforcement + L/LE/LEX/LEY.

Book ground truth: column.f77 reads W, BX, BY, H, L, LE, LEX, LEY, M, MX, MY.
For circular columns the overall depth H is the diameter, and the engine's
_uniaxial path uses h = dia (never c.depth), so the page must keep depth
synced to dia and disable the rectangular-only fields.
"""

import pytest
from PySide6.QtWidgets import QApplication

from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.report import format_column
from rcd2000.gui.pages.column_page import ColumnPage


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def page(app):
    page = ColumnPage()
    page._build_ui()
    return page


class TestCircularDepthEnforcement:
    def test_rectangular_keeps_rect_fields_enabled(self, page):
        # shape index 0 = Rectangular
        page.shape.setCurrentIndex(0)
        assert page.bx.isEnabled()
        assert page.by.isEnabled()
        assert page.depth.isEnabled()
        assert not page.dia.isEnabled()  # dia is ignored for rectangular

    def test_switch_to_circular_disables_rect_fields(self, page):
        page.shape.setCurrentIndex(1)  # Circular
        assert not page.bx.isEnabled()
        assert not page.by.isEnabled()
        assert not page.depth.isEnabled()
        assert page.dia.isEnabled()

    def test_dia_change_mirrors_depth_when_circular(self, page):
        page.shape.setCurrentIndex(1)
        page.dia.setValue(450)
        assert page.depth.value() == 450
        # depth stays synced on later changes too
        page.dia.setValue(600)
        assert page.depth.value() == 600

    def test_switch_to_circular_forces_depth_to_dia(self, page):
        page.depth.setValue(700)
        page.shape.setCurrentIndex(1)
        assert page.depth.value() == page.dia.value()

    def test_switch_back_to_rect_reenables_fields(self, page):
        page.shape.setCurrentIndex(1)
        page.shape.setCurrentIndex(0)
        assert page.bx.isEnabled()
        assert page.by.isEnabled()
        assert page.depth.isEnabled()
        assert not page.dia.isEnabled()

    def test_circular_calculate_passes_depth_equal_dia(self, page):
        page.shape.setCurrentIndex(1)
        page.dia.setValue(400)
        page.load.setValue(1500)
        inp, result = page.calculate()
        assert inp.depth == 400
        assert inp.shape == 2

    def test_engine_uses_dia_not_depth_for_circular(self, app):
        # The engine's _uniaxial path takes h = dia for circular columns, so
        # a mismatched depth input must not change the answer (the page sync
        # exists to keep the reported H consistent with the diameter).
        base = ColumnInput(
            column_id="C1", col_type=2, shape=2,
            load=1500.0, dia=400.0, depth=400.0,
            moment=120.0,
        )
        mismatched = ColumnInput(
            column_id="C1", col_type=2, shape=2,
            load=1500.0, dia=400.0, depth=600.0,
            moment=120.0,
        )
        d = ColumnDesigner(fcu=25, fy=460)
        r1 = d.design([base])[0]
        r2 = d.design([mismatched])[0]
        assert r1.steel_required == r2.steel_required
        assert r1.moment_capacity_x == r2.moment_capacity_x


class TestEffectiveLengthInputs:
    def test_calculate_carries_length_fields(self, page):
        page.shape.setCurrentIndex(0)
        page.length.setValue(3.5)
        page.le.setValue(3.0)
        page.lex.setValue(2.8)
        page.ley.setValue(2.5)
        inp, result = page.calculate()
        assert inp.length == 3.5
        assert inp.le == 3.0
        assert inp.lex == 2.8
        assert inp.ley == 2.5

    def test_state_roundtrip_length_fields(self, page):
        page.length.setValue(4.2)
        page.le.setValue(3.6)
        page.lex.setValue(3.4)
        page.ley.setValue(3.1)
        state = page.get_state()
        page.length.setValue(1.0)
        page.set_state(state)
        assert page.length.value() == 4.2
        assert page.le.value() == 3.6
        assert page.lex.value() == 3.4
        assert page.ley.value() == 3.1

    def test_report_includes_lengths_when_provided(self, app):
        inp = ColumnInput(
            column_id="C1", col_type=1, shape=1,
            load=1000.0, bx=300.0, by=300.0, depth=300.0,
            length=3.5, le=3.0, lex=2.8, ley=2.5,
        )
        r = ColumnDesigner(fcu=25, fy=460).design([inp])[0]
        text = format_column(inp, r)
        assert "COLUMN HEIGHT L" in text
        assert "EFFECTIVE LENGTH LE" in text
        assert "EFFECTIVE LENGTH LEX" in text
        assert "EFFECTIVE LENGTH LEY" in text

    def test_report_omits_lengths_when_absent(self, app):
        # Legacy callers that don't set the fields must not see new lines.
        inp = ColumnInput(
            column_id="C1", col_type=1, shape=1,
            load=1000.0, bx=300.0, by=300.0, depth=300.0,
        )
        r = ColumnDesigner(fcu=25, fy=460).design([inp])[0]
        text = format_column(inp, r)
        assert "EFFECTIVE LENGTH" not in text
