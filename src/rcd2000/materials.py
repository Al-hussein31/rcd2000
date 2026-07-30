from dataclasses import dataclass
from typing import Literal


@dataclass
class Concrete:
    fcu: float  # characteristic cube strength (N/mm²)
    gamma_m: float = 1.5  # partial safety factor for concrete

    @property
    def design_stress(self) -> float:
        return 0.45 * self.fcu

    def shear_stress_capacity(self, d: float, asym: float, b: float) -> float:
        ac = min(asym * 100.0 / (b * d), 3.0)
        ac = ac ** (1.0 / 3.0)
        dc = min(400.0 / d, 1.0)
        dc = dc ** 0.25
        return 0.632 * ac * dc

    def max_shear_stress(self) -> float:
        vm = 0.8 * self.fcu ** 0.5
        return min(vm, 5.0)

    @property
    def modulus_of_elasticity(self) -> float:
        return 200.0  # kN/mm²


@dataclass
class Steel:
    fy: float  # characteristic yield strength (N/mm²)
    gamma_m: float = 1.15  # partial safety factor for steel

    @property
    def design_stress(self) -> float:
        return 0.95 * self.fy / self.gamma_m * self.gamma_m

    @property
    def fy_design(self) -> float:
        return 0.95 * self.fy

    def bar_type(self) -> Literal["R", "Y"]:
        return "R" if self.fy <= 250 else "Y"

    def minimum_percent(self) -> float:
        return 0.24 if self.fy <= 250 else 0.13

    def ultimate_bond_stress(self, fcu: float) -> float:
        if self.fy <= 250:
            if fcu <= 20:
                return 1.70
            elif fcu <= 25:
                return 2.0
            elif fcu <= 30:
                return 2.2
            else:
                return 2.7
        else:
            if fcu <= 20:
                return 2.1
            elif fcu <= 25:
                return 2.5
            elif fcu <= 30:
                return 2.8
            else:
                return 3.4


PI = 3.141592653589793
