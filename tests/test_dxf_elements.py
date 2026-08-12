"""Tests for column, slab and footing DXF drawings (Batches 4-6)."""

import pytest

from rcd2000.dxf_export import DxfExporter
from rcd2000.drawing_models import (
    DrawingScale,
    ShapeCode,
    RebarBar,
    RebarZone,
    ColumnDrawing,
    SlabDrawing,
    FootingDrawing,
)


@pytest.fixture
def ex() -> DxfExporter:
    return DxfExporter()


@pytest.fixture
def column() -> ColumnDrawing:
    return ColumnDrawing(
        col_id="C1",
        b_mm=400,
        D_mm=400,
        height_mm=3200,
        main_bars=[
            RebarBar(20, 4, 3200, ShapeCode.STRAIGHT, "C1"),
        ],
        ties=[RebarBar(10, 16, 1400, ShapeCode.U_BAR, "CT1")],
        axial_kn=1500.0,
        moment_knm=120.0,
    )


@pytest.fixture
def slab() -> SlabDrawing:
    return SlabDrawing(
        slab_id="S1",
        panel_type="two_way",
        lx_mm=5000,
        ly_mm=4000,
        t_mm=150,
        bot_short=[
            RebarZone(
                bars=[RebarBar(12, 10, 4000, ShapeCode.STRAIGHT, "SB")],
                start_mm=0, end_mm=4000, offset_from_face_mm=30,
            )
        ],
        bot_long=[
            RebarZone(
                bars=[RebarBar(12, 8, 5000, ShapeCode.STRAIGHT, "BL")],
                start_mm=0, end_mm=5000, offset_from_face_mm=30,
            )
        ],
    )


@pytest.fixture
def footing() -> FootingDrawing:
    return FootingDrawing(
        footing_id="F1",
        len_mm=2200,
        wid_mm=2200,
        t_mm=450,
        x_bars=[RebarBar(16, 10, 2150, ShapeCode.STRAIGHT, "FX")],
        y_bars=[RebarBar(16, 10, 2150, ShapeCode.STRAIGHT, "FY")],
        col_b_mm=400,
        col_D_mm=400,
    )


class TestColumn:
    def test_plan_outline(self, ex, column):
        msp = ex.modelspace
        ex.draw_column_plan(msp, column)
        assert len(msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1

    def test_plan_centerlines(self, ex, column):
        msp = ex.modelspace
        ex.draw_column_plan(msp, column)
        assert len(msp.query('LINE[layer=="CENTERLINE"]')) == 2

    def test_plan_tie(self, ex, column):
        msp = ex.modelspace
        ex.draw_column_plan(msp, column)
        assert len(msp.query('LWPOLYLINE[layer=="REBAR_STIRRUP"]')) == 1

    def test_plan_bar_circles(self, ex, column):
        msp = ex.modelspace
        ex.draw_column_plan(msp, column)
        # 4 main bars
        assert len(msp.query('CIRCLE[layer=="REBAR_MAIN"]')) == 4

    def test_elevation(self, ex, column):
        msp = ex.modelspace
        ex.draw_column_elevation(msp, column)
        assert len(msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1
        assert len(msp.query('LINE[layer=="REBAR_MAIN"]')) >= 2
        assert len(msp.query('LINE[layer=="REBAR_STIRRUP"]')) == 16

    def test_audit_clean(self, ex, column):
        msp = ex.modelspace
        ex.draw_column_plan(msp, column)
        ex.draw_column_elevation(msp, column, (1500, 0))
        assert ex.audit() == 0


class TestSlab:
    def test_plan_outline(self, ex, slab):
        msp = ex.modelspace
        ex.draw_slab_plan(msp, slab)
        assert len(msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1

    def test_plan_mesh(self, ex, slab):
        msp = ex.modelspace
        ex.draw_slab_plan(msp, slab)
        # bottom short 10 + bottom long 8 = 18 REBAR_MAIN
        assert len(msp.query('LINE[layer=="REBAR_MAIN"]')) == 18

    def test_section(self, ex, slab):
        msp = ex.modelspace
        ex.draw_slab_section(msp, slab)
        assert len(msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1
        assert len(msp.query('LINE[layer=="REBAR_MAIN"]')) >= 1

    def test_audit_clean(self, ex, slab):
        msp = ex.modelspace
        ex.draw_slab_plan(msp, slab)
        ex.draw_slab_section(msp, slab, (0, 3000))
        assert ex.audit() == 0


class TestFooting:
    def test_plan_outline(self, ex, footing):
        msp = ex.modelspace
        ex.draw_footing_plan(msp, footing)
        assert len(msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1

    def test_plan_column_dashed(self, ex, footing):
        msp = ex.modelspace
        ex.draw_footing_plan(msp, footing)
        assert len(msp.query('LWPOLYLINE[layer=="SECTION_CUT"]')) == 1

    def test_plan_bars(self, ex, footing):
        msp = ex.modelspace
        ex.draw_footing_plan(msp, footing)
        # 10 x-bars + 10 y-bars
        assert len(msp.query('LINE[layer=="REBAR_MAIN"]')) == 10
        assert len(msp.query('LINE[layer=="REBAR_DIST"]')) == 10

    def test_section(self, ex, footing):
        msp = ex.modelspace
        ex.draw_footing_section(msp, footing)
        assert len(msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1

    def test_audit_clean(self, ex, footing):
        msp = ex.modelspace
        ex.draw_footing_plan(msp, footing)
        ex.draw_footing_section(msp, footing, (0, 3000))
        assert ex.audit() == 0
