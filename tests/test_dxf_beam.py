"""Tests for beam DXF drawing (Batch 3).

Builds a realistic single-span BeamDrawing and asserts plan, elevation,
section, and BBS output produce the expected entities on the right layers,
plus a clean audit.
"""

import pytest

from rcd2000.dxf_export import DxfExporter
from rcd2000.drawing_models import (
    DrawingScale,
    ShapeCode,
    RebarBar,
    RebarZone,
    BeamDrawing,
    BbsRow,
)


@pytest.fixture
def beam() -> BeamDrawing:
    """A realistic 6 m simply-supported beam 300 x 600."""
    return BeamDrawing(
        beam_id="B1",
        span_mm=6000,
        b_mm=300,
        D_mm=600,
        d_mm=550,
        cover_mm=40,
        top_zones=[
            RebarZone(
                bars=[RebarBar(20, 2, 6000, ShapeCode.STRAIGHT, "T1")],
                start_mm=0, end_mm=6000, offset_from_face_mm=45,
                layer="REBAR_MAIN",
            )
        ],
        bottom_zones=[
            RebarZone(
                bars=[RebarBar(25, 3, 6000, ShapeCode.STRAIGHT, "B1")],
                start_mm=0, end_mm=6000, offset_from_face_mm=45,
                layer="REBAR_MAIN",
            )
        ],
        stirrup_zones=[
            RebarZone(
                bars=[RebarBar(10, 20, 6000, ShapeCode.U_BAR, "S1")],
                start_mm=50, end_mm=5950, offset_from_face_mm=40,
                layer="REBAR_STIRRUP",
            )
        ],
        mu_knm=150.0,
        vu_kn=100.0,
        ast_provided_mm2=1472.6,
    )


@pytest.fixture
def ex() -> DxfExporter:
    return DxfExporter()


class TestBeamPlan:
    def test_outline_and_hatch(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_plan(msp, beam)
        assert len(msp.query("HATCH")) == 1
        outline = msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')
        assert len(outline) == 1

    def test_centerline(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_plan(msp, beam)
        assert len(msp.query('LINE[layer=="CENTERLINE"]')) == 1

    def test_top_and_bottom_bars(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_plan(msp, beam)
        # top: 2 bars, bottom: 3 bars = 5 REBAR_MAIN lines (plan runs)
        main = msp.query('LINE[layer=="REBAR_MAIN"]')
        assert len(main) == 5

    def test_stirrup_ticks(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_plan(msp, beam)
        # stirrup zone: 20 bars -> ticks on REBAR_STIRRUP
        assert len(msp.query('LINE[layer=="REBAR_STIRRUP"]')) == 20

    def test_dimensions(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_plan(msp, beam)
        assert len(msp.query("DIMENSION")) == 2


class TestBeamElevation:
    def test_outline(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_elevation(msp, beam)
        assert len(msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1

    def test_bar_runs(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_elevation(msp, beam)
        main = msp.query('LINE[layer=="REBAR_MAIN"]')
        # one line per zone (bars in the same zone overlap in elevation view)
        assert len(main) == 2

    def test_stirrups_present(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_elevation(msp, beam)
        assert len(msp.query('LINE[layer=="REBAR_STIRRUP"]')) >= 20

    def test_supports(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_elevation(msp, beam)
        assert len(msp.query('LINE[layer=="GRID"]')) == 2


class TestBeamSection:
    def test_outline(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_section(msp, beam)
        assert len(msp.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1

    def test_stirrup_outline(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_section(msp, beam)
        assert len(msp.query('LWPOLYLINE[layer=="REBAR_STIRRUP"]')) == 1

    def test_bar_circles(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_section(msp, beam)
        # top 2 + bottom 3 = 5 bar circles
        assert len(msp.query('CIRCLE[layer=="REBAR_MAIN"]')) == 5

    def test_dimensions(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_section(msp, beam)
        assert len(msp.query("DIMENSION")) == 2


class TestBbs:
    def test_bbs_table(self, ex, beam):
        msp = ex.modelspace
        rows = [
            BbsRow("T1", ShapeCode.STRAIGHT, 20, 2, 6000),
            BbsRow("B1", ShapeCode.STRAIGHT, 25, 3, 6000),
            BbsRow("S1", ShapeCode.U_BAR, 10, 20, 1250, "links"),
        ]
        ex.draw_bbs(msp, rows)
        # 3 data rows + 1 header
        assert len(msp.query('TEXT[layer=="TEXT"]')) >= 4 * 3


class TestBeamComposite:
    def test_audit_clean(self, ex, beam):
        msp = ex.modelspace
        ex.draw_beam_plan(msp, beam)
        ex.draw_beam_elevation(msp, beam, (0, 1000))
        ex.draw_beam_section(msp, beam, (7000, 0))
        assert ex.audit() == 0

    def test_save_file(self, ex, beam, tmp_path):
        msp = ex.modelspace
        ex.draw_beam_plan(msp, beam)
        ex.draw_beam_elevation(msp, beam, (0, 1000))
        ex.draw_beam_section(msp, beam, (7000, 0))
        out = tmp_path / "beam.dxf"
        ex.save(str(out))
        assert out.exists() and out.stat().st_size > 1000
