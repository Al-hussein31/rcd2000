"""Drawing model dataclasses for CAD export.

Layer 1 of the CAD pipeline: a unit-clear, Qt-free representation of
everything the DXF writer draws. Each model maps 1:1 to a structural
element designed by the RCD2000 engine (beam, column, slab, footing).

All linear dimensions are in **mm**. Scale is applied only at draw time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


class DrawingScale(Enum):
    """Standard structural drawing scales (1:20 .. 1:100)."""

    S1_20 = 20
    S1_25 = 25
    S1_50 = 50
    S1_100 = 100


class ShapeCode(str, Enum):
    """BS 8666 / ISO 3766 bending shape codes.

    Common shapes used in reinforcement detailing. Extend as needed.
    """

    STRAIGHT = "00"
    STR_END_HOOK = "11"      # straight with one end hook
    BOTH_HOOKS = "12"
    L_BEND = "21"
    U_BAR = "24"
    T_BAR = "34"


@dataclass
class RebarBar:
    """A single reinforcement bar type (unique diameter + count + length)."""

    diameter_mm: int
    count: int
    length_mm: float
    shape: ShapeCode = ShapeCode.STRAIGHT
    mark: str = ""

    @property
    def area_mm2(self) -> float:
        """Total cross-sectional area of the bar group (mm²)."""
        import math

        return self.count * math.pi * (self.diameter_mm / 2.0) ** 2


@dataclass
class RebarZone:
    """A contiguous run of identical bars along a member.

    ``start_mm``/``end_mm`` are measured along the member axis from the
    left end. ``offset_from_face_mm`` is the concrete cover to the bar
    centreline (perpendicular to the face the bars run along).
    """

    bars: List[RebarBar] = field(default_factory=list)
    start_mm: float = 0.0
    end_mm: float = 0.0
    offset_from_face_mm: float = 0.0
    layer: str = "REBAR_MAIN"

    @property
    def length_mm(self) -> float:
        return max(0.0, self.end_mm - self.start_mm)


@dataclass
class BeamDrawing:
    """Complete drawing data for one beam (plan + elevation + sections)."""

    beam_id: str = "B1"
    span_mm: float = 0.0
    b_mm: int = 0
    D_mm: int = 0
    d_mm: int = 0
    cover_mm: int = 30
    top_zones: List[RebarZone] = field(default_factory=list)
    bottom_zones: List[RebarZone] = field(default_factory=list)
    stirrup_zones: List[RebarZone] = field(default_factory=list)
    mu_knm: float = 0.0
    vu_kn: float = 0.0
    ast_provided_mm2: float = 0.0
    scale: DrawingScale = DrawingScale.S1_50
    show_dimensions: bool = True
    show_bbs: bool = True


@dataclass
class ColumnDrawing:
    """Complete drawing data for one column (plan + elevation)."""

    col_id: str = "C1"
    b_mm: int = 0
    D_mm: int = 0
    height_mm: float = 0.0
    main_bars: List[RebarBar] = field(default_factory=list)
    ties: List[RebarBar] = field(default_factory=list)
    axial_kn: float = 0.0
    moment_knm: float = 0.0
    scale: DrawingScale = DrawingScale.S1_50


@dataclass
class SlabDrawing:
    """Complete drawing data for one slab panel (plan + section)."""

    slab_id: str = "S1"
    panel_type: str = "one_way"  # one_way | two_way | cantilever
    lx_mm: float = 0.0
    ly_mm: float = 0.0
    t_mm: int = 0
    top_short: List[RebarZone] = field(default_factory=list)
    top_long: List[RebarZone] = field(default_factory=list)
    bot_short: List[RebarZone] = field(default_factory=list)
    bot_long: List[RebarZone] = field(default_factory=list)
    scale: DrawingScale = DrawingScale.S1_50


@dataclass
class FootingDrawing:
    """Complete drawing data for one isolated footing (plan + section)."""

    footing_id: str = "F1"
    len_mm: float = 0.0
    wid_mm: float = 0.0
    t_mm: int = 0
    x_bars: List[RebarBar] = field(default_factory=list)
    y_bars: List[RebarBar] = field(default_factory=list)
    col_b_mm: int = 0
    col_D_mm: int = 0
    scale: DrawingScale = DrawingScale.S1_50


@dataclass
class StairDrawing:
    """Complete drawing data for one straight-flight stair (plan + section)."""

    stair_id: str = "ST1"
    span_mm: float = 0.0
    tread_mm: float = 0.0
    rise_mm: float = 0.0
    waist_mm: int = 0
    width_mm: float = 0.0
    main_bars: List[RebarBar] = field(default_factory=list)
    distribution_bars: List[RebarBar] = field(default_factory=list)
    design_moment_knm: float = 0.0
    steel_required_mm2: float = 0.0
    scale: DrawingScale = DrawingScale.S1_50


@dataclass
class BbsRow:
    """One row of a Bar Bending Schedule."""

    mark: str = ""
    shape: ShapeCode = ShapeCode.STRAIGHT
    dia_mm: int = 0
    n: int = 0
    length_mm: float = 0.0
    bend_info: str = ""


@dataclass
class Sheet:
    """One paper-space sheet (title block + views)."""

    sheet_no: str = "S-01"
    title: str = "GENERAL"
    project: str = ""
    rev: str = "A"
    engineer: str = ""
    date: str = ""
    paper: Tuple[float, float] = (841.0, 594.0)  # A1 landscape
    scale_note: str = "SCALE 1:50"


def bbs_row_from_bar(mark: str, bar: RebarBar) -> BbsRow:
    """Create a BBS row from a RebarBar (helper used by adapters/tests)."""
    return BbsRow(
        mark=mark or bar.mark,
        shape=bar.shape,
        dia_mm=bar.diameter_mm,
        n=bar.count,
        length_mm=bar.length_mm,
    )
