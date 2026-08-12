"""Tests for IFC export (Batch 12).

Requires IfcOpenShell (optional dep). Skips cleanly when unavailable.
Verifies: file structure, member entities, nested rebar, bar types with
mapped geometry, psets/qtos, and zero schema validation issues.
"""

import pytest

pytest.importorskip("ifcopenshell")

import ifcopenshell  # noqa: E402

from rcd2000.drawing_models import (  # noqa: E402
    DrawingScale,
    ShapeCode,
    RebarBar,
    RebarZone,
    BeamDrawing,
    ColumnDrawing,
    SlabDrawing,
    FootingDrawing,
)
from rcd2000.ifc_export import IfcExporter, export_drawings  # noqa: E402


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
        mu_knm=150.0, vu_kn=100.0, ast_provided_mm2=1472.6,
    )


@pytest.fixture
def column() -> ColumnDrawing:
    return ColumnDrawing(
        col_id="C1", b_mm=400, D_mm=400, height_mm=3200,
        main_bars=[RebarBar(20, 4, 3200)],
        ties=[RebarBar(10, 16, 1400)],
        axial_kn=1500.0, moment_knm=120.0,
    )


class TestIfcExporter:
    def test_project_structure(self, beam, tmp_path):
        ex = IfcExporter("TEST")
        out = ex.export([beam], str(tmp_path / "b.ifc"))
        f = ifcopenshell.open(out)
        assert len(f.by_type("IfcProject")) == 1
        assert len(f.by_type("IfcSite")) == 1
        assert len(f.by_type("IfcBuilding")) == 1
        assert len(f.by_type("IfcBuildingStorey")) == 1

    def test_beam_with_rebar(self, beam, tmp_path):
        ex = IfcExporter("TEST")
        out = ex.export([beam], str(tmp_path / "b.ifc"))
        f = ifcopenshell.open(out)
        assert len(f.by_type("IfcBeam")) == 1
        # 2 top + 3 bottom + 20 stirrups
        assert len(f.by_type("IfcReinforcingBar")) == 25
        assert len(f.by_type("IfcReinforcingBarType")) >= 3
        assert len(f.by_type("IfcRelNests")) >= 1

    def test_rebar_nested_in_beam(self, beam, tmp_path):
        ex = IfcExporter("TEST")
        out = ex.export([beam], str(tmp_path / "b.ifc"))
        f = ifcopenshell.open(out)
        beam_el = f.by_type("IfcBeam")[0]
        nests = f.by_type("IfcRelNests")
        nested_bars = []
        for rel in nests:
            if rel.RelatingObject == beam_el:
                nested_bars.extend(rel.RelatedObjects)
        assert len(nested_bars) == 25

    def test_material_assigned(self, beam, tmp_path):
        ex = IfcExporter("TEST")
        out = ex.export([beam], str(tmp_path / "b.ifc"))
        f = ifcopenshell.open(out)
        mats = f.by_type("IfcMaterial")
        names = {m.Name for m in mats}
        assert "C30/37" in names
        assert "B500B" in names

    def test_psets(self, beam, tmp_path):
        ex = IfcExporter("TEST")
        out = ex.export([beam], str(tmp_path / "b.ifc"))
        f = ifcopenshell.open(out)
        pset_names = {p.Name for p in f.by_type("IfcPropertySet")}
        assert "Pset_ConcreteElementGeneral" in pset_names
        assert "Pset_RCDDesignResults" in pset_names

    def test_qtos(self, beam, tmp_path):
        ex = IfcExporter("TEST")
        out = ex.export([beam], str(tmp_path / "b.ifc"))
        f = ifcopenshell.open(out)
        qto_names = {q.Name for q in f.by_type("IfcElementQuantity")}
        assert "Qto_BeamBaseQuantities" in qto_names
        assert "Qto_ReinforcingElementBaseQuantities" in qto_names

    def test_column(self, column, tmp_path):
        ex = IfcExporter("TEST")
        out = ex.export([column], str(tmp_path / "c.ifc"))
        f = ifcopenshell.open(out)
        assert len(f.by_type("IfcColumn")) == 1
        # 4 main + 16 ties
        assert len(f.by_type("IfcReinforcingBar")) == 20

    def test_slab_and_footing(self, tmp_path):
        slab = SlabDrawing(slab_id="S1", lx_mm=5000, ly_mm=4000, t_mm=150)
        ftg = FootingDrawing(footing_id="F1", len_mm=2200, wid_mm=2200,
                             t_mm=450)
        ex = IfcExporter("TEST")
        out = ex.export([slab, ftg], str(tmp_path / "sf.ifc"))
        f = ifcopenshell.open(out)
        assert len(f.by_type("IfcSlab")) == 1
        assert len(f.by_type("IfcFooting")) == 1

    def test_zero_validation_issues(self, beam, column, tmp_path):
        ex = IfcExporter("TEST")
        out = ex.export([beam, column], str(tmp_path / "all.ifc"))
        f = ifcopenshell.open(out)
        from ifcopenshell import validate as v
        logger = v.json_logger()
        v.validate(f, logger, express_rules=True)
        assert len(list(getattr(logger, "statements", []))) == 0

    def test_export_drawings_convenience(self, beam, tmp_path):
        out = export_drawings([beam], str(tmp_path / "b.ifc"),
                              project_name="P")
        assert out.endswith(".ifc")
        f = ifcopenshell.open(out)
        assert len(f.by_type("IfcBeam")) == 1
