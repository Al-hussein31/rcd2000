"""Round-trip tests for get_state / set_state on every DesignFormPage subclass."""

import pytest
from PySide6.QtWidgets import QApplication

from rcd2000.gui.pages.column_page import ColumnPage
from rcd2000.gui.pages.beam_page import BeamPage
from rcd2000.gui.pages.slab_page import SlabPage
from rcd2000.gui.pages.stair_page import StairPage
from rcd2000.gui.pages.base_page import BasePage
from rcd2000.gui.pages.continuous_beam_page import ContinuousBeamPage


# ── Helpers ──────────────────────────────────────────────────────────

def _set_non_default(page):
    """Set non-default values on every input widget of *page*."""
    if isinstance(page, ColumnPage):
        page.col_type.setCurrentIndex(2)
        page.shape.setCurrentIndex(1)  # Circular - depth auto-syncs to dia
        page.load.setValue(2500)
        page.bx.setValue(400)
        page.by.setValue(300)
        page.dia.setValue(500)
        page.depth.setValue(500)  # must equal dia for circular
        page.length.setValue(3.5)
        page.le.setValue(3.0)
        page.lex.setValue(2.8)
        page.ley.setValue(2.5)
        page._set_combo_int(page.col_fcu, 35)
        page._set_combo_int(page.col_fy, 500)
        page.col_max_steel.setValue(6.0)
        page.col_dh.setValue(0.95)
        page.moment_x.setValue(150)
        page.moment_y.setValue(80)
        page.moment.setValue(45)

    elif isinstance(page, BeamPage):
        page._set_combo_int(page.beam_fcu, 40)
        page._set_combo_int(page.beam_fy, 500)
        page._set_combo_int(page.beam_fyv, 460)
        page.b_b.setValue(300)
        page.b_bf.setValue(600)
        page.b_h.setValue(800)
        page.b_hf.setValue(150)
        page.n_supports.setValue(3)
        page.n_members.setValue(2)
        page.ty1.setCurrentIndex(1)
        page.ty2.setCurrentIndex(0)
        page.cant_load_1.setValue(25.0)
        page.cant_moment_1.setValue(30.0)
        page.cant_load_2.setValue(15.0)
        page.cant_moment_2.setValue(20.0)
        page.gk.setValue(15.5)
        page.qk.setValue(8.2)
        # Member grid
        for w in page._member_widgets:
            w[1].setValue(6.5)   # length
            w[2].setValue(250)   # udl
            w[3].setValue(10)     # wt
            w[4].setValue(5)      # wb
            w[5].setValue(2.0)    # ab
            w[6].setValue(30)     # pl
            w[7].setValue(3.0)    # ap

    elif isinstance(page, SlabPage):
        page.slab_type.setCurrentIndex(2)
        page._set_combo_int(page.slab_fcu, 30)
        page._set_combo_int(page.slab_fy, 460)
        page.s_depth.setValue(200)
        page.s_span.setValue(5.5)
        page.s_ly.setValue(7.0)
        page.s_case.setValue(3)
        page.s_sd.setValue(24)
        page.gk.setValue(12.0)
        page.qk.setValue(6.5)
        page.s_cant_load_1.setValue(25)
        page.s_cant_moment_1.setValue(40)
        page.s_cant_load_2.setValue(15)
        page.s_cant_moment_2.setValue(20)
        page.panel_npl.setValue(2)
        for w in page._panel_pl_widgets:
            w[0].setValue(50)   # pl
            w[1].setValue(2.0)  # ap
        page.cont_nspan.setValue(4)
        for w in page._cont_span_widgets:
            w[0].setValue(5.0)   # length
            w[1].setValue(15.0)  # udl
            w[2].setValue(30)    # pl
            w[3].setValue(2.5)   # ap

    elif isinstance(page, StairPage):
        page.s_span.setValue(3.5)
        page.s_tread.setValue(280)
        page.s_rise.setValue(160)
        page.s_imp.setValue(3.0)
        page.s_spl.setValue(1.5)
        page.s_wld.setValue(24)
        page.gk.setValue(7.0)
        page.qk.setValue(3.0)

    elif isinstance(page, BasePage):
        page.base_type.setCurrentIndex(2)   # Combined
        page.col_shape.setCurrentIndex(0)
        page._set_combo_int(page.base_fcu, 35)
        page._set_combo_int(page.base_fy, 460)
        page.base_pb.setValue(250)
        page.base_load.setValue(1800)
        page.base_a1.setValue(350)
        page.base_a2.setValue(250)
        page.base_dia.setValue(400)
        page.base_h.setValue(500)
        page.base_l1.setValue(2.5)
        page.base_l2.setValue(1.8)
        page.base_dowel.setValue(20)
        page.gk.setValue(10.0)
        page.qk.setValue(5.0)
        # Combined-footing columns
        for i, w in enumerate(page._col_widgets):
            w[1].setValue(400 + i * 100)   # load
            w[2].setValue(i * 4.0)         # dist
            w[3].setCurrentIndex(i % 2)    # shape
            w[4].setValue(350 + i)         # a1
            w[5].setValue(250 + i)         # a2
            w[6].setValue(400 + i)         # dia
            w[7].setValue(16 + i)          # dowel

    elif isinstance(page, ContinuousBeamPage):
        page.cb_ns.setValue(4)
        page.cb_nm.setValue(3)
        page.cb_end1.setCurrentIndex(1)
        page.cb_end2.setCurrentIndex(0)
        page.cb_cant_load_1.setValue(20.0)
        page.cb_cant_moment_1.setValue(35.0)
        page.cb_cant_load_2.setValue(10.0)
        page.cb_cant_moment_2.setValue(15.0)
        for w in page._cb_member_widgets:
            w[1].setValue(7.0)       # length
            w[2].setValue(0.005)     # inertia
            w[3].setValue(1.2)       # e_mod
            w[4].setValue(18.0)      # udl
            w[5].setValue(12.0)      # wt
            w[6].setValue(6.0)       # wb
            w[7].setValue(3.0)       # ab
            w[8].setValue(40.0)      # pl
            w[9].setValue(3.5)       # ap


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """One QApplication for the whole module."""
    return QApplication.instance() or QApplication([])


@pytest.fixture(params=[
    ColumnPage, BeamPage, SlabPage, StairPage, BasePage, ContinuousBeamPage,
])
def page(request, app):
    p = request.param()
    p._build_ui()
    return p


# ── Round-trip tests ─────────────────────────────────────────────────

class TestStateRoundTrip:
    def test_round_trip(self, page):
        _set_non_default(page)
        state1 = page.get_state()

        # Fresh instance, set state, get state again
        fresh = type(page)()
        fresh._build_ui()
        fresh.set_state(state1)
        state2 = fresh.get_state()

        assert state1 == state2, (
            f"State round-trip mismatch for {type(page).__name__}:\n"
            f"  before: {state1}\n  after:  {state2}"
        )

    def test_missing_keys_ignored(self, page):
        _set_non_default(page)
        state = page.get_state()
        # Remove a key — set_state must not crash
        key = next(iter(state))
        del state[key]
        fresh = type(page)()
        fresh._build_ui()
        fresh.set_state(state)  # should not raise

    def test_extra_keys_ignored(self, page):
        _set_non_default(page)
        state = page.get_state()
        state["_nonexistent_key"] = 42
        fresh = type(page)()
        fresh._build_ui()
        fresh.set_state(state)  # should not raise
