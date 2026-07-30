from typing import Tuple
from dataclasses import dataclass
import math


@dataclass
class SteelDesignResult:
    ast: float  # tension steel area (mm²)
    asb: float  # bottom/compression steel area (mm²)
    heck: int   # 0 = section inadequate, 1 = OK


def gauss(ag: list[list[float]], y: list[float],
          ng: int, ndim: int) -> list[float]:
    """Gaussian elimination solver for simultaneous linear equations.
    Used in Clapeyron three-moment method.
    """
    x = [0.0] * ndim
    ag = [row[:] for row in ag]
    y = y[:]

    for k in range(ng - 1):
        for i in range(k + 1, ng):
            if ag[k][k] == 0.0:
                continue
            z = ag[i][k] / ag[k][k]
            for j in range(k, ng):
                ag[i][j] -= z * ag[k][j]
            y[i] -= y[k] * z

    x[ng - 1] = y[ng - 1] / ag[ng - 1][ng - 1]

    for i in range(ng - 2, -1, -1):
        su = 0.0
        for j in range(i + 1, ng):
            su += x[j] * ag[i][j]
        x[i] = (y[i] - su) / ag[i][i]

    return x


def steel_beam(m: float, b: float, bf: float, d: float, h: float,
               fcu: float, fy: float) -> SteelDesignResult:
    """Design beam reinforcement to BS 8110.
    Returns top steel (ast) and bottom steel (asb).
    heck = 0 if section is over-reinforced.
    """
    heck = 1
    ast = 0.0
    asb = 0.0

    if fy <= 250.0:
        amin = 0.25 * b * d / 100.0
    else:
        amin = 0.13 * b * d / 100.0

    amax = 0.04 * b * h
    k = (m * 1.0e6) / (fcu * bf * d ** 2.0)

    if k > 0.156:
        z = 0.77688 * d
        kp = 0.156
        x = (d - z) / 0.45
        asb = (k - kp) * fcu * b * d ** 2.0 / (0.95 * fy * (d - 0.5 * x))
        ast = kp * fcu * bf * d ** 2.0 / (0.95 * fy * z) + asb
    else:
        z = d * (0.5 + math.sqrt(0.25 - k / 0.9))
        la = z / d
        if la >= 0.95:
            z = 0.95 * d
        x = (d - z) / 0.45
        ast = (m * 1.0e6) / (0.95 * fy * z)

    if ast < amin:
        ast = amin
    if asb < amin:
        asb = amin
    if ast >= amax:
        heck = 0

    return SteelDesignResult(ast=ast, asb=asb, heck=heck)


def steel_slab(m: float, d: float, fcu: float, fy: float) -> Tuple[float, int]:
    """Design slab/1000mm strip reinforcement to BS 8110.
    Returns (ast, heck).
    """
    heck = 1
    h = d + 25
    ast = 0.0

    k = (m * 1.0e6) / (fcu * 1000.0 * d ** 2.0)
    if k > 0.156:
        heck = 0
        return ast, heck

    la = 0.5 + math.sqrt(0.25 - k / 0.9)
    if la >= 0.95:
        la = 0.95
    ast = (m * 1.0e6) / (0.95 * fy * la * d)

    c = 0.24 if fy <= 250 else 0.13
    amin = c * 1000.0 * h / 100.0
    if amin > ast:
        ast = amin

    return ast, heck


def steel_area(m: float, d: float, fcu: float, fy: float) -> Tuple[float, int]:
    """General steel area calculation (slab/1000mm strip)."""
    return steel_slab(m, d, fcu, fy)


def rodia_slab(ast: float, fy: float) -> Tuple[str, float, float]:
    """Select bar diameter and spacing for slab.
    Returns (bar_type, bar_dia_mm, spacing_mm).

    Picks the smallest bar that gives spacing in [100, 200] mm.
    For small As, picks smallest bar with spacing capped at 200 mm.
    """
    bar_type = "Y"
    bd = [8.0, 10.0, 12.0, 16.0, 20.0, 25.0, 32.0]
    pi = math.pi

    if ast <= 0.0:
        return bar_type, 10.0, 200.0

    for rd in bd:
        sv = 1000.0 * pi * rd ** 2.0 / (4.0 * ast)
        if sv >= 100.0:
            if sv > 200.0:
                sv = 200.0
            return bar_type, rd, sv

    return bar_type, bd[-1], 75.0


def rodia_beam(ast: float, pi: float, fy: float) -> Tuple[str, float, float]:
    """Select bar diameter and spacing for beam.
    Returns (bar_type, bar_dia_mm, spacing_mm).
    """
    if fy <= 250:
        t = "R"
    else:
        t = "Y"

    if ast <= 905.0:
        rd = 12.0
    elif ast <= 1610.0:
        rd = 16.0
    elif ast <= 2510.0:
        rd = 20.0
    elif ast <= 3930.0:
        rd = 25.0
    elif ast <= 6430.0:
        rd = 32.0
    else:
        rd = 40.0

    ar = pi * rd ** 2.0 / 4.0
    v = ast / ar
    v = 1000.0 * v
    n = int(v / 25.0) - 25
    sv = float(n)
    if sv < 75.0:
        sv = 75.0

    return t, rd, sv


def permlb(vbl: float, rdt: float, spt: float, pi: float,
           d: float, fy: float, fcu: float) -> Tuple[float, float]:
    """Bond/perimeter check. Returns (fbs, ubs)."""
    rn = 1000.0 / spt
    fbs = (vbl * 1000.0) / (rn * rdt * pi * d)

    if fy <= 250:
        if fcu <= 20.0:
            ubs = 1.70
        elif fcu <= 25.0:
            ubs = 2.0
        elif fcu <= 30.0:
            ubs = 2.2
        else:
            ubs = 2.7
    else:
        if fcu <= 20.0:
            ubs = 2.1
        elif fcu <= 25.0:
            ubs = 2.5
        elif fcu <= 30.0:
            ubs = 2.8
        else:
            ubs = 3.4

    return fbs, ubs


def perms(hcv: float, rd: float, sv: float, pi: float,
          d: float) -> Tuple[float, float]:
    """Shear capacity check. Returns (vs, vc)."""
    asv = pi * rd ** 2.0 / 4.0 * (1000.0 / sv)
    ac = asv * 100.0 / (1000.0 * d)
    if ac > 3.00:
        ac = 3.00
    ac = ac ** (1.0 / 3.0)
    oc = 400.0 / d
    if oc < 1.0:
        oc = 1.0
    oc = oc ** 0.25
    vc = 0.632 * ac * oc
    return hcv, vc


def deflect_beam(n: int, nn: int, b: float, d: float, asb: float,
                 as_req: float, fy: float, m: float, span: float,
                 sr: float) -> Tuple[float, float, int]:
    """Check deflection using BS 8110 basic span/effective-depth ratio.
    Returns (required_depth_mm, factor, heck).
    """
    heck = 1

    fs = 0.667 * fy * (as_req / asb) if asb > 0 else 0.667 * fy
    fact = 120.0 * (0.9 + m / (b * d ** 2.0))
    fact = 0.55 + (477.0 - fs) / fact
    if nn < 1:
        sr_base = 20.0
    else:
        sr_base = 26.0
    if fact >= 2.0:
        fact = 2.0

    di = (span * 1000.0) / (sr_base * fact)
    return di, fact, heck


def shear_links(v: float, a: float, fy: float, fcu: float,
                b: float, d: float) -> Tuple[float, int]:
    """Design shear links to BS 8110.
    Returns (spacing_mm, heck).
    heck = 0 if shear stress exceeded (increase section).
    """
    heck = 1
    v = abs(v)

    vv = v * 1000.0 / (b * d)
    vm = 0.8 * math.sqrt(fcu)
    if vm > 5.0:
        vm = 5.0

    if vv > vm:
        heck = 0
        return 0.0, heck

    ac = 100.0 * a / (b * d)
    if ac > 3.00:
        ac = 3.00
    ac = ac ** (1.0 / 3.0)
    dc = 400.0 / d
    if dc < 1.0:
        dc = 1.0
    dc = dc ** 0.25
    vc = 0.63 * ac * dc
    hvc = 0.5 * vc
    pvc = vc + 0.40

    if vv < hvc:
        sv = 0.75 * d
    elif hvc <= vv < pvc:
        sv = (0.95 * fy * 157.0) / (0.4 * b)
    else:
        sv = (157.0 * 0.95 * fy) / (b * (vv - vc))

    sp = 0.75 * d
    if sv > sp:
        sv = sp

    return sv, heck
