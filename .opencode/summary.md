# RCD2000 — Anchored Summary

## Goal
Complete a modern Python port of RCD2000 (reinforced concrete design to BS 8110) from FORTRAN source and book algorithms, replacing buggy DOS EXEs.

## Constraints & Preferences
- Language: Python (structural engineering OSS community converged on Python)
- Must verify against original FORTRAN source for correctness
- Must use math matching BS 8110 hand calculation precision
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
- Fixed Clapeyron RHS factor, base moment/*1000 factor, base shear critical section, StairResult defaults
- Fixed base.py punching shear unit mismatch, column.py uniaxial xh/at init, steel_percent calc
- Created `tests/test_validation.py`: 44 checks across ALL 7 modules
- **FORTRAN verification**: Compiled FORTRAN source with gfortran, compared column (axial/uniaxial) outputs — Python matches FORTRAN exactly (AXIAL: AST=678 ✓, UNIAX: ASC=540 ✓ for PS=6/DH=0.9)
- **Discovered latent FORTRAN bug**: Arrays `NU(10,50)`/`MU(10,50)` but loop goes to `NN=60` for PS=6% → out-of-bounds memory access in original EXE. Our Python port uses flat lists, avoiding this
- Pushed to GitHub: https://github.com/Al-hussein31/rcd2000

### In Progress
- (none)

### Blocked
- (none)

## Key Decisions
- Python over C#: structural engineering OSS converged on Python
- Skip Reko/FORTRAN decompilation: book OCR + EXE behavior sufficient to reconstruct all algorithms
- Clapeyron RHS uses equivalent UDL not raw free moment; AG matrix includes 1/EI divisors
- Hogging moments = positive in FORTRAN convention
- Each module standalone with dataclass I/O (no global state)
- Validation tests use FORTRAN source as ground truth

## Critical Context
- Original FORTRAN files: 13 files, 3057 lines total in source/
- Original FORTRAN has array dimension bug in UNIAX: NU(10,50) but loop goes to NN=60 → out-of-bounds
- Column _uniaxial: Nu/Mu table 9×60 values; search J-outer/I-inner finds first match
- cli.py entry: `python3 -m rcd2000 beam|column|slab|stair|base|continuous-beam|info`

## Relevant Files
- `/Users/MAC/Desktop/RCD2000/src/rcd2000/column.py`: uniaxial fix
- `/Users/MAC/Desktop/RCD2000/src/rcd2000/base.py`: punching shear fix
- `/Users/MAC/Desktop/RCD2000/tests/test_validation.py`: 44 checks
- `/Users/MAC/Desktop/RCD2000/tests/dosbox/test_uniax_dbg.for`: FORTRAN debug test
- GitHub: https://github.com/Al-hussein31/rcd2000
