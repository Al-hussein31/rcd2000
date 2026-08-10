# File Import — Design Spec (v1)

> Status: approved for design, pending user sign-off on this document.
> Feature: create jobs from existing engineer input files instead of typing everything.

## 1. Goal

Engineers have inputs on paper, in txt/csv files, in Excel sheets, or as old
RCD2000 output files. The app should:

1. Detect what a file is about ("smart" auto-detection of design type + fields).
2. Parse it into the app's input state (batch: one row = one design item).
3. Show an **editable preview** so the user can fix mis-detected values.
4. Create a **new job** pre-filled with the designs; user clicks DESIGN when ready.

## 2. Entry Points

All "New Job" paths open a dropdown menu instead of going straight to the header
dialog:

| Trigger | Location |
|---|---|
| New Job button | Home page (`home_page.py:new_btn`) |
| New Job button | History page empty state (`history_page.py:empty_btn`) |
| Ctrl+N action | App menu bar (`app.py:new_action`) |

All three already emit/funnel into `app._new_job()` (app.py:346) — the menu
replaces that slot's body:

```
New Job
├── Blank Job…            → existing JobHeaderDialog flow (unchanged)
├── Import from File…     → file dialog → detect → preview → create
└── Download Template…    → choose module → save CSV template for filling
```

## 3. Supported Formats

| # | Format | Detect by | Batch behavior |
|---|---|---|---|
| 1 | CSV | first data line after header | 1 row = 1 design item |
| 2 | Excel .xlsx | same as CSV (openpyxl, already installed) | 1 row = 1 design item |
| 3 | TXT key:value | `Field = value` lines | 1 file = 1 design |
| 4 | RCD2000 output file | `Beam Id:` / `Panel No.` / `Column Ref:` block markers | 1 block = 1 design |
| 5 | App job JSON | top-level `slug` + `items[].type_key` | items copied 1:1 (duplicate/restore) |

Priority order when signatures overlap: job JSON > RCD2000 output > key:value >
CSV/XLSX. `#`-prefixed lines are ignored (comment/template rows).

## 4. Architecture

### 4.1 Pure logic — `src/rcd2000/gui/importer.py` (NO Qt imports)

Everything testable headless, reusable by CLI later:

```
detect_format(path)                    → ("csv"|"xlsx"|"keyvalue"|"rcd2000"|"jobjson"|None)
detect_module(path, table)             → ("column"|"beam"|"slab"|"stair"|"base"|"cont_beam"|None)
parse_csv_or_xlsx(path)                → Table(headers, rows, sheet_name)
parse_keyvalue(path)                   → Table(headers=["FIELD"], rows=[{field: value}])
parse_rcd2000_output(path)             → list[Table] (one per block) + job_ref
parse_job_json(path)                   → (Job, warning)
map_table(module_key, table)           → (rows: list[state_dict], warnings: list[str])
build_job(name, header, items_spec)    → Job (uses Job.next_label for C1/B1/S1…)
write_template(module_key, path)       → CSV template
```

State contract: **produced state dicts must match each page's `get_state()` keys
exactly** (e.g. column: `col_type`, `shape`, `load`, `bx`, `by`, `dia`, `depth`,
`length`, `le`, `lex`, `ley`, `col_fcu`, `col_fy`, `col_max_steel`, `col_dh`,
`moment_x`, `moment_y`, `moment` — see `column_page.py:224`). Round-trip guarantee
under test: `set_state(map_table(...))` → `get_state()` → identical values.

### 4.2 GUI — `src/rcd2000/gui/import_dialog.py`

- `ImportPreviewDialog` (QDialog): module selector (shown when ambiguous), editable
  values table, warnings panel, Cancel / Create Job.
- `new_job_menu(parent) -> QMenu` helper; `app._new_job` execs it at the trigger.

## 5. Module Auto-Detection ("smart")

Score-based: each module owns an alias vocabulary. Normalize tokens
(lowercase, strip non-alnum) before matching.

| Module | Strong markers (weight 3) | Weak markers (weight 1) |
|---|---|---|
| column | `columnid`/`columnref` | `bx`, `by`, `lex`, `ley`, `colfcu`, `axialload`, `mx`, `my`, `dia` |
| beam | `beamid`, `spanlength`, `udl` | `fyv`, `bf`, `hf`, `nsup`, `nmem` |
| slab | `panelno`, `lx`, `ly` | `gk`, `qk`, `slab` |
| stair | `stairref`, `riser`, `tread` | `stairs`, `going`, `gk`, `qk` |
| base | `baseref`/`footing`, `l1`, `l2` | `pb`, `base`, `sq`, `rect` |
| cont_beam | `continuous`, `member` | `inertia`, `emod` |

Rules:
- Best score wins. Require score ≥ 3, else **ambiguous → preview asks user**.
- Tie-break: value-range heuristics (e.g. `fcu` ∈ 20–80, `fy` ∈ 200–600) and
  field-name specificity.
- RCD2000 output: block markers (`Beam Id:`, `Panel No.`, `Column Ref:`,
  `Stair Ref:`, `Base Ref:`) pick module directly; unknown block marker →
  ambiguous.
- Job JSON: `type_key` decides, no scoring.

## 6. Field Aliases & Units

### 6.1 Alias tables

Canonical key → accepted aliases (headers, key:value names, and RCD2000 labels).
Examples (full tables live in `importer.py`):

**column** — canonical keys and aliases:
```
col_type:      COLUMN TYPE, TYPE                  (1=axial 2=uniax 3=biax)
shape:         SHAPE                              (1=rect 2=circ)
load:          LOAD, AXIAL LOAD, N, P
bx:            BX, WIDTH X, B
by:            BY, WIDTH Y, D
dia:           DIA, DIAMETER
depth:         DEPTH, H
length:        LENGTH, HEIGHT, L
le:            LE, EFF LENGTH
lex:           LEX
ley:           LEY
col_fcu:       FCU, F CU
col_fy:        FY, F Y
col_max_steel: MAX STEEL, MAX STEEL %, MS
col_dh:        DH RATIO, DH
moment_x:      MX, MOMENT X, MOMENT-X, M_X
moment_y:      MY, MOMENT Y, MOMENT-Y, M_Y
moment:        M, MOMENT
```
**beam** — `beam_id` (BEAM ID, BEAM, ID), `b` (B, WIDTH, BW), `bf` (BF, FLANGE WIDTH),
`h` (H, DEPTH), `hf` (HF, FLANGE DEPTH), `fcu`, `fy`, `fyv` (FYV, STIRRUP),
`n_supports` (NSUP, NO OF SUPPORTS), `n_members` (NM, NO OF MEMBERS),
spans `L1..Ln` (SPAN 1..N), UDLs `UDL1..UDLn` (W1..Wn), triangular `WT`,
point-load columns `P1..Pn`/`Q1..Qn` (POSITION, LOAD).

**slab / stair / base / cont_beam** — same structure; exact canonical keys
finalized from `SlabPanelInput`, `StairInput`, `BaseInput(+ColumnOnBase)`,
`ContinuousBeamInput(+ContinuousBeamMember)` dataclasses during implementation.

### 6.2 Unit parsing & conversion

Values may carry suffixes (RCD2000 output does: `2200.mm`, `18.200kN/m`).
Parser strips the suffix and converts to the canonical engine unit from the
dataclass comment (e.g. `bx` mm, `length` m, `load` kN, `moment` kN.m,
`fcu` N/mm²).

| Suffix | Canonical target | Conversion |
|---|---|---|
| `.mm`, `mm` | mm | ×1 |
| `cm` | mm | ×10 |
| `m` | mm (section) / m (length fields) | ×1000 when target mm |
| `kN`, `kn` | kN | ×1 |
| `N` | kN | ÷1000 |
| `kN/m`, `kn/m` | kN/m | ×1 |
| `kNm`, `kN.m` | kN.m | ×1 |
| `N/mm2`, `N/mm²` | N/mm² | ×1 |
| `kN/m2`, `kN/m²` | kN/m² (area loads) | ×1 |
| `sq.mm`, `mm2` | mm² | ×1 |
| `%` | percent | ×1 |

Template headers carry units as hints the parser may override, e.g.
`Length [m]`, `B [mm]` — bracket suffix is stripped from the alias.

## 7. Import Preview Dialog

| Element | Behavior |
|---|---|
| Module combo | Auto-picked; shown/enabled only when ambiguous or for override |
| Table | rows = designs, columns = canonical fields; editable cells; invalid cells highlighted red with tooltip |
| Warnings panel | unknown headers ignored (listed), unconvertible values (flagged), missing required fields (listed, not blocking) |
| Batch cap | > 200 designs → confirm dialog before continuing |
| Create Job | name = file stem (title-cased), `header.job_ref` = file stem, rest from profile defaults; opens workbench directly |

## 8. Templates ("Download Template…")

Per-module CSV: header row = canonical names with unit hints (`Load [kN]`,
`B [mm]`, `L1 [m]` …), one `#` comment row with instructions, then blank rows.
Engineers fill it in Excel; import detects it back. Guarantee: template →
import → identical values (round-trip test).

## 9. Edge Cases & Failure Modes

- Empty file / no headers / no rows → error dialog, no job created.
- Unknown module with zero matches → preview requires manual module choice.
- Non-numeric value in numeric field → cell flagged, import proceeds with 0 + warning.
- Units in mixed forms in one file → per-cell parsing (no file-wide assumption).
- Job JSON from future version (unknown keys) → ignore unknowns (mirrors
  `Job.from_dict` forward-compat), warn.
- Duplicate import → new job with new slug; original untouched.
- Old RCD2000 files with `JOB REF:` → that value becomes `header.job_ref`; blank
  header fields fall back to profile defaults.
- Importing a file while a job is open → saves current job first (existing
  `_save_current_job` in `_open_workbench`), then creates the new one.

## 10. Testing Plan — `tests/test_importer.py` (pure, no Qt)

1. Format detection: csv, xlsx, key:value, rcd2000, job JSON, garbage → None.
2. Module scoring: column sheet → column; beam sheet → beam; ambiguous → needs choice.
3. Unit parsing: `"2200.mm"`, `"2.4m"` (→ mm fields), `"18.200kN/m"`, `"0.0182N/mm2"`, `"5kNm"`, `"12sq.mm"`.
4. Alias mapping incl. template bracket units.
5. Batch: 10-row beam sheet → 10 items labeled B1..B10.
6. RCD2000 output fixture: multi-beam file → items with correct span/UDL values + job_ref.
7. Job JSON round-trip: Job.to_dict → import → same items/state (new slug).
8. Template round-trip: write → import → identical values.
9. Missing fields → warnings, no crash.
10. State contract: `set_state` → `get_state` → identical for every module.

GUI wiring: 1 offscreen smoke test (menu opens, cancel works).

## 11. Milestones

1. `importer.py` pure logic + `test_importer.py` — commit, push.
2. `import_dialog.py` preview + app menu wiring (Home/History/Ctrl+N) — commit, push.
3. Templates + RCD2000 output polish + full suite green — commit, push.

## 12. Open Questions (minor, decide during implementation)

- xlsx: read first sheet only, or all sheets as separate imports? (V1: first sheet + warn if more.)
- Key:value files with multiple designs: `[Beam]`/`[Column]` section headers supported? (V1: one design per file; section headers → error + suggestion to split.)
