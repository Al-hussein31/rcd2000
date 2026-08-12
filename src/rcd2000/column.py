"""Column analysis and design to BS 8110:1997.
Port of Oyenuga's COLUMN program (pages 242-246).

Handles 3 column types:
  1: Axially loaded
  2: Uniaxially loaded
  3: Biaxially loaded

Uses strain compatibility to generate Nu/Mu interaction curves.
"""
import math
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ColumnInput:
    column_id: str
    col_type: int     # 1=axial, 2=uniaxial, 3=biaxial
    shape: int        # 1=rectangular, 2=circular
    load: float       # kN
    bx: float = 0.0   # mm (width x-axis)
    by: float = 0.0   # mm (width y-axis)
    dia: float = 0.0  # mm (circular)
    depth: float = 0.0  # mm (overall depth)
    length: float = 0.0   # m (column height)
    le: float = 0.0   # m (effective length)
    lex: float = 0.0
    ley: float = 0.0
    moment_x: float = 0.0   # kN.m
    moment_y: float = 0.0   # kN.m
    moment: float = 0.0     # kN.m (for uniaxial)
    brc: int = 1            # bracing: 1=braced, 2=unbraced (book BRC)


@dataclass
class ColumnResult:
    column_id: str
    col_type: int
    shape: int
    steel_required: float    # mm²
    axial_capacity: float    # kN (Nu)
    moment_capacity_x: float  # kN.m (Mux)
    moment_capacity_y: float  # kN.m (Muy)
    steel_percent: float
    heck: int                # 0=ok, 1=section inadequate
    biaxial_check_ok: bool = True
    srx: float = 0.0         # slenderness ratio about x-axis (lex/hx)
    sry: float = 0.0         # slenderness ratio about y-axis (ley/hy)
    madx: float = 0.0        # additional moment about x-axis (kN.m)
    mady: float = 0.0        # additional moment about y-axis (kN.m)
    slender_x: bool = False  # slender about x-axis
    slender_y: bool = False  # slender about y-axis
    design_type: int = 0     # effective design type used (1/2/3, 0=as input)


def _steel_stress(e: float, fy: float) -> float:
    """Calculate steel stress from strain using bilinear model."""
    es = fy / 210000.0
    if e <= es:
        return e * 200000.0
    return 0.95 * fy


class ColumnDesigner:
    """Designs reinforced concrete columns to BS 8110."""

    def __init__(self, fcu: float = 25.0, fy: float = 460.0,
                 max_steel_pct: float = 4.0, dh_ratio: float = 0.85):
        self.fcu = fcu
        self.fy = fy
        self.max_steel_pct = max_steel_pct
        self.dh_ratio = dh_ratio  # d/h ratio
        self.results: List[ColumnResult] = []

    def design(self, columns: List[ColumnInput]) -> List[ColumnResult]:
        self.results = []
        for c in columns:
            r = self._design_column(c)
            self.results.append(r)
        return self.results

    def _design_column(self, c: ColumnInput) -> ColumnResult:
        r = ColumnResult(
            column_id=c.column_id,
            col_type=c.col_type,
            shape=c.shape,
            steel_required=0.0,
            axial_capacity=0.0,
            moment_capacity_x=0.0,
            moment_capacity_y=0.0,
            steel_percent=0.0,
            heck=0,
        )

        if c.shape == 1:
            ag = c.bx * c.by
            hx, hy = c.bx, c.by
        else:
            ag = math.pi * c.dia ** 2.0 / 4.0
            hx = hy = c.dia

        # ── Slenderness check (book: braced SR > 15, unbraced SR > 10) ──
        # When slender, an additional moment is added:
        #   ba = (1/2000) * (le/b')^2   where b' = smaller dimension
        #   au = ba * 1.0 * h           (h = section depth in that plane)
        #   Madd = N * au / 1000        (kN.m)
        # Verified against book Example 7.8: b'=225, le=4080 mm
        #   -> ba = (4080/225)^2/2000 = 0.164, Madd = 0.164*0.225*1200
        #   = 44.28 kN.m.
        srx = sry = 0.0
        madx = mady = 0.0
        slender_x = slender_y = False
        if hx > 0 and hy > 0 and c.brc in (1, 2):
            limit = 15.0 if c.brc == 1 else 10.0
            bp = min(hx, hy)
            lex_mm = c.lex * 1000.0
            ley_mm = c.ley * 1000.0
            if lex_mm > 0:
                srx = lex_mm / hx
                if srx > limit:
                    slender_x = True
                    ba = (1.0 / 2000.0) * (lex_mm / bp) ** 2.0
                    madx = c.load * ba * hx / 1000.0
            if ley_mm > 0:
                sry = ley_mm / hy
                if sry > limit:
                    slender_y = True
                    ba = (1.0 / 2000.0) * (ley_mm / bp) ** 2.0
                    mady = c.load * ba * hy / 1000.0

        r.srx = srx
        r.sry = sry
        r.madx = madx
        r.mady = mady
        r.slender_x = slender_x
        r.slender_y = slender_y

        # ── Amplify the design moments with the slenderness additions ──
        if c.col_type == 3:
            mix, miy = c.moment_x, c.moment_y
        elif c.col_type == 2:
            mix, miy = c.moment, 0.0
        else:
            mix = miy = 0.0
        mx = mix + madx
        my = miy + mady

        # ── Design-type selection (book TY) ──
        # The book re-derives the type from the amplified moments using
        # MMIN = min(0.05*BMAX, 20)*pi/1000, so an axially loaded column
        # that is slender in either direction is redesigned as uniaxial or
        # biaxial ("an axially loaded column may end up being designed as
        # biaxially loaded"). Explicit user types (2/3) are respected.
        eff_type = c.col_type
        if c.col_type == 1:
            bmax = max(hx, hy)
            ect = min(0.05 * bmax, 20.0)
            mmin = ect * math.pi / 1000.0
            if mx <= mmin and my <= mmin:
                eff_type = 1
            elif mx > mmin and my <= mmin:
                eff_type = 2
            else:
                eff_type = 3
        r.design_type = eff_type

        dc = ColumnInput(
            column_id=c.column_id, col_type=eff_type, shape=c.shape,
            load=c.load, bx=c.bx, by=c.by, dia=c.dia, depth=c.depth,
            moment_x=mx, moment_y=my, moment=mx,
        )
        if eff_type == 1:
            self._axial(dc, ag, r)
        elif eff_type == 2:
            self._uniaxial(dc, ag, r)
        elif eff_type == 3:
            self._biaxial(dc, ag, r)

        r.steel_percent = r.steel_required * 100.0 / ag if ag > 0 else 0.0

        return r

    def _axial(self, c: ColumnInput, ag: float, r: ColumnResult):
        p = c.load
        ast = (p * 1000.0 - 0.35 * self.fcu * ag) / (0.7 * self.fy - 0.35 * self.fcu)
        amin = 0.4 * ag / 100.0
        amax = self.max_steel_pct * ag / 100.0

        if ast < amin:
            ast = amin
        if ast > amax:
            r.heck = 1

        r.steel_required = ast
        r.axial_capacity = (0.35 * self.fcu * ag + 0.7 * self.fy * ast) / 1000.0

    def _uniaxial(self, c: ColumnInput, ag: float, r: ColumnResult):
        """Generate Nu/Mu interaction curves from strain compatibility."""

        if c.shape == 1:
            h = c.depth if c.depth > 0 else c.bx
            b = c.by if c.by > 0 else c.bx
        else:
            h = c.dia
            b = h

        dh = self.dh_ratio
        k1 = 0.4 * self.fcu
        k2 = 0.45
        nn = int(self.max_steel_pct / 0.1)

        nu_table = []
        mu_table = []
        as_table = []

        at = 0.0
        for i in range(9):
            xh = 0.2 + i * 0.1  # 0.2 to 1.0
            for j in range(nn):
                at += 0.001
                hx = 1.0 / xh
                esc = (1.0 - 0.1 * hx) * 0.0035
                es = (0.9 * hx - 1.0) * 0.0035
                fsc = _steel_stress(esc, self.fy)
                fs = _steel_stress(es, self.fy)
                nu = k1 * xh + fsc * at - fs * at
                mu = (k1 * xh * (0.5 - k2 * xh)
                      + fsc * at * (dh - 0.5)
                      - fs * at * (0.5 - dh))
                nu_table.append(nu)
                mu_table.append(mu)
                as_table.append(at)
            at = 0.003

        p_nbh = c.load * 1000.0 / (b * h)
        m_bh = c.moment * 1.0e6 / (b * h ** 2.0)

        found = False
        for j in range(nn):
            for i in range(9):
                idx = i * nn + j
                if idx < len(nu_table) and idx < len(mu_table):
                    if nu_table[idx] >= p_nbh and mu_table[idx] >= m_bh:
                        r.axial_capacity = (nu_table[idx] * b * h) / 1000.0
                        r.moment_capacity_x = (mu_table[idx] * b * h ** 2.0) / 1.0e6
                        r.steel_required = as_table[idx] * b * h if idx < len(as_table) else 0.0
                        found = True
                        break
            if found:
                break

        if not found:
            if abs(p_nbh) < 1e-6 and abs(m_bh) < 1e-6:
                r.steel_required = 0.4 * ag / 100.0
            else:
                r.heck = 1

        amin = 0.4 * ag / 100.0
        amax = self.max_steel_pct * ag / 100.0
        if r.steel_required < amin:
            r.steel_required = amin
        if r.steel_required > amax:
            r.heck = 1

    def _biaxial(self, c: ColumnInput, ag: float, r: ColumnResult):
        """Biaxial column design using BS 8110 interaction.
        Uses (Mx/Mux)^alpha + (My/Muy)^alpha <= 1.
        """
        h = c.depth if c.depth > 0 else c.bx
        b = c.by if c.by > 0 else c.bx

        # Compute x-axis uniaxial result in a temporary result to avoid
        # overwriting r's fields before we capture Mux.
        tmp_x = ColumnResult(
            column_id=c.column_id, col_type=c.col_type, shape=c.shape,
            steel_required=0.0, axial_capacity=0.0,
            moment_capacity_x=0.0, moment_capacity_y=0.0,
            steel_percent=0.0, heck=0,
        )
        mem_x = ColumnInput(
            column_id=c.column_id, col_type=2, shape=c.shape,
            load=c.load, bx=c.bx, by=c.by, dia=c.dia,
            depth=c.depth, moment=c.moment_x or c.moment,
        )
        self._uniaxial(mem_x, ag, tmp_x)
        mux = tmp_x.moment_capacity_x
        steel_x = tmp_x.steel_required

        # Compute y-axis uniaxial result in a separate temporary result.
        tmp_y = ColumnResult(
            column_id=c.column_id, col_type=c.col_type, shape=c.shape,
            steel_required=0.0, axial_capacity=0.0,
            moment_capacity_x=0.0, moment_capacity_y=0.0,
            steel_percent=0.0, heck=0,
        )
        mem_y = ColumnInput(
            column_id=c.column_id, col_type=2, shape=c.shape,
            load=c.load, bx=c.by, by=c.bx, dia=c.dia,
            depth=c.depth, moment=c.moment_y or c.moment,
        )
        self._uniaxial(mem_y, ag, tmp_y)
        muy = tmp_y.moment_capacity_y
        steel_y = tmp_y.steel_required

        if mux > 0 and muy > 0:
            alpha = 1.0
            if c.shape == 1:
                n_bh = c.load * 1000.0 / (b * h)
                nuz = 0.45 * self.fcu * ag + 0.95 * self.fy * max(steel_x, steel_y)
                nuz = nuz / 1000.0
                if abs(nuz - c.load) > 0.001:
                    n_ratio = c.load / nuz
                    if n_ratio <= 0.2:
                        alpha = 1.0
                    elif n_ratio < 0.8:
                        alpha = 0.67 + 1.67 * n_ratio
                    else:
                        alpha = 2.0

            biaxial_ratio = ((c.moment_x or c.moment) / mux) ** alpha + \
                            ((c.moment_y or c.moment) / muy) ** alpha
            r.biaxial_check_ok = biaxial_ratio <= 1.0
            r.steel_required = max(steel_x, steel_y)
            r.axial_capacity = max(tmp_x.axial_capacity, tmp_y.axial_capacity)
            r.moment_capacity_x = mux
            r.moment_capacity_y = muy
        else:
            r.biaxial_check_ok = False
            r.heck = 1
