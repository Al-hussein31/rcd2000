"""Base (foundation) design to BS 8110.
Port of Oyenuga's BASE program (pages 315-318).

Handles:
  1: Square isolated footing
  2: Rectangular isolated footing
  3: Combined footing
"""
import math
from dataclasses import dataclass, field
from typing import List, Tuple
from rcd2000.utils import gauss, steel_area, rodia_slab, permlb, perms


@dataclass
class ColumnOnBase:
    load: float        # kN
    dist: float        # m from reference
    shape: int         # 1=rect, 2=circ
    a1: float = 0.0    # mm (rect dim 1)
    a2: float = 0.0    # mm (rect dim 2)
    dia: float = 0.0   # mm (circular)
    dowel_dia: float = 0.0  # mm


@dataclass
class BaseInput:
    base_id: str
    base_type: int     # 1=square, 2=rect, 3=combined
    col_type: int      # 1=rect, 2=circ (for isolated)
    load: float        # kN (for isolated) or total (combined)
    pb: float = 150.0  # kN/m² allowable bearing pressure
    fcu: float = 25.0
    fy: float = 460.0
    a1: float = 0.0    # mm (col dim 1 for rect)
    a2: float = 0.0    # mm (col dim 2 for rect)
    dia: float = 0.0   # mm (col diameter for circ)
    dowel_dia: float = 0.0    # mm
    h: float = 200.0    # mm base thickness
    l1: float = 0.0     # m base length
    l2: float = 0.0     # m base width
    # Combined footing
    n_columns: int = 0
    columns: List[ColumnOnBase] = field(default_factory=list)


@dataclass
class BaseResult:
    base_id: str
    base_type: int
    l1: float          # mm base length
    l2: float          # mm base width
    h: float           # mm base depth
    fnet: float        # kN/m² net upward pressure
    # Reinforcement parallel to L1
    m1: float = 0.0    # kN.m
    as1: float = 0.0   # mm²
    bar_type1: str = "Y"
    rd1: float = 12.0
    sp1: float = 200.0
    # Reinforcement parallel to L2
    m2: float = 0.0    # kN.m
    as2: float = 0.0   # mm²
    bar_type2: str = "Y"
    rd2: float = 12.0
    sp2: float = 200.0
    # Stresses
    shear_stress: float = 0.0
    punching_shear: float = 0.0
    local_bond: float = 0.0
    perm_shear: float = 0.0
    perm_bond: float = 0.0
    # Support/span reinforcement (combined)
    support_moments: List[float] = field(default_factory=list)
    support_steels: List[float] = field(default_factory=list)
    span_moments: List[float] = field(default_factory=list)
    span_steels: List[float] = field(default_factory=list)
    heck: int = 1
    # Dowels (starter bars): BS 8110 practice; the book's base.f77
    # calculation section is not in the reference set, so this is a
    # documented extension, not a book-line-for-line match.
    dowel_area: float = 0.0    # required dowel steel area (mm²)
    dowel_count: int = 0       # required bars of the provided diameter
    dowel_ok: bool = True
    dowel_areas: List[float] = field(default_factory=list)  # per column
    dowel_counts: List[int] = field(default_factory=list)
    dowel_oks: List[bool] = field(default_factory=list)


class BaseDesigner:
    """Designs reinforced concrete foundations to BS 8110."""

    def __init__(self, pb: float = 150.0, fcu: float = 25.0, fy: float = 460.0):
        self.pb = pb
        self.fcu = fcu
        self.fy = fy
        self.results: List[BaseResult] = []

    def design(self, bases: List[BaseInput]) -> List[BaseResult]:
        self.results = []
        for b in bases:
            r = self._design_base(b)
            self.results.append(r)
        return self.results

    @staticmethod
    def _dowel_check(load: float, dowel_dia: float, col_area: float,
                     fy: float):
        """Required starter-bar (dowel) steel for one column:
        max(0.4% of the column section, full factored load transfer at
        0.87·fy). Returns (area_mm2, bar_count, ok).

        Extension note: the book's BASE calculation section is not in the
        repository's f77 set, so this follows BS 8110 practice rather than
        the book line-by-line (see DESIGN_AUDIT.md section 6).
        """
        as_req = max(0.004 * col_area, load * 1000.0 / (0.87 * fy))
        if dowel_dia <= 0:
            return as_req, 0, False
        bar_area = math.pi / 4.0 * dowel_dia ** 2.0
        count = int(math.ceil(as_req / bar_area))
        return as_req, count, count * bar_area >= as_req

    def _design_base(self, b: BaseInput) -> BaseResult:
        pb = b.pb or self.pb
        fcu = b.fcu or self.fcu
        fy = b.fy or self.fy
        h = b.h or 200.0

        if b.base_type != 3:
            return self._design_isolated(b, pb, fcu, fy, h)
        else:
            return self._design_combined(b, pb, fcu, fy, h)

    def _design_isolated(self, b: BaseInput, pb: float,
                         fcu: float, fy: float, h: float) -> BaseResult:
        r = BaseResult(base_id=b.base_id, base_type=b.base_type,
                       l1=0.0, l2=0.0, h=h, fnet=0.0)

        # Calculate required area
        w_total = b.load
        ar = w_total * 1.1 / (1.47 * pb)

        if b.base_type == 1:
            l1 = math.sqrt(ar)
            l1 = (int(l1 / 0.05) + 1) * 0.05 if l1 > 0 else 0.5
            l2 = l1
        else:
            if b.l1 <= 0:
                l1 = math.sqrt(ar)
                l1 = (int(l1 / 0.05) + 1) * 0.05
                l2 = ar / l1
            else:
                l1 = b.l1
                l2 = b.l2 if b.l2 > 0 else ar / l1

        ap = l1 * l2
        if ap < ar:
            l1 = math.sqrt(ar)
            l1 = (int(l1 / 0.05) + 1) * 0.05
            l2 = ar / l1
            ap = l1 * l2

        r.l1 = l1 * 1000.0
        r.l2 = l2 * 1000.0

        # Iterate for depth
        max_iter = 20
        for _ in range(max_iter):
            r.heck = 1  # failed until the full check chain passes
            fnet = (w_total * 1.1) / ap - (h * 24.0 * 1.40) / 1000.0
            r.fnet = fnet

            if fnet <= 0:
                h += 50
                continue

            d = h - 50.0

            # Calculate moments
            if b.col_type == 1:
                ax = b.a1 if b.a1 > 0 else 300.0
                ay = b.a2 if b.a2 > 0 else 300.0
            else:
                ax = b.dia if b.dia > 0 else 300.0
                ay = b.dia if b.dia > 0 else 300.0

            x1 = (l1 * 1000.0 - ax) / 2.0 / 1000.0
            x2 = (l2 * 1000.0 - ay) / 2.0 / 1000.0

            m1 = (fnet * x1 ** 2.0) / 2.0  # kN.m per m width
            ast1, heck1 = steel_area(m1, d, fcu, fy)
            if heck1 == 0:
                h += 50
                continue

            m2 = (fnet * x2 ** 2.0) / 2.0
            ast2, heck2 = steel_area(m2, d, fcu, fy)
            if heck2 == 0:
                h += 50
                continue

            r.m1 = m1
            r.as1 = ast1
            r.m2 = m2
            r.as2 = ast2

            # Shear check (BS 8110 clause 3.11.4.3 - critical at d from column face)
            proj1 = (l1 * 1000.0 - ax) / 2.0  # mm
            proj2 = (l2 * 1000.0 - ay) / 2.0  # mm
            crit_dist1 = max(proj1 - d, 0.0) / 1000.0  # m
            crit_dist2 = max(proj2 - d, 0.0) / 1000.0  # m
            vs1_v = fnet * crit_dist1  # kN/m per m width
            vs2_v = fnet * crit_dist2  # kN/m per m width
            vs_v = max(vs1_v, vs2_v)
            svs = (vs_v * 1000.0) / (1000.0 * d)

            r.shear_stress = svs

            # Concrete shear capacity
            ac = min(100.0 * ast1 / (1000.0 * d), 3.0)
            ac = ac ** (1.0 / 3.0)
            dc_v = min(400.0 / d, 1.0)
            dc_v = dc_v ** 0.25
            vc = 0.632 * ac * dc_v
            r.perm_shear = vc

            if svs > vc:
                h += 50
                continue

            # Punching shear
            if b.col_type == 1:
                pc = 2.0 * (ax / 1000.0 + ay / 1000.0)
            else:
                pc = math.pi * ax / 1000.0

            crit_p = pc + 3.0 * math.pi * h / 1000.0
            if b.col_type == 1:
                acrit = ((ax / 1000.0 + 3.0 * h / 1000.0)
                         * (ay / 1000.0 + 3.0 * h / 1000.0)
                         - (4.0 - math.pi) * (1.5 * h / 1000.0) ** 2.0)
            else:
                acrit = (ax / 1000.0 + 3.0 * h / 1000.0) ** 2.0 * math.pi / 4.0

            vpun = max(fnet * (ap - acrit), 0.0)
            vps = vpun / (crit_p * d) if crit_p > 0 else 0.0
            r.punching_shear = vps

            if vps > vc:
                h += 50
                continue

            # Local bond
            _, rdb1, spb1 = rodia_slab(ast1, fy)
            vbl = (l1 / 2.0) * fnet
            fbs, ubs = permlb(vbl, rdb1, spb1, math.pi, d, fy, fcu)
            r.local_bond = fbs
            r.perm_bond = ubs

            if fbs > ubs:
                h += 50
                continue

            r.h = h
            r.bar_type1, r.rd1, r.sp1 = rodia_slab(ast1, fy)
            r.bar_type2, r.rd2, r.sp2 = rodia_slab(ast2, fy)
            r.heck = 0  # every check in the chain passed at this depth
            break

        # Dowel (starter-bar) check for the single column
        if b.col_type == 1:
            cax = b.a1 if b.a1 > 0 else 300.0
            cay = b.a2 if b.a2 > 0 else 300.0
            col_area = cax * cay
        else:
            cd = b.dia if b.dia > 0 else 300.0
            col_area = math.pi / 4.0 * cd ** 2.0
        (r.dowel_area, r.dowel_count,
         r.dowel_ok) = self._dowel_check(b.load, b.dowel_dia, col_area, fy)
        return r

    def _design_combined(self, b: BaseInput, pb: float,
                         fcu: float, fy: float, h: float) -> BaseResult:
        r = BaseResult(base_id=b.base_id, base_type=b.base_type,
                       l1=0.0, l2=0.0, h=h, fnet=0.0)

        ncols = b.n_columns
        cols = b.columns[:ncols]

        if ncols == 0:
            return r

        # Total load and centroid
        twc = sum(c.load for c in cols)
        mwc = sum(c.load * c.dist for c in cols)
        xbar = mwc / twc if twc > 0 else 0.0

        # Required area
        ar = twc * 1.1 / (1.47 * pb)

        # Determine base dimensions
        if b.l2 <= 0:
            b.l2 = 2.0  # assume 2m width
        l1_needed = ar / b.l2

        # Center L1 on the load resultant (xbar) so the soil pressure is
        # uniform. Column distances are in metres from a common reference;
        # the footing must cover the outermost columns on both sides of the
        # resultant while satisfying the area requirement.
        x_min = min(c.dist for c in cols)
        x_max = max(c.dist for c in cols)
        l1 = max(l1_needed, 2.0 * (xbar - x_min), 2.0 * (x_max - xbar))
        l1 = (int(l1 / 0.05) + 1) * 0.05
        l2 = b.l2

        r.l1 = l1 * 1000.0
        r.l2 = l2 * 1000.0

        ap = l1 * l2
        fnet = (twc * 1.1) / ap - (h * 24.0 * 1.40) / 1000.0
        r.fnet = fnet

        if fnet <= 0:
            h += 100

        d = h - 50.0
        nm = ncols - 1
        ns = ncols
        nn = nm - 1

        # Span lengths and free moments
        span = []
        for k in range(nm):
            span.append(cols[k + 1].dist - cols[k].dist)

        fm = [sp ** 2.0 * fnet / 8.0 for sp in span]
        shl = [fnet * sp / 2.0 for sp in span]
        shr = [fnet * sp / 2.0 for sp in span]

        # Overhang projections from the resultant-centred footing edges to
        # the outermost column centres (dist in metres - no /1000 unit bug)
        ohl = l1 / 2.0 - (xbar - x_min)  # overhang left (m)
        ohr = l1 / 2.0 - (x_max - xbar)  # overhang right (m)
        ml = (ohl ** 2.0) * fnet / 2.0
        mr = (ohr ** 2.0) * fnet / 2.0

        # Support moments using 3-moment equation
        mt = [0.0] * ns
        mt[0] = ml
        mt[ns - 1] = mr

        if nm >= 2:
            mat = [[0.0] * nn for _ in range(nn)]
            rhs = [0.0] * nn

            if nn == 1:
                # Exactly 3 columns / 2 spans: one interior support.
                # 2(L0+L1)·M1 = (fnet/4)(L0^3+L1^3) - ml·L0 - mr·L1
                mat[0][0] = 2.0 * (span[0] + span[1])
                rhs[0] = (fnet / 4.0) * (span[0] ** 3.0 + span[1] ** 3.0)
                rhs[0] -= ml * span[0]
                rhs[0] -= mr * span[1]
            else:
                mat[0][0] = 2.0 * (span[0] + span[1])
                mat[0][1] = span[1]
                rhs[0] = (fnet / 4.0) * (span[0] ** 3.0 + span[1] ** 3.0)
                rhs[0] -= ml * span[0]

                mat[nn - 1][nn - 2] = span[nm - 2]
                mat[nn - 1][nn - 1] = 2.0 * (span[nm - 2] + span[nm - 1])
                rhs[nn - 1] = (fnet / 4.0) * (span[nm - 2] ** 3.0 + span[nm - 1] ** 3.0)
                rhs[nn - 1] -= mr * span[nm - 1]

                if nn > 2:
                    for k in range(1, nn - 1):
                        mat[k][k - 1] = span[k]
                        mat[k][k] = 2.0 * (span[k] + span[k + 1])
                        mat[k][k + 1] = span[k + 1]
                        rhs[k] = (fnet / 4.0) * (span[k] ** 3.0 + span[k + 1] ** 3.0)

            xmt = gauss(mat, rhs, nn, nn)
            for i in range(nn):
                mt[i + 1] = xmt[i]
        elif nm == 1:
            mt[0] = ml
            mt[ns - 1] = mr

        # Span moments
        for k in range(nm):
            ms = fm[k] - (mt[k] + mt[k + 1]) * 0.5
            of = (mt[k] - mt[k + 1]) / span[k] if span[k] > 0 else 0.0
            shl[k] += of
            shr[k] -= of

            ast, heck = steel_area(abs(ms), d, fcu, fy)
            r.span_moments.append(ms)
            r.span_steels.append(ast)

        # Support moments
        for k in range(ns):
            ast, heck = steel_area(abs(mt[k]), d, fcu, fy)
            r.support_moments.append(mt[k])
            r.support_steels.append(ast)

        # Transverse reinforcement
        d_trans = h - 70.0
        x1 = (l2 * 1000.0 - 300.0) / 2.0 / 1000.0
        m_trans = (fnet * x1 ** 2.0) / 2.0
        ast_trans, heckt = steel_area(m_trans, d_trans, fcu, fy)
        r.m1 = m_trans
        r.as1 = ast_trans

        # Distribution steel
        if fy <= 250:
            tk = 0.25
        else:
            tk = 0.15
        ant = tk * 1000.0 * d / 100.0
        r.as2 = ant

        r.bar_type1, r.rd1, r.sp1 = rodia_slab(ast_trans, fy)
        r.bar_type2, r.rd2, r.sp2 = rodia_slab(ant, fy)

        r.h = h

        # Per-column dowel (starter-bar) checks
        for c in cols:
            if c.shape == 1:
                ca = ((c.a1 if c.a1 > 0 else 300.0)
                      * (c.a2 if c.a2 > 0 else 300.0))
            else:
                ca = math.pi / 4.0 * (c.dia if c.dia > 0 else 300.0) ** 2.0
            da, dc, dok = self._dowel_check(c.load, c.dowel_dia, ca, fy)
            r.dowel_areas.append(da)
            r.dowel_counts.append(dc)
            r.dowel_oks.append(dok)
        r.heck = 0  # combined design is single-pass and completes
        return r
