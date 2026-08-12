"""Tests for the CAD drawing-model dataclasses (Batch 1).

Pure Python — no Qt, no ezdxf. Validates defaults, unit conventions,
and the RebarBar/BBS helper.
"""

import pytest

from rcd2000.drawing_models import (
    DrawingScale,
    ShapeCode,
    RebarBar,
    RebarZone,
    BeamDrawing,
    ColumnDrawing,
    SlabDrawing,
    FootingDrawing,
    BbsRow,
    Sheet,
    bbs_row_from_bar,
)


class TestScalesAndShapes:
    def test_default_scale_is_1_50(self):
        assert DrawingScale.S1_50.value == 50

    def test_all_scales_positive(self):
        for scale in DrawingScale:
            assert scale.value > 0

    def test_shape_codes(self):
        assert ShapeCode.STRAIGHT == "00"
        assert ShapeCode.BOTH_HOOKS == "12"
        assert ShapeCode.L_BEND == "21"


class TestRebarBar:
    def test_area_round(self):
        # 4 x Ø20 -> 4 * pi * 10^2 = 1256.6 mm²
        bar = RebarBar(diameter_mm=20, count=4, length_mm=6000)
        assert bar.area_mm2 == pytest.approx(1256.637, rel=1e-3)

    def test_mark_default_empty(self):
        assert RebarBar(20, 2, 1000).mark == ""

    def test_default_shape_straight(self):
        assert RebarBar(20, 2, 1000).shape is ShapeCode.STRAIGHT


class TestRebarZone:
    def test_length(self):
        zone = RebarZone(
            bars=[RebarBar(20, 2, 5000)],
            start_mm=250,
            end_mm=5750,
            offset_from_face_mm=50,
        )
        assert zone.length_mm == 5500

    def test_zero_length_when_reversed(self):
        zone = RebarZone(start_mm=5000, end_mm=250)
        assert zone.length_mm == 0


class TestDrawingDataclasses:
    def test_beam_defaults(self):
        beam = BeamDrawing()
        assert beam.beam_id == "B1"
        assert beam.cover_mm == 30
        assert beam.scale is DrawingScale.S1_50
        assert beam.top_zones == []

    def test_beam_scale_field(self):
        beam = BeamDrawing(scale=DrawingScale.S1_100)
        assert beam.scale.value == 100

    def test_column_defaults(self):
        col = ColumnDrawing()
        assert col.col_id == "C1"
        assert col.main_bars == []

    def test_slab_defaults(self):
        slab = SlabDrawing()
        assert slab.panel_type == "one_way"
        assert slab.top_short == []

    def test_footing_defaults(self):
        ftg = FootingDrawing()
        assert ftg.footing_id == "F1"
        assert ftg.x_bars == []

    def test_sheet_defaults(self):
        s = Sheet()
        assert s.sheet_no == "S-01"
        assert s.paper == (841.0, 594.0)


class TestBbsHelper:
    def test_bbs_row_from_bar(self):
        bar = RebarBar(diameter_mm=20, count=4, length_mm=6000,
                       shape=ShapeCode.BOTH_HOOKS, mark="2")
        row = bbs_row_from_bar("2", bar)
        assert isinstance(row, BbsRow)
        assert row.dia_mm == 20
        assert row.n == 4
        assert row.length_mm == 6000
        assert row.shape is ShapeCode.BOTH_HOOKS
        assert row.mark == "2"
