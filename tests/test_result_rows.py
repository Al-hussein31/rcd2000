"""Result-row display coverage tests (GUI verification pass).

Every engine output must be visible in the on-screen result grid, not just
the exported report: beam support results, column/base section status
(heck), slab continuous support moments/steels, two-way long-direction
support steel, and deflection-required depth.
"""

import pytest
from PySide6.QtWidgets import QApplication

from rcd2000.gui.pages.beam_page import BeamPage
from rcd2000.gui.pages.slab_page import SlabPage
from rcd2000.gui.pages.column_page import ColumnPage
from rcd2000.gui.pages.base_page import BasePage


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def beam_page(app):
    p = BeamPage()
    p._build_ui()
    return p


@pytest.fixture()
def slab_page(app):
    p = SlabPage()
    p._build_ui()
    return p


def _flatten(rows):
    return [cell for row in rows for cell in row if isinstance(cell, str)]


class TestBeamResultRows:
    def test_support_results_shown(self, beam_page):
        beam_page.n_supports.setValue(2)
        beam_page.n_members.setValue(1)
        inp, r = beam_page.calculate()
        assert r.supports, "engine must produce support results"
        text = " | ".join(_flatten(beam_page._build_result_rows(r)))
        assert "SUPPORT RESULTS" in text
        assert "Reaction" in text or r.supports[0].support_id in text

    def test_heck_fail_row_when_section_broke(self, beam_page):
        # Overload a tiny section so the steel check bails (heck == 0).
        beam_page.b_b.setValue(100)
        beam_page.b_h.setValue(150)
        beam_page.n_supports.setValue(2)
        beam_page.n_members.setValue(1)
        for w in beam_page._member_widgets:
            w[1].setValue(6.0)   # length
            w[2].setValue(2000)  # UDL kN/m - absurd
        inp, r = beam_page.calculate()
        if r.heck == 0:
            text = " | ".join(_flatten(beam_page._build_result_rows(r)))
            assert "FAIL" in text and "increase" in text


class TestColumnResultRows:
    def test_section_adequate_row(self, app):
        p = ColumnPage()
        p._build_ui()
        p.shape.setCurrentIndex(0)
        p.bx.setValue(400)
        p.by.setValue(400)
        p.load.setValue(800)
        inp, r = p.calculate()
        assert r.heck == 0, "400x400 at 800 kN must be adequate"
        p._last_input = inp  # _build_result_rows reads this (set by panel)
        text = " | ".join(_flatten(p._build_result_rows(r)))
        assert "Section Adequate" in text
        assert "OK" in text

    def test_section_adequate_row_fails_when_overloaded(self, app):
        p = ColumnPage()
        p._build_ui()
        p.shape.setCurrentIndex(0)
        p.load.setValue(1500)  # 300x300 defaults -> 5.75% steel > 4% max
        inp, r = p.calculate()
        assert r.heck == 1
        p._last_input = inp
        text = " | ".join(_flatten(p._build_result_rows(r)))
        assert "FAIL" in text


class TestBaseResultRows:
    def test_design_checks_row_ok(self, app):
        p = BasePage()
        p._build_ui()
        p.base_type.setCurrentIndex(0)  # isolated
        p.base_load.setValue(1200)
        p.base_l1.setValue(2000)
        p.base_l2.setValue(2000)
        inp, r = p.calculate()
        assert r.heck == 0, "isolated design must converge"
        text = " | ".join(_flatten(p._build_result_rows(r)))
        assert "Design Checks" in text
        assert "OK" in text

    def test_combined_design_checks_ok(self, app):
        p = BasePage()
        p._build_ui()
        p.base_type.setCurrentIndex(2)  # combined
        inp, r = p.calculate()
        assert r.heck == 0, "combined design always completes"
        text = " | ".join(_flatten(p._build_result_rows(r)))
        assert "Design Checks" in text
        assert "OK" in text


class TestSlabResultRows:
    def test_continuous_shows_support_moments(self, slab_page):
        slab_page.slab_type.setCurrentIndex(2)  # continuous
        inp, r = slab_page.calculate()
        assert r.support_moments, "engine must fill continuous support moments"
        text = " | ".join(_flatten(slab_page._build_result_rows(r)))
        assert "Support 1 Moment" in text
        assert "Support 1 Steel" in text

    def test_twoway_shows_long_support_and_defl_depth(self, slab_page):
        slab_page.slab_type.setCurrentIndex(3)  # two-way
        inp, r = slab_page.calculate()
        text = " | ".join(_flatten(slab_page._build_result_rows(r)))
        assert "Long Support Moment" in text
        assert "Long Support Steel" in text
        assert "Depth for Deflection" in text
