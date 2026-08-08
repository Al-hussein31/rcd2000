"""Beam analysis and design to BS 8110:1997.
Port of Oyenuga's BEAM + BMADE program (pages 207-215).

Clapeyron three-moment method for continuous beams.
Full reinforcement design including shear links.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from rcd2000.utils import (
    gauss, steel_beam, rodia_beam, deflect_beam, shear_links
)


def paf(x: float, w: float, d: float) -> float:
    """Point load factor for Clapeyron's three-moment equation."""
    return w * x * (d * d - x * x) / d


@dataclass
class BeamInput:
    beam_id: str
    n_supports: int
    n_members: int
    b: float       # mm - beam width
    bf: float      # mm - flange width
    h: float       # mm - overall depth
    hf: float      # mm - flange depth
    fcu: float     # N/mm²
    fy: float      # N/mm²
    fyv: float     # N/mm² - stirrup
    member_lengths: List[float] = field(default_factory=list)
    member_udl: List[float] = field(default_factory=list)
    member_wt: List[float] = field(default_factory=list)
    member_wb: List[float] = field(default_factory=list)
    member_ab: List[float] = field(default_factory=list)
    member_npl: List[int] = field(default_factory=list)
    member_pl: List[List[Tuple[float, float]]] = field(default_factory=list)
    support_grid: List[str] = field(default_factory=list)
    ty1: int = 1
    ty2: int = 1
    cant_load_1: float = 0.0
    cant_moment_1: float = 0.0
    cant_load_2: float = 0.0
    cant_moment_2: float = 0.0


@dataclass
class BeamSpanResult:
    span_id: str
    length: float
    udl: float
    moment: float          # kN.m - max span moment
    steel_bot: float       # mm²
    steel_top: float       # mm²
    bar_type: str = "Y"
    bar_dia_bot: float = 12.0
    bar_spacing_bot: float = 100.0
    bar_dia_top: float = 12.0
    bar_spacing_top: float = 100.0
    shear_left: float = 0.0
    shear_right: float = 0.0
    sv_left: float = 0.0
    sv_right: float = 0.0
    defl_req_depth: float = 0.0
    defl_ok: bool = True


@dataclass
class BeamSupportResult:
    support_id: str
    reaction: float
    moment: float          # kN.m
    steel_top: float       # mm²
    steel_bot: float       # mm²
    bar_type: str = "Y"
    bar_dia_top: float = 12.0
    bar_spacing_top: float = 100.0
    bar_dia_bot: float = 12.0
    bar_spacing_bot: float = 100.0


@dataclass
class BeamResult:
    beam_id: str
    spans: List[BeamSpanResult] = field(default_factory=list)
    supports: List[BeamSupportResult] = field(default_factory=list)
    heck: int = 1


class BeamDesigner:
    """Designs reinforced concrete beams to BS 8110."""

    def __init__(self, fcu: float = 25.0, fy: float = 460.0,
                 fyv: float = 250.0):
        self.fcu = fcu
        self.fy = fy
        self.fyv = fyv
        self.results: List[BeamResult] = []

    def design(self, beams: List[BeamInput]) -> List[BeamResult]:
        self.results = []
        for beam in beams:
            r = self._design_beam(beam)
            self.results.append(r)
        return self.results

    def _design_beam(self, b: BeamInput) -> BeamResult:
        nm = b.n_members
        ns = b.n_supports

        b.fcu = b.fcu or self.fcu
        b.fy = b.fy or self.fy
        b.fyv = b.fyv or self.fyv

        l = (b.member_lengths[:nm] if len(b.member_lengths) >= nm
             else [0.0] * nm)
        ud = (b.member_udl[:nm] if len(b.member_udl) >= nm
              else [0.0] * nm)
        wt = (b.member_wt[:nm] if len(b.member_wt) >= nm
              else [0.0] * nm)
        wb = (b.member_wb[:nm] if len(b.member_wb) >= nm
              else [0.0] * nm)
        ab = (b.member_ab[:nm] if len(b.member_ab) >= nm
              else [0.0] * nm)
        npl = (b.member_npl[:nm] if len(b.member_npl) >= nm
               else [0] * nm)
        if len(b.member_pl) < nm:
            b.member_pl += [[] for _ in range(nm - len(b.member_pl))]

        h = b.h
        # Equivalent UDL, static shears, free moments
        u_eq = [0.0] * nm
        srn1 = [0.0] * nm
        srn2 = [0.0] * nm
        freemt = [0.0] * nm

        while True:
            for i in range(nm):
                u_eq[i] = ud[i] + wt[i] / 3.0
                al = ab[i] / l[i] if l[i] > 0 else 0.0
                u_eq[i] += wb[i] * (1.0 - (2.0 / 3.0) * al) * 0.5

                srn1[i] = ud[i] * l[i] * 0.5
                srn2[i] = srn1[i]
                freemt[i] = ud[i] * l[i] ** 2.0 / 8.0

                srn1[i] += 0.25 * wt[i] * l[i]
                freemt[i] += (1.0 / 12.0) * wt[i] * l[i] ** 2.0

                al = ab[i] / l[i] if l[i] > 0 else 0.0
                srn1[i] += 0.5 * wb[i] * l[i] * (1.0 - al)
                sp = (3.0 - 4.0 * al ** 2.0) / 24.0
                freemt[i] += sp * wb[i] * l[i] ** 2.0
                srn2[i] = srn1[i]

                if npl[i] > 0 and i < len(b.member_pl):
                    for pl, dist in b.member_pl[i]:
                        al_p = dist / l[i] if l[i] > 0 else 0.0
                        ar = 1.0 - al_p
                        srn1[i] += pl * ar
                        srn2[i] += pl * al_p
                        if al_p <= 0.5:
                            freemt[i] += al_p * pl * l[i] * 0.5
                        else:
                            freemt[i] += ar * pl * l[i] * 0.5

                # Section inertia
                d = h - 50.0
                iv = (b.b * d ** 3.0) / 12.0 / 1.0e12

            # --- Clapeyron three-moment equation ---
            nn = ns - 1
            if b.ty1 == 1 and b.ty2 == 1:
                nn = ns
            elif b.ty1 == 0 and b.ty2 == 0:
                nn = ns - 2

            mt = [0.0] * ns

            if nn >= 1:
                ndim = nn
                ag = [[0.0] * ndim for _ in range(ndim)]
                rhs = [0.0] * ndim
                e = 1.0

                # Equivalent moment of inertia using section dimensions
                d = h - 50.0
                iv_list = [b.b * d ** 3.0 / 12.0 / 1.0e12 for _ in range(nm)]

                # First row
                idx = 0
                if b.ty1 == 1:
                    ei1 = e * iv_list[0]
                    ag[0][0] = 2.0 * l[0] / ei1
                    if ndim > 1:
                        ag[0][1] = l[0] / ei1
                    rhs[0] = u_eq[0] * l[0] ** 3.0 / (4.0 * ei1)
                    if npl[0] > 0:
                        for pl, dist in b.member_pl[0]:
                            rhs[0] += paf(dist, pl, l[0]) / ei1
                    idx = 1
                else:
                    ei1 = e * iv_list[0]
                    ei2 = e * iv_list[1] if nm > 1 else ei1
                    ag[0][0] = 2.0 * (l[0] / ei1 + l[1] / ei2)
                    if ndim > 1:
                        ag[0][1] = l[1] / ei2
                    rhs[0] = u_eq[0] * l[0] ** 3.0 / (4.0 * ei1)
                    rhs[0] += u_eq[1] * l[1] ** 3.0 / (4.0 * ei2) if nm > 1 else 0.0
                    if npl[0] > 0:
                        for pl, dist in b.member_pl[0]:
                            rhs[0] += paf(dist, pl, l[0]) / ei1
                    if nm > 1 and npl[1] > 0:
                        for pl, dist in b.member_pl[1]:
                            rhs[0] += paf(l[1] - dist, pl, l[1]) / ei2
                    idx = 1

                # Internal rows
                for ic in range(1, nn - 1):
                    i = idx
                    ip = idx + 1
                    if ip >= nm:
                        ip = nm - 1
                    ei1 = e * iv_list[i]
                    ei2 = e * iv_list[ip]
                    ag[ic][ic - 1] = l[i] / ei1
                    ag[ic][ic] = 2.0 * (l[i] / ei1 + l[ip] / ei2)
                    ag[ic][ic + 1] = l[ip] / ei2
                    rhs[ic] = u_eq[i] * l[i] ** 3.0 / (4.0 * ei1)
                    rhs[ic] += u_eq[ip] * l[ip] ** 3.0 / (4.0 * ei2)
                    if npl[i] > 0:
                        for pl, dist in b.member_pl[i]:
                            rhs[ic] += paf(dist, pl, l[i]) / ei1
                    if npl[ip] > 0:
                        for pl, dist in b.member_pl[ip]:
                            rhs[ic] += paf(l[ip] - dist, pl, l[ip]) / ei2
                    idx += 1

                # Last row
                if nn >= 2 and idx < nm:
                    i_last = nm - 1
                    if b.ty2 == 1:
                        ei1 = e * iv_list[i_last]
                        ag[nn - 1][nn - 2] = l[i_last] / ei1
                        ag[nn - 1][nn - 1] = 2.0 * l[i_last] / ei1
                        rhs[nn - 1] = u_eq[i_last] * l[i_last] ** 3.0 / (4.0 * ei1)
                        if npl[i_last] > 0:
                            for pl, dist in b.member_pl[i_last]:
                                rhs[nn - 1] += paf(l[i_last] - dist, pl, l[i_last]) / ei1
                    else:
                        ei1 = e * iv_list[i_last - 1]
                        ei2 = e * iv_list[i_last]
                        ag[nn - 1][nn - 2] = l[i_last - 1] / ei1
                        ag[nn - 1][nn - 1] = 2.0 * (l[i_last - 1] / ei1 + l[i_last] / ei2)
                        rhs[nn - 1] = u_eq[i_last - 1] * l[i_last - 1] ** 3.0 / (4.0 * ei1)
                        rhs[nn - 1] += u_eq[i_last] * l[i_last] ** 3.0 / (4.0 * ei2)
                        if npl[i_last - 1] > 0:
                            for pl, dist in b.member_pl[i_last - 1]:
                                rhs[nn - 1] += paf(dist, pl, l[i_last - 1]) / ei1
                        if npl[i_last] > 0:
                            for pl, dist in b.member_pl[i_last]:
                                rhs[nn - 1] += paf(l[i_last] - dist, pl, l[i_last]) / ei2

                xmt = gauss(ag, rhs, nn, ndim)
                if b.ty1 == 1 and b.ty2 == 1:
                    for i in range(nn):
                        mt[i] = xmt[i]
                else:
                    for i in range(nn):
                        mt[i + 1] = xmt[i]

            # --- Calculate span moments and shears ---
            spmt = [0.0] * nm
            sfn1 = [0.0] * nm
            sfn2 = [0.0] * nm

            for i in range(nm):
                n1 = i
                n2 = min(i + 1, ns - 1)
                spmt[i] = freemt[i] - (mt[n1] + mt[n2]) * 0.5
                diffmt = (mt[n1] - mt[n2]) / l[i] if l[i] > 0 else 0.0
                sfn1[i] = srn1[i] + diffmt
                sfn2[i] = srn2[i] - diffmt

            # --- Reactions ---
            reactn = [0.0] * ns
            if nm == 1:
                reactn[0] = sfn1[0]
                reactn[1] = sfn2[0]
            else:
                reactn[0] = sfn1[0]
                reactn[ns - 1] = sfn2[nm - 1]
                for i in range(1, ns - 1):
                    reactn[i] = sfn2[i - 1] + sfn1[i]

            # --- Design reinforcement ---
            d = h - 50.0
            span_results = []
            support_results = []

            for i in range(nm):
                m_design = abs(spmt[i])
                sr = steel_beam(m_design, b.b, b.bf, d, h, b.fcu, b.fy)
                if sr.heck == 0:
                    h += 50
                    break

                di, fact, heck_d = deflect_beam(
                    i, min(b.n_members - 1, 1), b.b, d, sr.ast, sr.ast,
                    b.fy, m_design, l[i], 26.0 if b.n_members > 1 else 20.0
                )
                if heck_d == 0:
                    h += 25
                    break

                pt, rdb, svb = rodia_beam(sr.ast, math.pi, b.fy)
                pt2, rdt, svt = rodia_beam(sr.asb, math.pi, b.fy)

                sv_l, heck_sl = shear_links(sfn1[i], sr.ast, b.fyv, b.fcu, b.b, d)
                sv_r, heck_sr = shear_links(sfn2[i], sr.ast, b.fyv, b.fcu, b.b, d)

                span_results.append(BeamSpanResult(
                    span_id=f"{b.beam_id}-S{i + 1}",
                    length=l[i], udl=u_eq[i],
                    moment=m_design,
                    steel_bot=sr.ast, steel_top=sr.asb,
                    bar_type=pt, bar_dia_bot=rdb, bar_spacing_bot=svb,
                    bar_dia_top=rdt, bar_spacing_top=svt,
                    shear_left=sfn1[i], shear_right=sfn2[i],
                    sv_left=sv_l, sv_right=sv_r,
                    defl_req_depth=di, defl_ok=(heck_d == 1),
                ))
            else:
                # Only runs if loop completed without break
                for i in range(ns):
                    m_support = abs(mt[i] if i < len(mt) else 0.0)
                    sr = steel_beam(m_support, b.b, b.bf, d, h, b.fcu, b.fy)
                    pt, rdt, svt = rodia_beam(sr.ast, math.pi, b.fy)
                    pt2, rdb, svb = rodia_beam(sr.asb, math.pi, b.fy)

                    support_results.append(BeamSupportResult(
                        support_id=f"{b.beam_id}-Sup{i + 1}",
                        reaction=reactn[i], moment=m_support,
                        steel_top=sr.ast, steel_bot=sr.asb,
                        bar_type=pt, bar_dia_top=rdt, bar_spacing_top=svt,
                        bar_dia_bot=rdb, bar_spacing_bot=svb,
                    ))
                return BeamResult(
                    beam_id=b.beam_id,
                    spans=span_results,
                    supports=support_results,
                    heck=1,
                )
            # Fallback: all spans broke (over-reinforced) - return with heck=0
            return BeamResult(
                beam_id=b.beam_id,
                spans=span_results,
                supports=support_results,
                heck=0,
            )
