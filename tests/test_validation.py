"""Comprehensive validation: Python port vs FORTRAN source and known BS 8110 results."""

import math
import sys
sys.path.insert(0, 'src')

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
failures = []
passes = []

def check(name, expected, got, tol=0.01):
    if abs(expected - got) <= tol * max(1.0, abs(expected)):
        passes.append(f"  ✓ {name}: {got}")
    else:
        msg = f"  ✗ {name}: expected {expected}, got {got}"
        failures.append(msg)
        print(msg)

def check_rel(name, expected, got, tol_pct=1.0):
    """Check with relative tolerance in percent."""
    if expected == 0:
        if abs(got) <= tol_pct * 0.01:
            passes.append(f"  ✓ {name}: {got}")
            return
        msg = f"  ✗ {name}: expected {expected}, got {got}"
        failures.append(msg)
        print(msg)
        return
    pct = abs(got - expected) / abs(expected) * 100
    if pct <= tol_pct:
        passes.append(f"  ✓ {name}: {got}")
    else:
        msg = f"  ✗ {name}: expected {expected}, got {got} ({pct:.1f}% off)"
        failures.append(msg)
        print(msg)

print("=" * 60)
print("RCD2000 VALIDATION SUITE")
print("=" * 60)

# ============================================================
# 1. UTILITY FUNCTIONS
# ============================================================
print("\n--- 1. UTILITY FUNCTIONS ---")

# 1a. STEEL (steel_slab) — matches FORTRAN STEEL subroutine
# FORTRAN: STEEL(M=215.3, D=250, FCU=25, FY=460)
# K = 215.3e6/(25*1000*62500) = 0.1378
# LA = 0.5+sqrt(0.25-0.1378/0.9) = 0.5+0.338 = 0.838
# AST = 215.3e6/(0.95*460*0.838*250) = 2354 mm²
# C = 0.13, H = 275, AM = 0.13*1000*275/100 = 357.5
# AST = max(2354, 357.5) = 2354
ast, heck = steel_slab(215.3, 250, 25, 460)
check("STEEL M=215.3 d=250", 2429, round(ast, 0))
check("STEEL heck=1", 1, heck)

# 1b. STEEL with over-reinforced section
# K > 0.156 → heck=0
ast, heck = steel_slab(500, 250, 25, 460)
check("STEEL over-reinforced heck=0", 0, heck)

# 1c. STEEL with minimum steel
# Large d gives small steel needed, minimum governs
# For fy=460: c=0.13, h=425+25=450, amin=0.13*1000*450/100=585
ast, heck = steel_slab(50, 425, 25, 460)
check("STEEL minimum steel", 585, round(ast, 0))

# 1d. PERMS — matches FORTRAN PERMS subroutine
# FORTRAN: PERMS(HCV,RD=12,SV=150,PI,D=250)
# AS = PI*144/4*(1000/150) = 113.1*6.667 = 754 mm²/m
# AC = 754*100/(1000*250) = 0.302
# AC = 0.302^(1/3) = 0.671
# OC = max(400/250,1) = 1.6^0.25 = 1.125
# VC = 0.632*0.671*1.125 = 0.477
hcv, vc = perms(0, 12, 150, pi, 250)
check("PERMS vc with Y12@150, d=250", 0.477, round(vc, 3))

# Larger depth: d=500
# AS = same 754 mm²/m
# AC = 754*100/(1000*500) = 0.151
# AC^(1/3) = 0.532
# OC = max(400/500,1) = 1.0^0.25 = 1.0
# VC = 0.632*0.532*1.0 = 0.336
hcv, vc = perms(0, 12, 150, pi, 500)
check("PERMS vc with Y12@150, d=500", 0.336, round(vc, 3))

# 1e. PERMLB — matches FORTRAN PERMLB subroutine
# FORTRAN: PERMLB(VBL=300, RDT=12, SPT=150, PI, D=250, FY=460, FCU=25)
# RN = 1000/150 = 6.667
# FBS = 300*1000/(6.667*12*PI*250) = 300000/62832 = 4.775
# Too many bars. Let's use more realistic values.
# Actually, the bond stress here is based on VBL which is shear force per meter.
# VBL for base = (l1/2)*fnet. Let's use a simpler test.
# RN = number of bars = 1000/139 = 7.19
# FBS = 300*1000/(7.19*12*PI*600) = 300000/162,684 = 1.844
fbs, ubs = permlb(300, 12, 139, pi, 600, 460, 25)
check("PERMLB fbs=1.844", 1.844, round(fbs, 3))
check("PERMLB ubs FCU=25,FY=460 = 2.5", 2.5, ubs)

# Lower bond for FCU=20 with FY=460: ubs=2.1
fbs, ubs = permlb(300, 12, 139, pi, 600, 460, 20)
check("PERMLB ubs FCU=20,FY=460 = 2.1", 2.1, ubs)

# 1f. GAUSS — matches FORTRAN GAUSS subroutine
# Simple 2x2 system:
# 2x + 3y = 8
# 4x + 5y = 14
# Solution: x=1, y=2
ag = [[2.0, 3.0], [4.0, 5.0]]
y = [8.0, 14.0]
x = gauss(ag, y, 2, 2)
check("GAUSS x=1", 1.0, round(x[0], 6))
check("GAUSS y=2", 2.0, round(x[1], 6))

# 1g. RODIA_BEAM — matches FORTRAN RODDIA subroutine
# FORTRAN: RODDIA(AS=1000, PI=3.14159, FY=460)
# AS=1000 → between 905 and 1610 → RD=16
# AR = PI*256/4 = 201.06
# V = 1000/201.06 = 4.974
# V = 1000*4.974 = 4974
# N = INT(4974/25)-25 = 198-25 = 173... wait, INT(4974/25) = INT(198.96) = 198
# 198-25 = 173
# SV = 173 mm
t, rd, sv = rodia_beam(1000, pi, 460)
check("RODDIA_beam AS=1000 RD=16", 16, rd)
check("RODDIA_beam AS=1000 SV=173", 173, round(sv, 0))

# Wait, INT(198.96)-25 = 173? Let me recheck...
# Actually in FORTRAN: N = INT(V / 25.0) - 25
# V = 4974, V/25 = 198.96, INT = 198, 198-25 = 173
# So SV = 173. But that's only 173mm spacing? That actually seems reasonable.
# The RODDIA formulas produce a spacing based on N = INT(1000*AS/AR/25) - 25
# which seems to work out as: spacing = 25/(AS/AR) * 1000 ? 

# Actually I think the RODDIA subroutine might be buggy. Let's trace again:
# V = AS/AR = AST / (PI*RD^2/4) = number of bars per meter
# V = 1000.0 * V = ???
# This multiplies by 1000 which seems wrong.

# Actually no - V in the original FORTRAN was likely meant to be AS in cm²/m.
# If AS=10cm²/m (1000mm²/m), AR=PI*1.6²/4=2.01cm²:
# V = 10/2.01 = 4.97
# N = INT(4.97/25*1000)-25 = INT(198.8)-25 = 173
# Hmm that's the same result.

# Actually I think the FORTRAN is using a formula where:
# N = INT(V/25) where V is the spacing in mm, computed backwards
# V = AS/AR = bars/m
# To get spacing: SV = 1000/V 
# 1000/V = 1000/(AS/AR) = 1000*AR/AS
# So N = INT(1000*AR/AS/25) ??? This doesn't easily simplify.

# Let me just check what our beam rodia gives and verify it's reasonable.
t, rd, sv = rodia_beam(2429, pi, 460)  # from original column at h=300
print(f"    rodia_beam(2429) → Y{rd:.0f}@{sv:.0f}")

# 1h. SHEAR_LINKS
# V = 337.5 kN, b=300, d=500, fy=460, fcu=25
# v = 337.5*1000/(300*500) = 2.25 N/mm²
# vm = min(0.8*sqrt(25), 5) = 4.0
# With As=1473 (example):
sv, heck = shear_links(337.5, 1473, 460, 25, 300, 500)
check("SHEAR_LINKS heck OK", 1, heck)
print(f"    shear_links(337.5, 1473, 460, 25, 300, 500) → sv={sv:.0f}")

# 1i. DEFLECT_BEAM
# Basic test for simply supported beam
di, fact, heck = deflect_beam(0, 2, 1000, 250, 1473, 1473, 460, 100, 5, 20)
check("DEFLECT_BEAM heck", 1, heck)
print(f"    deflect_beam → d_req={di:.1f}mm, factor={fact:.3f}")

# ============================================================
# 2. CONTINUOUS BEAM (Clapeyron)
# ============================================================
print("\n--- 2. CONTINUOUS BEAM (Clapeyron) ---")

cba = ContinuousBeamAnalyzer()

# 2a. 2-span beam with UDL (wL²/8 at center support)
# 2 spans of 6m each, UDL=45 kN/m
# Theory: M_center = wL²/8 = 45*36/8 = 202.5 kN.m
# Reactions: R_left = 3wL/8 = 101.25 kN (end supports each)
# R_center = 10wL/8 = 337.5 kN
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

# 2b. Single span (simple beam confirmation)
beam = ContinuousBeamInput(
    n_supports=2, n_members=1, end1_type=0, end2_type=0,
    members=[
        ContinuousBeamMember(member_id="S1", length=6, udl=45, inertia=1, e_mod=1),
    ]
)
r = cba.analyze(beam)
check("CBM 1-span UDL end M=0", 0.0, round(r.support_moments[0], 1))
check("CBM 1-span UDL span M = wL²/8", 202.5, round(r.span_moments[0], 1))

# 2c. 3-span beam with UDL (verification)
# 3 spans of 6m each, UDL=30 kN/m
# Using Clapeyron: center supports should be symmetric
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
print("\n--- 3. COLUMN DESIGN ---")

cd = ColumnDesigner(fcu=25, fy=460, max_steel_pct=4.0, dh_ratio=0.85)

# 3a. Axial column
# 300x300 column, 2000 kN load
# FORTRAN AXIAL:
# AST = (2000*1000 - 0.35*25*90000)/(0.7*460 - 0.35*25)
# AST = (2000000 - 787500)/(322 - 8.75) = 1212500/313.25 = 3871 mm²
# AMIN = 0.4*90000/100 = 360
# AMAX = 4*90000/100 = 3600
# 3871 > 3600 → HECK = 1 (section inadequate!)
c = ColumnInput(column_id="C1", col_type=1, shape=1, load=2000, bx=300, by=300)
r = cd.design([c])[0]
# Large load → heck=1, AST=3871
check("AXIAL 300x300 2000kN AST", 3871, round(r.steel_required, 0))
check("AXIAL 300x300 2000kN heck=1 (section inadequate)", 1, r.heck)
check("AXIAL 300x300 2000kN steel%", 4.3, round(r.steel_percent, 1))

# 3b. Axial column with reasonable load
# 300x300 column, 1000 kN load
# AST = (1000000 - 787500)/313.25 = 212500/313.25 = 678 mm²
# AMIN = 360, AMAX = 3600
# 678 > 360 → OK
c = ColumnInput(column_id="C2", col_type=1, shape=1, load=1000, bx=300, by=300)
r = cd.design([c])[0]
check("AXIAL 300x300 1000kN AST", 678, round(r.steel_required, 0))

# Minimum steel case
c = ColumnInput(column_id="C3", col_type=1, shape=1, load=100, bx=300, by=300)
r = cd.design([c])[0]
check("AXIAL 300x300 100kN AST=amin", 360, round(r.steel_required, 0))
check("AXIAL 300x300 100kN steel %", 0.4, round(r.steel_percent, 1))

# 3c. Uniaxial column
# 300x300 column, 1000 kN, 50 kN.m moment
# Using Nu/Mu chart search
c = ColumnInput(column_id="C4", col_type=2, shape=1, load=1000, bx=300, by=300,
                depth=300, moment=50)
r = cd.design([c])[0]
print(f"    UNIAXIAL 300x300 P=1000 M=50 → Ast={r.steel_required:.0f} mm², "
      f"Nu={r.axial_capacity:.0f} kN, Mux={r.moment_capacity_x:.1f} kN.m, "
      f"heck={r.heck}")

# Small load + no moment → minimum steel
c = ColumnInput(column_id="C5", col_type=2, shape=1, load=100, bx=300, by=300,
                depth=300)
r = cd.design([c])[0]
check("UNIAXIAL 300x300 P=100 M=0 → minimum steel", 360, round(r.steel_required, 0))

print("\n--- 4. BASE (FOUNDATION) DESIGN ---")

bd = BaseDesigner(pb=150, fcu=25, fy=460)

# 4a. Square isolated base 2000kN on 300x300 column
br = bd.design([BaseInput(base_id="F1", base_type=1, col_type=1,
                           load=2000, a1=300, a2=300, h=300)])[0]
print(f"    Isolated base 2000kN: {br.l1:.0f}x{br.l2:.0f}x{br.h:.0f}mm")
print(f"    fnet={br.fnet:.2f} kN/m², As={br.as1:.0f} mm²/m Y{br.rd1:.0f}@{br.sp1:.0f}")
print(f"    shear={br.shear_stress:.3f}/{br.perm_shear:.3f}, "
      f"punch={br.punching_shear:.3f}, bond={br.local_bond:.2f}/{br.perm_bond:.2f}")
check("BASE 2000kN: depth convergence h", 650, round(br.h, 0))
check("BASE 2000kN: steel area", 815, round(br.as1, 0))
assert br.shear_stress <= br.perm_shear, f"Shear FAIL: {br.shear_stress} > {br.perm_shear}"
assert br.punching_shear <= br.perm_shear, f"Punch FAIL: {br.punching_shear} > {br.perm_shear}"
assert br.local_bond <= br.perm_bond, f"Bond FAIL: {br.local_bond} > {br.perm_bond}"
passes.append("  ✓ BASE 2000kN: all stress checks PASS")

# 4b. Square isolated base 1000kN
br = bd.design([BaseInput(base_id="F2", base_type=1, col_type=1,
                           load=1000, a1=300, a2=300, h=300)])[0]
print(f"    Isolated base 1000kN: {br.l1:.0f}x{br.l2:.0f}x{br.h:.0f}mm, "
      f"As={br.as1:.0f} Y{br.rd1:.0f}@{br.sp1:.0f}")
check("BASE 1000kN: depth convergence h", 450, round(br.h, 0))
assert br.shear_stress <= br.perm_shear
assert br.punching_shear <= br.perm_shear
passes.append("  ✓ BASE 1000kN: all stress checks PASS")

# 4c. Rectangular column on square base
br = bd.design([BaseInput(base_id="F3", base_type=1, col_type=1,
                           load=2000, a1=400, a2=600, h=300)])[0]
print(f"    Base, rect column 400x600, 2000kN: {br.l1:.0f}x{br.l2:.0f}x{br.h:.0f}mm, "
      f"As1={br.as1:.0f}@{br.sp1:.0f}, As2={br.as2:.0f}@{br.sp2:.0f}")
assert br.shear_stress <= br.perm_shear
assert br.punching_shear <= br.perm_shear
passes.append("  ✓ BASE rect column: all stress checks PASS")

# 4d. Circular column
br = bd.design([BaseInput(base_id="F4", base_type=1, col_type=2,
                           load=2000, dia=400, h=300)])[0]
print(f"    Base, circ column d=400, 2000kN: {br.l1:.0f}x{br.l2:.0f}x{br.h:.0f}mm, "
      f"As={br.as1:.0f} Y{br.rd1:.0f}@{br.sp1:.0f}")
assert br.shear_stress <= br.perm_shear
assert br.punching_shear <= br.perm_shear
passes.append("  ✓ BASE circular column: all stress checks PASS")

# ============================================================
# 5. BEAM DESIGN
# ============================================================
print("\n--- 5. BEAM DESIGN ---")

bd_beam = BeamDesigner(fcu=25, fy=460, fyv=460)

# 5a. Simple beam 6m span, UDL=45 kN/m (from book example)
# w=45 kN/m on 6m → M=202.5 kN.m, V=135 kN
# Section 300x600
# k=202.5e6/(25*300*550²)=0.089, la=0.5+sqrt(0.25-0.089/0.9)=0.889
# ast=202.5e6/(0.95*460*0.889*550)=948 mm²
# For pinned-pinned ends in our port: ty1=0, ty2=0
bi = BeamInput(
    beam_id="B1", n_members=1, n_supports=2,
    b=300, bf=300, h=600, hf=0,
    fcu=25, fy=460, fyv=460,
    member_lengths=[6.0], member_udl=[45.0],
    ty1=0, ty2=0,
)
r = bd_beam.design([bi])[0]
check("BEAM simple 6m UDL=45 M", 202.5, round(r.spans[0].moment, 1))

# 5b. 2-span continuous beam 6m+6m, UDL=45 kN/m
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

# ============================================================
# 6. SLAB DESIGN
# ============================================================
print("\n--- 6. SLAB DESIGN ---")

sd = SlabDesigner(fcu=25, fy=460)

# 6a. Simply supported slab
# 5m span, UDL=12 kN/m (typical office)
# M = wL²/8 = 12*25/8 = 37.5 kN.m/m
p = SlabPanelInput(panel_id="S1", panel_type=2, depth=175, fcu=25, fy=460,
                   udl=12, span=5)
r = sd.design([p])[0]
check("SLAB simply supported M=37.5", 37.5, round(r.moment_span, 1))
print(f"    Simply supported 5m, UDL=12 → M={r.moment_span:.1f}, "
      f"As={r.steel_span:.0f} Y{r.bar_dia:.0f}@{r.bar_spacing:.0f}")

# 6b. Two-way slab, case 1
# 5m x 4m, UDL=12, case=1
p = SlabPanelInput(panel_id="S2", panel_type=4, depth=175, fcu=25, fy=460,
                   udl=12, span=4, ly=5, case=1)
r = sd.design([p])[0]
print(f"    Two-way 5x4m case1: Ms={r.moment_span:.2f}, "
      f"Ml={r.moment_long_span:.2f}, Ms_sup={r.moment_support:.2f}")

# 6c. Cantilever slab
# 1.5m cantilever, UDL=15 kN/m
# M = wL²/2 = 15*2.25/2 = 16.875 kN.m/m
p = SlabPanelInput(panel_id="S3", panel_type=1, depth=175, fcu=25, fy=460,
                   udl=15, span=1.5)
r = sd.design([p])[0]
check("SLAB cantilever M=16.875", 16.875, round(r.moment_span, 3))
print(f"    Cantilever 1.5m, UDL=15 → M={r.moment_span:.1f}, "
      f"As={r.steel_span:.0f} Y{r.bar_dia:.0f}@{r.bar_spacing:.0f}")

# ============================================================
# 7. STAIR DESIGN
# ============================================================
print("\n--- 7. STAIR DESIGN ---")

std = StairDesigner(fcu=25, fy=460)

# 7a. Straight stair flight
# 3.5m span, 250mm tread, 150mm riser, LL=3.0 kN/m²
p = StairInput(stair_id="ST1", span=3.5, tread=250, rise=150,
               imposed_load=3.0)
r = std.design([p])[0]
print(f"    Stair 3.5m: waist={r.waist_thickness:.0f}mm, M={r.design_moment:.2f} kN.m, "
      f"As={r.steel_required:.0f} Y{r.bar_dia:.0f}@{r.bar_spacing:.0f}")

# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'='*60}")
print(f"VALIDATION SUMMARY")
print(f"{'='*60}")
print(f"PASSED: {len(passes)}")
print(f"FAILED: {len(failures)}")
if failures:
    print("\nFAILURES:")
    for f in failures:
        print(f)
else:
    print("\nAll checks passed! ✓")

sys.exit(1 if failures else 0)
