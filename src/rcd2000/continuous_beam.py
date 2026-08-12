"""Continuous beam analysis using Clapeyron's three-moment equation.
Port of Oyenuga's CONTINUOUS_BEAM program (pages 89-93).

The three-moment equation is:
  M_i*L_i/E_iI_i + 2*M_{i+1}*(L_i/E_iI_i + L_{i+1}/E_{i+1}I_{i+1})
  + M_{i+2}*L_{i+1}/E_{i+1}I_{i+1}
  = w_i*L_i**3/(4*E_iI_i) + w_{i+1}*L_{i+1}**3/(4*E_{i+1}I_{i+1})
  + SUM(PAF)/E_iI_i + SUM(PAF_rev)/E_{i+1}I_{i+1}

Where PAF = P * a * (L**2 - a**2) / L for point loads.
Uses equivalent UDL (converted from triangular/trapezoidal) for support moments.
"""
import math
from dataclasses import dataclass, field
from typing import List, Tuple
from rcd2000.utils import gauss


def paf(x: float, w: float, d: float) -> float:
    """Point load factor for Clapeyron's three-moment equation.
    PAF = W * X * (D**2 - X**2) / D
    """
    return w * x * (d * d - x * x) / d


@dataclass
class ContinuousBeamMember:
    member_id: str
    length: float          # m
    inertia: float         # m^4 (moment of inertia)
    e_mod: float = 1.0     # relative E
    udl: float = 0.0       # kN/m
    wt: float = 0.0        # kN/m - triangular
    wb: float = 0.0        # kN/m - trapezoidal max
    ab: float = 0.0        # m - distance for trapezoidal load
    npl: int = 0
    point_loads: List[Tuple[float, float]] = field(default_factory=list)
    n1: int = 0            # support number at the left end (book N1, 1-based; 0 = sequential)
    n2: int = 0            # support number at the right end (book N2, 1-based; 0 = sequential)

    span_moment: float = 0.0
    shear_left: float = 0.0
    shear_right: float = 0.0


@dataclass
class ContinuousBeamInput:
    n_supports: int
    n_members: int
    members: List[ContinuousBeamMember] = field(default_factory=list)
    end1_type: int = 0  # 0=pin, 1=fixed
    end2_type: int = 0
    end1_cant_load: float = 0.0
    end1_cant_moment: float = 0.0
    end2_cant_load: float = 0.0
    end2_cant_moment: float = 0.0


@dataclass
class ContinuousBeamResult:
    support_moments: List[float] = field(default_factory=list)
    support_reactions: List[float] = field(default_factory=list)
    span_moments: List[float] = field(default_factory=list)
    span_shear_left: List[float] = field(default_factory=list)
    span_shear_right: List[float] = field(default_factory=list)
    members: List[ContinuousBeamMember] = field(default_factory=list)


class ContinuousBeamAnalyzer:
    """Analyzes continuous beams using Clapeyron's three-moment equation."""

    def analyze(self, beam: ContinuousBeamInput) -> ContinuousBeamResult:
        nm = beam.n_members
        ns = beam.n_supports
        members = beam.members

        l = [m.length for m in members]
        iv = [m.inertia for m in members]
        e = [m.e_mod for m in members]

        # Calculate free moments and static shears using actual loads
        srn1 = [0.0] * nm
        srn2 = [0.0] * nm
        freemt = [0.0] * nm
        u_eq = [0.0] * nm

        for i in range(nm):
            srn1[i] = members[i].udl * l[i] * 0.5
            srn2[i] = srn1[i]
            freemt[i] = members[i].udl * l[i] ** 2.0 / 8.0

            # Triangular load
            srn1[i] += 0.25 * members[i].wt * l[i]
            freemt[i] += (1.0 / 12.0) * members[i].wt * l[i] ** 2.0

            # Trapezoidal load
            al = members[i].ab / l[i] if l[i] > 0 else 0.0
            srn1[i] += 0.5 * members[i].wb * l[i] * (1.0 - al)
            sp = (3.0 - 4.0 * al ** 2.0) / 24.0
            freemt[i] += sp * members[i].wb * l[i] ** 2.0
            srn2[i] = srn1[i]

            # Point loads
            for pl, dist in members[i].point_loads:
                al = dist / l[i] if l[i] > 0 else 0.0
                ar = 1.0 - al
                srn1[i] += pl * ar
                srn2[i] += pl * al
                if al <= 0.5:
                    freemt[i] += al * pl * l[i] * 0.5
                else:
                    freemt[i] += ar * pl * l[i] * 0.5

            # Equivalent UDL for Clapeyron RHS
            u_eq[i] = members[i].udl + members[i].wt / 3.0
            u_eq[i] += members[i].wb * (1.0 - (2.0 / 3.0) * al) * 0.5

        # Determine number of unknown support moments (NN)
        nn = ns - 1
        if beam.end1_type == 1 and beam.end2_type == 1:
            nn = ns
        elif beam.end1_type == 0 and beam.end2_type == 0:
            nn = ns - 2

        mt = [0.0] * ns

        if nn >= 1:
            ndim = nn
            ag = [[0.0] * ndim for _ in range(ndim)]
            rhs = [0.0] * ndim

            # First row
            idx = 0
            if beam.end1_type == 1:
                ei1 = e[0] * iv[0]
                ag[0][0] = 2.0 * l[0] / ei1
                if ndim > 1:
                    ag[0][1] = l[0] / ei1
                rhs[0] = u_eq[0] * l[0] ** 3.0 / (4.0 * ei1)
                for pl, dist in members[0].point_loads:
                    rhs[0] += paf(dist, pl, l[0]) / ei1
                idx = 1
            else:
                ei1 = e[0] * iv[0]
                ei2 = e[1] * iv[1] if nm > 1 else ei1
                ag[0][0] = 2.0 * (l[0] / ei1 + l[1] / ei2)
                if ndim > 1:
                    ag[0][1] = l[1] / ei2
                rhs[0] = u_eq[0] * l[0] ** 3.0 / (4.0 * ei1)
                rhs[0] += u_eq[1] * l[1] ** 3.0 / (4.0 * ei2) if nm > 1 else 0.0
                # Point loads on left span
                for pl, dist in members[0].point_loads:
                    rhs[0] += paf(dist, pl, l[0]) / ei1
                # Point loads on right span (reverse side)
                if nm > 1:
                    for pl, dist in members[1].point_loads:
                        rhs[0] += paf(l[1] - dist, pl, l[1]) / ei2
                idx = 1

            # Internal rows
            for ic in range(1, nn - 1):
                i = idx
                ip = idx + 1
                if ip >= nm:
                    ip = nm - 1
                ei1 = e[i] * iv[i]
                ei2 = e[ip] * iv[ip]
                ag[ic][ic - 1] = l[i] / ei1
                ag[ic][ic] = 2.0 * (l[i] / ei1 + l[ip] / ei2)
                ag[ic][ic + 1] = l[ip] / ei2
                rhs[ic] = u_eq[i] * l[i] ** 3.0 / (4.0 * ei1)
                rhs[ic] += u_eq[ip] * l[ip] ** 3.0 / (4.0 * ei2)
                for pl, dist in members[i].point_loads:
                    rhs[ic] += paf(dist, pl, l[i]) / ei1
                for pl, dist in members[ip].point_loads:
                    rhs[ic] += paf(l[ip] - dist, pl, l[ip]) / ei2
                idx += 1

            # Last row (for nn >= 2)
            if nn >= 2 and idx < nm:
                i_last = nm - 1
                if beam.end2_type == 1:
                    ei1 = e[i_last] * iv[i_last]
                    ag[nn - 1][nn - 2] = l[i_last] / ei1
                    ag[nn - 1][nn - 1] = 2.0 * l[i_last] / ei1
                    rhs[nn - 1] = u_eq[i_last] * l[i_last] ** 3.0 / (4.0 * ei1)
                    for pl, dist in members[i_last].point_loads:
                        rhs[nn - 1] += paf(l[i_last] - dist, pl, l[i_last]) / ei1
                else:
                    ei1 = e[i_last - 1] * iv[i_last - 1] if i_last > 0 else e[0] * iv[0]
                    ei2 = e[i_last] * iv[i_last]
                    ag[nn - 1][nn - 2] = l[i_last - 1] / ei1
                    ag[nn - 1][nn - 1] = 2.0 * (l[i_last - 1] / ei1 + l[i_last] / ei2)
                    rhs[nn - 1] = u_eq[i_last - 1] * l[i_last - 1] ** 3.0 / (4.0 * ei1)
                    rhs[nn - 1] += u_eq[i_last] * l[i_last] ** 3.0 / (4.0 * ei2)
                    for pl, dist in members[i_last - 1].point_loads:
                        rhs[nn - 1] += paf(dist, pl, l[i_last - 1]) / ei1
                    for pl, dist in members[i_last].point_loads:
                        rhs[nn - 1] += paf(l[i_last] - dist, pl, l[i_last]) / ei2

            xmt = gauss(ag, rhs, nn, ndim)
            if beam.end1_type == 1 and beam.end2_type == 1:
                for i in range(nn):
                    mt[i] = xmt[i]
            else:
                for i in range(nn):
                    mt[i + 1] = xmt[i]

        # Calculate span moments and shear forces
        spmt = [0.0] * nm
        sfn1 = [0.0] * nm
        sfn2 = [0.0] * nm

        # Book N1/N2 name the actual support numbers at each end of the
        # member (the matrix assembly stays sequential; N1/N2 are only used
        # here, in the results module). Defaults: member i connects supports
        # i and i+1 (0-based), matching the sequential case.
        for i in range(nm):
            n1 = members[i].n1 - 1 if members[i].n1 > 0 else i
            n2 = members[i].n2 - 1 if members[i].n2 > 0 else min(i + 1, ns - 1)
            n1 = max(0, min(n1, ns - 1))
            n2 = max(0, min(n2, ns - 1))
            spmt[i] = freemt[i] - (mt[n1] + mt[n2]) * 0.5
            diffmt = (mt[n1] - mt[n2]) / l[i] if l[i] > 0 else 0.0
            sfn1[i] = srn1[i] + diffmt
            sfn2[i] = srn2[i] - diffmt

        # Calculate reactions
        reactn = [0.0] * ns
        if nm == 1:
            reactn[0] = sfn1[0]
            reactn[1] = sfn2[0]
        else:
            reactn[0] = sfn1[0]
            reactn[ns - 1] = sfn2[nm - 1]
            for i in range(1, ns - 1):
                reactn[i] = sfn2[i - 1] + sfn1[i]

        # Add cantilever loads
        reactn[0] += beam.end1_cant_load
        reactn[ns - 1] += beam.end2_cant_load

        for i, m in enumerate(members):
            m.span_moment = spmt[i]
            m.shear_left = sfn1[i]
            m.shear_right = sfn2[i]

        return ContinuousBeamResult(
            support_moments=mt,
            support_reactions=reactn,
            span_moments=spmt,
            span_shear_left=sfn1,
            span_shear_right=sfn2,
            members=members,
        )
