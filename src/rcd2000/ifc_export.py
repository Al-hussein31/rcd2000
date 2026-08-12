"""IFC4 export for RCD2000 (Batch 12).

Maps the CAD DrawingModels (beam/column/slab/footing + rebar) into an
IFC4 file via IfcOpenShell 0.8.x, for BIM interoperability
(Revit/Tekla/Allplan/BlenderBIM).

Design decisions (per buildingSMART IFC4):
- Rebar is attached to its concrete member with **IfcRelNests**
  (Element Nesting concept) — nested children are placed relative to
  the host member, which is exactly how bars sit inside a beam.
- Bar shape geometry uses **IfcSweptDiskSolid** with an
  IfcIndexedPolyCurve directrix, shared across occurrences via a cached
  **IfcReinforcingBarType** + IfcRepresentationMap (mapped geometry).
- All linear dimensions are converted mm -> m at the module boundary.
- Design results go in Pset_ConcreteElementGeneral + a custom
  Pset_RCDDesignResults; quantities in Qto_*BaseQuantities and
  Qto_ReinforcingElementBaseQuantities.

Pure Python + IfcOpenShell. Optional dependency:
``pip install "rcd2000[ifc]"`` (ifcopenshell).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

import ifcopenshell
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.aggregate
import ifcopenshell.api.spatial
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.unit
import ifcopenshell.api.context
import ifcopenshell.api.nest
import ifcopenshell.api.type
from ifcopenshell.util.shape_builder import ShapeBuilder

from .drawing_models import (
    RebarBar,
    RebarZone,
    BeamDrawing,
    ColumnDrawing,
    SlabDrawing,
    FootingDrawing,
)

# mm -> m conversion at the module boundary
M = 0.001

# IFC class per drawing type
_MEMBER_CLASS = {
    "beam": "IfcBeam",
    "column": "IfcColumn",
    "slab": "IfcSlab",
    "footing": "IfcFooting",
}

# IFC reinforcing role per layer (BS8666/EC2 convention)
_ROLE = {
    "REBAR_MAIN": "MAIN",
    "REBAR_DIST": "TRANSVERSE",
    "REBAR_STIRRUP": "SHEAR",
}

_CONCRETE_GRADE = "C30/37"
_STEEL_GRADE = "B500B"


class IfcExporter:
    """Builds an IFC4 file from RCD2000 drawing models."""

    def __init__(self, project_name: str = "RCD2000 Project",
                 schema: str = "IFC4") -> None:
        self.ifc = ifcopenshell.api.project.create_file(version=schema)
        self.project_name = project_name
        self._storey = None
        self._body_ctx = None
        self._builder: Optional[ShapeBuilder] = None
        self._bar_type_cache: Dict[Tuple[int, str, str], object] = {}
        self._material_concrete = None
        self._material_steel = None
        self._create_structure()

    # ── project skeleton ─────────────────────────────────────────────

    def _create_structure(self) -> None:
        ifc = self.ifc
        project = ifcopenshell.api.root.create_entity(
            ifc, "IfcProject", name=self.project_name
        )
        site = ifcopenshell.api.root.create_entity(ifc, "IfcSite", name="Site")
        building = ifcopenshell.api.root.create_entity(
            ifc, "IfcBuilding", name="Building"
        )
        self._storey = ifcopenshell.api.root.create_entity(
            ifc, "IfcBuildingStorey", name="Level 1"
        )
        ifcopenshell.api.aggregate.assign_object(
            ifc, relating_object=project, products=[site]
        )
        ifcopenshell.api.aggregate.assign_object(
            ifc, relating_object=site, products=[building]
        )
        ifcopenshell.api.aggregate.assign_object(
            ifc, relating_object=building, products=[self._storey]
        )

        # explicit SI units (length = metre)
        u = ifcopenshell.api.unit.add_si_unit(
            ifc, unit_type="LENGTHUNIT", prefix=None
        )
        ifcopenshell.api.unit.assign_unit(ifc, [u])

        # representation contexts
        model_ctx = ifcopenshell.api.context.add_context(
            ifc, context_type="Model"
        )
        self._body_ctx = ifcopenshell.api.context.add_context(
            ifc,
            context_type="Model",
            context_identifier="Body",
            target_view="MODEL_VIEW",
            parent=model_ctx,
        )
        self._builder = ShapeBuilder(ifc)
        self._material_concrete = ifcopenshell.api.material.add_material(
            ifc, name=_CONCRETE_GRADE, category="concrete"
        )
        self._material_steel = ifcopenshell.api.material.add_material(
            ifc, name=_STEEL_GRADE, category="steel"
        )

    # ── public API ───────────────────────────────────────────────────

    def export(self, drawings: Iterable, output_path: str) -> str:
        """Export drawing models to an IFC file. Returns the path."""
        for d in drawings:
            self.add_element(d)
        self.ifc.write(output_path)
        return output_path

    def add_element(self, drawing) -> None:
        """Add one beam/column/slab/footing drawing (with rebar)."""
        if isinstance(drawing, BeamDrawing):
            self._add_member("beam", drawing, drawing.b_mm, drawing.D_mm,
                             drawing.span_mm, 0.0)
        elif isinstance(drawing, ColumnDrawing):
            self._add_member("column", drawing, drawing.b_mm, drawing.D_mm,
                             drawing.height_mm, 0.0)
        elif isinstance(drawing, SlabDrawing):
            self._add_slab(drawing)
        elif isinstance(drawing, FootingDrawing):
            self._add_footing(drawing)
        else:
            raise TypeError(f"unsupported drawing type: {type(drawing)}")

    # ── members ──────────────────────────────────────────────────────

    def _add_member(self, kind: str, drawing, b_mm: float, d_mm: float,
                    length_mm: float, z_base: float = 0.0) -> object:
        ifc = self.ifc
        member = ifcopenshell.api.root.create_entity(
            ifc, _MEMBER_CLASS[kind], name=getattr(drawing, "beam_id",
            getattr(drawing, "col_id", getattr(drawing, "footing_id", "EL")))
        )
        # place at origin of storey (identity matrix, SI metres)
        ifcopenshell.api.geometry.edit_object_placement(
            ifc, product=member, matrix=np.eye(4), is_si=True
        )
        profile = self._builder.profile(
            self._builder.rectangle((b_mm * M, d_mm * M))
        )
        body = ifcopenshell.api.geometry.add_profile_representation(
            ifc,
            context=self._body_ctx,
            profile=profile,
            depth=length_mm * M,
        )
        ifcopenshell.api.geometry.assign_representation(
            ifc, product=member, representation=body
        )
        ifcopenshell.api.spatial.assign_container(
            ifc, products=[member], relating_structure=self._storey
        )
        ifcopenshell.api.material.assign_material(
            ifc, products=[member], material=self._material_concrete
        )

        # reinforcement
        bars = []
        if isinstance(drawing, BeamDrawing):
            for zone in (drawing.top_zones + drawing.bottom_zones):
                bars.extend(self._add_zone_bars(member, drawing, zone, 0.0))
            for zone in drawing.stirrup_zones:
                bars.extend(self._add_zone_bars(member, drawing, zone, 0.0))
        elif isinstance(drawing, ColumnDrawing):
            # main bars around the perimeter + ties
            for bar in drawing.main_bars:
                bars.extend(self._add_bar_occurrences(member, drawing,
                                                      bar, 0.0))
            for tie in drawing.ties:
                bars.extend(self._add_bar_occurrences(member, drawing,
                                                      tie, 0.0))

        if bars:
            ifcopenshell.api.nest.assign_object(
                ifc, relating_object=member, related_objects=bars
            )

        # design psets
        self._add_member_psets(member, drawing)
        self._add_member_qtos(member, kind, drawing, b_mm, d_mm, length_mm)
        return member

    def _add_zone_bars(self, member, drawing, zone: RebarZone,
                       z_base: float) -> List[object]:
        out = []
        for bar in zone.bars:
            out.extend(self._add_bar_occurrences(member, drawing, bar,
                                                 z_base))
        return out

    def _add_bar_occurrences(self, member, drawing, bar: RebarBar,
                             z_base: float) -> List[object]:
        """Create one IfcReinforcingBar per bar occurrence."""
        ifc = self.ifc
        role = _ROLE.get(getattr(bar, "layer", "REBAR_MAIN"), "MAIN")
        bar_type = self._get_bar_type(bar.diameter_mm, role)
        length_m = bar.length_mm * M

        occurrences = []
        # simple layout: distribute along member for scheme clarity
        n = max(bar.count, 1)
        for i in range(n):
            b = ifcopenshell.api.root.create_entity(
                ifc, "IfcReinforcingBar",
                name=f"{bar.diameter_mm}-{i + 1}",
            )
            b.Tag = str(bar.mark or bar.diameter_mm)
            ifcopenshell.api.geometry.edit_object_placement(
                ifc, product=b, matrix=np.eye(4), is_si=True
            )
            # relative position inside the member (local frame, metres)
            x = 0.05 + 0.05 * (i % 3)
            y = 0.05 + 0.05 * ((i // 3) % 3)
            b.ObjectPlacement.RelativePlacement.Location.Coordinates = (
                x, y, z_base + 0.05
            )
            mapped = ifc.create_entity(
                "IfcMappedItem",
                MappingSource=bar_type.RepresentationMaps[0],
                MappingTarget=ifc.create_entity(
                    "IfcCartesianTransformationOperator3D"
                ),
            )
            ifcopenshell.api.geometry.assign_representation(
                ifc,
                product=b,
                representation=ifc.create_entity(
                    "IfcShapeRepresentation",
                    ContextOfItems=self._body_ctx,
                    RepresentationIdentifier="Body",
                    RepresentationType="MappedRepresentation",
                    Items=[mapped],
                ),
            )
            ifcopenshell.api.type.assign_type(
                ifc, related_objects=[b], relating_type=bar_type
            )
            occurrences.append(b)

        # rebar quantity on first occurrence (Count/Length/Weight)
        if occurrences:
            qto = ifcopenshell.api.pset.add_qto(
                ifc, product=occurrences[0],
                name="Qto_ReinforcingElementBaseQuantities",
            )
            weight_kg = bar.count * length_m * 7850.0 * \
                np.pi * (bar.diameter_mm * M / 2.0) ** 2
            ifcopenshell.api.pset.edit_qto(
                ifc, qto=qto,
                properties={
                    "Count": n,
                    "Length": round(length_m, 4),
                    "Weight": round(weight_kg, 2),
                },
            )
        return occurrences

    def _get_bar_type(self, dia_mm: int, role: str) -> object:
        key = (dia_mm, role, _STEEL_GRADE)
        if key in self._bar_type_cache:
            return self._bar_type_cache[key]

        ifc = self.ifc
        bar_type = ifcopenshell.api.root.create_entity(
            ifc, "IfcReinforcingBarType",
            predefined_type=role,
            name=f"T{dia_mm}-{_STEEL_GRADE}",
        )
        origin = ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity(
                "IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)
            ),
        )
        # straight bar directrix along local X, length in metres
        pts = ifc.create_entity(
            "IfcCartesianPointList3D",
            CoordList=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        )
        directrix = ifc.create_entity("IfcIndexedPolyCurve", Points=pts)
        swept = ifc.create_entity(
            "IfcSweptDiskSolid",
            Directrix=directrix,
            Radius=(dia_mm * M) / 2.0,
        )
        map_items = ifc.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=self._body_ctx,
            RepresentationIdentifier="Body",
            RepresentationType="AdvancedSweptSolid",
            Items=[swept],
        )
        repr_map = ifc.create_entity(
            "IfcRepresentationMap",
            MappingOrigin=origin,
            MappedRepresentation=map_items,
        )
        bar_type.RepresentationMaps = [repr_map]
        ifcopenshell.api.material.assign_material(
            ifc, products=[bar_type], material=self._material_steel
        )
        self._bar_type_cache[key] = bar_type
        return bar_type

    # ── slabs & footings ─────────────────────────────────────────────

    def _add_slab(self, slab: SlabDrawing) -> object:
        ifc = self.ifc
        member = ifcopenshell.api.root.create_entity(
            ifc, "IfcSlab", name=slab.slab_id
        )
        ifcopenshell.api.geometry.edit_object_placement(
            ifc, product=member, matrix=np.eye(4), is_si=True
        )
        profile = self._builder.profile(
            self._builder.rectangle((slab.lx_mm * M, slab.ly_mm * M))
        )
        body = ifcopenshell.api.geometry.add_profile_representation(
            ifc, context=self._body_ctx, profile=profile,
            depth=slab.t_mm * M,
        )
        ifcopenshell.api.geometry.assign_representation(
            ifc, product=member, representation=body
        )
        ifcopenshell.api.spatial.assign_container(
            ifc, products=[member], relating_structure=self._storey
        )
        ifcopenshell.api.material.assign_material(
            ifc, products=[member], material=self._material_concrete
        )
        self._add_member_psets(member, slab)
        qto = ifcopenshell.api.pset.add_qto(
            ifc, product=member, name="Qto_SlabBaseQuantities"
        )
        ifcopenshell.api.pset.edit_qto(
            ifc, qto=qto,
            properties={
                "Depth": slab.t_mm * M,
                "NetArea": (slab.lx_mm * M) * (slab.ly_mm * M),
            },
        )
        return member

    def _add_footing(self, ftg: FootingDrawing) -> object:
        ifc = self.ifc
        member = ifcopenshell.api.root.create_entity(
            ifc, "IfcFooting", name=ftg.footing_id
        )
        ifcopenshell.api.geometry.edit_object_placement(
            ifc, product=member, matrix=np.eye(4), is_si=True
        )
        profile = self._builder.profile(
            self._builder.rectangle((ftg.len_mm * M, ftg.wid_mm * M))
        )
        body = ifcopenshell.api.geometry.add_profile_representation(
            ifc, context=self._body_ctx, profile=profile,
            depth=ftg.t_mm * M,
        )
        ifcopenshell.api.geometry.assign_representation(
            ifc, product=member, representation=body
        )
        ifcopenshell.api.spatial.assign_container(
            ifc, products=[member], relating_structure=self._storey
        )
        ifcopenshell.api.material.assign_material(
            ifc, products=[member], material=self._material_concrete
        )
        self._add_member_psets(member, ftg)
        qto = ifcopenshell.api.pset.add_qto(
            ifc, product=member, name="Qto_FootingBaseQuantities"
        )
        ifcopenshell.api.pset.edit_qto(
            ifc, qto=qto,
            properties={
                "Depth": ftg.t_mm * M,
                "FootingArea": (ftg.len_mm * M) * (ftg.wid_mm * M),
            },
        )
        return member

    # ── psets / qtos ─────────────────────────────────────────────────

    def _add_member_psets(self, member, drawing) -> None:
        ifc = self.ifc
        # standard concrete design pset
        pset = ifcopenshell.api.pset.add_pset(
            ifc, product=member, name="Pset_ConcreteElementGeneral"
        )
        cover_m = getattr(drawing, "cover_mm", 40) * M
        props = {
            "StrengthClass": _CONCRETE_GRADE,
            "ConcreteCover": round(cover_m, 4),
            "ConcreteCoverAtMainBars": round(cover_m, 4),
            "ReinforcementStrengthClass": _STEEL_GRADE,
        }
        ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)

        # custom design-results pset (never uses Qto_/Pset_ standard names)
        results = {}
        if isinstance(drawing, BeamDrawing):
            results = {
                "M_Ed_kNm": round(drawing.mu_knm, 2),
                "V_Ed_kN": round(drawing.vu_kn, 2),
                "Ast_provided_mm2": round(drawing.ast_provided_mm2, 1),
            }
        elif isinstance(drawing, ColumnDrawing):
            results = {
                "N_Ed_kN": round(drawing.axial_kn, 2),
                "M_Ed_kNm": round(drawing.moment_knm, 2),
            }
        if results:
            dp = ifcopenshell.api.pset.add_pset(
                ifc, product=member, name="Pset_RCDDesignResults"
            )
            ifcopenshell.api.pset.edit_pset(ifc, pset=dp, properties=results)

    def _add_member_qtos(self, member, kind: str, drawing, b_mm: float,
                         d_mm: float, length_mm: float) -> None:
        ifc = self.ifc
        name = {
            "beam": "Qto_BeamBaseQuantities",
            "column": "Qto_ColumnBaseQuantities",
        }.get(kind)
        if not name:
            return
        qto = ifcopenshell.api.pset.add_qto(ifc, product=member, name=name)
        cross_area = (b_mm * M) * (d_mm * M)
        ifcopenshell.api.pset.edit_qto(
            ifc, qto=qto,
            properties={
                "NominalLength": round(length_mm * M, 4),
                "GrossCrossSectionArea": round(cross_area, 5),
                "NetVolume": round(cross_area * (length_mm * M), 5),
            },
        )

    # ── validation helpers ───────────────────────────────────────────

    def validate(self, express_rules: bool = True) -> List[dict]:
        """Run ifcopenshell validation; return list of issue dicts."""
        from ifcopenshell import validate as v

        logger = v.json_logger()
        v.validate(self.ifc, logger, express_rules=express_rules)
        return list(getattr(logger, "statements", []))


def export_drawings(
    drawings: Iterable,
    output_path: str,
    project_name: str = "RCD2000 Project",
) -> str:
    """Convenience: export a list of drawing models to an IFC file."""
    ex = IfcExporter(project_name=project_name)
    return ex.export(drawings, output_path)
