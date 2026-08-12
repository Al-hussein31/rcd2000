# RCD2000 → CAD Export: Master Implementation Plan (2026)

> **Goal:** Turn RCD2000's calculation engine into a one-click drawing generator.
> Engineers should be able to run a calculation and receive a ready-to-submit
> AutoCAD drawing (beam plan/section/elevation, column details, slab
> reinforcement plans, footing details, bar bending schedules) — **no manual
> CAD arrangement required**.
>
> **Status:** Planning (Batch 0 complete: research + architecture decision)
>
> **Primary stack:** `ezdxf 1.4.x` (headless DXF generation) — no AutoCAD license
> required. **Fallback:** Autodesk Platform Services (Design Automation API) for
> native `.dwg` when clients demand it.
>
> **Reference implementation to study:** `structural-lib-is456`
> (`pip install "structural-lib-is456[dxf]"`, MIT, github.com/Pravin-surawase/
> structural_engineering_lib) — IS 456 design → detailing → BBS → DXF in Python.

---

## Why This Matters (The Problem)

Today the workflow is:

```
RCD2000 calculation → numbers in a report → engineer manually drafts in AutoCAD
```

That manual step costs hours per element and is a source of errors (transcription,
mis-scaling, inconsistent layer naming). This plan eliminates it:

```
RCD2000 calculation → DrawingModel dataclass → ezdxf → .dxf → open in AutoCAD, done
```

---

## Research Findings (2026 State of the Art)

### Tool Landscape Comparison

| Approach | Library/Service | AutoCAD Required? | Platform | Maturity | Verdict |
|----------|-----------------|-------------------|----------|----------|---------|
| **Native DXF** | **ezdxf 1.4.4** (May 2026) | ❌ No | Win/Mac/Linux/Web | ⭐⭐⭐⭐⭐ Active | **Primary** |
| **Native IFC/BIM** | **IfcOpenShell 0.8.5** (Apr 2026) | ❌ No | Any | ⭐⭐⭐⭐ Active | Future-proofing |
| **Cloud Automation** | Autodesk Platform Services (Design Automation API) | ☁️ Cloud | Web/API | ⭐⭐⭐⭐ | `.dwg` fallback |
| **COM Automation** | pyautocad / comtypes / autocad-automation | ✅ Desktop | Windows only | ⭐⭐⭐ Legacy | Avoid (slow, fragile) |
| **AutoLISP Generation** | Write `.lsp`/`.scr` → `acad.exe /b` | ✅ Execution | Windows only | ⭐⭐⭐ Stable | Niche only |
| **3D Parametric** | CadQuery / Build123D (OCCT) | ❌ No | Any | ⭐⭐⭐ | 3D joints only |

**Key evidence:** The 2026 Springer paper *"AutoCAD Automation Through Python
Scripting"* (INGEGRAF 2025) benchmarked win32com, pyautocad, PyAutoGUI, and ezdxf
for a layer-prefixing task. **ezdxf was fastest and most reliable for headless
drawing generation**; COM approaches are 10–50× slower and require licensed
AutoCAD on a Windows machine.

### Why NOT AutoLISP as the primary path

- Requires full AutoCAD on a Windows box per engineer (license cost).
- LISP debugging is painful; version drift across AutoCAD releases.
- Cannot run in CI/CD or on a server (headless).
- The one legit use: **wrapping existing battle-tested LISP detailing routines**
  (e.g. steel tables, connection details) via a `.scr` script — niche, ~10% of drawings.

### Why NOT pyautocad / COM as primary

- Last commit 2016; bad docs; slow; Windows + licensed AutoCAD only.
- ObjectARX/COM is the "legacy integration" route, not a greenfield build route.

### Why DXF (not DWG) as the primary deliverable

- AutoCAD, AutoCAD LT, and every CAD/BIM tool reads DXF (it's the interchange format).
- ezdxf writes R12→R2018; full control over layers, blocks, dims, hatch, paper space.
- For clients that *require* `.dwg`: ezdxf output → APS Design Automation API
  (AutoCAD-in-the-cloud SaveAs) → `.dwg`. ~$3 per 12 cloud-minutes, 300 free
  minutes/month. This keeps the core pipeline license-free.

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 0: Calculation engine (exists)                        │
│  rcd2000/beam.py, slab.py, column.py, base.py, stair.py      │
└───────────────────────────────┬─────────────────────────────┘
                                │ (results already tested — 259 tests green)
┌───────────────────────────────▼─────────────────────────────┐
│  Layer 1: DrawingModel dataclasses (NEW)                     │
│  rcd2000/drawing_models.py                                   │
│  BeamDrawing, ColumnDrawing, SlabDrawing, FootingDrawing,    │
│  RebarBar, RebarZone, DrawingScale, TitleBlock, BbsRow       │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│  Layer 2: ezdxf writer (NEW)                                 │
│  rcd2000/dxf_export.py  (DxfExporter — stateless, testable)  │
│  layers / dimstyles / textstyles / blocks / hatch            │
│  draw_beam_plan/elevation/section, column, slab, footing     │
│  paper space layouts + title block + BBS table               │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│  Layer 3: RCD2000 adapters (NEW)                             │
│  rcd2000/cad_adapters.py                                     │
│  beam_to_drawing(), column_to_drawing(), slab_to_drawing(),  │
│  footing_to_drawing()                                        │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│  Layer 4: CLI + optional GUI button (NEW)                    │
│  python -m rcd2000 dxf beam.json -o beam.dxf                 │
│  GUI: "Export to CAD" button per result card                 │
└─────────────────────────────────────────────────────────────┘
```

**Design rules**
- Layers 1–4 are **pure Python, no Qt dependency** → testable headlessly, usable
  in CLI/CI/web.
- DXF writer is **stateless** (takes a DrawingModel, returns entities) → trivially
  unit-tested by inspecting entity counts/layers/geometry.
- Calculation engine **never imports** the drawing layers (no circular deps).
- Units: **all drawing math in mm**; scale applied at draw time.

---

## Batch Plan (Work Order)

Each batch is independently shippable. Do them **in order** — each builds on the
previous. Every batch ends with: tests green + DXF file artifact + commit.

---

### Batch 0 — Foundation & Research ✅ (DONE)
- [x] Web research: ezdxf, IfcOpenShell, APS, pyautocad, structural-lib-is456
- [x] Architecture decision: **ezdxf primary, APS for .dwg, IfcOpenShell later**
- [x] This plan document written
- [ ] **Next action:** `pip install ezdxf==1.4.4` and confirm it imports in the
      project venv; add `dxf` extra to pyproject.toml (`optional-dependencies`).

---

### Batch 1 — DrawingModel Dataclasses

**Deliverable:** `src/rcd2000/drawing_models.py` + `tests/test_drawing_models.py`
**Goal:** Type-safe, unit-clear representation of everything we draw. No Qt, no ezdxf yet.

**Contents:**
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional

class DrawingScale(Enum):
    S1_20 = 20; S1_25 = 25; S1_50 = 50; S1_100 = 100

class ShapeCode(str, Enum):
    """BS 8666 / ISO 3766 bending shapes."""
    STRAIGHT = "00"; STR_END_HOOK = "11"; BOTH_HOOKS = "12"
    L_BEND = "21"; U_BAR = "24"; T_BAR = "34"
    # extend as needed

@dataclass
class RebarBar:
    diameter_mm: int
    count: int
    length_mm: float
    shape: ShapeCode = ShapeCode.STRAIGHT
    mark: str = ""

@dataclass
class RebarZone:
    """A contiguous run of identical bars along a member."""
    bars: List[RebarBar]
    start_mm: float
    end_mm: float
    offset_from_face_mm: float = 0.0   # concrete cover to bar centreline
    layer: str = "REBAR_MAIN"

@dataclass
class BeamDrawing:
    beam_id: str
    span_mm: float
    b_mm: int; D_mm: int; d_mm: int; cover_mm: int
    top_zones: List[RebarZone] = field(default_factory=list)
    bottom_zones: List[RebarZone] = field(default_factory=list)
    stirrup_zones: List[RebarZone] = field(default_factory=list)  # Ø, spacing, legs
    mu_knm: float = 0.0; vu_kn: float = 0.0
    ast_provided_mm2: float = 0.0
    scale: DrawingScale = DrawingScale.S1_50
    show_dimensions: bool = True
    show_bbs: bool = True

@dataclass
class ColumnDrawing:
    col_id: str
    b_mm: int; D_mm: int; height_mm: float
    main_bars: List[RebarBar] = field(default_factory=list)
    ties: List[RebarBar] = field(default_factory=list)
    axial_kn: float = 0.0; moment_knm: float = 0.0
    scale: DrawingScale = DrawingScale.S1_50

@dataclass
class SlabDrawing:
    slab_id: str
    panel_type: str = "one_way"   # one_way | two_way | cantilever
    lx_mm: float = 0.0; ly_mm: float = 0.0; t_mm: int = 0
    top_short: List[RebarZone] = field(default_factory=list)
    top_long: List[RebarZone] = field(default_factory=list)
    bot_short: List[RebarZone] = field(default_factory=list)
    bot_long: List[RebarZone] = field(default_factory=list)
    scale: DrawingScale = DrawingScale.S1_50

@dataclass
class FootingDrawing:
    footing_id: str
    len_mm: float; wid_mm: float; t_mm: int
    x_bars: List[RebarBar] = field(default_factory=list)
    y_bars: List[RebarBar] = field(default_factory=list)
    col_b_mm: int = 0; col_D_mm: int = 0
    scale: DrawingScale = DrawingScale.S1_50

@dataclass
class BbsRow:
    mark: str; shape: ShapeCode; dia_mm: int; n: int
    length_mm: float; bend_info: str = ""

@dataclass
class Sheet:
    """One paper-space sheet (title block + views)."""
    sheet_no: str = "S-01"; title: str = "GENERAL"
    paper: Tuple[float, float] = (841.0, 594.0)  # A1 portrait default
```

**Tests** (pure, no Qt):
- instantiate each dataclass with realistic values
- default scale is 1:50; ShapeCode strings render correctly
- BbsRow from a RebarBar (helper `bbs_row_from_bar()`)

**Acceptance:** `pytest tests/test_drawing_models.py -q` green; no new deps.

---

### Batch 2 — DxfExporter Core (layers, styles, blocks, primitives)

**Deliverable:** `src/rcd2000/dxf_export.py` core + `tests/test_dxf_export_core.py`
**Goal:** A reusable, tested DXF canvas with the structural layer standard,
dimension styles, text styles, standard blocks, and drawing primitives.

**Layer standard (BS 8666 / ISO 13567-inspired):**

| Layer | Color | Lineweight | Purpose |
|-------|-------|-----------|---------|
| `CONCRETE_OUTLINE` | White (7) | 30 | Member outlines |
| `CONCRETE_HATCH` | Gray (8) | 0 | Concrete fill hatch |
| `REBAR_MAIN` | Red (1) | 20 | Main longitudinal bars |
| `REBAR_STIRRUP` | Yellow (2) | 15 | Links/stirrups |
| `REBAR_DIST` | Green (3) | 15 | Distribution/secondary bars |
| `DIMENSIONS` | Cyan (4) | 10 | Dimension lines |
| `TEXT` | White (7) | 10 | Labels & notes |
| `GRID` | Gray (8) | 5 | Grid lines |
| `CENTERLINE` | Magenta (6) | 5 | Center lines (dashed) |
| `SECTION_CUT` | White (7) | 25 | Section cut symbols |

**Exporter skeleton:**
```python
class DxfExporter:
    def __init__(self, dxfversion: str = "R2010"):
        self.doc = ezdxf.new(dxfversion, setup=True)
        self._setup_layers(); self._setup_dimstyles(); self._setup_textstyles()
        self._create_blocks()

    # ── primitives (all take a layout + mm coords, apply scale internally) ──
    def rect(self, layout, x0,y0, x1,y1, layer="CONCRETE_OUTLINE"): ...
    def hatch_rect(self, layout, x0,y0, x1,y1, pattern="ANSI31", layer="CONCRETE_HATCH"): ...
    def line(self, layout, p0, p1, layer="CONCRETE_OUTLINE"): ...
    def polyline(self, layout, points, layer, close=False): ...
    def circle(self, layout, center, r, layer="REBAR_MAIN"): ...
    def bar_line(self, layout, p0, p1, dia_mm, layer="REBAR_MAIN"):
        """Draw a reinforcement bar as a thick line + end circles (scheme view)."""
    def text(self, layout, s, pos, h=2.5, layer="TEXT", align=CENTER): ...
    def dim_linear(self, layout, p0, p1, offset, style="STRUCT_50"): ...
```

**Dimension style** (the structural one):
```
STRUCT_50: dimscale=50, dimasz=2.5, dimtxt=2.5, dimgap=1.0,
           dimclrd=cyan, dimclrt=white, dimlwd=10, dimtofl=1
```

**Standard blocks:**
- `BAR_MARK` — circle Ø6 with ATTDEF `MARK` (bar mark text)
- `SECTION_CUT_NS` / `SECTION_CUT_EW` — section cut symbols
- `NORTH_ARROW` — north arrow block
- `REV_TRIANGLE` — revision triangle block

**Tests:**
- creates a doc; layer set matches the standard exactly
- rect/line/hatch produce correct entity types on the right layer
- bar_line produces N entities (2 end circles + line) on REBAR_MAIN
- dim style STRUCT_50 has correct dimscale/colors
- `doc.audit()` reports 0 errors after a small drawing

**Acceptance:** all green; `exporter.save("batch2.dxf")` opens in ezdxf's own
drawing add-on (`ezdxf draw batch2.dxf` renders PNG) with no errors.

---

### Batch 3 — Beam Drawing (plan + elevation + section) ⭐ first real drawing

**Deliverable:** `dxf_export.py` beam methods + `tests/test_dxf_beam.py` + sample `beam.dxf`
**Goal:** A complete single-span beam drawing sheet.

**Methods:**
- `draw_beam_plan(msp, beam: BeamDrawing)` — plan view: concrete outline, top bars,
  bottom bars (offset visually), stirrup zone markers, centerline, dimension runs
  (span, offsets), bar marks.
- `draw_beam_elevation(msp, beam, x0, y0)` — longitudinal: outline, top/bottom
  curtailment zones, stirrup distribution (links shown as vertical ticks),
  support lines, dims, bar marks with `BAR_MARK` block refs.
- `draw_beam_section(msp, beam, x_mm, y_mm, at="support"|"mid"|"both")` —
  cross-section: rectangle with cover, top bars (circles) at cover offset,
  bottom bars, stirrup outline (closed shape with 135° hooks), centerline,
  dimension (width), rebar labels.
- `draw_bbs(msp, rows: List[BbsRow], x, y)` — BBS table using `ezdxf.tables` /
  `msp.add_table()` (or line-grid if TABLE unstable): columns Mark | Shape |
  Ø | No. | Length | Note.
- `beam_sheet(beam) -> Sheet` — paper space A1 with title block + one viewport
  showing the model-space beam assembly.

**Test assertions:**
- plan has ≥ 1 hatch + ≥ 4 outline lines + ≥ 2 bar runs on REBAR_MAIN
- section has circles == total main bars count
- dims present on the plan (≥ 2 linear dims)
- BBS rows count == number of bar marks
- `doc.audit()` clean; save → file exists > 1KB

**Manual QA:** `ezdxf draw beam.dxf -o beam.png` → inspect PNG visually (scale,
bars inside outline, marks legible).

---

### Batch 4 — Column Drawing (plan + elevation)

**Deliverable:** `dxf_export.py` column methods + `tests/test_dxf_column.py` + `column.dxf`

**Methods:**
- `draw_column_plan(msp, col)` — rectangular section: outline + main bar circles
  (corner + face bars), tie outline (closed loop with hooks), dims, centerlines,
  bar mark labels.
- `draw_column_elevation(msp, col, x0, y0)` — full-height: vertical main bars,
  tie lines at computed spacing (incl. tighter spacing at top/bottom per code),
  lapping indication, section markers, dims.
- `column_sheet(col) -> Sheet`

**Test assertions:**
- plan circles == len(main_bars); tie entity count matches tie layout
- elevation tie count == computed spacing count
- audit clean

---

### Batch 5 — Slab Reinforcement Plan

**Deliverable:** `dxf_export.py` slab methods + `tests/test_dxf_slab.py` + `slab.dxf`

**Methods:**
- `draw_slab_plan(msp, slab)` — panel outline, grid (if two-way), top mesh bars
  (short + long, with extent arrows), bottom mesh, bar marks at each direction,
  span dimension runs, note text.
- `draw_slab_section(msp, slab, x0, y0)` — thickness section: top/bottom bars,
  cover, mesh overlap (lap) indication, dims.
- `slab_sheet(slab) -> Sheet`

**Test assertions:** mesh lines exist per zone; dims present; audit clean.

---

### Batch 6 — Footing Drawing (plan + section)

**Deliverable:** `dxf_export.py` footing methods + `tests/test_dxf_footing.py` + `footing.dxf`

**Methods:**
- `draw_footing_plan(msp, ftg)` — footing outline, column outline (dashed) on top,
  x/y bar mesh (circles at ends in section; lines in plan), centerlines, dims.
- `draw_footing_section(msp, ftg, x0, y0)` — thickness section with top & bottom
  mesh, cover, dowels from column, dims.
- `footing_sheet(ftg) -> Sheet`

**Test assertions:** bar counts match x_bars/y_bars; audit clean.

---

### Batch 7 — Paper Space Sheets + Title Block + Sheet Set

**Deliverable:** `sheet.py` / methods in `dxf_export.py` + `tests/test_dxf_sheets.py`
**Goal:** Production-quality multi-sheet output: A1/A2/A3, title block with
attributes (Project, Sheet No., Rev, Engineer, Date), viewport per view,
sheet list.

**Contents:**
- `SheetSpec` dataclass: paper size, orientation, title block fields,
  revision table, scale note.
- `DxfExporter.new_sheet(spec) -> Paperspace` — draws border + title block
  (as block with ATTDEFs), creates a VIEWPORT rectangle, sets
  `vp.dxf.view_center`/`view_height` to frame model-space content.
- `DxfExporter.title_block(spec)` — block with attribute tags:
  `PROJECT, TITLE, SHEET_NO, REV, SCALE, ENGINEER, DATE, DRAWN_BY`.
- `export_full_project(drawings, sheet_specs, out_path)` — one DXF, many sheets.

**Test assertions:** layout count == sheets; title block attrs populated;
viewport exists per layout; audit clean.

---

### Batch 8 — RCD2000 Adapters (calculation → drawing)

**Deliverable:** `src/rcd2000/cad_adapters.py` + `tests/test_cad_adapters.py`
**Goal:** Bridge every existing engine result into a DrawingModel.

**Contents:**
```python
def beam_to_drawing(inp: BeamInput, result: BeamResult) -> BeamDrawing:
    # map geometry, bar diameter/spacing → zones
    # requires a new DET (detailing) layer: bar layout + curtailment logic

def column_to_drawing(inp: ColumnInput, result) -> ColumnDrawing: ...
def slab_to_drawing(inp: SlabPanelInput, result) -> SlabDrawing: ...
def footing_to_drawing(inp: BaseInput, result) -> FootingDrawing: ...
def stair_to_drawing(inp: StairInput, result) -> StairDrawing: ...
```

**New subsystem — Detailing (`rcd2000/detailing.py`)** *(the real engineering work)*
Turns "Ast required + bar dia + spacing" into actual bar layouts:
- pick bar sizes from available set (16/20/25…) to meet Ast
- top/bottom curtailment zones (support vs midspan)
- stirrup spacing zones (v vs v_max, end zones tighter)
- lap lengths, anchorage, hooks (per code — BS 8110/EC2 references in `references/`)
- BBS rows

**Test assertions:** adapter round-trip (result → drawing → numbers match);
detailing zones cover the full span; spacing code-compliant vs known inputs.

---

### Batch 9 — CLI + GUI Integration

**Deliverable:** `python -m rcd2000 dxf` CLI + GUI "Export to CAD" buttons + tests

**CLI:**
```
python -m rcd2000 dxf beam --input beam.json --output beam.dxf --scale 50
python -m rcd2000 dxf project --config project.json --outdir drawings/
python -m rcd2000 dxf batch --folder jobs/ --outdir drawings/
```
- JSON schema mirrors DrawingModel inputs (round-trip with state files the GUI
  already saves — reuse importer state keys where possible).

**GUI (PySide6):**
- Each result card gains **"Export DXF"** button → saves alongside the report
  (default path next to report output; user-selectable).
- Progress indicator for batch export.
- No new page; tiny addition to each page's result area (BasePage/DesignFormPage hook).

**Test assertions:** CLI produces a DXF for each element type from a fixture JSON;
GUI button exists on each page (widget presence test); CLI exit code 0.

---

### Batch 10 — Polish, Standards & Validation

**Deliverable:** drawing standards doc + DXF QA harness + render snapshots
**Goal:** Output is consistent, code-compliant, and visually verified every build.

- **Standards doc** `CAD_STANDARDS.md`: layer table, text sizes vs scale, dim
  style, bar mark convention, sheet layout. Mirrors what a drafting office expects.
- **QA harness** (`tests/test_dxf_qa.py`):
  - every generated DXF passes `doc.audit()` (0 errors)
  - entity counts per layer within expected ranges
  - geometry stays inside sheet extents
  - auto-render PNG via `ezdxf.draw` for eyeball check on CI artifacts
- **Fixture-based golden files**: check-in sample `.dxf` for each element;
  regression test diffs entity counts (not binary bytes).

---

### Batch 11 — (Optional) Native .dwg via Autodesk Platform Services

**Deliverable:** `rcd2000/aps.py` + docs + auth flow
**Goal:** When a client demands `.dwg`, convert `.dxf` → `.dwg` in the cloud.

- Sign up APS (free tier: 300 AutoCAD minutes/mo).
- `dxf_to_dwg(dxf_path) -> dwg_path`: create bucket, upload DXF, run
  AutoCAD Design Automation workitem (`Open` + `SaveAs .dwg`), download.
- CLI: `python -m rcd2000 dxf --to-dwg`.
- **Keep this optional:** it costs tokens; default output stays DXF.

---

### Batch 12 — (Optional) BIM / IFC Export via IfcOpenShell

**Deliverable:** `rcd2000/ifc_export.py` + `tests/test_ifc_export.py`
**Goal:** Structural model handover for Revit/Tekla/Allplan/BIM workflows.

- Build an `IfcProject`/`IfcSite`/`IfcBuilding`/`IfcBuildingStorey` skeleton.
- Map each DrawingModel to `IfcBeam`, `IfcColumn`, `IfcSlab`, `IfcFooting`.
- Add reinforcement as `IfcReinforcingBar` (NominalDiameter, SteelGrade,
  BarRole, cross-section placement) + `IfcRelContainedInSpatialStructure`.
- Set quantities (Qto_BeamBaseQuantities etc.) via `ifcopenshell.api`.
- Test: reopen `.ifc`, count elements, validate with `ifcopenshell.validate()`.

---

## Cross-Cutting Concerns

### Units & Scale
- **Internal drawing units = mm** (matches RCD2000's mm-based dimensions).
- `scale` applied only in `DxfExporter` draw methods (`mm / scale.value`).
- Dimension entities use `dimstyle.dxf.dimscale = scale` so AutoCAD shows real mm.
- Always draw model space at true geometry; do scaling in paper-space viewport.

### Layer Discipline
- Every entity must land on a defined layer (no "0" layer for content).
- Layer names follow the table in Batch 2 — do not invent new names mid-project.

### Fonts
- ezdxf ships OpenSans; register `OPEN_SANS` + `OPEN_SANS_BOLD` styles.
- Text height convention: 2.5 mm (title), 2.0 mm (body), 1.8 mm (notes) at 1:50.

### Bar Marks
- `BAR_MARK` block with attribute; mark format `N-Ødia` (e.g. `2-Ø20`).
- Auto-increment marks per drawing; unique across the sheet.

### Testing Doctrine
- Every batch: pure-Python unit tests + `doc.audit()` + PNG render check.
- CI: run `pytest` + generate all sample DXF + render PNGs as artifacts.

### Git Workflow
- Feature branch per batch: `feat/dxf-export-batch-{n}`.
- Commit at end of each batch with: tests, sample DXF, PNG render, standards notes.
- Push after each batch (source of truth = GitHub).

---

## Dependencies to Add

```toml
[project.optional-dependencies]
dxf = ["ezdxf>=1.4,<2"]
# future:
# ifc = ["ifcopenshell>=0.8"]
# aps = ["aps-client"]
```

Install with `pip install -e ".[dxf]"`.

---

## Deliverable Checklist (End State)

- [ ] `python -m rcd2000 dxf beam beam.json -o beam.dxf` → A1 sheet with plan,
      elevation, section, BBS, title block
- [ ] Same for column, slab, footing, stair
- [ ] Multi-sheet project export
- [ ] GUI "Export DXF" on every result card
- [ ] 100% DXF QA pass (audit clean, renders legible, layers standard)
- [ ] (Optional) .dwg via APS
- [ ] (Optional) .ifc via IfcOpenShell

---

## Effort Estimate (Working Time)

| Batch | Scope | Est. Effort |
|-------|-------|-------------|
| 0 | Foundation | ✅ done |
| 1 | DrawingModels | 0.5 day |
| 2 | Exporter core | 1 day |
| 3 | Beam drawing | 2–3 days |
| 4 | Column drawing | 1–2 days |
| 5 | Slab drawing | 2 days |
| 6 | Footing drawing | 1 day |
| 7 | Sheets + title blocks | 2 days |
| 8 | Adapters + detailing | 3–5 days |
| 9 | CLI + GUI | 1–2 days |
| 10 | Standards + QA | 1–2 days |
| 11 | APS .dwg (optional) | 1–2 days |
| 12 | IFC (optional) | 3–5 days |

**Total core (1–10): ~2.5–4 weeks.**
**With optional 11–12: ~4–6 weeks.**

---

## How to Run the First Batch

```bash
# 1. Install ezdxf
pip install -e ".[dxf]"

# 2. Sanity check
python -c "import ezdxf; print(ezdxf.__version__)"

# 3. Start Batch 1: write drawing_models.py
```

---

*Document created: 2026-08-12 · Repo: github.com/Al-hussein31/rcd2000*
