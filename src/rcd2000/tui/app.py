import re
from typing import Any, ClassVar

from textual import on
from textual.reactive import reactive
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.widgets import (
    Button,
    Input,
    Static,
    TabbedContent,
    TabPane,
)

from rcd2000.base import BaseDesigner, BaseInput
from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.continuous_beam import ContinuousBeamAnalyzer, ContinuousBeamInput, ContinuousBeamMember
from rcd2000.report import format_base, format_beam, format_column, format_continuous_beam, format_slab, format_stair
from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.stair import StairDesigner, StairInput


def _floats(val: str) -> list[float]:
    return [float(x) for x in re.split(r"[\s,;]+", val.strip()) if x]


def _point_loads(val: str) -> list[tuple[float, float]]:
    result = []
    for part in re.split(r"[\s;]+", val.strip()):
        if not part:
            continue
        part = part.strip("()[]")
        nums = part.split(",")
        if len(nums) == 2:
            result.append((float(nums[0]), float(nums[1])))
    return result


class FieldRow(Horizontal):
    def __init__(self, label: str, widget: Any, unit: str = "") -> None:
        super().__init__(classes="field-row")
        self._label_text = label
        self._field_widget = widget
        self._unit_text = unit

    def compose(self) -> ComposeResult:
        yield Static(self._label_text, classes="field-label")
        yield self._field_widget
        if self._unit_text:
            yield Static(self._unit_text, classes="field-unit")


class SectionBox(Vertical):
    def __init__(self, title: str, *children: Any) -> None:
        super().__init__(classes="section-box")
        self._title = title
        self._children = children

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="section-title")
        for child in self._children:
            yield child


class ResultsPanel(Vertical):
    def show_text(self, text: str) -> ComposeResult:
        for line in text.split("\n"):
            if line.strip():
                yield Static(line)

    def render_result(self, result: Any) -> ComposeResult:
        if hasattr(result, "__dataclass_fields__"):
            for field_name, field_info in result.__dataclass_fields__.items():
                val = getattr(result, field_name)
                if isinstance(val, float):
                    yield Static(f"  {field_name}: {val:.4f}")
                elif isinstance(val, bool):
                    yield Static(f"  {field_name}: {'OK' if val else 'FAIL'}")
                elif isinstance(val, list):
                    count = len(val)
                    if count <= 10:
                        yield Static(f"  {field_name}: {val!r}")
                    else:
                        yield Static(f"  {field_name}: [{count} items]")
                else:
                    yield Static(f"  {field_name}: {val!r}")
        else:
            yield Static(str(result))

    def clear(self) -> None:
        for w in list(self.children):
            w.remove()


def _input(placeholder: str = "") -> Input:
    return Input(placeholder=placeholder)


def _choice(default: str = "1") -> Input:
    """A multiple-choice field, DOS-style: you type the option number
    instead of navigating a dropdown or radio list. Every field in the
    form now works the same way - type a value, Tab to the next one."""
    return Input(placeholder=default)


class ColumnScreen(ScrollableContainer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._widgets: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        col_type = _choice("1")
        shape = _choice("1")
        field_id = _input("e.g. C1")
        load = _input("0")
        bx = _input("0")
        by = _input("0")
        dia = _input("0")
        depth = _input("0")
        length = _input("0")
        le = _input("0")
        lex = _input("0")
        ley = _input("0")
        mx = _input("0")
        my = _input("0")
        moment = _input("0")
        fcu = _input("25")
        fy = _input("460")

        self._widgets["col_type"] = col_type
        self._widgets["shape"] = shape
        self._widgets["col_id"] = field_id
        self._widgets["load"] = load
        self._widgets["bx"] = bx
        self._widgets["by"] = by
        self._widgets["dia"] = dia
        self._widgets["depth"] = depth
        self._widgets["length"] = length
        self._widgets["le"] = le
        self._widgets["lex"] = lex
        self._widgets["ley"] = ley
        self._widgets["mx"] = mx
        self._widgets["my"] = my
        self._widgets["moment"] = moment
        self._widgets["fcu"] = fcu
        self._widgets["fy"] = fy

        yield Static("Column Design  -  BS 8110 Clause 3.8", classes="section-title")
        yield SectionBox(
            "General",
            FieldRow("Column ID", field_id),
            FieldRow("Column Type (1=Axial 2=Uniaxial 3=Biaxial)", col_type),
            FieldRow("Shape (1=Rectangular 2=Circular)", shape),
        )
        yield SectionBox(
            "Loading",
            FieldRow("Axial Load", load, "kN"),
        )
        yield SectionBox(
            "Section Dimensions",
            FieldRow("Width bx", bx, "mm"),
            FieldRow("Width by", by, "mm"),
            FieldRow("Diameter (circular)", dia, "mm"),
            FieldRow("Depth", depth, "mm"),
            FieldRow("Column Height", length, "m"),
            FieldRow("Effective Length Le", le, "m"),
            FieldRow("Effective Length x (Lex)", lex, "m"),
            FieldRow("Effective Length y (Ley)", ley, "m"),
        )
        yield SectionBox(
            "Moments",
            FieldRow("Moment about x (Mx)", mx, "kN.m"),
            FieldRow("Moment about y (My)", my, "kN.m"),
            FieldRow("Moment (uniaxial)", moment, "kN.m"),
        )
        yield SectionBox(
            "Material Properties",
            FieldRow("fcu", fcu, "N/mm²"),
            FieldRow("fy", fy, "N/mm²"),
        )
        yield Horizontal(
            Button("Calculate", variant="primary", id="calc-btn"),
            Button("Clear Form", id="clear-btn"),
            Button("Show Report", id="report-btn"),
            classes="button-bar",
        )

    def get_inputs(self) -> dict[str, Any]:
        w = self._widgets
        def _f(key: str, default: float = 0) -> float:
            v = w[key].value
            return float(v) if v else default
        def _i(key: str, default: int = 1) -> int:
            v = w[key].value
            try:
                return int(v) if v else default
            except ValueError:
                return default
        return {
            "column_id": w["col_id"].value or "C1",
            "col_type": _i("col_type", 1),
            "shape": _i("shape", 1),
            "load": _f("load", 0),
            "bx": _f("bx", 0),
            "by": _f("by", 0),
            "dia": _f("dia", 0),
            "depth": _f("depth", 0),
            "length": _f("length", 0),
            "le": _f("le", 0),
            "lex": _f("lex", 0),
            "ley": _f("ley", 0),
            "moment_x": _f("mx", 0),
            "moment_y": _f("my", 0),
            "moment": _f("moment", 0),
        }

    def calculate(self):
        d = self.get_inputs()
        ci = ColumnInput(**d)
        designer = ColumnDesigner()
        return designer.design([ci])[0], d


class BeamScreen(ScrollableContainer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._widgets: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        beam_id = _input("e.g. B1")
        n_supports = _input("2")
        n_members = _input("1")
        b = _input("300")
        bf = _input("0")
        h = _input("500")
        hf = _input("0")
        fcu = _input("25")
        fy = _input("460")
        fyv = _input("250")
        ty1 = _choice("1")
        ty2 = _choice("1")
        cant_load_1 = _input("0")
        cant_moment_1 = _input("0")
        cant_load_2 = _input("0")
        cant_moment_2 = _input("0")
        member_lengths = _input("6.0")
        member_udl = _input("0")
        member_wt = _input("0")
        member_wb = _input("0")
        member_ab = _input("0")
        member_npl = _input("0")
        member_pl = _input("(load_kN,dist_m);(load_kN,dist_m)")

        self._widgets.update(dict(
            beam_id=beam_id, n_supports=n_supports, n_members=n_members,
            b=b, bf=bf, h=h, hf=hf, fcu=fcu, fy=fy, fyv=fyv,
            ty1=ty1, ty2=ty2,
            cant_load_1=cant_load_1, cant_moment_1=cant_moment_1,
            cant_load_2=cant_load_2, cant_moment_2=cant_moment_2,
            member_lengths=member_lengths, member_udl=member_udl,
            member_wt=member_wt, member_wb=member_wb, member_ab=member_ab,
            member_npl=member_npl, member_pl=member_pl,
        ))

        yield Static("Continuous Beam Design  -  BS 8110 Clause 3.4", classes="section-title")
        yield SectionBox(
            "General",
            FieldRow("Beam ID", beam_id),
            FieldRow("No. of Supports", n_supports),
            FieldRow("No. of Members", n_members),
        )
        yield SectionBox(
            "Section Dimensions",
            FieldRow("Beam Width b", b, "mm"),
            FieldRow("Flange Width bf", bf, "mm"),
            FieldRow("Overall Depth h", h, "mm"),
            FieldRow("Flange Depth hf", hf, "mm"),
        )
        yield SectionBox(
            "Material Properties",
            FieldRow("fcu", fcu, "N/mm²"),
            FieldRow("fy", fy, "N/mm²"),
            FieldRow("fyv (stirrup steel)", fyv, "N/mm²"),
        )
        yield SectionBox(
            "End Conditions",
            FieldRow("End 1 Type (0=Pinned 1=Fixed)", ty1),
            FieldRow("End 2 Type (0=Pinned 1=Fixed)", ty2),
            FieldRow("Cantilever Load 1", cant_load_1, "kN"),
            FieldRow("Cantilever Moment 1", cant_moment_1, "kN.m"),
            FieldRow("Cantilever Load 2", cant_load_2, "kN"),
            FieldRow("Cantilever Moment 2", cant_moment_2, "kN.m"),
        )
        yield SectionBox(
            "Member Loading (comma/space separated per member)",
            FieldRow("Member Lengths (m)", member_lengths),
            FieldRow("UDL (kN/m)", member_udl),
            FieldRow("Triangular Load wt (kN/m)", member_wt),
            FieldRow("Trapezoidal Load wb (kN/m)", member_wb),
            FieldRow("Trap. Distance ab (m)", member_ab),
            FieldRow("Pt. Loads per span npl", member_npl),
            FieldRow("Pt. Loads (load,dist_m)", member_pl),
        )
        yield Horizontal(
            Button("Calculate", variant="primary", id="calc-btn"),
            Button("Clear Form", id="clear-btn"),
            Button("Show Report", id="report-btn"),
            classes="button-bar",
        )

    def get_inputs(self) -> dict[str, Any]:
        w = self._widgets
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        def _s(key: str, default: str = "") -> str:
            return w[key].value or default
        return {
            "beam_id": w["beam_id"].value or "B1",
            "n_supports": max(2, round(_f("n_supports", 2))),
            "n_members": max(1, round(_f("n_members", 1))),
            "b": _f("b", 300),
            "bf": _f("bf", 0),
            "h": _f("h", 500),
            "hf": _f("hf", 0),
            "fcu": _f("fcu", 25),
            "fy": _f("fy", 460),
            "fyv": _f("fyv", 250),
            "member_lengths": _floats(_s("member_lengths", "6.0")),
            "member_udl": _floats(_s("member_udl", "0")),
            "member_wt": _floats(_s("member_wt", "0")),
            "member_wb": _floats(_s("member_wb", "0")),
            "member_ab": _floats(_s("member_ab", "0")),
            "member_npl": [int(x) for x in _floats(_s("member_npl", "0"))],
            "member_pl": [_point_loads(w["member_pl"].value)],
            "support_grid": [],
            "ty1": int(w["ty1"].value or "1"),
            "ty2": int(w["ty2"].value or "1"),
            "cant_load_1": _f("cant_load_1", 0),
            "cant_moment_1": _f("cant_moment_1", 0),
            "cant_load_2": _f("cant_load_2", 0),
            "cant_moment_2": _f("cant_moment_2", 0),
        }

    def calculate(self):
        d = self.get_inputs()
        bi = BeamInput(**d)
        designer = BeamDesigner(fcu=d["fcu"], fy=d["fy"], fyv=d["fyv"])
        return designer.design([bi])[0], d


class SlabScreen(ScrollableContainer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._widgets: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        panel_type = _choice("1")
        panel_id = _input("e.g. S1")
        depth = _input("200")
        fcu = _input("25")
        fy = _input("460")
        udl = _input("0")
        span = _input("0")
        ly = _input("0")
        ratio = _input("20")
        npl = _input("0")
        point_loads = _input("(load,dist);(load,dist)")
        nspan = _input("0")
        span_lengths = _input("6.0")
        span_udls = _input("0")
        span_npls = _input("0")
        span_pls = _input("(load,dist);(load,dist) / (load,dist);(load,dist)")
        cant_moments = _input("0")
        cant_loads = _input("0")
        case = _choice("1")

        self._widgets.update(dict(
            panel_type=panel_type, panel_id=panel_id, depth=depth,
            fcu=fcu, fy=fy, udl=udl, span=span, ly=ly, ratio=ratio,
            npl=npl, point_loads=point_loads, nspan=nspan,
            span_lengths=span_lengths, span_udls=span_udls,
            span_npls=span_npls, span_pls=span_pls,
            cant_moments=cant_moments, cant_loads=cant_loads,
            case=case,
        ))

        yield Static("Slab Design  -  BS 8110 Clause 3.5 & 3.6", classes="section-title")
        yield SectionBox(
            "General",
            FieldRow("Panel ID", panel_id),
            FieldRow("Type (1=Cantilever 2=Simply Supp. 3=Continuous 4=Two-way)", panel_type),
            FieldRow("Slab Depth", depth, "mm"),
            FieldRow("Span", span, "m"),
            FieldRow("Long Span ly", ly, "m"),
            FieldRow("Span/Eff Depth Ratio", ratio),
        )
        yield SectionBox(
            "Material Properties",
            FieldRow("fcu", fcu, "N/mm²"),
            FieldRow("fy", fy, "N/mm²"),
        )
        yield SectionBox(
            "Loading",
            FieldRow("UDL", udl, "kN/m"),
            FieldRow("No. of Pt. Loads", npl),
            FieldRow("Point Loads (load,dist)", point_loads),
        )
        yield SectionBox(
            "Continuous Slab",
            FieldRow("No. of Spans", nspan),
            FieldRow("Span Lengths (m)", span_lengths),
            FieldRow("Span UDLs (kN/m)", span_udls),
            FieldRow("Pt. Loads/span", span_npls),
            FieldRow("Pt. Loads/span list", span_pls),
            FieldRow("Cant. End Moments (kN.m)", cant_moments),
            FieldRow("Cant. End Loads (kN)", cant_loads),
        )
        yield SectionBox(
            "Two-way Slab",
            FieldRow("Case (1-9, BS 8110 Table 3.14)", case),
        )
        yield Horizontal(
            Button("Calculate", variant="primary", id="calc-btn"),
            Button("Clear Form", id="clear-btn"),
            Button("Show Report", id="report-btn"),
            classes="button-bar",
        )

    def get_inputs(self) -> dict[str, Any]:
        w = self._widgets
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        def _s(key: str, default: str = "") -> str:
            return w[key].value or default
        return {
            "panel_id": w["panel_id"].value or "S1",
            "panel_type": int(w["panel_type"].value or "1"),
            "depth": _f("depth", 200),
            "fcu": _f("fcu", 25),
            "fy": _f("fy", 460),
            "udl": _f("udl", 0),
            "span": _f("span", 0),
            "ly": _f("ly", 0),
            "span_depth_ratio": _f("ratio", 20),
            "npl": int(_f("npl", 0)),
            "point_loads": _point_loads(_s("point_loads", "")),
            "nspan": int(_f("nspan", 0)),
            "span_lengths": _floats(_s("span_lengths", "6.0")),
            "span_udls": _floats(_s("span_udls", "0")),
            "span_npls": [int(x) for x in _floats(_s("span_npls", "0"))],
            "span_pls": [],
            "cant_moments": _floats(_s("cant_moments", "0")),
            "cant_loads": _floats(_s("cant_loads", "0")),
            "case": int(w["case"].value or "1"),
        }

    def calculate(self):
        d = self.get_inputs()
        pi = SlabPanelInput(**d)
        designer = SlabDesigner(fcu=d["fcu"], fy=d["fy"])
        return designer.design([pi])[0], d


class StairScreen(ScrollableContainer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._widgets: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        stair_id = _input("e.g. ST1")
        span = _input("0")
        tread = _input("0")
        rise = _input("0")
        imposed = _input("0")
        spl = _input("0")
        wld = _input("0")
        cw = _input("25")

        self._widgets.update(dict(
            stair_id=stair_id, span=span, tread=tread, rise=rise,
            imposed=imposed, spl=spl, wld=wld, cw=cw,
        ))

        yield Static("Stair Design  -  BS 8110 Clause 3.9", classes="section-title")
        yield SectionBox("General", FieldRow("Stair ID", stair_id))
        yield SectionBox("Geometry", FieldRow("Span", span, "m"), FieldRow("Tread", tread, "mm"), FieldRow("Rise", rise, "mm"))
        yield SectionBox("Loading", FieldRow("Imposed Load", imposed, "kN/m²"), FieldRow("Sup. Dead Load", spl, "kN/m²"), FieldRow("Waterproof Load", wld, "kN/m²"), FieldRow("Concrete Weight", cw, "kN/m³"))
        yield Horizontal(
            Button("Calculate", variant="primary", id="calc-btn"),
            Button("Clear Form", id="clear-btn"),
            Button("Show Report", id="report-btn"),
            classes="button-bar",
        )

    def get_inputs(self) -> dict[str, Any]:
        w = self._widgets
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        return {
            "stair_id": w["stair_id"].value or "ST1",
            "stair_type": 1,
            "span": _f("span", 0),
            "tread": _f("tread", 0),
            "rise": _f("rise", 0),
            "imposed_load": _f("imposed", 0),
            "spl": _f("spl", 0),
            "wld": _f("wld", 0),
            "concrete_weight": _f("cw", 25),
        }

    def calculate(self):
        d = self.get_inputs()
        si = StairInput(**d)
        designer = StairDesigner(fcu=25.0, fy=460.0)
        return designer.design([si])[0], d


class BaseScreen(ScrollableContainer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._widgets: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        base_type = _choice("1")
        col_shape = _choice("1")
        base_id = _input("e.g. F1")
        load_v = _input("0")
        pb_v = _input("150")
        fcu_v = _input("25")
        fy_v = _input("460")
        a1 = _input("0")
        a2 = _input("0")
        dia_v = _input("0")
        dowel = _input("0")
        h_v = _input("200")
        l1 = _input("0")
        l2 = _input("0")

        self._widgets.update(dict(
            base_type=base_type, col_shape=col_shape, base_id=base_id,
            load=load_v, pb=pb_v, fcu=fcu_v, fy=fy_v,
            a1=a1, a2=a2, dia=dia_v, dowel=dowel, h=h_v, l1=l1, l2=l2,
        ))

        yield Static("Foundation Design  -  BS 8110 Clause 3.7", classes="section-title")
        yield SectionBox(
            "General",
            FieldRow("Base ID", base_id),
            FieldRow("Base Type (1=Square 2=Rectangular 3=Combined)", base_type),
            FieldRow("Column Shape (1=Rectangular 2=Circular)", col_shape),
        )
        yield SectionBox("Loading", FieldRow("Axial Load", load_v, "kN"))
        yield SectionBox("Material Properties", FieldRow("fcu", fcu_v, "N/mm²"), FieldRow("fy", fy_v, "N/mm²"), FieldRow("Allowable Bearing Pressure", pb_v, "kN/m²"))
        yield SectionBox("Column Dimensions", FieldRow("Dimension a1", a1, "mm"), FieldRow("Dimension a2", a2, "mm"), FieldRow("Diameter (circular)", dia_v, "mm"), FieldRow("Dowel Diameter", dowel, "mm"))
        yield SectionBox("Base Dimensions", FieldRow("Base Thickness h", h_v, "mm"), FieldRow("Base Length L1", l1, "m"), FieldRow("Base Width L2", l2, "m"))
        yield Horizontal(
            Button("Calculate", variant="primary", id="calc-btn"),
            Button("Clear Form", id="clear-btn"),
            Button("Show Report", id="report-btn"),
            classes="button-bar",
        )

    def get_inputs(self) -> dict[str, Any]:
        w = self._widgets
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        return {
            "base_id": w["base_id"].value or "F1",
            "base_type": int(w["base_type"].value or "1"),
            "col_type": int(w["col_shape"].value or "1"),
            "load": _f("load", 0),
            "pb": _f("pb", 150),
            "fcu": _f("fcu", 25),
            "fy": _f("fy", 460),
            "a1": _f("a1", 0),
            "a2": _f("a2", 0),
            "dia": _f("dia", 0),
            "dowel_dia": _f("dowel", 0),
            "h": _f("h", 200),
            "l1": _f("l1", 0),
            "l2": _f("l2", 0),
            "n_columns": 0,
            "columns": [],
        }

    def calculate(self):
        d = self.get_inputs()
        bi = BaseInput(**d)
        designer = BaseDesigner(pb=d["pb"], fcu=d["fcu"], fy=d["fy"])
        return designer.design([bi])[0], d


class ContinuousBeamScreen(ScrollableContainer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._widgets: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        n_supports = _input("2")
        n_members = _input("1")
        end1_type = _choice("0")
        end2_type = _choice("0")
        end1_cl = _input("0")
        end1_cm = _input("0")
        end2_cl = _input("0")
        end2_cm = _input("0")
        member_lengths = _input("6.0")
        member_inertia = _input("0.001")
        member_e_mod = _input("1.0")
        member_udl = _input("0")
        member_wt = _input("0")
        member_wb = _input("0")
        member_ab = _input("0")
        member_npl = _input("0")
        member_pl = _input("(load,dist);(load,dist)")

        self._widgets.update(dict(
            n_supports=n_supports, n_members=n_members,
            end1_type=end1_type, end2_type=end2_type,
            end1_cl=end1_cl, end1_cm=end1_cm, end2_cl=end2_cl, end2_cm=end2_cm,
            member_lengths=member_lengths, member_inertia=member_inertia,
            member_e_mod=member_e_mod, member_udl=member_udl,
            member_wt=member_wt, member_wb=member_wb, member_ab=member_ab,
            member_npl=member_npl, member_pl=member_pl,
        ))

        yield Static("Continuous Beam Analysis  -  Clapeyron Three-Moment", classes="section-title")
        yield SectionBox(
            "General",
            FieldRow("No. of Supports", n_supports),
            FieldRow("No. of Members", n_members),
        )
        yield SectionBox(
            "End Conditions",
            FieldRow("End 1 Type (0=Pinned 1=Fixed)", end1_type),
            FieldRow("End 2 Type (0=Pinned 1=Fixed)", end2_type),
            FieldRow("Cantilever Load 1", end1_cl, "kN"),
            FieldRow("Cantilever Moment 1", end1_cm, "kN.m"),
            FieldRow("Cantilever Load 2", end2_cl, "kN"),
            FieldRow("Cantilever Moment 2", end2_cm, "kN.m"),
        )
        yield SectionBox(
            "Member Properties (comma/space separated)",
            FieldRow("Member Lengths (m)", member_lengths),
            FieldRow("Moment of Inertia I (m⁴)", member_inertia),
            FieldRow("Relative E-mod E/Es", member_e_mod),
            FieldRow("UDL (kN/m)", member_udl),
            FieldRow("Triangular Load (kN/m)", member_wt),
            FieldRow("Trapezoidal Load (kN/m)", member_wb),
            FieldRow("Trap. Load Dist. (m)", member_ab),
            FieldRow("Pt. Loads per span", member_npl),
            FieldRow("Pt. Loads (load,dist)", member_pl),
        )
        yield Horizontal(
            Button("Calculate", variant="primary", id="calc-btn"),
            Button("Clear Form", id="clear-btn"),
            Button("Show Report", id="report-btn"),
            classes="button-bar",
        )

    def get_inputs(self) -> dict[str, Any]:
        w = self._widgets
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        def _s(key: str, default: str = "") -> str:
            return w[key].value or default
        nm = max(1, round(_f("n_members", 1)))
        lengths = _floats(_s("member_lengths", "6.0"))
        inertias = _floats(_s("member_inertia", "0.001"))
        e_mods = _floats(_s("member_e_mod", "1.0"))
        udls = _floats(_s("member_udl", "0"))
        wts = _floats(_s("member_wt", "0"))
        wbs = _floats(_s("member_wb", "0"))
        abs_ = _floats(_s("member_ab", "0"))
        members = []
        for i in range(nm):
            members.append(
                ContinuousBeamMember(
                    member_id=f"M{i+1}",
                    length=lengths[i] if i < len(lengths) else 6.0,
                    inertia=inertias[i] if i < len(inertias) else 0.001,
                    e_mod=e_mods[i] if i < len(e_mods) else 1.0,
                    udl=udls[i] if i < len(udls) else 0,
                    wt=wts[i] if i < len(wts) else 0,
                    wb=wbs[i] if i < len(wbs) else 0,
                    ab=abs_[i] if i < len(abs_) else 0,
                    npl=0,
                    point_loads=[],
                )
            )
        return {
            "n_supports": max(2, round(_f("n_supports", 2))),
            "n_members": nm,
            "members": members,
            "end1_type": int(w["end1_type"].value or "0"),
            "end2_type": int(w["end2_type"].value or "0"),
            "end1_cant_load": _f("end1_cl", 0),
            "end1_cant_moment": _f("end1_cm", 0),
            "end2_cant_load": _f("end2_cl", 0),
            "end2_cant_moment": _f("end2_cm", 0),
        }

    def calculate(self):
        d = self.get_inputs()
        cb_in = ContinuousBeamInput(**d)
        analyzer = ContinuousBeamAnalyzer()
        return analyzer.analyze(cb_in), d


SCREENS: list[tuple[str, type]] = [
    ("Column", ColumnScreen),
    ("Beam", BeamScreen),
    ("Slab", SlabScreen),
    ("Stair", StairScreen),
    ("Base", BaseScreen),
    ("Cont_Beam", ContinuousBeamScreen),
]


class RCD2000TUI(App):
    CSS_PATH = "styles.tcss"
    TITLE = "RCD2000 - Reinforced Concrete Design to BS 8110"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("f1", "show_help", "Help"),
        Binding("f2", "calculate", "Calculate"),
        Binding("f3", "clear_form", "Clear"),
        Binding("f4", "toggle_report", "Report"),
        Binding("f10", "quit", "Quit"),
        Binding("q", "quit", "Quit"),
    ]

    current_result: Any | None = None
    current_report_text: str = ""
    current_inputs: dict[str, Any] = {}
    show_report_flag: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static(" RCD2000 v1.0.0  -  Reinforced Concrete Design to BS 8110  -  Terminal UI", id="header")
        with TabbedContent(id="tabs"):
            for name, screen_cls in SCREENS:
                yield TabPane(name, screen_cls(), id=name.lower().replace(" ", "_"))
        yield Static("", id="footer")
        yield ResultsPanel(id="results-panel")

    def on_mount(self) -> None:
        self.refresh_footer()
        self.set_timer(0.1, self._focus_first_input)

    @on(TabbedContent.TabActivated)
    def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        # Whenever the user switches tabs (click or keyboard), move focus
        # into the newly visible form. Without this, focus silently stays
        # on a widget in the now-hidden tab and keystrokes appear to do
        # nothing - this was the main source of "where do I type" confusion.
        self.call_after_refresh(self._focus_first_input)

    def _focus_first_input(self) -> None:
        try:
            screen = self.get_current_screen()
            focusable = screen.query("Input")
            if focusable:
                focusable.first().focus()
        except Exception:
            pass

    def refresh_footer(self) -> None:
        footer = self.query_one("#footer", Static)
        footer.update(
            " ↹ Tab/Shift+Tab: move between fields   ⏎ Enter: next field   "
            "F1:Help  F2:Calculate  F3:Clear  F4:Report  F10:Quit"
        )

    def get_current_screen(self) -> ScrollableContainer:
        tabs = self.query_one(TabbedContent)
        pane = tabs.active_pane
        if pane is not None:
            return pane.query(ScrollableContainer).first()
        return self.query(ScrollableContainer).first()

    def action_show_help(self) -> None:
        self.notify(
            "RCD2000 TUI - Design to BS 8110\n\n"
            "Every field is a plain text box - type a value and press Tab\n"
            "(or Enter) to move to the next one, like the original DOS tool.\n"
            "For multiple-choice fields (Type, Shape, End Condition, etc.),\n"
            "just type the option number shown in the field's label.\n\n"
            "F2 or Calculate runs the design. F4 toggles the full report.\n"
            "Results show below the form.",
            title="Help",
            timeout=10,
        )

    def action_calculate(self) -> None:
        screen = self.get_current_screen()
        if not isinstance(screen, ScrollableContainer):
            return
        try:
            result, inputs = screen.calculate()
            self.current_result = result
            self.current_inputs = inputs
            self.current_report_text = self._build_report(screen, result)
            self.show_report_flag = False
            self._refresh_results()
            self.notify("Calculation complete", severity="information")
        except Exception as e:
            self.notify(f"Calculation error: {e}", severity="error")

    def action_clear_form(self) -> None:
        screen = self.get_current_screen()
        if isinstance(screen, ScrollableContainer):
            for w in screen.query(Input):
                w.value = ""
        self.current_result = None
        self.current_report_text = ""
        self.current_inputs = {}
        self.query_one("#results-panel", ResultsPanel).clear()
        self.notify("Form cleared", severity="information")
        self._focus_first_input()

    def action_toggle_report(self) -> None:
        if self.current_result is not None:
            self.show_report_flag = not self.show_report_flag

    def _build_report(self, screen: ScrollableContainer, result: Any) -> str:
        from datetime import date
        try:
            if isinstance(screen, ColumnScreen):
                return format_column(ColumnInput(**self.current_inputs), result, "RCD2000", str(date.today()), "TUI", 25, 460)
            elif isinstance(screen, BeamScreen):
                return format_beam(BeamInput(**self.current_inputs), result, "RCD2000", str(date.today()), "TUI")
            elif isinstance(screen, SlabScreen):
                return format_slab(SlabPanelInput(**self.current_inputs), result, "RCD2000", str(date.today()), "TUI")
            elif isinstance(screen, StairScreen):
                return format_stair(StairInput(**self.current_inputs), result, "RCD2000", str(date.today()), "TUI")
            elif isinstance(screen, BaseScreen):
                return format_base(BaseInput(**self.current_inputs), result, "RCD2000", str(date.today()), "TUI")
            elif isinstance(screen, ContinuousBeamScreen):
                cb_in = ContinuousBeamInput(**self.current_inputs)
                return format_continuous_beam(cb_in, result, "RCD2000", str(date.today()), "TUI")
        except Exception:
            return ""
        return ""

    def _refresh_results(self) -> None:
        rp = self.query_one("#results-panel", ResultsPanel)
        rp.clear()
        result = self.current_result
        if result is None:
            return
        if self.show_report_flag and self.current_report_text:
            for line in self.current_report_text.split("\n"):
                if line.strip():
                    rp.mount(Static(line))
        else:
            for line in rp.render_result(result):
                rp.mount(line)

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Pressing Enter in a field previously did nothing visible, which
        # read as "I typed and nothing happened." Now it just advances to
        # the next field, matching how people expect forms to behave.
        self.screen.focus_next()

    @on(Button.Pressed, "#calc-btn")
    def on_calc_button(self) -> None:
        self.action_calculate()

    @on(Button.Pressed, "#clear-btn")
    def on_clear_button(self) -> None:
        self.action_clear_form()

    @on(Button.Pressed, "#report-btn")
    def on_report_button(self) -> None:
        self.action_toggle_report()


def main() -> None:
    RCD2000TUI.run()