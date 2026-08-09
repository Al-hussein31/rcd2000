"""Comprehensive validation: Python port vs FORTRAN source and known BS 8110 results.

Converted from script-style to proper pytest tests.
"""
import math
import pytest

from rcd2000.utils import (steel_slab, steel_area, gauss, permlb, perms,
                           rodia_slab, rodia_beam, deflect_beam, shear_links)
from rcd2000.materials import Concrete, Steel
from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.continuous_beam import ContinuousBeamAnalyzer, ContinuousBeamInput, ContinuousBeamMember
from rcd2000.base import BaseDesigner, BaseInput
from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.stair import StairDesigner, StairInput

pi = math.pi


def check(name, expected, got, tol=0.01):
    """Check with absolute tolerance."""
    assert abs(expected - got) <= tol * max(1.0, abs(expected)), (
        f"{name}: expected {expected}, got {got}"
    )


def check_rel(name, expected, got, tol_pct=1.0):
    """Check with relative tolerance in percent."""
    if expected == 0:
        assert abs(got) <= tol_pct * 0.01, f"{name}: expected {expected}, got {got}"
        return
    pct = abs(got - expected) / abs(expected) * 100
    assert pct <= tol_pct, f"{name}: expected {expected}, got {got} ({pct:.1f}% off)"


# ============================================================
# 1. UTILITY FUNCTIONS
# ============================================================

class TestSteelSlab:
    def test_steel_basic(self):
        ast, heck = steel_slab(215.3, 250, 25, 460)
        check("STEEL M=215.3 d=250", 2429, round(ast, 0))
        assert heck == 1

    def test_steel_over_reinforced(self):
        ast, heck = steel_slab(500, 250, 25, 460)
        assert heck == 0

    def test_steel_minimum(self):
        ast, heck = steel_slab(50, 425, 25, 460)
        check("STEEL minimum steel", 585, round(ast, 0))


class TestPerms:
    def test_perms_d250(self):
        _, vc = perms(0, 12, 150, pi, 250)
        check("PERMS vc with Y12@150, d=250", 0.477, round(vc, 3))

    def test_perms_d500(self):
        _, vc = perms(0, 12, 150, pi, 500)
        check("PERMS vc with Y12@150, d=500", 0.336, round(vc, 3))


class TestPermlb:
    def test_permlb_fcu25(self):
        fbs, ubs = permlb(300, 12, 139, pi, 600, 460, 25)
        check("PERMLB fbs=1.844", 1.844, round(fbs, 3))
        check("PERMLB ubs FCU=25,FY=460 = 2.5", 2.5, ubs)

    def test_permlb_fcu20(self):
        _, ubs = permlb(300, 12, 139, pi, 600, 460, 20)
        check("PERMLB ubs FCU=20,FY=460 = 2.1", 2.1, ubs)


class TestGauss:
    def test_gauss_2x2(self):
        ag = [[2.0, 3.0], [4.0, 5.0]]
        y = [8.0, 14.0]
        x = gauss(ag, y, 2, 2)
        check("GAUSS x=1", 1.0, round(x[0], 6))
        check("GAUSS y=2", 2.0, round(x[1], 6))


class TestRodiaBeam:
    def test_rodia_beam_1000(self):
        _, rd, sv = rodia_beam(1000, pi, 460)
        check("RODDIA_beam AS=1000 RD=16", 16, rd)
        check("RODDIA_beam AS=1000 SV=173", 173, round(sv, 0))

    def test_rodia_beam_2429(self):
        _, rd, sv = rodia_beam(2429, pi, 460)
        assert rd > 0
        assert sv > 0


class TestShearLinks:
    def test_shear_links_ok(self):
        sv, heck = shear_links(337.5, 1473, 460, 25, 300, 500)
        assert heck == 1
        assert sv > 0


class TestDeflectBeam:
    def test_deflect_beam(self):
        di, fact, heck = deflect_beam(0, 2, 1000, 250, 1473, 1473, 460, 100, 5, 20)
        assert heck == 1
        assert di > 0

    def test_sr_argument_is_honored(self):
        # Book DEFLEC: DI = SPAN / (SR * FACT) * 1000.
        # Lower SR (cantilever = 7) must demand a deeper section than SR 20/26.
        # Regression: the sr argument used to be ignored (sr_base from nn).
        args = dict(b=1000, d=250, asb=1473, as_req=1473, fy=460, m=100, span=5)
        di7, _, _ = deflect_beam(0, 1, sr=7.0, **args)
        di20, _, _ = deflect_beam(0, 2, sr=20.0, **args)
        di26, _, _ = deflect_beam(0, 3, sr=26.0, **args)
        assert di7 > di20 > di26
        # Exact book formula with FACT capped at 2.0:
        # FS = 0.667*460 = 306.82; FACT = 0.55 + (477 - 306.82)/120*(0.9+...) > 2 -> 2.0
        assert di7 == 5000.0 / (7.0 * 2.0)
        assert di26 == 5000.0 / (26.0 * 2.0)

    def test_same_sr_same_result_regardless_of_nn(self):
        # nn only labels the panel type in the book; it must not change the ratio.
        di_a, _, _ = deflect_beam(0, 0, 1000, 250, 1473, 1473, 460, 100, 5, 20)
        di_b, _, _ = deflect_beam(0, 3, 1000, 250, 1473, 1473, 460, 100, 5, 20)
        assert di_a == di_b
        assert di_a == 5000.0 / (20.0 * 2.0)


# ============================================================
# 2. CONTINUOUS BEAM (Clapeyron)
# ============================================================

class TestContinuousBeam:
    def test_2_span_udl(self):
        cba = ContinuousBeamAnalyzer()
        beam = ContinuousBeamInput(
            n_supports=3, n_members=2, end1_type=0, end2_type=0,
            members=[
                ContinuousBeamMember(member_id="S1", length=6, udl=45, inertia=1, e_mod=1),
                ContinuousBeamMember(member_id="S2", length=6, udl=45, inertia=1, e_mod=1),
            ]
        )
        r = cba.analyze(beam)
        check("CBM 2-span UDL center support M", 202.5, round(r.support_moments[1], 1))
        check("CBM 2-span UDL span M (wL²/16)", 101.25, round(r.span_moments[0], 2))
        check("CBM 2-span UDL R_left (3wL/8)", 101.25, round(r.support_reactions[0], 2))
        check("CBM 2-span UDL R_center (10wL/8)", 337.5, round(r.support_reactions[1], 2))
        check("CBM 2-span UDL R_right (3wL/8)", 101.25, round(r.support_reactions[2], 2))

    def test_1_span_udl(self):
        cba = ContinuousBeamAnalyzer()
        beam = ContinuousBeamInput(
            n_supports=2, n_members=1, end1_type=0, end2_type=0,
            members=[
                ContinuousBeamMember(member_id="S1", length=6, udl=45, inertia=1, e_mod=1),
            ]
        )
        r = cba.analyze(beam)
        check("CBM 1-span UDL end M=0", 0.0, round(r.support_moments[0], 1))
        check("CBM 1-span UDL span M = wL²/8", 202.5, round(r.span_moments[0], 1))

    def test_3_span_udl(self):
        cba = ContinuousBeamAnalyzer()
        beam = ContinuousBeamInput(
            n_supports=4, n_members=3, end1_type=0, end2_type=0,
            members=[
                ContinuousBeamMember(member_id="S1", length=6, udl=30, inertia=1, e_mod=1),
                ContinuousBeamMember(member_id="S2", length=6, udl=30, inertia=1, e_mod=1),
                ContinuousBeamMember(member_id="S3", length=6, udl=30, inertia=1, e_mod=1),
            ]
        )
        r = cba.analyze(beam)
        check("CBM 3-span UDL M support 1", 108.0, round(r.support_moments[1], 1))
        check("CBM 3-span UDL M support 2", 108.0, round(r.support_moments[2], 1))


# ============================================================
# 3. COLUMN DESIGN
# ============================================================

class TestColumn:
    def test_axial_2000kN(self):
        cd = ColumnDesigner(fcu=25, fy=460, max_steel_pct=4.0, dh_ratio=0.85)
        c = ColumnInput(column_id="C1", col_type=1, shape=1, load=2000, bx=300, by=300)
        r = cd.design([c])[0]
        check("AXIAL 300x300 2000kN AST", 3871, round(r.steel_required, 0))
        assert r.heck == 1
        check("AXIAL 300x300 2000kN steel%", 4.3, round(r.steel_percent, 1))

    def test_axial_1000kN(self):
        cd = ColumnDesigner(fcu=25, fy=460, max_steel_pct=4.0, dh_ratio=0.85)
        c = ColumnInput(column_id="C2", col_type=1, shape=1, load=1000, bx=300, by=300)
        r = cd.design([c])[0]
        check("AXIAL 300x300 1000kN AST", 678, round(r.steel_required, 0))

    def test_axial_minimum_steel(self):
        cd = ColumnDesigner(fcu=25, fy=460, max_steel_pct=4.0, dh_ratio=0.85)
        c = ColumnInput(column_id="C3", col_type=1, shape=1, load=100, bx=300, by=300)
        r = cd.design([c])[0]
        check("AXIAL 300x300 100kN AST=amin", 360, round(r.steel_required, 0))
        check("AXIAL 300x300 100kN steel %", 0.4, round(r.steel_percent, 1))

    def test_uniaxial(self):
        cd = ColumnDesigner(fcu=25, fy=460, max_steel_pct=4.0, dh_ratio=0.85)
        c = ColumnInput(column_id="C4", col_type=2, shape=1, load=1000, bx=300, by=300,
                        depth=300, moment=50)
        r = cd.design([c])[0]
        assert r.steel_required > 0
        assert r.axial_capacity > 0
        assert r.moment_capacity_x > 0

    def test_uniaxial_minimum_steel(self):
        cd = ColumnDesigner(fcu=25, fy=460, max_steel_pct=4.0, dh_ratio=0.85)
        c = ColumnInput(column_id="C5", col_type=2, shape=1, load=100, bx=300, by=300,
                        depth=300)
        r = cd.design([c])[0]
        check("UNIAXIAL 300x300 P=100 M=0 → minimum steel", 360, round(r.steel_required, 0))


# ============================================================
# 4. BASE (FOUNDATION) DESIGN
# ============================================================

class TestBase:
    def test_isolated_2000kN(self):
        bd = BaseDesigner(pb=150, fcu=25, fy=460)
        br = bd.design([BaseInput(base_id="F1", base_type=1, col_type=1,
                                  load=2000, a1=300, a2=300, h=300)])[0]
        check("BASE 2000kN: depth convergence h", 650, round(br.h, 0))
        check("BASE 2000kN: steel area", 815, round(br.as1, 0))
        assert br.shear_stress <= br.perm_shear
        assert br.punching_shear <= br.perm_shear
        assert br.local_bond <= br.perm_bond

    def test_isolated_1000kN(self):
        bd = BaseDesigner(pb=150, fcu=25, fy=460)
        br = bd.design([BaseInput(base_id="F2", base_type=1, col_type=1,
                                  load=1000, a1=300, a2=300, h=300)])[0]
        check("BASE 1000kN: depth convergence h", 450, round(br.h, 0))
        assert br.shear_stress <= br.perm_shear
        assert br.punching_shear <= br.perm_shear

    def test_rect_column(self):
        bd = BaseDesigner(pb=150, fcu=25, fy=460)
        br = bd.design([BaseInput(base_id="F3", base_type=1, col_type=1,
                                  load=2000, a1=400, a2=600, h=300)])[0]
        assert br.shear_stress <= br.perm_shear
        assert br.punching_shear <= br.perm_shear

    def test_circular_column(self):
        bd = BaseDesigner(pb=150, fcu=25, fy=460)
        br = bd.design([BaseInput(base_id="F4", base_type=1, col_type=2,
                                  load=2000, dia=400, h=300)])[0]
        assert br.shear_stress <= br.perm_shear
        assert br.punching_shear <= br.perm_shear


# ============================================================
# 5. BEAM DESIGN
# ============================================================

class TestBeam:
    def test_simple_beam(self):
        bd_beam = BeamDesigner(fcu=25, fy=460, fyv=460)
        bi = BeamInput(
            beam_id="B1", n_members=1, n_supports=2,
            b=300, bf=300, h=600, hf=0,
            fcu=25, fy=460, fyv=460,
            member_lengths=[6.0], member_udl=[45.0],
            ty1=0, ty2=0,
        )
        r = bd_beam.design([bi])[0]
        check("BEAM simple 6m UDL=45 M", 202.5, round(r.spans[0].moment, 1))

    def test_2_span_continuous(self):
        bd_beam = BeamDesigner(fcu=25, fy=460, fyv=460)
        bi = BeamInput(
            beam_id="B2", n_members=2, n_supports=3,
            b=300, bf=300, h=600, hf=0,
            fcu=25, fy=460, fyv=460,
            member_lengths=[6.0, 6.0], member_udl=[45.0, 45.0],
            ty1=0, ty2=0,
        )
        r = bd_beam.design([bi])[0]
        check("BEAM 2-span center support M", 202.5, round(r.supports[1].moment, 1))
        check("BEAM 2-span span1 M", 101.25, round(r.spans[0].moment, 2))
        check("BEAM 2-span span2 M", 101.25, round(r.spans[1].moment, 2))

    def test_cantilever_load_adds_to_reaction(self):
        # Book: REACTN(I) += CANTW(I) at the end supports.
        bd_beam = BeamDesigner(fcu=25, fy=460, fyv=460)
        bi = BeamInput(
            beam_id="B3", n_members=1, n_supports=2,
            b=300, bf=300, h=600, hf=0,
            fcu=25, fy=460, fyv=460,
            member_lengths=[6.0], member_udl=[45.0],
            ty1=0, ty2=0,
            cant_load_1=50.0, cant_load_2=0.0,
        )
        r = bd_beam.design([bi])[0]
        # Without cantilever: 135 kN each end. Left reaction must be 185.
        check("BEAM cantilever load R_left", 185.0, round(r.supports[0].reaction, 1))
        check("BEAM cantilever load R_right", 135.0, round(r.supports[1].reaction, 1))

    def test_cantilever_moment_adds_to_end_support_moment(self):
        # Book: CMT1 applies at the end support (fixed-end boundary moment).
        bd_beam = BeamDesigner(fcu=25, fy=460, fyv=460)
        bi = BeamInput(
            beam_id="B4", n_members=1, n_supports=2,
            b=300, bf=300, h=600, hf=0,
            fcu=25, fy=460, fyv=460,
            member_lengths=[6.0], member_udl=[45.0],
            ty1=0, ty2=0,
            cant_moment_1=40.0, cant_moment_2=0.0,
        )
        r = bd_beam.design([bi])[0]
        # End support moment must include the cantilever moment.
        check("BEAM cantilever moment M_left", 40.0, round(r.supports[0].moment, 1))
        # Span moment shifts down by CMT/2 (chord effect): 202.5 - 20 = 182.5
        check("BEAM cantilever moment span M", 182.5, round(r.spans[0].moment, 1))

    def test_cantilever_load_designs_end_span_links(self):
        # Book: VC = CLD1 for the cantilever end shear check.
        bd_beam = BeamDesigner(fcu=25, fy=460, fyv=460)
        bi = BeamInput(
            beam_id="B5", n_members=1, n_supports=2,
            b=300, bf=300, h=600, hf=0,
            fcu=25, fy=460, fyv=460,
            member_lengths=[6.0], member_udl=[45.0],
            ty1=0, ty2=0,
            cant_load_1=500.0,  # far exceeds span shear - links must handle it
        )
        r = bd_beam.design([bi])[0]
        # Link spacing at the cantilever end must be tighter than at the far end
        # (larger shear -> smaller spacing), and finite.
        assert 0 < r.spans[0].sv_left < r.spans[0].sv_right


# ============================================================
# 6. SLAB DESIGN
# ============================================================

class TestSlab:
    def test_simply_supported(self):
        sd = SlabDesigner(fcu=25, fy=460)
        p = SlabPanelInput(panel_id="S1", panel_type=2, depth=175, fcu=25, fy=460,
                           udl=12, span=5)
        r = sd.design([p])[0]
        check("SLAB simply supported M=37.5", 37.5, round(r.moment_span, 1))

    def test_two_way(self):
        sd = SlabDesigner(fcu=25, fy=460)
        p = SlabPanelInput(panel_id="S2", panel_type=4, depth=175, fcu=25, fy=460,
                           udl=12, span=4, ly=5, case=1)
        r = sd.design([p])[0]
        assert r.moment_span > 0
        assert r.moment_long_span > 0

    def test_cantilever(self):
        sd = SlabDesigner(fcu=25, fy=460)
        p = SlabPanelInput(panel_id="S3", panel_type=1, depth=175, fcu=25, fy=460,
                           udl=15, span=1.5)
        r = sd.design([p])[0]
        check("SLAB cantilever M=16.875", 16.875, round(r.moment_span, 3))

    def test_cantilever_point_load(self):
        # Book CANTI: MC = U.L^2/2 + sum(PL.APC); V = U.L + sum(PL)
        sd = SlabDesigner(fcu=25, fy=460)
        p = SlabPanelInput(panel_id="S1", panel_type=1, depth=175, fcu=25, fy=460,
                           udl=15, span=1.5, npl=1,
                           point_loads=[(20.0, 0.75)])
        r = sd.design([p])[0]
        check("SLAB cantilever PL M=31.875", 31.875, round(r.moment_span, 3))
        check("SLAB cantilever PL V=42.5", 42.5, round(r.shear_left, 1))

    def test_simply_supported_point_load(self):
        # Point load adds PL.d.(L-d)/L to the mid moment and reactions
        sd = SlabDesigner(fcu=25, fy=460)
        p = SlabPanelInput(panel_id="S1", panel_type=2, depth=175, fcu=25, fy=460,
                           udl=12, span=5, npl=1,
                           point_loads=[(20.0, 2.0)])
        r = sd.design([p])[0]
        # 37.5 (UDL) + 20*2*3/5 = 24 -> 61.5
        check("SLAB simply PL M=61.5", 61.5, round(r.moment_span, 1))
        # Left reaction: 30 (UDL) + 20*3/5 = 12 -> 42
        check("SLAB simply PL V_left=42", 42.0, round(r.shear_left, 1))

    def test_continuous_cantilever_terms(self):
        # Book CONTI: RCT(1) += CTL(1); MTC(1) += CTM(1)
        sd = SlabDesigner(fcu=25, fy=460)
        p = SlabPanelInput(
            panel_id="S1", panel_type=3, depth=175, fcu=25, fy=460,
            nspan=2, span_lengths=[4.0, 4.0], span_udls=[12.0, 12.0],
            cant_loads=[10.0, 0.0], cant_moments=[5.0, 0.0],
        )
        r = sd.design([p])[0]
        # End span f = 48: rct[0] = 24 + 10 = 34; mtc[0] = -48*4/9 + 5 = -16.333
        check("SLAB cont cant rct0=34", 34.0, round(r.support_reactions[0], 1))
        check("SLAB cont cant mtc0=-16.333", -16.333, round(r.support_moments[0], 3))

    def test_continuous_point_load_in_span(self):
        # Book CONTI: F = W.L + sum(PLC); MSC = F.L/9 for end spans
        sd = SlabDesigner(fcu=25, fy=460)
        p = SlabPanelInput(
            panel_id="S1", panel_type=3, depth=175, fcu=25, fy=460,
            nspan=2, span_lengths=[4.0, 4.0], span_udls=[12.0, 12.0],
            span_npls=[1, 0], span_pls=[[(20.0, 2.0)], []],
        )
        r = sd.design([p])[0]
        # f0 = 48 + 20 = 68 -> 68*4/9 = 30.222
        check("SLAB cont PL span M=30.222", 30.222, round(r.span_moments[0], 3))
        check("SLAB cont PL span2 M=21.333", 21.333, round(r.span_moments[1], 3))

    def test_twoway_span_depth_ratio_honored(self):
        # Lower SR (10) must demand a deeper section than SR 30
        sd = SlabDesigner(fcu=25, fy=460)
        plo = SlabPanelInput(panel_id="S1", panel_type=4, depth=150, fcu=25, fy=460,
                             udl=12, span=4, ly=5, case=1, span_depth_ratio=10.0)
        phi = SlabPanelInput(panel_id="S2", panel_type=4, depth=150, fcu=25, fy=460,
                             udl=12, span=4, ly=5, case=1, span_depth_ratio=30.0)
        rlo = sd.design([plo])[0]
        rhi = sd.design([phi])[0]
        assert rlo.depth > rhi.depth
        assert rhi.defl_ok


# ============================================================
# 7. STAIR DESIGN
# ============================================================

class TestStair:
    def test_straight_flight(self):
        std = StairDesigner(fcu=25, fy=460)
        p = StairInput(stair_id="ST1", span=3.5, tread=250, rise=150,
                       imposed_load=3.0)
        r = std.design([p])[0]
        assert r.waist_thickness > 0
        assert r.design_moment > 0
        assert r.steel_required > 0


# ============================================================
# 8. MATERIALS
# ============================================================

class TestMaterials:
    def test_concrete_design_stress(self):
        c = Concrete(fcu=25)
        assert c.design_stress == 0.45 * 25

    def test_steel_design_stress(self):
        s = Steel(fy=460)
        assert s.fy_design == 0.95 * 460

    def test_concrete_shear_capacity(self):
        c = Concrete(fcu=25)
        vc = c.shear_stress_capacity(d=500, asym=1473, b=300)
        assert vc > 0

    def test_steel_bar_type(self):
        s_250 = Steel(fy=250)
        s_460 = Steel(fy=460)
        assert s_250.bar_type() == "R"
        assert s_460.bar_type() == "Y"

    def test_steel_ultimate_bond(self):
        s = Steel(fy=460)
        assert s.ultimate_bond_stress(25) == 2.5
        assert s.ultimate_bond_stress(20) == 2.1
