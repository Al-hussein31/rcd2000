"""Stair design to BS 8110:1997.
Port of Oyenuga's STAIR program (pages 173-177).

Straight flight stair (waist slab type, spanning longitudinally).
"""
import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class StairInput:
    stair_id: str
    stair_type: int = 1  # only type 1 (straight flight) currently
    span: float = 0.0    # m
    tread: float = 0.0   # mm
    rise: float = 0.0    # mm
    imposed_load: float = 0.0  # kN/m²
    spl: float = 0.0     # superimposed dead load kN/m²
    wld: float = 0.0     # kN/m³
    concrete_weight: float = 25.0  # kN/m³


@dataclass
class StairResult:
    stair_id: str = ""
    stair_type: int = 0
    waist_thickness: float = 0.0
    total_udl: float = 0.0
    design_moment: float = 0.0
    effective_depth: float = 0.0
    k_value: float = 0.0
    lever_arm_factor: float = 0.0
    lever_arm_z: float = 0.0
    steel_required: float = 0.0
    bar_type: str = "Y"
    bar_dia: float = 10.0
    bar_spacing: float = 200.0


class StairDesigner:
    """Designs reinforced concrete stairs to BS 8110."""

    def __init__(self, fcu: float = 25.0, fy: float = 460.0):
        self.fcu = fcu
        self.fy = fy
        self.results: List[StairResult] = []

    def design(self, stairs: List[StairInput]) -> List[StairResult]:
        self.results = []
        for s in stairs:
            r = self._design_stair(s)
            self.results.append(r)
        return self.results

    def _design_stair(self, s: StairInput) -> StairResult:
        r = StairResult(stair_id=s.stair_id, stair_type=s.stair_type)

        # Assume waist thickness = span / 20
        waist = s.span / 20.0
        if waist < 0.100:
            waist = 0.100

        tm = s.tread / 1000.0
        rm = s.rise / 1000.0

        # Self-weight of waist slab (sloping) on plan
        sws = s.concrete_weight * waist * math.sqrt(tm ** 2 + rm ** 2) / tm
        # Self-weight of steps
        sts = 0.5 * rm * s.concrete_weight
        # Finishes
        fin = 1.0
        # Total dead load
        gk = sws + sts + fin + s.spl
        # Total ultimate load (BS 8110: 1.4 Gk + 1.6 Qk)
        udl = 1.4 * gk + 1.6 * s.imposed_load

        # Design moment (simply supported)
        msb = udl * s.span ** 2 / 8.0

        # Effective depth (assume h=175, cover=20, bar=8)
        d = 175.0 - 20.0 - 8.0

        # K = M / (b * d² * fcu)
        k = msb * 1.0e6 / (1000.0 * d ** 2 * self.fcu)

        # Lever arm
        if k < 0.156:
            la = 0.5 + math.sqrt(0.25 - k / 0.9)
        else:
            la = 0.5 + math.sqrt(0.25 - 0.156 / 0.9)
        if la > 0.95:
            la = 0.95

        z = la * d
        ast = msb * 1.0e6 / (0.87 * self.fy * z)

        r.waist_thickness = waist * 1000.0
        r.total_udl = udl
        r.design_moment = msb
        r.effective_depth = d
        r.k_value = k
        r.lever_arm_factor = la
        r.lever_arm_z = z
        r.steel_required = ast

        from rcd2000.utils import rodia_slab
        r.bar_type, r.bar_dia, r.bar_spacing = rodia_slab(ast, self.fy)

        return r
