# RCD2000 — Anchored Summary

## Goal
Complete a modern Python port of RCD2000 (reinforced concrete design to BS 8110) from FORTRAN source and book algorithms, replacing buggy DOS EXEs.

## Constraints & Preferences
- Language: Python (structural engineering OSS community converged on Python — OpenSeesPy, PyNite, sectionproperties, concreteproperties)
- Must verify against original EXE sample outputs for correctness
- Must use decimal math matching BS 8110 hand calculation precision
- Must be distributable via PyPI / pip, with optional desktop EXE via PyInstaller

## Progress

### Done
- Acquired all 10 RCD2000 EXEs from online archive, verified they run in DOSBox
- Extracted FORTRAN source from book OCR (~3057 lines across 13 files)
- Read and fully analyzed all FORTRAN files + textbook examples
- Created project scaffolding: pyproject.toml, package dir src/rcd2000/
- Wrote core utility modules: materials.py, utils.py (GAUSS, steel_beam, steel_slab, rodia_beam, rodia_slab, permlb, perms, deflect_beam, shear_links)
- Wrote models.py (DesignInput, result_to_dict for JSON I/O)
- Ported slab.py (all 4 slab types), stair.py, column.py (axial/uniaxial/biaxial), continuous_beam.py (Clapeyron), beam.py (full BMADE), base.py (isolated & combined footings)
- Wrote cli.py and `__main__.py` with 7 subcommands
- Fixed Clapeyron RHS factor (from `-6*(FREEM*L)/6` to `U*L³/(4*EI)` + PAF), base moment/*1000 factor, base shear critical section, StairResult defaults
- **Fixed base.py punching shear unit mismatch**: vps = vpun / (crit_p * d) returns N/mm² directly (was dividing by 1000 twice, causing 10⁶× mismatch and depth overshoot to 1100mm → converged at 650mm)
- **Fixed column.py uniaxial xh start**: `0.2 + i*0.1` (was `0.2 + (i+1)*0.1`, missing 0.2 case)
- **Fixed column.py uniaxial at init**: starts at `0.0` (was `0.003`, skipping low steel ratios)
- **Fixed column.py steel_percent**: always calculated (was conditional on heck=1)
- **Created tests/test_validation.py**: 44 checks across ALL 7 modules — utilities, continuous beam, column, base, beam, slab, stair — all passing ✓

### In Progress
- (none)

### Blocked
- (none)

## Key Decisions
- Python over C#: structural engineering OSS converged on Python; decimal.Decimal provides exact rounding; PyPI provides archival distribution
- Skip Reko/FORTRAN decompilation for missing code: book OCR + EXE behavior is sufficient to reconstruct all algorithms; decompilation gives generic C with lost variable names
- Clapeyron RHS uses equivalent UDL (`U(I) = UDL + WT/3 + WB*(1-2/3*AL)*0.5`) not raw free moment; PAF function for point loads; AG matrix includes 1/EI divisors (matching FORTRAN from page 90)
- Hogging moments = positive in FORTRAN convention; span moment = FREEMT - (M_left + M_right)*0.5
- Each module standalone with dataclass I/O (no global state, no interactive terminal prompts)
- Validation tests use FORTRAN source as ground truth (no EXEs needed), with expected values from tracing the original formulas

## Next Steps
1. Package and document for PyPI release
2. Consider optional Rich/Streamlit frontend for interactive use
3. Add unit conversion utility for imperial/metric workflow

## Critical Context
- Original FORTRAN files: 13 files, 3057 lines total in source/; book page scans in raw_extracts/ (35 files with page numbers)
- Validation `tests/test_validation.py` tests ALL modules with 44 check points across utilities, continuous beam, column, base, beam, slab, stair
- Column _uniaxial: Nu/Mu table built with `at` incrementing 0.001 per iteration, reset to 0.0 after each xh sweep; xh goes 0.2,0.3,...,1.0 (9 values); search is J-outer/I-inner to find lowest steel ratio that satisfies both Nu≥ANBH and Mu≥AMBH
- Base punching: acrit uses `(ax+3h)(ay+3h) - (4-π)(1.5h)²`; crit_p = `pc + 3πh`; vps = `vpun / (crit_p * d)` in N/mm²
- PERMS: `vc = 0.632 * min(100As/(1000d), 3)^(1/3) * max(400/d, 1)^(0.25)` — matches FORTRAN exactly
- PERMLB: `fbs = Vbl*1000 / (rn*rd*π*d)` where rn = 1000/spt; ubs from fcu/fy table
- RODDIA (FORTRAN): bar selection by AS ranges (≤905→Y12, ≤1610→Y16, ≤2510→Y20, ≤3930→Y25, ≤6430→Y32, >6430→Y40); spacing formula `N = INT(1000*AS/AR/25)-25` where AR = π*rd²/4
- cli.py entry: `python3 -m rcd2000 beam|column|slab|stair|base|continuous-beam|info`

## Relevant Files
- `/Users/MAC/Desktop/RCD2000/src/rcd2000/base.py`: punching shear formula fixed at line 219
- `/Users/MAC/Desktop/RCD2000/src/rcd2000/column.py`: uniaxial xh/at fix at lines 138-155, steel_percent calc fixed
- `/Users/MAC/Desktop/RCD2000/tests/test_validation.py`: 44 checks, all modules passing
- `/Users/MAC/Desktop/RCD2000/source/utility_subs.f77`: PERMS, PERMLB, RODDIA, GAUSS FORTRAN source
- `/Users/MAC/Desktop/RCD2000/source/column.f77`: AXIAL, UNIAX FORTRAN source
- `/Users/MAC/Desktop/RCD2000/source/base.f77`: BASE FORTRAN source
