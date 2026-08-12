"""Tests for the DxfExporter core (Batch 2).

Verifies layer standard, dimension/text styles, standard blocks, and
primitives — plus a clean doc.audit() on a small composite drawing.
"""

import pytest

from rcd2000.dxf_export import DxfExporter
from rcd2000.drawing_models import DrawingScale


@pytest.fixture
def ex() -> DxfExporter:
    return DxfExporter()


class TestSetup:
    def test_layer_standard_exact(self, ex):
        layer_names = {l.dxf.name for l in ex.doc.layers}
        assert layer_names >= set(DxfExporter.LAYERS)

    def test_layer_linetypes(self, ex):
        center = ex.doc.layers.get("CENTERLINE")
        assert center.dxf.linetype == "CENTER"

    def test_dimstyles_exist(self, ex):
        for name in ("STRUCT_20", "STRUCT_25", "STRUCT_50", "STRUCT_100"):
            assert name in ex.doc.dimstyles

    def test_struct50_params(self, ex):
        ds = ex.doc.dimstyles.get("STRUCT_50")
        assert ds.dxf.dimscale == 1
        assert ds.dxf.dimlfac == 50
        assert ds.dxf.dimtxt == 2.5
        assert ds.dxf.dimasz == 2.5

    def test_textstyles_exist(self, ex):
        assert "OPEN_SANS" in ex.doc.styles
        assert "OPEN_SANS_BOLD" in ex.doc.styles

    def test_blocks_exist(self, ex):
        for name in ("BAR_MARK", "NORTH_ARROW", "SECTION_CUT"):
            assert name in ex.doc.blocks


class TestPrimitives:
    def test_rect_creates_lwpolyline_on_layer(self, ex):
        msp = ex.modelspace
        ex.rect(msp, 0, 0, 6000, 300)
        polys = msp.query("LWPOLYLINE")
        assert len(polys) == 1
        assert polys[0].dxf.layer == "CONCRETE_OUTLINE"

    def test_rect_scales_50(self, ex):
        msp = ex.modelspace
        ex.rect(msp, 0, 0, 6000, 300)
        pts = list(msp.query("LWPOLYLINE")[0].get_points())
        xs = [p[0] for p in pts]
        assert max(xs) == pytest.approx(6000 / 50)  # 120

    def test_hatch_rect(self, ex):
        msp = ex.modelspace
        ex.hatch_rect(msp, 0, 0, 6000, 300)
        assert len(msp.query("HATCH")) == 1
        assert msp.query("HATCH")[0].dxf.layer == "CONCRETE_HATCH"

    def test_line(self, ex):
        msp = ex.modelspace
        ex.line(msp, (0, 0), (100, 100))
        assert len(msp.query("LINE")) == 1

    def test_polyline_closed(self, ex):
        msp = ex.modelspace
        ex.polyline(msp, [(0, 0), (10, 0), (10, 10)], close=True)
        pl = msp.query("LWPOLYLINE")[0]
        assert pl.closed

    def test_circle(self, ex):
        msp = ex.modelspace
        ex.circle(msp, (100, 100), 10, layer="REBAR_MAIN")
        c = msp.query("CIRCLE")[0]
        assert c.dxf.layer == "REBAR_MAIN"
        assert c.dxf.radius == pytest.approx(10 / 50)

    def test_text_centered(self, ex):
        msp = ex.modelspace
        ex.text(msp, "B1", (100, 100), align=1)
        t = msp.query("TEXT")[0]
        assert t.dxf.layer == "TEXT"
        assert t.dxf.height == pytest.approx(4.0 / 50)

    def test_bar_line_three_entities(self, ex):
        msp = ex.modelspace
        ex.bar_line(msp, (0, 0), (1000, 0), 20)
        assert len(msp.query("LINE")) == 1
        assert len(msp.query("CIRCLE")) == 2

    def test_dim_linear_renders(self, ex):
        msp = ex.modelspace
        ex.dim_linear(msp, (0, 0), (1000, 0), offset=-200)
        # rendered dimension creates an anonymous block + DIMENSION entity
        assert len(msp.query("DIMENSION")) == 1

    def test_blockref_with_attributes(self, ex):
        msp = ex.modelspace
        ex.blockref(msp, "BAR_MARK", (50, 50), attributes={"MARK": "2-Ø20"})
        refs = msp.query("INSERT")
        assert len(refs) == 1
        assert refs[0].dxf.name == "BAR_MARK"


class TestAudit:
    def test_audit_clean_after_composite(self, ex):
        msp = ex.modelspace
        ex.rect(msp, 0, 0, 6000, 300)
        ex.hatch_rect(msp, 0, 0, 6000, 300)
        ex.bar_line(msp, (100, 50), (5900, 50), 20)
        ex.bar_line(msp, (100, 250), (5900, 250), 16, layer="REBAR_DIST")
        ex.text(msp, "SECTION A-A", (3000, 600))
        ex.dim_linear(msp, (0, 0), (6000, 0), offset=-150)
        ex.bar_mark(msp, (500, 400), "1-Ø20")
        assert ex.audit() == 0
