"""Slab analysis and design to BS 8110:1997.
Port of Oyenuga's SLAB program (pages 144-150 + subs).

Handles 4 slab types:
  1: Cantilever
  2: Simply supported
  3: Continuous (one-way)
  4: Two-way
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from rcd2000.utils import steel_slab, rodia_slab, deflect_beam


@dataclass
class SlabPanelInput:
    panel_id: str
    panel_type: int  # 1-4
    depth: float       # mm
    fcu: float         # N/mm²
    fy: float          # N/mm²
    # Cantilever / Simply supported / Two-way
    udl: float = 0.0   # kN/m
    span: float = 0.0  # m (cantilever, simply supported)
    npl: int = 0
    point_loads: List[Tuple[float, float]] = field(default_factory=list)
    # Continuous slab
    nspan: int = 0
    span_lengths: List[float] = field(default_factory=list)
    span_udls: List[float] = field(default_factory=list)
    span_npls: List[int] = field(default_factory=list)
    span_pls: List[List[Tuple[float, float]]] = field(default_factory=list)
    cant_moments: List[float] = field(default_factory=list)
    cant_loads: List[float] = field(default_factory=list)
    # Two-way slab
    ly: float = 0.0  # m
    case: int = 0    # 1-9
    span_depth_ratio: float = 20.0


@dataclass
class SlabPanelResult:
    panel_id: str
    panel_type: int
    # Moments
    moment_span: float = 0.0     # kN.m/m
    moment_support: float = 0.0  # kN.m/m (for continuous)
    # Steel
    steel_span: float = 0.0      # mm²/m
    steel_support: float = 0.0   # mm²/m
    bar_type: str = "Y"
    bar_dia: float = 10.0
    bar_spacing: float = 200.0
    # Shear
    shear_left: float = 0.0
    shear_right: float = 0.0
    # Deflection
    defl_required: float = 0.0
    defl_ok: bool = True
    # Two-way extras
    moment_long_span: float = 0.0
    steel_long_span: float = 0.0
    moment_long_support: float = 0.0
    steel_long_support: float = 0.0
    torsional_steel: float = 0.0
    eq_udl_short: float = 0.0
    eq_udl_long: float = 0.0
    coeff_short_span: float = 0.0
    coeff_short_support: float = 0.0
    coeff_long_span: float = 0.0
    coeff_long_support: float = 0.0
    # Continuous slab
    span_moments: List[float] = field(default_factory=list)
    span_steels: List[float] = field(default_factory=list)
    support_moments: List[float] = field(default_factory=list)
    support_steels: List[float] = field(default_factory=list)
    support_reactions: List[float] = field(default_factory=list)
    # Effective depth
    depth: float = 0.0


class SlabDesigner:
    """Designs reinforced concrete slabs to BS 8110."""

    def __init__(self, fcu: float = 25.0, fy: float = 460.0):
        self.fcu = fcu
        self.fy = fy
        self.results: List[SlabPanelResult] = []

    def design(self, panels: List[SlabPanelInput]) -> List[SlabPanelResult]:
        self.results = []
        for panel in panels:
            result = self._design_panel(panel)
            self.results.append(result)
        return self.results

    def _design_panel(self, p: SlabPanelInput) -> SlabPanelResult:
        r = SlabPanelResult(panel_id=p.panel_id, panel_type=p.panel_type)
        p.fcu = p.fcu or self.fcu
        p.fy = p.fy or self.fy

        if p.panel_type == 1:
            self._design_cantilever(p, r)
        elif p.panel_type == 2:
            self._design_simply_supported(p, r)
        elif p.panel_type == 3:
            self._design_continuous(p, r)
        elif p.panel_type == 4:
            self._design_twoway(p, r)

        return r

    def _design_cantilever(self, p: SlabPanelInput, r: SlabPanelResult):
        sr = 7.0
        h = p.depth
        while True:
            v = p.udl * p.span
            mc = p.udl * p.span ** 2.0 / 2.0
            for pl, dist in p.point_loads:
                mc += pl * dist
                v += pl
            d = h - 25.0
            ast, heck = steel_slab(mc, d, p.fcu, p.fy)
            if heck == 0:
                h += 25
                continue
            di, fact, heck2 = deflect_beam(
                0, 1, 1000.0, d, ast, ast, p.fy, mc, p.span, sr
            )
            r.moment_span = mc
            r.steel_span = ast
            r.shear_left = v
            r.defl_required = di
            r.defl_ok = heck2 == 1
            bar_type, rd, sv = rodia_slab(ast, p.fy)
            r.bar_type = bar_type
            r.bar_dia = rd
            r.bar_spacing = sv
            r.depth = h
            break

    def _design_simply_supported(self, p: SlabPanelInput, r: SlabPanelResult):
        sr = 20.0
        h = p.depth
        while True:
            v = p.udl * p.span / 2.0
            vb = v
            ms = p.udl * p.span ** 2.0 / 8.0
            for pl, dist in p.point_loads:
                ms += pl * dist * (p.span - dist) / p.span
                v += pl * (p.span - dist) / p.span
                vb += pl * dist / p.span
            d = h - 25.0
            ast, heck = steel_slab(ms, d, p.fcu, p.fy)
            if heck == 0:
                h += 25
                continue
            di, fact, heck2 = deflect_beam(
                0, 2, 1000.0, d, ast, ast, p.fy, ms, p.span, sr
            )
            r.moment_span = ms
            r.steel_span = ast
            r.shear_left = v
            r.shear_right = vb
            r.defl_required = di
            r.defl_ok = heck2 == 1
            bar_type, rd, sv = rodia_slab(ast, p.fy)
            r.bar_type = bar_type
            r.bar_dia = rd
            r.bar_spacing = sv
            r.depth = h
            break

    def _design_continuous(self, p: SlabPanelInput, r: SlabPanelResult):
        sr = 26.0
        ns = p.nspan + 1
        h = p.depth
        while True:
            msc = [0.0] * p.nspan
            mtc = [0.0] * ns
            rct = [0.0] * ns
            for j in range(p.nspan):
                l = p.span_lengths[j]
                w = p.span_udls[j]
                f = w * l
                if j < len(p.span_npls):
                    for k in range(p.span_npls[j]):
                        f += p.span_pls[j][k][0]
                if j == 0:
                    msc[j] = f * l / 9.0
                    mtc[j] = -f * l / 9.0
                elif j == p.nspan - 1:
                    msc[j] = f * l / 9.0
                    mtc[j + 1] = -f * l / 9.0
                else:
                    msc[j] = f * l / 16.0
                    mtc[j] = -f * l / 12.0
                    mtc[j + 1] = -f * l / 12.0
                rct[j] = f / 2.0
            rct[0] += p.cant_loads[0] if len(p.cant_loads) > 0 else 0.0
            rct[ns - 1] += p.cant_loads[1] if len(p.cant_loads) > 1 else 0.0
            mtc[0] += p.cant_moments[0] if len(p.cant_moments) > 0 else 0.0
            mtc[ns - 1] += p.cant_moments[1] if len(p.cant_moments) > 1 else 0.0

            d = h - 25.0
            asc = []
            ok = True
            for j in range(p.nspan):
                ast, heck = steel_slab(msc[j], d, p.fcu, p.fy)
                if heck == 0:
                    h += 25
                    ok = False
                    break
                asc.append(ast)
            if not ok:
                continue
            atc = []
            for j in range(ns):
                ast, heck = steel_slab(abs(mtc[j]), d, p.fcu, p.fy)
                if heck == 0:
                    h += 25
                    ok = False
                    break
                atc.append(ast)
            if not ok:
                continue
            di, fact, heck2 = deflect_beam(
                0, 3, 1000.0, d, asc[0], asc[0], p.fy, msc[0],
                p.span_lengths[0], sr
            )
            r.span_moments = msc
            r.span_steels = asc
            r.support_moments = mtc
            r.support_steels = atc
            r.support_reactions = rct
            r.defl_required = di
            r.defl_ok = heck2 == 1
            r.depth = h
            break

    def _design_twoway(self, p: SlabPanelInput, r: SlabPanelResult):
        lx = min(p.span, p.ly)
        ly = max(p.span, p.ly)
        k = ly / lx
        cn = p.case
        sr = p.span_depth_ratio

        dg = [0.032, 0.037, 0.037, 0.047, 0.000, 0.045, 0.000, 0.057, 0.000]
        dl = [0.024, 0.028, 0.028, 0.035, 0.035, 0.035, 0.043, 0.043, 0.050]

        ds = [
            -0.0384 + 0.0816 * k - 0.0190 * k ** 2.0,
            -0.0254 + 0.0691 * k - 0.0153 * k ** 2.0,
            -0.0471 + 0.0945 * k - 0.0195 * k ** 2.0,
            -0.0321 + 0.0843 * k - 0.0169 * k ** 2.0,
            -0.0003 + 0.0438 * k - 0.0090 * k ** 2.0,
            -0.0726 + 0.1356 * k - 0.0277 * k ** 2.0,
            -0.0314 + 0.0970 * k - 0.0225 * k ** 2.0,
            -0.0628 + 0.1337 * k - 0.0271 * k ** 2.0,
            -0.0612 + 0.1509 * k - 0.0335 * k ** 2.0,
        ]
        dt = [
            -0.0431 + 0.0970 * k - 0.0216 * k ** 2.0,
            -0.0332 + 0.0914 * k - 0.0205 * k ** 2.0,
            -0.0620 + 0.1254 * k - 0.0260 * k ** 2.0,
            -0.0467 + 0.1184 * k - 0.0248 * k ** 2.0,
            -0.0079 + 0.0680 * k - 0.0149 * k ** 2.0,
            0.0,
            -0.0385 + 0.1250 * k - 0.0287 * k ** 2.0,
            0.0,
            0.0,
        ]

        ci = cn - 1
        h = p.depth
        while True:
            d = h - 25.0
            ms = ds[ci] * p.udl * lx ** 2.0
            r.coeff_short_span = ds[ci]
            ast, heck = steel_slab(ms, d, p.fcu, p.fy)
            if heck == 0:
                h += 25
                continue
            r.steel_span = ast
            mt = dt[ci] * p.udl * lx ** 2.0
            r.coeff_short_support = dt[ci]
            ast2, heck2 = steel_slab(mt, d, p.fcu, p.fy)
            if heck2 == 0:
                h += 25
                continue
            r.steel_support = ast2

            d2 = d - 14.0
            ml = dl[ci] * p.udl * lx ** 2.0
            r.coeff_long_span = dl[ci]
            ast3, heck3 = steel_slab(ml, d2, p.fcu, p.fy)
            if heck3 == 0:
                h += 25
                continue
            r.steel_long_span = ast3
            mg = dg[ci] * p.udl * lx ** 2.0
            r.coeff_long_support = dg[ci]
            ast4, heck4 = steel_slab(mg, d2, p.fcu, p.fy)
            if heck4 == 0:
                h += 25
                continue
            r.steel_long_support = ast4

            di, fact, heck5 = deflect_beam(
                0, 4, 1000.0, d, r.steel_span, ast, p.fy, ms, lx, sr
            )
            r.defl_required = di
            r.defl_ok = heck5 == 1
            if heck5 == 0:
                h += 25
                continue

            r.moment_span = ms
            r.moment_support = mt
            r.moment_long_span = ml
            r.moment_long_support = mg
            r.torsional_steel = max(0.75 * r.steel_span, 0.25 * 1000.0 * h / 100.0)
            r.eq_udl_short = (1.0 / 3.0) * p.udl * lx
            r.eq_udl_long = (0.5 * p.udl * lx) * (1.0 - 1.0 / (3.0 * k ** 2.0))
            r.depth = h
            break
