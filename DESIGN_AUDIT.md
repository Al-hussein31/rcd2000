# RCD2000 Design Audit vs Oyenuga Book (FORTRAN Source)

Audit date: 2026-08-08. Ground truth: original FORTRAN programs in `references/`.
Scope: for every design module, compare (a) book inputs vs GUI inputs vs engine dataclass fields, and (b) calculation formulas vs the f77 subroutines.

Legend: [OK] verified correct. [GAP] input the book accepts that the app cannot collect. [DEAD] field declared but never used by the engine. [BUG] calculation deviation found.

---

## 1. BEAM (book pp. 207-215; `beam_main.f77`, `beam_subs.f77`)

### Inputs
| Book reads | App GUI collects | Engine field | Status |
|---|---|---|---|
| B, BF, H, HF | yes | b, bf, h, hf | [OK] |
| TY1 / TY2 (end types) | yes | ty1, ty2 | [OK] |
| CLD1, CMT1 (left cantilever load + moment) | NO | cant_load_1, cant_moment_1 | [GAP] + [DEAD] |
| CLD2, CMT2 (right cantilever load + moment) | NO | cant_load_2, cant_moment_2 | [GAP] + [DEAD] |
| per member: M, L, UD, WT, WB, AB | yes | member_id, length, udl, wt, wb, ab | [OK] |
| per member: NPL (no. point loads), P, AP | NO | member_npl, member_pl | [GAP] |
| support grid numbers NDD | NO | support_grid | [GAP] |

### Calculation checks (`beam_subs.f77` vs `utils.py` / `beam.py`)
- [OK] STEELB: amin 0.13/0.25, amax 0.04.b.h, K cap 0.156, z = 0.95d, compression path (z = 0.77688d, x = (d - z)/0.45, asb, ast), 0.95.fy design stress.
- [OK] SHEAR: vc = 0.63(100As/bd)^(1/3)(400/d)^(1/4) (book 0.63 vs app 0.632: cosmetic), 0.5vc / vc+0.40 bands, sv = 0.75d / 0.95.fy.157/(0.4b) / 157.0.95.fy/(b(vv-vc)), 157mm2 = 2-leg T8 assumed.
- [OK] RODDIA bar ladder: 905/1610/2510/3930 thresholds, incl. the odd spacing formula (faithful port of the book quirk).
- [GAP] H < 75 -> H = 75 clamp exists in the book (`beam_main.f77`) but is NOT enforced by the app (app only validates h >= b + 100).

### Verdict
Engine analysis uses the Clapeyron three-moment matrix (verified earlier) but the two end-cantilever fields are declared and never read: `cant_load_1/2` and `cant_moment_1/2` appear ONLY in the dataclass. The book feeds CLD1/CMT1/CLD2/CMT2 into the fixed-end moments of the end spans. So beams with end cantilevers design with zero overhang moment: engine-level gap, unreachable via GUI anyway (GUI has no fields).

---

## 2. CONTINUOUS BEAM (book pp. 89-93; `continuous_beam.f77`)

### Inputs
| Book reads | App GUI collects | Engine field | Status |
|---|---|---|---|
| NS, NM | yes | n_supports, n_members | [OK] |
| per end: TY, CANTW, CANTMT | NO (GUI has end1/end2 type only) | end1_cant_load, end1_cant_moment, end2_... | [GAP] |
| per member: M, N1, N2, L, IV, E | length, inertia, e_mod only; N1/N2 not collected | member_id, start_node, end_node, length, inertia, e_mod | [GAP] node connectivity |
| UD, WT, WB, AB | yes | udl, wt, wb, ab | [OK] |
| NPL, P (point loads) | NO | point_loads | [GAP] engine supports (paf) but GUI never collects |

### Calculation checks
- [OK] Three-moment assembly verified: ag matrix 2L/EI, w-bar terms, mt from w-bar + point-load terms.
- [OK] end1_cant_load / end2_cant_load ARE applied to reactions (reactn[0] += ..., reactn[ns-1] += ...).
- [BUG] end1_cant_moment / end2_cant_moment are DEAD: declared, never added to the support moment (mt[0] / mt[ns-1]). The book's CANTMT feeds the moment-distribution end moment. Partial port.

### Verdict
Cantilever LOADS reach the reactions, but cantilever MOMENTS never influence the design moment; point loads supported by the engine but the GUI offers no entry.

---

## 3. SLAB (book pp. 144-150; `slab_main.f77`, `slab_subs.f77`)

### Inputs
| Panel type | Book reads | App GUI | Status |
|---|---|---|---|
| Cantilever | LCAN, UDL, H, NPL, PL/A | depth, span, gk/qk | [GAP] point loads missing |
| Simply supported | LSS, UDL, H, NPL, PL/A | depth, span, gk/qk | [GAP] point loads missing |
| Continuous | NSPAN, H, CANTMT(1), CANTLD(1), CANTMT(2), CANTLD(2); per span LCON, UDLC, NPLC, PLC/ALC | nspan, per-span length+udl | [GAP] end cantilever moment/load and per-span point loads missing |
| Two-way | LX, LY, UDL, H, SD (span/depth), CASE 1-9 | depth, span, ly, case, gk/qk | [GAP] SD not exposed (engine default 20) |

### Calculation checks (`slab_subs.f77` vs `slab.py`)
- [OK] CANTI: MC = U.L^2/2 + sum(PL.APC); V = U.L + sum(PL).
- [OK] SIMPLY: M = W.L^2/8, V = W.L/2 (span/depth 20).
- [OK] CONTI: edge spans F.L/9 and -F.L/9, interior F.L/16 / -F.L/12, end reaction additions CTL(1)/CTL(NS), end moment additions CTM(1)/CTM(NS); steel at every support + span. (App engine implements these; GUI cannot supply the cant terms.)
- [OK] TWOWAY coefficients: DG, DL, DS, DT data arrays (9 cases) and the K polynomial fits match the book exactly (D/25, D/35 factors, case-dependent exponents).
- [BUG] DEFLEC port: the book computes DI = SPAN / (SR * FACT) * 1000 using the SR THAT WAS PASSED IN (cantilever 7, simply 20, continuous 26, two-way 20). The app's `deflect_beam` IGNORES the `sr` argument and derives `sr_base` from the `nn` argument (26 unless nn < 1 -> 20):
  - Cantilever slab: passes sr = 7 but uses 26 -> required depth is ~3.7x too small. Deflection check far too lenient.
  - Simply supported slab: sr = 20 ignored -> uses 26 -> too lenient.
  - Two-way: sr = 20 ignored -> uses 26 -> too lenient.
  - Continuous: 26 == 26, correct by accident.
  - Beams: single span nn = min(nm-1, 1) = 0 -> 20 (correct); multi-span nn = 1 -> 26 (correct). Beams are right only because the caller happens to pass nn matching the ratio.
- [OK] STEEL subroutine: amin 0.13%, h = d + 25, z cap, K > 0.156 compression path identical to book.

### Verdict
Moment/shear/steel math is a faithful port; the deflection subroutine has a real parameter bug that weakens the check for cantilever, simply supported and two-way slabs.

---

## 4. STAIR (book pp. 173-177; `stair.f77`)

### Inputs
| Book reads | App GUI | Status |
|---|---|---|
| LST (span), TR (tread), RS (rise), LLD (imposed) | span, tread, rise, imposed | [OK] |
| SPLD (superimposed dead) | spl | [OK] |
| WLD (weight density) | wld | [OK] (book reads it too but never uses it) |

### Calculation checks
- [OK] WAIST = span/20 (min 0.100 clamp), SWS = 25.h.sqrt(t^2 + r^2)/t, STS = 0.5.rise.25, FIN = 1.0 fixed finishes, GKS = SWS + STS + FIN + SPLD, UDL = 1.4Gk + 1.6Qk, M = w.L^2/8, d = 175 - 20 - 8 = 147, K, z-factor, As = M/(0.87.fy.z). All verified line-by-line.
- [OK] WLD quirk faithfully preserved: field exists, never used in either program.

### Verdict
Only module that is a complete, faithful port on both inputs and calculations.

---

## 5. COLUMN (book pp. 242-246; `column.f77`)

### Inputs
| Book reads | App GUI | Engine field | Status |
|---|---|---|---|
| TY (1 axial / 2 uniaxial / 3 biaxial), CS (1 rect / 2 circ) | yes | column_type, shape | [OK] |
| CID, W, BX, BY, H | yes | load, bx, by, depth (dia for circ) | [OK] |
| L (height), LE, LEX, LEY (effective lengths) | NO | length, le, lex, ley | [GAP] declared, never set by GUI, never used by engine (no slenderness check at all) |
| M (uniaxial), MX, MY | yes | moment_x, moment_y | [OK] |
| global PS (max steel %), DH (d/h ratio) from job header | header dialog collects max_steel_pct + dh | - | [BUG] header fields are NEVER applied: page builds ColumnDesigner(fcu=fcu, fy=fy) only, so the book's global steel/depth ratio inputs do nothing |
| circular: DIA, L, W (+MIX/MIY) | dia, load (+moments) | dia | [OK] |

### Calculation checks (`column.f77` vs `column.py`)
- [OK] AXIAL: AG = PI.DIA^2/4 for circular, steel min 0.004/0.8%, AST = 0.4% default, brace bars 25% rule, 0.45fcu + 0.75fy/0.95fy formula per book.
- [OK] UNIAX interaction curve: KI = 0.4.fcu, K2 = 0.45, XH 0.2 -> 1.0 (9 steps), NN = PS/0.1 steel steps, strains ESC = (1 - 0.1/XH).0.0035 and ES = (0.9/XH - 1).0.0035, NU = KI.XH + FSC.AT - FS.AT, MU formulas with DH terms, search loop over the (I, J) table. Verified identical to the f77 subroutine.
- [WARN] For circular columns the app must use depth == dia; GUI has separate depth/dia fields. Engine relies on the caller: `_axial` uses `h = depth` for the area when non-circular... confirm page passes depth = dia for circular. (Engine `_circular_area` path uses dia.) Flag: enforce depth == dia on the page when shape = Circular.

### Verdict
Interaction-curve math is exact. The notable gaps: effective lengths never collected (so no slenderness handling, though the book's own program also reads but largely ignores LE/LEX/LEY for design), and the job-header max steel % + D/H ratio are collected in the header dialog but never reach the designer.

---

## 6. BASE (book pp. 315-318; `base.f77`)

### Inputs
| Book reads | App GUI | Engine field | Status |
|---|---|---|---|
| NB, PB (soil bearing), FCU, FY | soil pressure, fcu, fy | pb, fcu, fy | [OK] |
| BN, TY (1 square / 2 rect / 3 combined) | type combo incl. Combined | - | [GAP] |
| isolated rect: CT, W, A1, A2, DW (dowel dia) | col shape, load, a1, a2, dowel | dowel_dia | [GAP] + [DEAD] dowel never used by engine |
| isolated circ: W, DIA, DW | load, dia, dowel | dia, dowel_dia | [GAP] + [DEAD] |
| combined: NC, CTC per column, per col (rect) WC, AC, ACI, AC2, DWC / (circ) WC, AC, DIAC, DWC | NO UI AT ALL | n_columns, columns | [GAP] selecting "Combined" in the GUI yields empty/zero results |

### Calculation checks
- [WARN] `references/base.f77` contains only the I/O wrapper and print formats: the footing calculation section is NOT in the repository's f77 set, so the base math cannot be verified against the book directly. Constants used by the app (AR = W.1.1/(1.47.pb), fnet = W.1.1/A - h.24.1.4/1000, p = W*1.1/A, pu = 1.4/1.6 combination) need the book pages 315+ to confirm the 1.1 and 1.47 factors.
- [BUG] Combined-footing overhang units: `ohl = l1/2 - cols[0].dist/1000.0` and `ohr = l1/2 - (l1 - cols[-1].dist/1000.0)` divide dist by 1000, but BaseColumn.dist is documented in METRES. With dist in m the overhangs collapse to ~l1/2 regardless of layout.
- [BUG] Combined-footing centering: `l1 = max(l1_needed, x_last * 2.0)` centers on the LAST column, not on the load resultant (xbar = mwc/twc), so unequal column loads produce an eccentric base with non-uniform pressure. The book centers the base on the resultant.
- [WARN] dowel_dia collected by GUI and declared in BaseInput but never referenced in `_design_isolated` or `_design_combined`.

### Verdict
Isolated square/rect path is usable, but combined footings are unreachable from the GUI, and the engine's combined path has unit and centering bugs. Dowel diameter is a dead input.

---

## 7. GLOBAL / MATERIALS (`utility_subs.f77` vs `materials.py`)
- [OK] PERMLB bond table FY > 250: 2.1 / 2.5 / 2.8 / 3.4 matches exactly.
- [OK] FY <= 250 branch (1.70 / 2.0 / 2.2 / 2.7) is a sensible extension not present in the book (book only covers FY > 250) - no conflict.
- [OK] PERMS shear matches the SHEAR subroutine.
- [OK] Job header fcu/fy/fyv/soil pressure ARE applied to the pages (form_page apply_header_defaults).
- [BUG] Job header max_steel_pct + dh collected but never wired to the column designer (see section 5).

---

## PRIORITY FIX LIST
1. [BUG] `deflect_beam` ignores its `sr` argument (slab deflection far too lenient for cantilever / simply supported / two-way). Fix: use the passed `sr` as the book does; keep `nn` only for the interactive steel-increase flag.
2. [BUG] Job header Max steel % and D/H ratio are dead: wire them into ColumnDesigner (max_steel_pct, dh_ratio) on the column page.
3. [GAP] Beam: add point-load and end-cantilever (load + moment) inputs to the beam page; make the engine actually use cant_load_1/2 and cant_moment_1/2 in the fixed-end moments.
4. [GAP] Slab: add point-load entry (cantilever/simply), end cantilever moment/load + per-span point loads (continuous), and expose SD for two-way.
5. [GAP] Continuous beam: add point loads + end cantilever load/moment inputs; engine must add end1/end2_cant_moment to mt[0]/mt[ns-1].
6. [BUG] Base combined path: fix dist unit handling (drop /1000) and center l1 on the load resultant; add combined-footing column entry to the GUI or disable the option.
7. [DEAD] dowel_dia: implement the dowel check or drop the input.
8. [GAP] Column: enforce depth == dia for circular; collect L / LE / LEX / LEY (even if only for reporting; book reads them).
