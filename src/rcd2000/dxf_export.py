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
        for scale_name, scale_val in (
            ("STRUCT_20", 20),
            ("STRUCT_25", 25),
            ("STRUCT_50", 50),
            ("STRUCT_100", 100),
        ):
            ds = self.doc.dimstyles.new(scale_name)
            ds.dxf.dimscale = scale_val
            ds.dxf.dimasz = 2.5          # arrow size (paper mm)
            ds.dxf.dimtxt = 2.5          # text height (paper mm)
            ds.dxf.dimgap = 1.0
            ds.dxf.dimtofl = 1           # force line between ext lines
            ds.dxf.dimclrd = colors.CYAN
            ds.dxf.dimclrt = colors.WHITE
            ds.dxf.dimclre = colors.WHITE
            ds.dxf.dimlwd = 10
            ds.dxf.dimlwe = 10

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
