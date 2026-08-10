"""File import for RCD2000 jobs — pure logic, no Qt widgets.

Pipeline (see IMPORT_SPEC.md):

    detect_format(path)         → "csv" | "xlsx" | "keyvalue" | "rcd2000" | "jobjson" | None
    parse_file(path)            → ParsedFile (detect + parse + score module)
    map_table(module_key, t)    → (states, labels, warnings)  -- state dicts for pages
    build_job(name, header, ...)→ Job with pre-filled items
    write_template(module_key)  → CSV template for engineers to fill

Every mapping target is a page ``get_state()`` key (e.g. ``load``, ``bx``,
``col_fcu``), so imported state round-trips through ``set_state`` untouched.
"""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass, field

# ── Text normalisation ──────────────────────────────────────────────────

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_UNIT_BRACKETS = re.compile(r"\s*\[[^\]]*\]\s*$")


def norm_token(text: str) -> str:
    """Lowercase, strip punctuation/units-brackets: 'Span Length 1 [m]' → 'spanlength1'."""
    return _NON_ALNUM.sub("", _UNIT_BRACKETS.sub("", (text or "").lower()))


def norm_value(raw: str) -> str:
    """Normalise a raw cell: strip quotes/spaces, unify superscripts."""
    v = (raw or "").strip().strip('"').strip("'").strip()
    v = v.replace("\u00b2", "2").replace("\u00b3", "3").replace("\u2074", "4")
    v = v.replace("\u00d7", "x").replace("\u2022", "")
    return v.strip()


# ── Units ───────────────────────────────────────────────────────────────

#: unit string (normalised) → canonical unit key
_UNIT_MAP = {
    "mm": "mm", "cm": "cm", "m": "m", "m2": "m2", "m3": "m3", "m4": "m4",
    "m^4": "m4", "mm2": "mm2", "sqmm": "mm2", "sq.mm": "mm2", "mm^2": "mm2",
    "kn": "kN", "n": "N", "knm": "kN.m", "kn.m": "kN.m", "kn*m": "kN.m",
    "kn/m": "kN/m", "knperm": "kN/m", "kn/m2": "kN/m2", "kn/m^2": "kN/m2",
    "knperm2": "kN/m2", "kn/m3": "kN/m3", "knperm3": "kN/m3",
    "n/mm2": "N/mm2", "n/mm^2": "N/mm2", "npermm2": "N/mm2",
    "%": "pct", "pct": "pct", "percent": "pct", "": "", "m^2": "m2",
}

#: value text → canonical unit key (used when parsing "2200.mm")
_UNIT_SUFFIX = re.compile(
    r"(?i)^([-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*(?:\.\s*)?"
    r"(mm2|mm\^?2|mm|sq\.?mm|cm|m\^?[234]|m|kn/m\^?2|knperm2|kn/m\^?3|knperm3|"
    r"kn/m|knperm|knm|kn\.m|kn\*m|kn|n/mm\^?2|npermm2|n|%|pct|percent)?$"
)


def _num(text: str) -> float | None:
    t = text.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def parse_value(raw: str, unit: str = "") -> tuple[float | None, str | None]:
    """Parse ``raw`` for a field of canonical unit ``unit``.

    Returns ``(value, warning)``.  ``None`` value means unparseable.
    Bare numbers stay in the canonical unit, except two smart heuristics
    (both surface a warning so the preview can fix them):
      - m-length fields: bare value >= 100 is assumed mm (÷1000)
      - N/mm² fields: bare value >= 1000 is assumed kN/m² (÷1000)
    """
    v = norm_value(raw)
    if not v:
        return None, None
    m = _UNIT_SUFFIX.match(v)
    if not m:
        return None, "Unrecognised value: %r" % raw
    number = _num(m.group(1))
    if number is None:
        return None, "Not a number: %r" % raw
    u = _UNIT_MAP.get((m.group(2) or "").lower().replace(" ", ""), "")

    warning = None
    if u == "":
        # Bare number — canonical unit, with heuristics.
        if unit == "m" and abs(number) >= 100:
            warning = "Bare %s assumed mm for a metre field (÷1000)" % raw
            number = number / 1000.0
        elif unit == "N/mm2" and abs(number) >= 1000:
            warning = "Bare %s assumed kN/m2 for a N/mm2 field (÷1000)" % raw
            number = number / 1000.0
        return number, warning

    conv = {
        "mm": {"mm": 1.0, "cm": 10.0, "m": 1000.0},
        "m": {"mm": 0.001, "cm": 0.01, "m": 1.0},
        "kN": {"kN": 1.0, "N": 0.001},
        "kN.m": {"kN.m": 1.0, "kN": 1.0},  # 5 kNm ~ 5 kN.m
        "kN/m": {"kN/m": 1.0},
        "kN/m2": {"kN/m2": 1.0, "N/mm2": 1000.0},
        "N/mm2": {"N/mm2": 1.0, "kN/m2": 0.001},
        "kN/m3": {"kN/m3": 1.0},
        "mm2": {"mm2": 1.0},
        "m2": {"m2": 1.0},
        "m3": {"m3": 1.0},
        "m4": {"m4": 1.0},
        "pct": {"pct": 1.0},
    }
    if not unit:
        # No expected unit — accept any recognised unit verbatim.
        if u in conv or u == "":  # pragma: no branch
            return number, warning
        return None, "Unit %r not recognised" % u
    table = conv.get(unit)
    if table is None or u not in table:
        return None, "Unit %r not recognised for field (expected %s)" % (u, unit)
    return number * table[u], warning


def parse_int(raw: str) -> tuple[int | None, str | None]:
    v = norm_value(raw)
    if not v:
        return None, None
    f = _num(v)
    if f is None:
        return None, "Not a number: %r" % raw
    return int(round(f)), None


# ── Combo value maps (raw file text → page combo index) ────────────────

def _combo_map(mapping: dict) -> callable:
    def f(raw: str) -> tuple[int | None, str | None]:
        key = norm_token(raw)
        if key in mapping:
            return mapping[key], None
        v, w = parse_int(raw)
        if v is not None and v in mapping:
            return mapping[v], None
        return None, "Unknown choice: %r" % raw
    return f


#: column type: file text / engine 1-based number → page combo index
_COL_TYPE = {
    "axial": 0, "axiallyloaded": 0, "axially": 0,
    "uniaxial": 1, "uniaxialbending": 1,
    "biaxial": 2, "biaxialbending": 2,
    1: 0, 2: 1, 3: 2,
}
_SHAPE = {"rect": 0, "rectangular": 0, "square": 0, "round": 1,
          "circ": 1, "circular": 1, 1: 0, 2: 1}
_SLAB_TYPE = {
    "cantilever": 0, "cant": 0,
    "simplysupported": 1, "simply": 1, "simple": 1, "ss": 1,
    "continuous": 2, "oneway": 2,
    "twoway": 3, "two way": 3,
    1: 0, 2: 1, 3: 2, 4: 3,
}
_BASE_TYPE = {
    "square": 0, "squareisolated": 0,
    "rect": 1, "rectangular": 1, "rectangularisolated": 1, "isolated": 1,
    "combined": 2, 1: 0, 2: 1, 3: 2,
}
_END_TYPE = {"pinned": 0, "pin": 0, "simple": 0, "simplysupported": 0,
             "fixed": 1, "builtin": 1, "builtinend": 1, "continuous": 1,
             1: 0, 2: 1}

#: canonical field key → (aliases, kind, unit)
#: kind: "float" | "int" | "combo" | "label"    unit: canonical engine unit
_FIELD = {
    "column": {
        "col_type":      ({}, "combo", _combo_map(_COL_TYPE)),
        "shape":         ({}, "combo", _combo_map(_SHAPE)),
        "load":          ({}, "float", "kN"),
        "bx":            ({}, "float", "mm"),
        "by":            ({}, "float", "mm"),
        "dia":           ({}, "float", "mm"),
        "depth":         ({}, "float", "mm"),
        "length":        ({}, "float", "m"),
        "le":            ({}, "float", "m"),
        "lex":           ({}, "float", "m"),
        "ley":           ({}, "float", "m"),
        "col_fcu":       ({}, "float", "N/mm2"),
        "col_fy":        ({}, "float", "N/mm2"),
        "col_max_steel": ({}, "float", "pct"),
        "col_dh":        ({}, "float", "ratio"),
        "moment_x":      ({}, "float", "kN.m"),
        "moment_y":      ({}, "float", "kN.m"),
        "moment":        ({}, "float", "kN.m"),
    },
    "beam": {
        "beam_fcu":      ({}, "float", "N/mm2"),
        "beam_fy":       ({}, "float", "N/mm2"),
        "beam_fyv":      ({}, "float", "N/mm2"),
        "b_b":           ({}, "float", "mm"),
        "b_bf":          ({}, "float", "mm"),
        "b_h":           ({}, "float", "mm"),
        "b_hf":          ({}, "float", "mm"),
        "n_supports":    ({}, "int", ""),
        "n_members":     ({}, "int", ""),
        "ty1":           ({}, "combo", _combo_map(_END_TYPE)),
        "ty2":           ({}, "combo", _combo_map(_END_TYPE)),
        "cant_load_1":   ({}, "float", "kN/m"),
        "cant_moment_1": ({}, "float", "kN.m"),
        "cant_load_2":   ({}, "float", "kN/m"),
        "cant_moment_2": ({}, "float", "kN.m"),
    },
    "slab": {
        "slab_type":     ({}, "combo", _combo_map(_SLAB_TYPE)),
        "slab_fcu":      ({}, "float", "N/mm2"),
        "slab_fy":       ({}, "float", "N/mm2"),
        "s_depth":       ({}, "float", "mm"),
        "s_span":        ({}, "float", "m"),
        "s_ly":          ({}, "float", "m"),
        "s_case":        ({}, "int", ""),
        "s_sd":          ({}, "float", "ratio"),
        "gk":            ({}, "float", "kN/m2"),
        "qk":            ({}, "float", "kN/m2"),
        "cant_load_1":   ({}, "float", "kN/m"),
        "cant_moment_1": ({}, "float", "kN.m"),
        "cant_load_2":   ({}, "float", "kN/m"),
        "cant_moment_2": ({}, "float", "kN.m"),
        "panel_npl":     ({}, "int", ""),
        "cont_nspan":    ({}, "int", ""),
    },
    "stair": {
        "s_span":        ({}, "float", "m"),
        "s_tread":       ({}, "float", "mm"),
        "s_rise":        ({}, "float", "mm"),
        "s_imp":         ({}, "float", "kN/m2"),
        "s_spl":         ({}, "float", "kN/m2"),
        "s_wld":         ({}, "float", "kN/m3"),
        "gk":            ({}, "float", "kN/m2"),
        "qk":            ({}, "float", "kN/m2"),
    },
    "base": {
        "base_type":     ({}, "combo", _combo_map(_BASE_TYPE)),
        "col_shape":     ({}, "combo", _combo_map(_SHAPE)),
        "base_fcu":      ({}, "float", "N/mm2"),
        "base_fy":       ({}, "float", "N/mm2"),
        "base_pb":       ({}, "float", "kN/m2"),
        "base_load":     ({}, "float", "kN"),
        "base_a1":       ({}, "float", "mm"),
        "base_a2":       ({}, "float", "mm"),
        "base_dia":      ({}, "float", "mm"),
        "base_h":        ({}, "float", "mm"),
        "base_l1":       ({}, "float", "m"),
        "base_l2":       ({}, "float", "m"),
        "base_dowel":    ({}, "float", "mm"),
        "gk":            ({}, "float", "kN/m2"),
        "qk":            ({}, "float", "kN/m2"),
    },
    "cont_beam": {
        "cb_ns":         ({}, "int", ""),
        "cb_nm":         ({}, "int", ""),
        "cb_end1":       ({}, "combo", _combo_map(_END_TYPE)),
        "cb_end2":       ({}, "combo", _combo_map(_END_TYPE)),
        "cant_load_1":   ({}, "float", "kN/m"),
        "cant_moment_1": ({}, "float", "kN.m"),
        "cant_load_2":   ({}, "float", "kN/m"),
        "cant_moment_2": ({}, "float", "kN.m"),
    },
}

#: label fields per module — the value becomes the design item label (C1, B1…)
_LABEL_ALIAS = {
    "column":    ("columnid", "columnref", "columnno", "id", "ref", "label", "design"),
    "beam":      ("beamid", "beamref", "beamno", "id", "ref", "label", "design"),
    "slab":      ("panelno", "panelid", "panelref", "id", "ref", "label", "design"),
    "stair":     ("stairref", "stairid", "stairs", "id", "ref", "label", "design"),
    "base":      ("baseref", "baseid", "footingno", "footing", "id", "ref", "label", "design"),
    "cont_beam": ("contbeamref", "continuousbeamref", "contbeam", "id", "ref", "label", "design"),
}

#: per-module aliases for every field (filled below the definitions)
_ALIASES = {
    "column": {
        "col_type": "columntype coltype ctype membertype type",
        "shape": "shape section sectiontype columnshape",
        "load": "load axialload axial n p axialforce columnload designload",
        "bx": "bx widthx widthxdimension width dimensionx b",
        "by": "by widthy dimensiony",
        "dia": "dia diameter diam",
        "depth": "depth overalldepth depthh h",
        "length": "length height l columnlength storeyheight columnheight",
        "le": "le effectivelength efflength leff",
        "lex": "lex effectivelengthx efflengthx lexle",
        "ley": "ley effectivelengthy efflengthy",
        "col_fcu": "fcu cu concretestrength concretegrade fc cuconcrete",
        "col_fy": "fy steelstrength rebarstrength yieldstrength",
        "col_max_steel": "maxsteel maxsteelpct ms steellimit maxsteelpercent",
        "col_dh": "dh dhratio dtoh effectivedepthratio dhratio",
        "moment_x": "mx momentx momentaboutx mxx",
        "moment_y": "my momenty momentabouty",
        "moment": "m moment uniaxialmoment designmoment",
    },
    "beam": {
        "beam_fcu": "fcu cu concretestrength concretegrade fc",
        "beam_fy": "fy steelstrength yieldstrength",
        "beam_fyv": "fyv stirrup linkstrength shearsteel links",
        "b_b": "b bw width beamwidth widthb",
        "b_bf": "bf flangewidth flangewidth",
        "b_h": "h depth overalldepth beamdepth depthh",
        "b_hf": "hf flangedepth flangethickness",
        "n_supports": "nsup noofsupports ns supports numberofsupports nosupports nsupports",
        "n_members": "nmem noofmembers nm members numberofmembers nomembers nmembers",
        "ty1": "end1 support1type leftsupport supporttype1 endcondition1",
        "ty2": "end2 support2type rightsupport supporttype2 endcondition2",
        "cant_load_1": "cantload1 cantileverload1 endload1 overhangload1",
        "cant_moment_1": "cantmoment1 cantilevermoment1 endmoment1",
        "cant_load_2": "cantload2 cantileverload2 endload2",
        "cant_moment_2": "cantmoment2 cantilevermoment2 endmoment2",
    },
    "slab": {
        "slab_type": "slabtype paneltype ptype type",
        "slab_fcu": "fcu cu concretestrength concretegrade fc",
        "slab_fy": "fy steelstrength yieldstrength",
        "s_depth": "depth overalldepth thickness slabdepth depthh h",
        "s_span": "span lx shortspan spanx lengthx spanlength",
        "s_ly": "ly longspan spany lengthy",
        "s_case": "case caseno bendingcase case2",
        "s_sd": "spandepth sd sdratio spandepthratio",
        "gk": "gk deadload permanentload dl",
        "qk": "qk liveload imposedload ll",
        "cant_load_1": "cantload1 cantileverload1 endload1",
        "cant_moment_1": "cantmoment1 cantilevermoment1 endmoment1",
        "cant_load_2": "cantload2 cantileverload2 endload2",
        "cant_moment_2": "cantmoment2 cantilevermoment2 endmoment2",
        "panel_npl": "npl nopointloads numberofpointloads pointloadcount npls",
        "cont_nspan": "nspan nospans numberofspans spans nspans",
    },
    "stair": {
        "s_span": "span going stairspan flightspan span2",
        "s_tread": "tread t goingwidth treadwidth",
        "s_rise": "rise riser r riserheight",
        "s_imp": "imposed liveload imposedload qk",
        "s_spl": "superimposed sdl superimposeddeadload spl",
        "s_wld": "wld weightoflanding landingweight",
        "gk": "gk deadload dl",
        "qk": "qk liveload ll",
    },
    "base": {
        "base_type": "basetype footingtype foundationtype type",
        "col_shape": "colshape columnshape shape",
        "base_fcu": "fcu cu concretestrength concretegrade fc",
        "base_fy": "fy steelstrength yieldstrength",
        "base_pb": "pb bearingpressure allowablebearing soilbearing",
        "base_load": "load axialload n totalload columnload designload",
        "base_a1": "a1 coldim1 cola1 columnlength coldim1a",
        "base_a2": "a2 coldim2 cola2 columnwidth",
        "base_dia": "dia diameter coldia columndia columndiameter",
        "base_h": "h depth thickness basedepth basethickness",
        "base_l1": "l1 length baselength lengthl1",
        "base_l2": "l2 width basewidth widthl2",
        "base_dowel": "dowel doweldia starterbar starter doweldiameter",
        "gk": "gk deadload dl",
        "qk": "qk liveload ll",
    },
    "cont_beam": {
        "cb_ns": "ns nsup noofsupports supports numberofsupports nosupports nspans",
        "cb_nm": "nm nmem noofmembers members numberofmembers nomembers nmembers",
        "cb_end1": "end1 leftsupport supporttype1 endcondition1",
        "cb_end2": "end2 rightsupport supporttype2 endcondition2",
        "cant_load_1": "cantload1 cantileverload1 endload1",
        "cant_moment_1": "cantmoment1 cantilevermoment1 endmoment1",
        "cant_load_2": "cantload2 cantileverload2 endload2",
        "cant_moment_2": "cantmoment2 cantilevermoment2 endmoment2",
    },
}

for _mod, _fields in _ALIASES.items():
    for _key, _words in _fields.items():
        _FIELD[_mod][_key][0].update(
            (norm_token(w), _key) for w in _words.split()
        )

#: member-array index patterns: normalized header → (member field, unit)
#: applied to beam (L1.., UDL1..), continuous beam (+ INERTIA/E) and slab
#: (SPAN LENGTH / UDL for continuous panels, PL/AP for point loads).
_MEMBER_PATTERNS = [
    (re.compile(r"^l(\d+)$"), "length", "m"),
    (re.compile(r"^span(\d+)$"), "length", "m"),
    (re.compile(r"^spanlength(\d+)$"), "length", "m"),
    (re.compile(r"^udl(\d+)$"), "udl", "kN/m"),
    (re.compile(r"^w(\d+)$"), "udl", "kN/m"),
    (re.compile(r"^wt(\d+)$"), "wt", "kN/m"),
    (re.compile(r"^wb(\d+)$"), "wb", "kN/m"),
    (re.compile(r"^ab(\d+)$"), "ab", "m"),
    (re.compile(r"^pl(\d+)$"), "pl", "kN"),
    (re.compile(r"^ap(\d+)$"), "ap", "m"),
    (re.compile(r"^inertia(\d+)$"), "inertia", "m4"),
    (re.compile(r"^emod(\d+)$"), "e_mod", "ratio"),
    (re.compile(r"^e(\d+)$"), "e_mod", "ratio"),
    (re.compile(r"^cload(\d+)$"), "combined_col_load", "kN"),
    (re.compile(r"^cdist(\d+)$"), "combined_col_dist", "m"),
]

#: strong per-module markers (doubled score in detection)
_STRONG = {
    "column": {"columnid", "columnref", "columnno", "colref"},
    "beam": {"beamid", "beamref", "beamno", "spanlength"},
    "slab": {"panelno", "panelid", "panelref"},
    "stair": {"stairref", "stairid"},
    "base": {"baseref", "baseid", "footingno", "footing"},
    "cont_beam": {"contbeamref", "continuousbeamref", "contbeam"},
}

#: block markers in RCD2000 output files → module
_RCD_BLOCK = {
    "beamid": "beam", "beamref": "beam", "beam": "beam",
    "panelno": "slab", "panel": "slab", "slabref": "slab",
    "columnref": "column", "columnno": "column", "columnid": "column",
    "stairref": "stair", "stairno": "stair",
    "baseref": "base", "baseid": "base", "footingno": "base", "footing": "base",
    "continuousbeam": "cont_beam", "contbeam": "cont_beam",
    "continuousbeamref": "cont_beam",
}


# ── Data model ──────────────────────────────────────────────────────────

@dataclass
class Table:
    """A parsed tabular source: raw headers + raw string rows."""

    headers: list[str]
    rows: list[dict[str, str]]
    format: str
    row_modules: list[str | None] = None   # parallel to rows (rcd2000)
    row_labels: list[str | None] = None    # parallel to rows (rcd2000)


@dataclass
class ParsedFile:
    """Result of parsing an import file (before module mapping)."""

    format: str
    table: Table
    module_key: str | None          # None → ambiguous, user must choose
    name: str                       # suggested job name (file stem)
    job_ref: str | None = None
    job: object | None = None       # Job instance for format == "jobjson"
    warnings: list[str] = field(default_factory=list)


# ── Format detection ────────────────────────────────────────────────────

def _read_head(path: str, limit: int = 200) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read(limit)


def detect_format(path: str) -> str | None:
    """Return the import format of *path* or None when unreadable."""
    try:
        head = _read_head(path)
    except OSError:
        return None
    if not head.strip():
        return None
    ext = os.path.splitext(path)[1].lower()
    # Job JSON
    if ext == ".json":
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        if isinstance(data, dict) and "items" in data and "slug" in data:
            return "jobjson"
        return None
    # RCD2000 output: block markers decide
    marker_lines = [l.strip() for l in head.splitlines()]
    if any(l.startswith(m) for l in marker_lines for m in (
            "Beam Id:", "Panel No.", "Column Ref:", "Stair Ref:",
            "Base Ref:", "Footing No.")) or \
       any(l.startswith("Continuous Beam") and "," not in l and
           not l.startswith("Continuous Beam Ref") for l in marker_lines):
        return "rcd2000"
    # key:value text:  "Field = value" lines without block markers
    lines = [l for l in head.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    eq_lines = sum(1 for l in lines[:40]
                   if re.match(r"^\s*[A-Za-z][A-Za-z0-9 /]*\s*=\s*\S", l))
    if eq_lines >= 2:
        return "keyvalue"
    if ext == ".xlsx":
        return "xlsx"
    if ext == ".csv" or "," in head or "\t" in head or ";" in head:
        return "csv"
    return None  # unrecognised: caller shows an error


# ── Parsers ─────────────────────────────────────────────────────────────

def _clean_cell(v) -> str:
    if v is None:
        return ""
    return norm_value(str(v))


def parse_csv_or_xlsx(path: str) -> Table:
    """Parse CSV (stdlib) or XLSX (openpyxl) into a Table."""
    ext = os.path.splitext(path)[1].lower()
    rows_raw: list[list[str]] = []
    if ext == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        for row in ws.iter_rows(values_only=True):
            rows_raw.append([_clean_cell(c) for c in row])
        wb.close()
    else:
        with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            for row in csv.reader(f):
                rows_raw.append([_clean_cell(c) for c in row])

    rows_raw = [r for r in rows_raw if any(c.strip() for c in r)]
    if not rows_raw:
        raise ValueError("File contains no data rows.")
    header_i = 0
    while header_i < len(rows_raw) and rows_raw[header_i][0].lstrip().startswith("#"):
        header_i += 1
    if header_i >= len(rows_raw):
        raise ValueError("File contains no header row.")
    headers = [norm_token(h) or f"col{i}" for i, h in enumerate(rows_raw[header_i])]
    table = Table(headers=headers, rows=[], format="csv" if ext != ".xlsx" else "xlsx")
    for r in rows_raw[header_i + 1:]:
        if not any(c.strip() for c in r):
            continue
        row = {}
        for i, h in enumerate(headers):
            row[h] = r[i] if i < len(r) else ""
        table.rows.append(row)
    return table


def parse_keyvalue(path: str) -> Table:
    """Parse 'Field = value' text (one design per file)."""
    fields: dict[str, list[str]] = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^\s*([A-Za-z][A-Za-z0-9 /()\[\].-]*)\s*=\s*(.+?)\s*$", line)
            if not m:
                continue
            key = norm_token(m.group(1))
            val = norm_value(m.group(2))
            if key in ("jobref", "jobrefid"):
                continue
            fields.setdefault(key, []).append(val)
    if not fields:
        raise ValueError("No 'Field = value' entries found.")
    table = Table(headers=list(fields.keys()), rows=[], format="keyvalue")
    table.rows.append({k: (",".join(v) if len(v) > 1 else v[0])
                       for k, v in fields.items()})
    return table


_RCD_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 /()\[\].-]*?)\s*=\s*(.+?)\s*$")


def parse_rcd2000_output(path: str) -> Table:
    """Parse an original RCD2000 output text file into a Table.

    Block markers ('Beam Id: B1', 'Panel No. P4', …) start a new design;
    'Field = value' lines fill it.  Job header lines ('JOB REF:', 'DATE:')
    are captured separately.  Comma-separated or repeated values become
    member arrays.
    """
    table = Table(headers=[], rows=[], format="rcd2000")
    table.row_modules = []
    table.row_labels = []
    current: dict[str, list[str]] = {}
    current_mod: str | None = None
    current_label: str | None = None

    def flush():
        if current_mod and current:
            # join repeated/comma values → single cell string (member arrays)
            row = {k: ", ".join(v) for k, v in current.items()}
            table.headers = list(dict.fromkeys(table.headers + list(row.keys())))
            table.rows.append(row)
            table.row_modules.append(current_mod)
            table.row_labels.append(current_label)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            marker = re.match(r"^\s*([A-Za-z][A-Za-z0-9 /().-]*?)\s*:\s*(.*?)\s*$", line)
            if marker:
                mkey = norm_token(marker.group(1))
                mval = marker.group(2)
                if mkey in _RCD_BLOCK:
                    flush()
                    current = {}
                    current_mod = _RCD_BLOCK[mkey]
                    current_label = mval or None
                    continue
                if mkey == "jobref":
                    continue  # header captured by caller via job_ref
                # 'Label: value' — numeric RHS is a field (e.g. 'Design data: 3')
                if re.match(r"^[-+]?[\d.,]+(?:\.(?:mm|m|kN|N)\w*)?$", norm_value(mval)):
                    current.setdefault(mkey, []).append(norm_value(mval))
                continue
            # standalone block header line, e.g. 'Continuous Beam'
            bare = norm_token(line)
            if bare in _RCD_BLOCK and "=" not in line:
                flush()
                current = {}
                current_mod = _RCD_BLOCK[bare]
                current_label = None
                continue
            m = _RCD_LINE.match(line)
            if m:
                key = norm_token(m.group(1))
                if key == "jobref":
                    continue
                current.setdefault(key, []).append(norm_value(m.group(2)))
    flush()
    if not table.rows:
        raise ValueError("No design blocks found in RCD2000 output file.")
    return table


def parse_job_json(path: str) -> ParsedFile:
    """Parse a job JSON file into a ParsedFile carrying the Job."""
    from rcd2000.gui.job import Job
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    job = Job.from_dict(data)
    name = os.path.splitext(os.path.basename(path))[0]
    return ParsedFile(
        format="jobjson",
        table=Table(headers=[], rows=[], format="jobjson"),
        module_key=None,
        name=name,
        job_ref=job.header.get("job_ref", ""),
        job=job,
    )


# ── Module detection ────────────────────────────────────────────────────

def _header_field(module: str, header: str) -> str | None:
    """Map a normalized header to a canonical field key (or None)."""
    fields = _FIELD[module]
    if header in fields:
        return header
    for key, (aliases, kind, unit) in fields.items():
        if header in aliases:
            return key
    if header in _LABEL_ALIAS[module]:
        return "_label"
    for pat, mfield, munit in _MEMBER_PATTERNS:
        if pat.match(header):
            return "_member"
    return None


def score_module(module: str, headers: list[str]) -> int:
    """Count how many headers a module's vocabulary explains."""
    score = 0
    for h in headers:
        if h in _STRONG[module]:
            score += 2
        elif _header_field(module, h) is not None:
            score += 1
    return score


def detect_module(headers: list[str]) -> str | None:
    """Return the best module for *headers*, None when ambiguous."""
    best, best_score, ties = None, 0, 0
    for mod in _FIELD:
        s = score_module(mod, headers)
        if s > best_score:
            best, best_score, ties = mod, s, 1
        elif s == best_score:
            ties += 1
    if best_score >= 3 and ties == 1:
        return best
    return None


# ── Mapping ─────────────────────────────────────────────────────────────

def _split_list(raw: str) -> list[str]:
    """Split '2.2, 2.4' / '2.2 2.4' into values."""
    v = norm_value(raw)
    if "," in v:
        return [x.strip() for x in v.split(",") if x.strip()]
    parts = v.split()
    if len(parts) > 1 and all(_num(p) is not None for p in parts):
        return parts
    return [v]


#: RCD2000-style unindexed member fields → (member field, canonical unit)
_RCD_MEMBER_FIELD = {
    "spanlength": ("length", "m"),
    "span": ("length", "m"),
    "udl": ("udl", "kN/m"),
    "wt": ("wt", "kN/m"),
    "wb": ("wb", "kN/m"),
    "pl": ("pl", "kN"),
    "ap": ("ap", "m"),
}

#: state key → (min, max) supported by the page widget; values outside are
#: clamped with a warning (the app spinboxes are all >= 0).
_RANGE = {
    "column": {
        "bx": (100, None), "by": (100, None), "dia": (100, None),
        "depth": (100, None),
        "col_max_steel": (0, 25), "col_dh": (0, 1),
    },
    "beam": {},
    "slab": {},
    "stair": {},
    "base": {},
    "cont_beam": {},
}


def _clamp(module: str, key: str, v: float) -> tuple[float, str | None]:
    """Clamp *v* to the page-supported range; return (value, warning)."""
    lo, hi = _RANGE.get(module, {}).get(key, (0, None))
    warn = None
    if lo is not None and v < lo:
        warn = f"{v:g} outside supported range (min {lo:g}) - clamped"
        v = lo
    if hi is not None and v > hi:
        warn = f"{v:g} outside supported range (max {hi:g}) - clamped"
        v = hi
    return v, warn


def _store(module: str, target: dict, key: str, v: float,
           header: str, warnings: list[str]) -> None:
    """Clamp + store a mapped value, surfacing any clamping warning."""
    v, warn = _clamp(module, key, v)
    if warn:
        warnings.append(f"{header}: {warn}")
    target[key] = v

def map_row(module: str, row: dict[str, str]) -> tuple[dict, str | None, list[str]]:
    """Map one raw row → (state dict, label, warnings).

    Member arrays (beam spans, continuous-beam members, slab spans/point
    loads) are collapsed into the page's ``members`` / ``cont_spans`` /
    ``panel_pls`` lists; ``n_members``/``n_supports`` are derived.
    """
    state: dict = {}
    warnings: list[str] = []
    label: str | None = None
    members: dict[int, dict] = {}
    panel_pls: dict[int, dict] = {}
    cont_spans: dict[int, dict] = {}
    combined_cols: dict[int, dict] = {}
    # Slab: PL/AP columns route to continuous spans for type 3 panels,
    # otherwise to the panel point loads (types 1/2).
    cont_mode = False
    if module == "slab":
        for h, raw in row.items():
            if raw.strip() and _header_field(module, h) == "slab_type":
                _, kind, unit = _FIELD[module]["slab_type"]
                v, _w = unit(norm_value(raw))
                cont_mode = v == 2
                break
    for header, raw in row.items():
        if not header or not raw.strip():
            continue
        # label columns
        if header in _LABEL_ALIAS[module]:
            label = norm_value(raw)
            continue
        # RCD2000-style unindexed member fields → member 1
        if module in ("beam", "cont_beam") and header in _RCD_MEMBER_FIELD:
            mfield, munit = _RCD_MEMBER_FIELD[header]
            for val in _split_list(raw):
                v, w = parse_value(val, munit)
                if v is None:
                    warnings.append(f"{header}: {w}")
                    continue
                _store(module, members.setdefault(1, {}), mfield, v, header, warnings)
            continue
        # RCD2000-style 'Section Size = 300 x 500'
        if header == "sectionsize" and module in ("beam", "column"):
            dims = _split_list(raw.replace("x", ","))
            if module == "beam" and len(dims) == 2:
                v1, w1 = parse_value(dims[0], "mm")
                v2, w2 = parse_value(dims[1], "mm")
                if v1 is None:
                    warnings.append(f"{header}: {w1}")
                else:
                    _store(module, state, "b_b", v1, header, warnings)
                if v2 is None:
                    warnings.append(f"{header}: {w2}")
                else:
                    _store(module, state, "b_h", v2, header, warnings)
            elif module == "column" and len(dims) == 2:
                v1, w1 = parse_value(dims[0], "mm")
                v2, w2 = parse_value(dims[1], "mm")
                if v1 is None:
                    warnings.append(f"{header}: {w1}")
                else:
                    _store(module, state, "bx", v1, header, warnings)
                if v2 is None:
                    warnings.append(f"{header}: {w2}")
                else:
                    _store(module, state, "by", v2, header, warnings)
            else:
                warnings.append(f"{header}: expected two dimensions")
            continue
        # member-array columns (beam, cont_beam, slab, column-combined only)
        member_hit = False
        if module in ("beam", "cont_beam", "slab", "column"):
            for pat, mfield, munit in _MEMBER_PATTERNS:
                m = pat.match(header)
                if not m:
                    continue
                member_hit = True
                idx = int(m.group(1))
                if module == "column" and not mfield.startswith("combined_col_"):
                    member_hit = False
                    break
                if mfield.startswith("combined_col_"):
                    k = mfield[len("combined_col_"):]
                    for val in _split_list(raw):
                        v, w = parse_value(val, munit)
                        if v is None:
                            warnings.append(f"{header}: {w}")
                            continue
                        _store(module, combined_cols.setdefault(idx, {}), k, v, header, warnings)
                    continue
                if module == "slab":
                    if mfield in ("pl", "ap"):
                        if cont_mode:
                            target = cont_spans
                        else:
                            target = panel_pls
                        for val in _split_list(raw):
                            v, w = parse_value(val, munit)
                            if v is None:
                                warnings.append(f"{header}: {w}")
                                continue
                            _store(module, target.setdefault(idx, {}), mfield, v, header, warnings)
                        continue
                    if mfield in ("length", "udl"):
                        for val in _split_list(raw):
                            v, w = parse_value(val, munit)
                            if v is None:
                                warnings.append(f"{header}: {w}")
                                continue
                            _store(module, cont_spans.setdefault(idx, {}), mfield, v, header, warnings)
                        continue
                    warnings.append(f"Unused column: {header}")
                    continue
                if module == "beam" and mfield not in ("inertia", "e_mod"):
                    for val in _split_list(raw):
                        v, w = parse_value(val, munit)
                        if v is None:
                            warnings.append(f"{header}: {w}")
                            continue
                        _store(module, members.setdefault(idx, {}), mfield, v, header, warnings)
                    continue
                if module == "cont_beam":
                    for val in _split_list(raw):
                        v, w = parse_value(val, munit)
                        if v is None:
                            warnings.append(f"{header}: {w}")
                            continue
                        _store(module, members.setdefault(idx, {}), mfield, v, header, warnings)
                    continue
                warnings.append(f"Unused column: {header}")
                continue
        if member_hit:
            continue

        # plain fields
        field = _header_field(module, header)
        if field is None or field == "_member":
            warnings.append(f"Ignored unknown column: {header}")
            continue
        _, kind, unit = _FIELD[module][field]
        if kind == "combo":
            v, w = unit(norm_value(raw))
            if v is None:
                warnings.append(f"{header}: {w}")
                continue
            state[field] = v
        elif kind == "int":
            v, w = parse_int(raw)
            if v is None:
                warnings.append(f"{header}: {w}")
                continue
            _store(module, state, field, float(v), header, warnings)
            state[field] = int(state[field])
        else:
            values = _split_list(raw)
            if len(values) > 1:
                warnings.append(f"{header}: multiple values on a single-value field - kept first")
            v, w = parse_value(values[0], unit)
            if v is None:
                warnings.append(f"{header}: {w}")
                continue
            _store(module, state, field, v, header, warnings)

    # assemble member lists
    if members:
        max_i = max(members)
        state["members"] = [dict(members.get(i, {})) for i in range(1, max_i + 1)]
        state["n_members"] = len(state["members"])
        state["n_supports"] = max(state.get("n_supports", 0), len(state["members"]) + 1)
    if panel_pls:
        max_i = max(panel_pls)
        state["panel_pls"] = [dict(panel_pls.get(i, {})) for i in range(1, max_i + 1)]
        if "panel_npl" not in state:
            state["panel_npl"] = len(state["panel_pls"])
    if cont_spans:
        max_i = max(cont_spans)
        state["cont_spans"] = [dict(cont_spans.get(i, {})) for i in range(1, max_i + 1)]
        if "cont_nspan" not in state:
            state["cont_nspan"] = len(state["cont_spans"])
        if state.get("slab_type") not in (2, None):
            warnings.append(
                "continuous span columns present but slab type is not Continuous - "
                "set slab type to 'Continuous' (3) to use them"
            )
    if combined_cols:
        max_i = max(combined_cols)
        state["combined_columns"] = [dict(combined_cols.get(i, {}))
                                     for i in range(1, max_i + 1)]
    return state, label, warnings


def map_table(module: str, table: Table) -> tuple[list[dict], list[str | None], list[str]]:
    """Map every row of *table* → (states, labels, warnings)."""
    states, labels, warnings = [], [], []
    for i, row in enumerate(table.rows):
        if table.row_modules and table.row_modules[i] not in (None, module):
            warnings.append(
                f"Row {i + 1}: skipped ({table.row_modules[i]} block) - "
                f"import one design type per file")
            states.append({})
            labels.append(None)
            continue
        s, l, w = map_row(module, row)
        if l is None and table.row_labels:
            l = table.row_labels[i]
        states.append(s)
        labels.append(l)
        warnings.extend(w)
    return states, labels, warnings


# ── Job building ────────────────────────────────────────────────────────

def build_job(name: str, header: dict | None, items: list[tuple[str, dict, str | None]]
              ) -> object:
    """Create a Job from (type_key, state, label) specs.

    Labels fall back to auto (C1, B1, …) when absent or duplicated.
    """
    from rcd2000.gui.job import Job, make_slug
    job = Job(slug=make_slug(name), name=name, header=header or {})
    used: set[str] = set()
    for type_key, state, label in items:
        it = job.add_item(type_key)
        it.state = dict(state)
        if label:
            if label in used:
                label = None
            else:
                used.add(label)
                it.label = label
    return job


def header_materials(states: list[dict]) -> dict:
    """Consensus header material values from imported rows.

    A key is included only when every row agrees, so
    ``apply_header_defaults`` cannot overwrite per-design values.
    """
    candidates = {
        "fcu": ("col_fcu", "beam_fcu", "slab_fcu", "base_fcu"),
        "fy": ("col_fy", "beam_fy", "slab_fy", "base_fy"),
        "fyv": ("beam_fyv",),
        "soil_pressure": ("base_pb",),
        "max_steel_pct": ("col_max_steel",),
        "dh": ("col_dh",),
    }
    out: dict = {}
    for hkey, state_keys in candidates.items():
        values = set()
        for s in states:
            for k in state_keys:
                if k in s:
                    values.add(s[k])
                    break
        if len(values) == 1:
            out[hkey] = values.pop()
    return out


# ── Templates ───────────────────────────────────────────────────────────

#: template column list per module: (display header, state key or pattern)
_TEMPLATE = {
    "column": [
        "Column ID", "TYPE", "SHAPE", "LOAD [kN]", "BX [mm]", "BY [mm]",
        "DIA [mm]", "DEPTH [mm]", "LENGTH [m]", "LE [m]", "LEX [m]", "LEY [m]",
        "FCU [N/mm2]", "FY [N/mm2]", "MAX STEEL [%]", "DH",
        "MX [kN.m]", "MY [kN.m]", "M [kN.m]",
    ],
    "beam": [
        "Beam ID", "FCU [N/mm2]", "FY [N/mm2]", "FYV [N/mm2]",
        "B [mm]", "BF [mm]", "H [mm]", "HF [mm]",
        "N SUPPORTS", "N MEMBERS", "END 1", "END 2",
        "CANT LOAD 1 [kN/m]", "CANT MOMENT 1 [kN.m]",
        "CANT LOAD 2 [kN/m]", "CANT MOMENT 2 [kN.m]",
    ] + [f"L{i} [m]" for i in range(1, 5)] + [f"UDL{i} [kN/m]" for i in range(1, 5)]
    + [f"WT{i} [kN/m]" for i in range(1, 5)] + [f"WB{i} [kN/m]" for i in range(1, 5)]
    + [f"AB{i} [m]" for i in range(1, 5)] + [f"PL{i} [kN]" for i in range(1, 5)]
    + [f"AP{i} [m]" for i in range(1, 5)],
    "slab": [
        "Panel No", "TYPE", "FCU [N/mm2]", "FY [N/mm2]", "DEPTH [mm]",
        "SPAN [m]", "LY [m]", "CASE", "SPAN/DEPTH", "GK [kN/m2]", "QK [kN/m2]",
        "CANT LOAD 1 [kN/m]", "CANT MOMENT 1 [kN.m]",
        "CANT LOAD 2 [kN/m]", "CANT MOMENT 2 [kN.m]",
    ] + [f"SPAN LENGTH {i} [m]" for i in range(1, 5)]
    + [f"UDL{i} [kN/m]" for i in range(1, 5)] + [f"PL{i} [kN]" for i in range(1, 5)]
    + [f"AP{i} [m]" for i in range(1, 5)],
    "stair": [
        "Stair Ref", "SPAN [m]", "TREAD [mm]", "RISE [mm]",
        "IMPOSED [kN/m2]", "SUPERIMPOSED [kN/m2]", "WLD [kN/m3]",
        "GK [kN/m2]", "QK [kN/m2]",
    ],
    "base": [
        "Base Ref", "TYPE", "COL SHAPE", "FCU [N/mm2]", "FY [N/mm2]",
        "PB [kN/m2]", "LOAD [kN]", "A1 [mm]", "A2 [mm]", "DIA [mm]",
        "H [mm]", "L1 [m]", "L2 [m]", "DOWEL [mm]", "GK [kN/m2]", "QK [kN/m2]",
    ],
    "cont_beam": [
        "Continuous Beam Ref", "NS", "NM", "END 1", "END 2",
        "CANT LOAD 1 [kN/m]", "CANT MOMENT 1 [kN.m]",
        "CANT LOAD 2 [kN/m]", "CANT MOMENT 2 [kN.m]",
    ] + [f"L{i} [m]" for i in range(1, 5)] + [f"INERTIA{i} [m4]" for i in range(1, 5)]
    + [f"E{i}" for i in range(1, 5)] + [f"UDL{i} [kN/m]" for i in range(1, 5)]
    + [f"WT{i} [kN/m]" for i in range(1, 5)] + [f"WB{i} [kN/m]" for i in range(1, 5)]
    + [f"AB{i} [m]" for i in range(1, 5)] + [f"PL{i} [kN]" for i in range(1, 5)]
    + [f"AP{i} [m]" for i in range(1, 5)],
}

_TEMPLATE_UNITS = {
    "column": "mm for section sizes, m for lengths, kN, kN.m, N/mm2, %",
    "beam": "mm for section sizes, m for spans, kN/m for UDL, kN, kN.m, N/mm2",
    "slab": "m for spans, mm for depth, kN/m2 for GK/QK, kN.m",
    "stair": "m for span, mm for tread/rise, kN/m2, kN/m3",
    "base": "m for L1/L2, mm for column/base sizes, kN/m2 for PB, kN, N/mm2",
    "cont_beam": "m for spans, m4 for inertia, kN/m, kN, kN.m",
}


def write_template(module: str, path: str) -> None:
    """Write a fill-in CSV template for *module*."""
    headers = _TEMPLATE[module]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["# RCD2000 %s - one design per row. Units are in [brackets]."
                    % module.replace("_", " ").title()])
        w.writerow(["# " + _TEMPLATE_UNITS[module]])
        w.writerow(["# Leave unused columns empty."])
        w.writerow(headers)
        w.writerow([])


# ── Top-level entry point ───────────────────────────────────────────────

def _rcd_job_ref(path: str) -> str | None:
    """Best-effort 'JOB REF: …' capture from an RCD2000 output file."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r"^\s*job\s*ref\s*:\s*(.+?)\s*$", line, re.I)
                if m:
                    return m.group(1).strip() or None
    except OSError:
        pass
    return None


def parse_file(path: str) -> ParsedFile | None:
    """Detect + parse + score *path* into a ParsedFile (None on failure)."""
    fmt = detect_format(path)
    if fmt is None:
        return None
    name = os.path.splitext(os.path.basename(path))[0]
    warnings: list[str] = []
    if fmt == "jobjson":
        return parse_job_json(path)
    if fmt == "rcd2000":
        table = parse_rcd2000_output(path)
        mods = {m for m in table.row_modules if m}
        module = next(iter(mods)) if len(mods) == 1 else None
        if len(mods) > 1:
            warnings.append(
                "Mixed design types in one file - import them one type at a time.")
        job_ref = _rcd_job_ref(path)
        return ParsedFile(fmt, table, module, name, job_ref=job_ref,
                          warnings=warnings)
    if fmt == "keyvalue":
        table = parse_keyvalue(path)
    else:
        table = parse_csv_or_xlsx(path)
    module = detect_module(table.headers)
    if module is None:
        warnings.append("Could not auto-detect the design type - choose it in the preview.")
    return ParsedFile(fmt, table, module, name, warnings=warnings)
