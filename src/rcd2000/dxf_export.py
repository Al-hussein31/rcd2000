"""Core DXF exporter for RCD2000 CAD output.

Layer 2 of the CAD pipeline: a stateless ezdxf canvas with the
structural layer standard, dimension/text styles, standard blocks and
drawing primitives. All draw methods take model-space coordinates in
**mm** and apply ``scale`` internally (``mm / scale``).

Design rules:
- every content entity lands on a defined layer (never layer "0")
- dimension entities use a structural dimstyle so AutoCAD shows real mm
- the exporter is pure Python (no Qt) and headless-testable
"""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple, Union

import ezdxf
from ezdxf import colors
from ezdxf.document import Drawing
from ezdxf.layouts import Layout, Modelspace, Paperspace
from ezdxf.math import Vec2

from .drawing_models import DrawingScale

Point = Union[Tuple[float, float], Vec2, Sequence[float]]


class DxfExporter:
    """Reusable DXF canvas for structural drawings."""

    # Layer standard (BS 8666 / ISO 13567-inspired)
    LAYERS = {
        "CONCRETE_OUTLINE": {"color": colors.WHITE, "lineweight": 30},
        "CONCRETE_HATCH": {"color": 8, "lineweight": 0},
        "REBAR_MAIN": {"color": colors.RED, "lineweight": 20},
        "REBAR_STIRRUP": {"color": colors.YELLOW, "lineweight": 15},
        "REBAR_DIST": {"color": colors.GREEN, "lineweight": 15},
        "DIMENSIONS": {"color": colors.CYAN, "lineweight": 9},
        "TEXT": {"color": colors.WHITE, "lineweight": 9},
        "GRID": {"color": 8, "lineweight": 5},
        "CENTERLINE": {
            "color": colors.MAGENTA,
            "lineweight": 5,
            "linetype": "CENTER",
        },
        "SECTION_CUT": {
            "color": colors.WHITE,
            "lineweight": 25,
            "linetype": "DASHED",
        },
        "VIEWPORT": {"color": 8, "lineweight": 0},
    }

    # Base text height in model units at 1:1 (scaled by dimscale for paper)
    TEXT_H_TITLE = 5.0
    TEXT_H_BODY = 4.0
    TEXT_H_NOTE = 3.5

    def __init__(self, dxfversion: str = "R2010") -> None:
        self.doc: Drawing = ezdxf.new(dxfversion, setup=True)
        self._setup_layers()
        self._setup_dimstyles()
        self._setup_textstyles()
        self._create_blocks()

    # ── setup ────────────────────────────────────────────────────────

    def _setup_layers(self) -> None:
        for name, attrs in self.LAYERS.items():
            kwargs = dict(attrs)
            lt = kwargs.pop("linetype", None)
            layer = self.doc.layers.add(name, **kwargs)
            if lt:
                layer.dxf.linetype = lt

    def _setup_dimstyles(self) -> None:
        # Detail-sheet convention: geometry is drawn at plot scale
        # (mm / scale). DIMLFAC multiplies the measured distance back to
        # real mm, and dimscale=1 keeps dimension text at paper size.
        for scale_name, scale_val in (
            ("STRUCT_20", 20),
            ("STRUCT_25", 25),
            ("STRUCT_50", 50),
            ("STRUCT_100", 100),
        ):
            ds = self.doc.dimstyles.new(scale_name)
            ds.dxf.dimscale = 1
            ds.dxf.dimlfac = scale_val    # linear factor -> real mm
            ds.dxf.dimasz = 2.5            # arrow size (paper mm)
            ds.dxf.dimtxt = 2.5            # text height (paper mm)
            ds.dxf.dimgap = 1.0
            ds.dxf.dimtofl = 1             # force line between ext lines
            ds.dxf.dimclrd = colors.CYAN
            ds.dxf.dimclrt = colors.WHITE
            ds.dxf.dimclre = colors.WHITE
            ds.dxf.dimlwd = 9
            ds.dxf.dimlwe = 9

    def _setup_textstyles(self) -> None:
        for name in ("OPEN_SANS", "OPEN_SANS_BOLD"):
            st = self.doc.styles.new(name)
            st.dxf.font = "OpenSansCondensed-Light.ttf"
            if name.endswith("BOLD"):
                st.dxf.font = "OpenSansCondensed-Bold.ttf"

    def _create_blocks(self) -> None:
        # Bar mark: circle + mark attribute
        blk = self.doc.blocks.new("BAR_MARK", base_point=(0, 0))
        blk.add_circle((0, 0), 4.0, dxfattribs={"layer": "REBAR_MAIN"})
        blk.add_attdef(
            "MARK",
            (0, -1.2),
            dxfattribs={
                "height": 2.0,
                "layer": "TEXT",
                "style": "OPEN_SANS",
                "halign": 1,
            },
        )

        # North arrow
        blk = self.doc.blocks.new("NORTH_ARROW", base_point=(0, 0))
        blk.add_lwpolyline(
            [(0, 0), (5, 0), (0, 12), (-5, 0), (0, 0)],
            close=True,
            dxfattribs={"layer": "TEXT"},
        )

        # Section cut marker (arrow with label attribute)
        blk = self.doc.blocks.new("SECTION_CUT", base_point=(0, 0))
        blk.add_line((0, 0), (6, 0), dxfattribs={"layer": "SECTION_CUT"})
        blk.add_line((6, 0), (4, 2), dxfattribs={"layer": "SECTION_CUT"})
        blk.add_line((6, 0), (4, -2), dxfattribs={"layer": "SECTION_CUT"})
        blk.add_attdef(
            "LABEL",
            (3, -5),
            dxfattribs={
                "height": 2.5,
                "layer": "TEXT",
                "style": "OPEN_SANS",
                "halign": 1,
            },
        )

    # ── document helpers ─────────────────────────────────────────────

    @property
    def modelspace(self) -> Modelspace:
        return self.doc.modelspace()

    def new_paperspace(self, name: str) -> Paperspace:
        return self.doc.layouts.new(name)

    def save(self, path: str) -> None:
        self.doc.saveas(path)

    def audit(self) -> int:
        """Return number of audit errors (0 = clean)."""
        auditor = self.doc.audit()
        return len(auditor.errors)

    # ── primitives (all take mm, apply scale via model() ) ────────────

    @staticmethod
    def _m(pt: Point, scale: DrawingScale) -> Vec2:
        """Scale mm coords into model units."""
        s = scale.value
        return Vec2(float(pt[0]) / s, float(pt[1]) / s)

    def rect(
        self,
        layout: Layout,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        scale: DrawingScale = DrawingScale.S1_50,
        layer: str = "CONCRETE_OUTLINE",
    ) -> None:
        s = scale.value
        layout.add_lwpolyline(
            [
                (x0 / s, y0 / s),
                (x1 / s, y0 / s),
                (x1 / s, y1 / s),
                (x0 / s, y1 / s),
            ],
            close=True,
            dxfattribs={"layer": layer},
        )

    def hatch_rect(
        self,
        layout: Layout,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        scale: DrawingScale = DrawingScale.S1_50,
        pattern: str = "ANSI31",
        layer: str = "CONCRETE_HATCH",
    ) -> None:
        s = scale.value
        h = layout.add_hatch(
            dxfattribs={"layer": layer, "color": 8}
        )
        h.set_pattern_fill(pattern, scale=0.5 * scale.value)
        h.paths.add_polyline_path(
            [
                (x0 / s, y0 / s),
                (x1 / s, y0 / s),
                (x1 / s, y1 / s),
                (x0 / s, y1 / s),
            ],
            is_closed=True,
        )

    def line(
        self,
        layout: Layout,
        p0: Point,
        p1: Point,
        scale: DrawingScale = DrawingScale.S1_50,
        layer: str = "CONCRETE_OUTLINE",
    ) -> None:
        layout.add_line(
            self._m(p0, scale),
            self._m(p1, scale),
            dxfattribs={"layer": layer},
        )

    def polyline(
        self,
        layout: Layout,
        points: Iterable[Point],
        scale: DrawingScale = DrawingScale.S1_50,
        layer: str = "CONCRETE_OUTLINE",
        close: bool = False,
    ) -> None:
        s = scale.value
        layout.add_lwpolyline(
            [(float(p[0]) / s, float(p[1]) / s) for p in points],
            close=close,
            dxfattribs={"layer": layer},
        )

    def circle(
        self,
        layout: Layout,
        center: Point,
        r_mm: float,
        scale: DrawingScale = DrawingScale.S1_50,
        layer: str = "REBAR_MAIN",
    ) -> None:
        layout.add_circle(
            self._m(center, scale),
            r_mm / scale.value,
            dxfattribs={"layer": layer},
        )

    def text(
        self,
        layout: Layout,
        s: str,
        pos: Point,
        height_mm: float = 4.0,
        scale: DrawingScale = DrawingScale.S1_50,
        layer: str = "TEXT",
        align: int = 1,  # 0=left,1=center,2=right
        style: str = "OPEN_SANS",
    ) -> None:
        from ezdxf.enums import TextEntityAlignment

        al = {
            0: TextEntityAlignment.LEFT,
            1: TextEntityAlignment.CENTER,
            2: TextEntityAlignment.RIGHT,
        }[align]
        t = layout.add_text(
            s,
            dxfattribs={
                "layer": layer,
                "style": style,
                "height": height_mm / scale.value,
            },
        )
        t.set_placement(self._m(pos, scale), align=al)

    def dim_linear(
        self,
        layout: Layout,
        p0: Point,
        p1: Point,
        offset: float,
        scale: DrawingScale = DrawingScale.S1_50,
        layer: str = "DIMENSIONS",
    ) -> None:
        """Linear dimension between two model points, offset perpendicular."""
        style = f"STRUCT_{scale.value}"
        override = layout.add_linear_dim(
            base=self._m((0, 0), scale),  # base is auto from points below
            p1=self._m(p0, scale),
            p2=self._m(p1, scale),
            location=self._m((0, offset), scale),
            dimstyle=style,
            dxfattribs={"layer": layer},
        )
        override.render()

    def bar_line(
        self,
        layout: Layout,
        p0: Point,
        p1: Point,
        dia_mm: float,
        scale: DrawingScale = DrawingScale.S1_50,
        layer: str = "REBAR_MAIN",
    ) -> None:
        """Draw a reinforcement bar as a line with end circles (scheme view)."""
        a = self._m(p0, scale)
        b = self._m(p1, scale)
        r = (dia_mm / 2.0) / scale.value
        layout.add_line(a, b, dxfattribs={"layer": layer})
        layout.add_circle(a, max(r, 0.15), dxfattribs={"layer": layer})
        layout.add_circle(b, max(r, 0.15), dxfattribs={"layer": layer})

    def blockref(
        self,
        layout: Layout,
        name: str,
        pos: Point,
        scale: DrawingScale = DrawingScale.S1_50,
        layer: str = "TEXT",
        attributes: Optional[dict] = None,
        rotation: float = 0.0,
    ) -> None:
        ref = layout.add_blockref(
            name,
            self._m(pos, scale),
            dxfattribs={"layer": layer, "rotation": rotation},
        )
        if attributes:
            for k, v in attributes.items():
                ref.add_attrib(k, str(v), dxfattribs={"layer": "TEXT"})

    def bar_mark(
        self,
        layout: Layout,
        pos: Point,
        mark: str,
        scale: DrawingScale = DrawingScale.S1_50,
    ) -> None:
        self.blockref(layout, "BAR_MARK", pos, scale, attributes={"MARK": mark})


# ── Beam drawing (Batch 3) ──────────────────────────────────────────

    def draw_beam_plan(
        self,
        layout: Layout,
        beam: "BeamDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Plan view: outline, top/bottom bars, stirrup zone, dims, marks."""
        from .drawing_models import BeamDrawing as _B  # noqa: F401 (typing)

        ox, oy = float(origin[0]), float(origin[1])
        s = beam.scale
        w = beam.span_mm
        b = float(beam.b_mm)

        # Concrete outline + hatch
        self.rect(layout, ox, oy, ox + w, oy + b, scale=s)
        self.hatch_rect(layout, ox, oy, ox + w, oy + b, scale=s)

        # Centerline
        self.line(layout, (ox, oy + b / 2), (ox + w, oy + b / 2),
                  scale=s, layer="CENTERLINE")

        # Top bars (near top edge) and bottom bars (near bottom edge)
        for zone in beam.top_zones:
            self._draw_plan_zone(
                layout, zone, ox, oy, b, "top", scale=s)
        for zone in beam.bottom_zones:
            self._draw_plan_zone(
                layout, zone, ox, oy, b, "bottom", scale=s)

        # Stirrup zone markers (short ticks perpendicular to axis)
        for zone in beam.stirrup_zones:
            for bar in zone.bars:
                n = max(bar.count, 1)
                step = zone.length_mm / n if n > 1 else 0
                for i in range(n):
                    x = zone.start_mm + i * step
                    self.line(
                        layout,
                        (ox + x, oy + 5),
                        (ox + x, oy + b - 5),
                        scale=s, layer="REBAR_STIRRUP",
                    )

        if beam.show_dimensions:
            self.dim_linear(layout, (ox, oy), (ox + w, oy), -150, scale=s)
            self.dim_linear(layout, (ox, oy), (ox, oy + b), 150, scale=s)

    def _draw_plan_zone(self, layout, zone, ox, oy, b, side, scale):
        """Draw one zone's bars as parallel lines in plan."""
        x0 = ox + zone.start_mm
        x1 = ox + zone.end_mm
        if side == "top":
            y = oy + b - zone.offset_from_face_mm
        else:
            y = oy + zone.offset_from_face_mm
        for bar in zone.bars:
            for i in range(max(bar.count, 1)):
                dy = i * (b / max(bar.count + 1, 2)) if side == "bottom" else -i * (b / max(bar.count + 1, 2))
                yy = y + dy if side == "bottom" else y - dy
                self.line(layout, (x0, yy), (x1, yy), scale=scale,
                          layer=zone.layer)

    def draw_beam_elevation(
        self,
        layout: Layout,
        beam: "BeamDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Longitudinal elevation: curtailment zones, stirrups, supports."""
        ox, oy = float(origin[0]), float(origin[1])
        s = beam.scale
        w = beam.span_mm
        D = float(beam.D_mm)

        self.rect(layout, ox, oy, ox + w, oy + D, scale=s)
        self.hatch_rect(layout, ox, oy, ox + w, oy + D, scale=s)

        # Top bars at cover below top face, bottom bars at cover above bottom
        for zone in beam.top_zones:
            y = oy + D - zone.offset_from_face_mm
            self._draw_elev_zone(layout, zone, ox, y, scale=s)
        for zone in beam.bottom_zones:
            y = oy + zone.offset_from_face_mm
            self._draw_elev_zone(layout, zone, ox, y, scale=s)

        # Stirrups: vertical ticks at spacing across full depth
        for zone in beam.stirrup_zones:
            for bar in zone.bars:
                n = max(bar.count, 1)
                step = zone.length_mm / n if n > 1 else 0
                for i in range(n + 1):
                    x = ox + zone.start_mm + i * step
                    self.line(layout, (x, oy + 4), (x, oy + D - 4),
                              scale=s, layer="REBAR_STIRRUP")

        # Support marks at both ends
        self.line(layout, (ox, oy - 30), (ox, oy + D + 30), scale=s,
                  layer="GRID")
        self.line(layout, (ox + w, oy - 30), (ox + w, oy + D + 30),
                  scale=s, layer="GRID")

        if beam.show_dimensions:
            self.dim_linear(layout, (ox, oy), (ox + w, oy), -150, scale=s)
            self.dim_linear(layout, (ox, oy), (ox, oy + D), 150, scale=s)

    def _draw_elev_zone(self, layout, zone, ox, y, scale):
        x0 = ox + zone.start_mm
        x1 = ox + zone.end_mm
        for bar in zone.bars:
            self.line(layout, (x0, y), (x1, y), scale=scale, layer=zone.layer)

    def draw_beam_section(
        self,
        layout: Layout,
        beam: "BeamDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Cross-section: outline, bar circles, stirrup outline, dims."""
        ox, oy = float(origin[0]), float(origin[1])
        s = beam.scale
        b = float(beam.b_mm)
        D = float(beam.D_mm)

        self.rect(layout, ox, oy, ox + b, oy + D, scale=s)

        # Stirrup outline at cover
        c = float(beam.cover_mm)
        self.polyline(
            layout,
            [(ox + c, oy + c), (ox + b - c, oy + c),
             (ox + b - c, oy + D - c), (ox + c, oy + D - c)],
            scale=s, layer="REBAR_STIRRUP", close=True,
        )

        # Main bars as circles at cover offset from each face
        def _bar_row(y_face, count, layer):
            r = 6.0
            xs = [ox + b / 2]
            if count >= 2:
                xs = [ox + c + r, ox + b - c - r]
            if count >= 3:
                xs = [ox + c + r, ox + b / 2, ox + b - c - r]
            for x in xs[:count]:
                self.circle(layout, (x, y_face), r, scale=s, layer=layer)

        for zone in beam.top_zones:
            for bar in zone.bars:
                _bar_row(oy + D - beam.cover_mm, bar.count, zone.layer)
        for zone in beam.bottom_zones:
            for bar in zone.bars:
                _bar_row(oy + beam.cover_mm, bar.count, zone.layer)

        if beam.show_dimensions:
            self.dim_linear(layout, (ox, oy), (ox + b, oy), -150, scale=s)
            self.dim_linear(layout, (ox, oy), (ox, oy + D), 150, scale=s)

    def draw_bbs(
        self,
        layout: Layout,
        rows: List["BbsRow"],
        origin: Point = (0.0, 0.0),
        scale: DrawingScale = DrawingScale.S1_50,
    ) -> None:
        """Bar Bending Schedule as a simple line table."""
        from .drawing_models import BbsRow  # noqa: F401

        ox, oy = float(origin[0]), float(origin[1])
        headers = ["MARK", "SHAPE", "Ø", "NO.", "LENGTH (mm)", "NOTE"]
        col_w = [150, 150, 80, 80, 250, 250]
        row_h = 60
        x = ox
        # Header
        for h, cw in zip(headers, col_w):
            self.text(layout, h, (x + cw / 2, oy + row_h / 2), height_mm=30,
                      scale=scale, align=1)
            x += cw
        # Rows
        for i, row in enumerate(rows):
            yy = oy - (i + 1) * row_h
            vals = [
                row.mark, row.shape.value, str(row.dia_mm), str(row.n),
                f"{row.length_mm:.0f}", row.bend_info,
            ]
            x = ox
            for v, cw in zip(vals, col_w):
                self.text(layout, v, (x + cw / 2, yy + row_h / 2),
                          height_mm=25, scale=scale, align=1)
                x += cw
        # Border lines
        total_w = sum(col_w)
        total_h = row_h * (len(rows) + 1)
        self.rect(layout, ox, oy - total_h, ox + total_w, oy, scale=scale,
                  layer="TEXT")
        for i in range(1, len(headers)):
            x = ox + sum(col_w[:i])
            self.line(layout, (x, oy), (x, oy - total_h), scale=scale,
                      layer="TEXT")
        for i in range(1, len(rows) + 1):
            yy = oy - i * row_h
            self.line(layout, (ox, yy), (ox + total_w, yy), scale=scale,
                      layer="TEXT")


# ── Column drawing (Batch 4) ────────────────────────────────────────

    def draw_column_plan(
        self,
        layout: Layout,
        col: "ColumnDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Column cross-section: outline, main-bar circles, tie outline."""
        ox, oy = float(origin[0]), float(origin[1])
        s = col.scale
        b = float(col.b_mm)
        D = float(col.D_mm)

        self.rect(layout, ox, oy, ox + b, oy + D, scale=s)

        # Centerlines
        self.line(layout, (ox, oy + D / 2), (ox + b, oy + D / 2),
                  scale=s, layer="CENTERLINE")
        self.line(layout, (ox + b / 2, oy), (ox + b / 2, oy + D),
                  scale=s, layer="CENTERLINE")

        # Tie outline (closed loop inside cover)
        c = 40.0
        self.polyline(
            layout,
            [(ox + c, oy + c), (ox + b - c, oy + c),
             (ox + b - c, oy + D - c), (ox + c, oy + D - c)],
            scale=s, layer="REBAR_STIRRUP", close=True,
        )

        # Main bars as circles arranged per count
        for bar in col.main_bars:
            self._draw_col_bars(
                layout, ox, oy, b, D, bar.count,
                self._col_layer(bar), s,
            )

        self.dim_linear(layout, (ox, oy), (ox + b, oy), -150, scale=s)
        self.dim_linear(layout, (ox, oy), (ox, oy + D), 150, scale=s)

    def _draw_col_bars(self, layout, ox, oy, b, D, count, layer, s):
        c = 40.0
        r = 6.0
        # arrange bars: corners first, then mid-face bars
        positions = []
        if count >= 4:
            positions = [
                (ox + c + r, oy + c + r),
                (ox + b - c - r, oy + c + r),
                (ox + b - c - r, oy + D - c - r),
                (ox + c + r, oy + D - c - r),
            ]
        if count >= 6:
            positions.extend([
                (ox + b / 2, oy + c + r),
                (ox + b / 2, oy + D - c - r),
            ])
        if count >= 8:
            positions.extend([
                (ox + c + r, oy + D / 2),
                (ox + b - c - r, oy + D / 2),
            ])
        # fallback: spread evenly along a ring if unusual counts
        if len(positions) < count:
            import math
            positions = [
                (ox + b / 2 + (b / 2 - c - r) * math.cos(2 * math.pi * i / count),
                 oy + D / 2 + (D / 2 - c - r) * math.sin(2 * math.pi * i / count))
                for i in range(count)
            ]
        for x, y in positions[:count]:
            self.circle(layout, (x, y), r, scale=s, layer=layer)

    def draw_column_elevation(
        self,
        layout: Layout,
        col: "ColumnDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Column elevation: vertical main bars, tie spacing, lapping."""
        ox, oy = float(origin[0]), float(origin[1])
        s = col.scale
        b = float(col.b_mm)
        H = col.height_mm

        self.rect(layout, ox, oy, ox + b, oy + H, scale=s)

        # Main bars: vertical lines full height
        main_count = sum(bar.count for bar in col.main_bars) or 4
        xs = [ox + b / 2]
        if main_count >= 4:
            xs = [ox + 25.0, ox + b - 25.0]
        for x in xs:
            for layer_ in ("REBAR_MAIN",):
                self.line(layout, (x, oy + 15), (x, oy + H - 15),
                          scale=s, layer="REBAR_MAIN")

        # Ties at spacing
        total_ties = sum(bar.count for bar in col.ties) or 1
        for i in range(1, total_ties + 1):
            y = oy + i * H / (total_ties + 1)
            self.line(layout, (ox + 5, y), (ox + b - 5, y),
                      scale=s, layer="REBAR_STIRRUP")

        self.dim_linear(layout, (ox, oy), (ox, oy + H), -150, scale=s)

    def _col_layer(self, bar) -> str:
        return getattr(bar, "layer", "REBAR_MAIN") or "REBAR_MAIN"


# ── Slab drawing (Batch 5) ──────────────────────────────────────────

    def draw_slab_plan(
        self,
        layout: Layout,
        slab: "SlabDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Slab reinforcement plan: panel outline + mesh bars per direction."""
        ox, oy = float(origin[0]), float(origin[1])
        s = slab.scale
        lx = slab.lx_mm
        ly = slab.ly_mm

        self.rect(layout, ox, oy, ox + lx, oy + ly, scale=s)
        self.hatch_rect(layout, ox, oy, ox + lx, oy + ly, scale=s)

        # Short direction (horizontal bars), top + bottom
        for zone, layer in ((slab.bot_short, "REBAR_MAIN"),
                            (slab.top_short, "REBAR_DIST")):
            for z in zone:
                self._draw_mesh_h(layout, z, ox, oy, ly, layer, s)
        # Long direction (vertical bars)
        for zone, layer in ((slab.bot_long, "REBAR_MAIN"),
                            (slab.top_long, "REBAR_DIST")):
            for z in zone:
                self._draw_mesh_v(layout, z, ox, oy, lx, layer, s)

        self.dim_linear(layout, (ox, oy), (ox + lx, oy), -150, scale=s)
        self.dim_linear(layout, (ox, oy), (ox, oy + ly), -150, scale=s)

    def _draw_mesh_h(self, layout, zone, ox, oy, ly, layer, s):
        # horizontal bars: vertical extent across the panel
        y0 = oy + zone.start_mm
        y1 = oy + zone.end_mm
        for bar in zone.bars:
            n = max(bar.count, 1)
            for i in range(n):
                x = ox + 15 + i * (zone.length_mm or 1) / n * 0 + 15
                # distribute across panel width for scheme clarity
                self.line(layout, (x, y0), (x, y1), scale=s, layer=layer)

    def _draw_mesh_v(self, layout, zone, ox, oy, lx, layer, s):
        x0 = ox + zone.start_mm
        x1 = ox + zone.end_mm
        for bar in zone.bars:
            n = max(bar.count, 1)
            for i in range(n):
                y = oy + 15 + i * 20
                self.line(layout, (x0, y), (x1, y), scale=s, layer=layer)

    def draw_slab_section(
        self,
        layout: Layout,
        slab: "SlabDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Slab cross-section: thickness, top/bottom mesh, cover."""
        ox, oy = float(origin[0]), float(origin[1])
        s = slab.scale
        lx = slab.lx_mm
        t = float(slab.t_mm)

        self.rect(layout, ox, oy, ox + lx, oy + t, scale=s)

        # bottom mesh line
        for zone in slab.bot_short + slab.bot_long:
            self.line(layout, (ox + 20, oy + 30), (ox + lx - 20, oy + 30),
                      scale=s, layer="REBAR_MAIN")
        # top mesh line
        for zone in slab.top_short + slab.top_long:
            self.line(layout, (ox + 20, oy + t - 30),
                      (ox + lx - 20, oy + t - 30),
                      scale=s, layer="REBAR_DIST")

        self.dim_linear(layout, (ox, oy), (ox, oy + t), 150, scale=s)


# ── Footing drawing (Batch 6) ───────────────────────────────────────

    def draw_footing_plan(
        self,
        layout: Layout,
        ftg: "FootingDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Footing plan: outline, column (dashed), x/y mesh."""
        ox, oy = float(origin[0]), float(origin[1])
        s = ftg.scale
        L = ftg.len_mm
        W = ftg.wid_mm

        self.rect(layout, ox, oy, ox + L, oy + W, scale=s)

        # Column outline (dashed) centered
        cb, cd = ftg.col_b_mm or 300, ftg.col_D_mm or 450
        cx, cy = ox + L / 2, oy + W / 2
        self.rect(layout, cx - cb / 2, cy - cd / 2, cx + cb / 2, cy + cd / 2,
                  scale=s, layer="SECTION_CUT")

        # x bars (horizontal): spread across length
        for bar in ftg.x_bars:
            n = max(bar.count, 1)
            for i in range(n):
                y = oy + 30 + i * (W - 60) / max(n, 2)
                self.line(layout, (ox + 20, y), (ox + L - 20, y),
                          scale=s, layer="REBAR_MAIN")
        # y bars (vertical)
        for bar in ftg.y_bars:
            n = max(bar.count, 1)
            for i in range(n):
                x = ox + 30 + i * (L - 60) / max(n, 2)
                self.line(layout, (x, oy + 20), (x, oy + W - 20),
                          scale=s, layer="REBAR_DIST")

        self.dim_linear(layout, (ox, oy), (ox + L, oy), -150, scale=s)
        self.dim_linear(layout, (ox, oy), (ox, oy + W), -150, scale=s)

    def draw_footing_section(
        self,
        layout: Layout,
        ftg: "FootingDrawing",
        origin: Point = (0.0, 0.0),
    ) -> None:
        """Footing section: thickness, top/bottom mesh, dowels."""
        ox, oy = float(origin[0]), float(origin[1])
        s = ftg.scale
        L = ftg.len_mm
        t = float(ftg.t_mm)

        self.rect(layout, ox, oy, ox + L, oy + t, scale=s)

        # bottom mesh
        for bar in ftg.x_bars + ftg.y_bars:
            self.line(layout, (ox + 25, oy + 50), (ox + L - 25, oy + 50),
                      scale=s, layer="REBAR_MAIN")
        # top mesh
        for bar in ftg.x_bars + ftg.y_bars:
            self.line(layout, (ox + 25, oy + t - 50),
                      (ox + L - 25, oy + t - 50),
                      scale=s, layer="REBAR_DIST")

        # column dowels: short vertical lines rising from footing
        if ftg.col_b_mm:
            cb = ftg.col_b_mm
            cx = ox + L / 2
            for dx in (-cb / 4, 0, cb / 4):
                self.line(layout, (cx + dx, oy + t), (cx + dx, oy + t + 100),
                          scale=s, layer="REBAR_MAIN")

        self.dim_linear(layout, (ox, oy), (ox, oy + t), 150, scale=s)
