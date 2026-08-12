"""Adapters: RCD2000 calculation results -> DrawingModel (Batch 8).

Bridges the engine's numeric results (Ast required, bar dia/spacing,
member geometry) into the DrawingModel dataclasses the DXF exporter
consumes. Includes a small detailing helper that turns a required steel
area + supplied bar schedule into RebarBar groups.

Units: engine results are mm / kN / kN.m. All drawing lengths are mm.
"""
from __future__ import annotations

import math
from typing import List, Optional

from .drawing_models import (
    DrawingScale,
    ShapeCode,
    RebarBar,
    RebarZone,
    BeamDrawing,
    ColumnDrawing,
    SlabDrawing,
    FootingDrawing,
    BbsRow,
    bbs_row_from_bar,
)
from .beam import BeamInput, BeamResult
from .column import ColumnInput, ColumnResult
from .slab import SlabPanelInput, SlabPanelResult
from .base import BaseInput, BaseResult
from .stair import StairInput, StairResult


# ── Detailing helpers ────────────────────────────────────────────────

def bars_for_area(
    area_mm2: float,
    length_mm: float,
    dia: float,
    spacing: float,
    min_bars: int = 2,
    layer: str = "REBAR_MAIN",
    shape: ShapeCode = ShapeCode.STRAIGHT,
) -> List[RebarBar]:
    """Convert Ast (mm²) + bar schedule into RebarBar groups.

    Determines how many bars of ``dia`` fit in ``length_mm`` at ``spacing``
    (rounded up, at least ``min_bars``) and returns a single RebarBar whose
    count carries the group.
    """
    if area_mm2 <= 0:
        return []
    bar_area = math.pi * (dia / 2.0) ** 2
    count = max(min_bars, math.ceil(area_mm2 / bar_area))
    # also respect max bars that fit at spacing across the width
    by_spacing = max(1, math.floor(length_mm / spacing) + 1)
    count = max(count, by_spacing)
    return [
        RebarBar(
            diameter_mm=int(round(dia)),
            count=count,
            length_mm=length_mm,
            shape=shape,
        )
    ]


def zone(
    bars: List[RebarBar],
    start_mm: float,
    end_mm: float,
    cover_mm: float,
    layer: str = "REBAR_MAIN",
) -> RebarZone:
    return RebarZone(
        bars=bars,
        start_mm=start_mm,
        end_mm=end_mm,
        offset_from_face_mm=cover_mm,
        layer=layer,
    )


def _bbs_rows_for_zones(zones: List[RebarZone], prefix: str) -> List[BbsRow]:
    rows: List[BbsRow] = []
    for i, z in enumerate(zones):
        for j, bar in enumerate(z.bars):
            mark = bar.mark or f"{prefix}{i + 1}"
            rows.append(bbs_row_from_bar(mark, bar))
    return rows


# ── Beam ─────────────────────────────────────────────────────────────

def beam_to_drawing(
    inp: BeamInput,
    result: BeamResult,
    scale: DrawingScale = DrawingScale.S1_50,
) -> BeamDrawing:
    """Map one beam span (first span) + result to a BeamDrawing.

    Uses the first span's results for the single-span detail sheet.
    """
    span = inp.member_lengths[0] if inp.member_lengths else 0.0
    span_mm = span * 1000.0
    span_res = result.spans[0] if result.spans else None
    cover = 40.0

    bottom_bars = []
    top_bars = []
    stirrups = []
    if span_res is not None:
        bottom_bars = bars_for_area(
            span_res.steel_bot, span_mm, span_res.bar_dia_bot,
            span_res.bar_spacing_bot, layer="REBAR_MAIN",
        )
        top_bars = bars_for_area(
            span_res.steel_top, span_mm, span_res.bar_dia_top,
            span_res.bar_spacing_top, layer="REBAR_DIST",
        )
        # stirrups: one U-bar per spacing interval across the span
        sv = max(span_res.sv_left or 150.0, 150.0)
        n_stir = max(1, int(span_mm / sv))
        stirrups = [
            RebarBar(10, n_stir, span_mm, ShapeCode.U_BAR, "S1")
        ]

    return BeamDrawing(
        beam_id=inp.beam_id,
        span_mm=span_mm,
        b_mm=int(inp.b),
        D_mm=int(inp.h),
        d_mm=int(inp.h - cover - 10),
        cover_mm=cover,
        top_zones=[zone(top_bars, 0, span_mm, cover, "REBAR_DIST")] if top_bars else [],
        bottom_zones=[zone(bottom_bars, 0, span_mm, cover, "REBAR_MAIN")] if bottom_bars else [],
        stirrup_zones=[zone(stirrups, 0, span_mm, cover, "REBAR_STIRRUP")] if stirrups else [],
        mu_knm=span_res.moment if span_res else 0.0,
        vu_kn=span_res.shear_left if span_res else 0.0,
        ast_provided_mm2=span_res.steel_bot if span_res else 0.0,
        scale=scale,
    )


# ── Column ───────────────────────────────────────────────────────────

def column_to_drawing(
    inp: ColumnInput,
    result: ColumnResult,
    scale: DrawingScale = DrawingScale.S1_50,
) -> ColumnDrawing:
    """Map a column input + result to a ColumnDrawing.

    Main bars are sized from the required steel area; ties at a code-
    reasonable spacing (smallest of 12*bar_dia / 300 mm).
    """
    b = int(inp.bx or 300)
    D = int(inp.by or inp.depth or 300)
    height_mm = inp.length * 1000.0
    cover = 40.0

    # main bars: try Ø20, fall back to Ø16 if area very small
    area = result.steel_required
    if area <= 0:
        area = 0.8 / 100.0 * b * D  # nominal 0.8% minimum
    dia = 20 if area > 4 * math.pi * 10 ** 2 else 16
    n_main = max(4, math.ceil(area / (math.pi * (dia / 2.0) ** 2)))
    main_bars = [
        RebarBar(dia, n_main, height_mm, ShapeCode.STRAIGHT, "C1")
    ]

    # ties: Ø10 at 12*16=192 -> use 200 mm, or tighter for small dims
    tie_dia = 10
    tie_spacing = min(12 * dia, 300)
    n_ties = max(1, int(height_mm / tie_spacing))
    tie_len = 2 * (b + D) - 8 * cover + 2 * 6 * tie_dia
    ties = [
        RebarBar(tie_dia, n_ties, tie_len, ShapeCode.U_BAR, "CT1")
    ]

    return ColumnDrawing(
        col_id=inp.column_id,
        b_mm=b,
        D_mm=D,
        height_mm=height_mm,
        main_bars=main_bars,
        ties=ties,
        axial_kn=inp.load,
        moment_knm=max(inp.moment, inp.moment_x, inp.moment_y),
        scale=scale,
    )


# ── Slab ─────────────────────────────────────────────────────────────

def slab_to_drawing(
    inp: SlabPanelInput,
    result: SlabPanelResult,
    scale: DrawingScale = DrawingScale.S1_50,
) -> SlabDrawing:
    """Map a slab panel to a SlabDrawing.

    One-way / cantilever: short-direction bars along the main span.
    Two-way: adds long-direction bars from the long-span results.
    """
    span_mm = inp.span * 1000.0
    ly_mm = inp.ly * 1000.0 if inp.ly else span_mm
    t = int(inp.depth)

    bot_short = bars_for_area(
        result.steel_span, ly_mm, result.bar_dia, result.bar_spacing,
        layer="REBAR_MAIN",
    )
    bot_long = []
    if inp.panel_type == 4 and result.steel_long_span:
        bot_long = bars_for_area(
            result.steel_long_span, span_mm, result.bar_dia,
            result.bar_spacing, layer="REBAR_MAIN",
        )

    panel_type = {1: "cantilever", 2: "one_way", 3: "two_way",
                  4: "two_way"}.get(inp.panel_type, "one_way")

    return SlabDrawing(
        slab_id=inp.panel_id,
        panel_type=panel_type,
        lx_mm=span_mm,
        ly_mm=ly_mm,
        t_mm=t,
        bot_short=[zone(bot_short, 0, ly_mm, 30)] if bot_short else [],
        bot_long=[zone(bot_long, 0, span_mm, 30)] if bot_long else [],
        scale=scale,
    )


# ── Footing ──────────────────────────────────────────────────────────

def footing_to_drawing(
    inp: BaseInput,
    result: BaseResult,
    scale: DrawingScale = DrawingScale.S1_50,
) -> FootingDrawing:
    """Map an isolated footing to a FootingDrawing."""
    l = result.l1 if result.l1 else inp.l1 * 1000.0
    w = result.l2 if result.l2 else inp.l2 * 1000.0
    t = int(result.h if result.h else inp.h)

    x_bars = bars_for_area(result.as1, l, result.rd1, result.sp1,
                           layer="REBAR_MAIN")
    y_bars = bars_for_area(result.as1, w, result.rd1, result.sp1,
                           layer="REBAR_DIST")

    col_b = int(inp.a1 or 300)
    col_D = int(inp.a2 or inp.dia or 300)

    return FootingDrawing(
        footing_id=inp.base_id,
        len_mm=l,
        wid_mm=w,
        t_mm=t,
        x_bars=x_bars,
        y_bars=y_bars,
        col_b_mm=col_b,
        col_D_mm=col_D,
        scale=scale,
    )


# ── Convenience: full export of one element from JSON-like inputs ────

def export_beam_dxf(inp: BeamInput, output_path: str,
                    scale: DrawingScale = DrawingScale.S1_50) -> None:
    """One-shot: design a beam and write a full DXF sheet."""
    from .dxf_export import DxfExporter
    from .drawing_models import Sheet

    result = BeamDesigner().design([inp])[0]
    drawing = beam_to_drawing(inp, result, scale)

    ex = DxfExporter()
    msp = ex.modelspace
    ex.draw_beam_plan(msp, drawing)
    ex.draw_beam_elevation(msp, drawing, (0, 900))
    ex.draw_beam_section(msp, drawing, (7000, 0))
    rows = _bbs_rows_for_zones(drawing.bottom_zones + drawing.top_zones, "B") \
        + _bbs_rows_for_zones(drawing.stirrup_zones, "S")
    ex.draw_bbs(msp, rows, origin=(7500, 700))

    sheet = Sheet(
        sheet_no="S-01",
        title=f"BEAM {inp.beam_id} - PLAN & DETAILS",
        scale_note=f"SCALE 1:{scale.value}",
    )
    layout = ex.new_sheet(sheet)
    ex.add_viewport(layout, center=(380, 320), size=(700, 400),
                    view_center=(120, 30), view_height=160)
    ex.save(output_path)


from .beam import BeamDesigner  # noqa: E402  (import at bottom to avoid cycle)
