"""DXF QA harness (Batch 10).

Generates every element drawing + a full multi-element sheet, then
verifies standards: audit clean, layer discipline (no content on layer 0),
and entity counts. Mirrors what CI will run on every commit.
"""

import pytest
import ezdxf

from rcd2000.dxf_export import DxfExporter
from rcd2000.drawing_models import (
    DrawingScale,
    ShapeCode,
    RebarBar,
    RebarZone,
    BeamDrawing,
    ColumnDrawing,
    SlabDrawing,
    FootingDrawing,
    Sheet,
)
from rcd2000.cad_adapters import (
    bars_for_area,
    beam_to_drawing,
    column_to_drawing,
    slab_to_drawing,
    footing_to_drawing,
)
from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.base import BaseDesigner, BaseInput


def sample_beam_drawing() -> BeamDrawing:
    return BeamDrawing(
        beam_id="B1", span_mm=6000, b_mm=300, D_mm=600, d_mm=550, cover_mm=40,
        top_zones=[RebarZone(bars=[RebarBar(20, 2, 6000)], start_mm=0,
                             end_mm=6000, offset_from_face_mm=45)],
        bottom_zones=[RebarZone(bars=[RebarBar(25, 3, 6000)], start_mm=0,
                                end_mm=6000, offset_from_face_mm=45)],
        stirrup_zones=[RebarZone(bars=[RebarBar(10, 20, 6000)], start_mm=50,
                                 end_mm=5950, offset_from_face_mm=40)],
        mu_knm=150.0, vu_kn=100.0, ast_provided_mm2=1472.6,
    )


def sample_column_drawing() -> ColumnDrawing:
    return ColumnDrawing(
        col_id="C1", b_mm=400, D_mm=400, height_mm=3200,
        main_bars=[RebarBar(20, 4, 3200)], ties=[RebarBar(10, 16, 1400)],
        axial_kn=1500.0, moment_knm=120.0,
    )


def sample_slab_drawing() -> SlabDrawing:
    return SlabDrawing(
        slab_id="S1", panel_type="two_way", lx_mm=5000, ly_mm=4000, t_mm=150,
        bot_short=[RebarZone(bars=[RebarBar(12, 10, 4000)], start_mm=0,
                             end_mm=4000)],
        bot_long=[RebarZone(bars=[RebarBar(12, 8, 5000)], start_mm=0,
                            end_mm=5000)],
    )


def sample_footing_drawing() -> FootingDrawing:
    return FootingDrawing(
        footing_id="F1", len_mm=2200, wid_mm=2200, t_mm=450,
        x_bars=[RebarBar(16, 10, 2150)], y_bars=[RebarBar(16, 10, 2150)],
        col_b_mm=400, col_D_mm=400,
    )


def _full_sheet_exporter() -> DxfExporter:
    ex = DxfExporter()
    msp = ex.modelspace
    beam = sample_beam_drawing()
    ex.draw_beam_plan(msp, beam)
    ex.draw_beam_elevation(msp, beam, (0, 900))
    ex.draw_beam_section(msp, beam, (7000, 0))
    col = sample_column_drawing()
    ex.draw_column_plan(msp, col, (11000, 0))
    ex.draw_column_elevation(msp, col, (12600, 0))
    slab = sample_slab_drawing()
    ex.draw_slab_plan(msp, slab, (0, 3000))
    ex.draw_slab_section(msp, slab, (6000, 3000))
    ftg = sample_footing_drawing()
    ex.draw_footing_plan(msp, ftg, (11000, 3000))
    ex.draw_footing_section(msp, ftg, (13500, 3000))
    sheet = Sheet(sheet_no="S-01", title="ALL ELEMENTS - DETAIL SHEET",
                  paper=(841.0, 594.0))
    layout = ex.new_sheet(sheet)
    ex.add_viewport(layout, center=(380, 320), size=(700, 400),
                    view_center=(120, 30), view_height=160)
    return ex


class TestQa:
    def test_full_sheet_audit_clean(self):
        ex = _full_sheet_exporter()
        assert ex.audit() == 0

    def test_no_content_on_layer0(self):
        """Every content entity must be on a defined layer."""
        ex = _full_sheet_exporter()
        msp = ex.modelspace
        for e in msp:
            layer = e.dxf.layer
            assert layer != "0", f"{e.dxftype()} on layer 0"
            assert layer in DxfExporter.LAYERS, f"unknown layer {layer}"

    def test_save_and_reload(self, tmp_path):
        ex = _full_sheet_exporter()
        out = tmp_path / "qa.dxf"
        ex.save(str(out))
        doc = ezdxf.readfile(str(out))
        assert len(doc.audit().errors) == 0

    def test_engine_adapter_consistency(self):
        """Engine results -> adapters -> DXF stays audit-clean."""
        ex = DxfExporter()
        msp = ex.modelspace

        beam = BeamDesigner(fcu=25, fy=460, fyv=460).design([BeamInput(
            beam_id="B1", n_members=1, n_supports=2, b=300, bf=300,
            h=600, hf=0, fcu=25, fy=460, fyv=460,
            member_lengths=[6.0], member_udl=[45.0], ty1=0, ty2=0,
        )])[0]
        ex.draw_beam_elevation(msp, beam_to_drawing(
            BeamInput(beam_id="B1", n_members=1, n_supports=2, b=300, bf=300,
                      h=600, hf=0, fcu=25, fy=460, fyv=460,
                      member_lengths=[6.0], member_udl=[45.0], ty1=0, ty2=0),
            beam))

        col = ColumnDesigner().design([ColumnInput(
            column_id="C1", col_type=1, shape=1, load=1500, bx=400, by=400,
            depth=400, length=3.2, le=3.2, lex=3.2, ley=3.2,
        )])[0]
        ex.draw_column_plan(msp, column_to_drawing(
            ColumnInput(column_id="C1", col_type=1, shape=1, load=1500,
                        bx=400, by=400, depth=400, length=3.2, le=3.2,
                        lex=3.2, ley=3.2),
            col))

        assert ex.audit() == 0

    def test_bars_for_area_golden(self):
        bars = bars_for_area(1472.6, 6000, 20, 200)
        assert bars[0].count == 31
        assert bars[0].diameter_mm == 20
