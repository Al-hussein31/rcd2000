"""Tests for paper-space sheets and title block (Batch 7)."""

import pytest

from rcd2000.dxf_export import DxfExporter
from rcd2000.drawing_models import (
    DrawingScale,
    ShapeCode,
    RebarBar,
    RebarZone,
    BeamDrawing,
    Sheet,
)


@pytest.fixture
def ex() -> DxfExporter:
    return DxfExporter()


@pytest.fixture
def sheet() -> Sheet:
    return Sheet(
        sheet_no="S-01",
        title="BEAM B1 - PLAN & DETAILS",
        project="TEST PROJECT",
        rev="A",
        engineer="J. DOE",
        date="2026-08-12",
        paper=(841.0, 594.0),
        scale_note="SCALE 1:50",
    )


@pytest.fixture
def beam() -> BeamDrawing:
    return BeamDrawing(
        beam_id="B1", span_mm=6000, b_mm=300, D_mm=600, d_mm=550, cover_mm=40,
        top_zones=[RebarZone(bars=[RebarBar(20, 2, 6000)], start_mm=0,
                             end_mm=6000, offset_from_face_mm=45)],
        bottom_zones=[RebarZone(bars=[RebarBar(25, 3, 6000)], start_mm=0,
                                end_mm=6000, offset_from_face_mm=45)],
        stirrup_zones=[RebarZone(bars=[RebarBar(10, 20, 6000)], start_mm=50,
                                 end_mm=5950, offset_from_face_mm=40)],
    )


class TestSheet:
    def test_creates_layout(self, ex, sheet):
        layout = ex.new_sheet(sheet)
        assert layout.name == "SHEET_S01"

    def test_border_frames(self, ex, sheet):
        layout = ex.new_sheet(sheet)
        # outer + inner frames
        assert len(layout.query('LWPOLYLINE[layer=="CONCRETE_OUTLINE"]')) == 1
        assert len(layout.query('LWPOLYLINE[layer=="TEXT"]')) >= 2

    def test_title_text_present(self, ex, sheet):
        layout = ex.new_sheet(sheet)
        texts = [t.dxf.text for t in layout.query("TEXT")]
        assert any("BEAM B1" in t for t in texts)
        assert any("PROJECT: TEST PROJECT" in t for t in texts)
        assert any("S-01" in t for t in texts)

    def test_audit_clean(self, ex, sheet):
        ex.new_sheet(sheet)
        assert ex.audit() == 0


class TestViewport:
    def test_viewport_added(self, ex, sheet, beam):
        # model space content first
        msp = ex.modelspace
        ex.draw_beam_elevation(msp, beam)
        # sheet with viewport framing the beam
        layout = ex.new_sheet(sheet)
        ex.add_viewport(
            layout,
            center=(420, 320),
            size=(700, 400),
            view_center=(60, 10),   # model coords (scaled 1:50)
            view_height=120,
        )
        vps = layout.query("VIEWPORT")
        # paperspace always has a main viewport (id 1) + our added one
        assert len(vps) == 2
        assert vps[0].dxf.id == 1 or vps[1].dxf.id == 1

    def test_sheet_save(self, ex, sheet, beam, tmp_path):
        msp = ex.modelspace
        ex.draw_beam_elevation(msp, beam)
        layout = ex.new_sheet(sheet)
        ex.add_viewport(
            layout,
            center=(420, 320), size=(700, 400),
            view_center=(60, 10), view_height=120,
        )
        out = tmp_path / "sheet.dxf"
        ex.save(str(out))
        assert out.exists() and out.stat().st_size > 1000
