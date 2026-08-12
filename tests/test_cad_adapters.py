"""Tests for CAD adapters (Batch 8): engine results -> DrawingModel."""

import math

import pytest

from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.base import BaseDesigner, BaseInput
from rcd2000.stair import StairDesigner, StairInput
from rcd2000.cad_adapters import (
    bars_for_area,
    beam_to_drawing,
    column_to_drawing,
    slab_to_drawing,
    footing_to_drawing,
    stair_to_drawing,
    drawing_for,
)
from rcd2000.drawing_models import DrawingScale


class TestBarsForArea:
    def test_zero_area(self):
        assert bars_for_area(0, 6000, 20, 150) == []

    def test_count_meets_area(self):
        # 1472 mm² with Ø20 (314 mm²/bar) -> ceil(1472/314) = 5 bars,
        # but distributed at 200 mm over 6000 mm -> 31 bars governs
        bars = bars_for_area(1472.6, 6000, 20, 200)
        assert bars[0].count == 31
        assert bars[0].diameter_mm == 20

    def test_count_respects_spacing(self):
        # tiny area but long member at 100 mm spacing -> many bars
        bars = bars_for_area(100, 6000, 12, 100)
        assert bars[0].count >= 60

    def test_min_bars(self):
        bars = bars_for_area(1, 6000, 12, 250, min_bars=2)
        assert bars[0].count >= 2


class TestBeamAdapter:
    def test_maps_geometry(self):
        inp = BeamInput(
            beam_id="B1", n_members=1, n_supports=2,
            b=300, bf=300, h=600, hf=0,
            fcu=30, fy=460, fyv=460,
            member_lengths=[6.0], member_udl=[30.0],
            ty1=0, ty2=0,
        )
        result = BeamDesigner().design([inp])[0]
        draw = beam_to_drawing(inp, result)
        assert draw.beam_id == "B1"
        assert draw.span_mm == 6000
        assert draw.b_mm == 300
        assert draw.D_mm == 600
        assert draw.bottom_zones, "expected bottom reinforcement"
        # zone covers the full span
        assert draw.bottom_zones[0].end_mm == pytest.approx(6000)

    def test_ast_passes_through(self):
        inp = BeamInput(
            beam_id="B2", n_members=1, n_supports=2,
            b=300, bf=300, h=600, hf=0,
            fcu=30, fy=460, fyv=460,
            member_lengths=[6.0], member_udl=[40.0],
            ty1=0, ty2=0,
        )
        result = BeamDesigner().design([inp])[0]
        draw = beam_to_drawing(inp, result)
        span_res = result.spans[0]
        # adapter-provided steel should satisfy the requirement
        provided = sum(b.area_mm2 for z in draw.bottom_zones for b in z.bars)
        assert provided >= span_res.steel_bot


class TestColumnAdapter:
    def test_maps_geometry_and_rebar(self):
        inp = ColumnInput(
            column_id="C1", col_type=1, shape=1,
            load=1500, bx=400, by=400, depth=400,
            length=3.2, le=3.2, lex=3.2, ley=3.2,
        )
        result = ColumnDesigner().design([inp])[0]
        draw = column_to_drawing(inp, result)
        assert draw.col_id == "C1"
        assert draw.b_mm == 400
        assert draw.height_mm == 3200
        assert draw.main_bars, "expected main bars"
        assert draw.main_bars[0].count >= 4
        assert draw.ties, "expected ties"

    def test_minimum_reinforcement(self):
        inp = ColumnInput(
            column_id="C2", col_type=1, shape=1,
            load=50, bx=250, by=250, depth=250,
            length=2.5, le=2.5, lex=2.5, ley=2.5,
        )
        result = ColumnDesigner().design([inp])[0]
        draw = column_to_drawing(inp, result)
        # nominal steel always provided
        assert draw.main_bars[0].count >= 4


class TestSlabAdapter:
    def test_one_way(self):
        inp = SlabPanelInput(
            panel_id="S1", panel_type=2, depth=175, fcu=25, fy=460,
            udl=12.0, span=5.0,
        )
        result = SlabDesigner().design([inp])[0]
        draw = slab_to_drawing(inp, result)
        assert draw.slab_id == "S1"
        assert draw.lx_mm == 5000
        assert draw.panel_type == "one_way"
        assert draw.bot_short, "expected bottom short bars"

    def test_cantilever(self):
        inp = SlabPanelInput(
            panel_id="SC", panel_type=1, depth=150, fcu=25, fy=460,
            udl=8.0, span=1.5,
        )
        result = SlabDesigner().design([inp])[0]
        draw = slab_to_drawing(inp, result)
        assert draw.panel_type == "cantilever"
        assert draw.lx_mm == 1500


class TestStairAdapter:
    def test_maps_geometry(self):
        inp = StairInput(
            stair_id="ST1", span=3.2, tread=280, rise=160,
            imposed_load=3.0, spl=1.5, wld=24,
        )
        result = StairDesigner().design([inp])[0]
        draw = stair_to_drawing(inp, result)
        assert draw.stair_id == "ST1"
        assert draw.span_mm == 3200
        assert draw.waist_mm == 160
        assert draw.tread_mm == 280

    def test_dispatcher(self):
        inp = StairInput(stair_id="ST1", span=3.2, tread=280, rise=160,
                         imposed_load=3.0, spl=1.5, wld=24)
        result = StairDesigner().design([inp])[0]
        draw = drawing_for(inp, result, "stair")
        assert draw.stair_id == "ST1"

    def test_dispatcher_unknown(self):
        with pytest.raises(TypeError):
            drawing_for(None, None, "cont_beam")


class TestFootingAdapter:
    def test_maps_geometry(self):
        inp = BaseInput(
            base_id="F1", base_type=1, col_type=1,
            load=1500, pb=150, fcu=25, fy=460,
            a1=400, a2=400,
        )
        result = BaseDesigner().design([inp])[0]
        draw = footing_to_drawing(inp, result)
        assert draw.footing_id == "F1"
        assert draw.len_mm > 0
        assert draw.x_bars, "expected x bars"
        assert draw.col_b_mm == 400
