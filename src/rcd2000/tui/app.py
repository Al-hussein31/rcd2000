import re
from typing import Any, ClassVar

from textual import on
from textual.reactive import reactive
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button,
    Input,
    RadioButton,
    RadioSet,
    Select,
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


def _input(placeholder: str = "") -> Input:
    return Input(placeholder=placeholder)


def _select(options: list[tuple[str, str]], default: str = "") -> Select:
    return Select(options, value=default or options[0][1])


def _radio(options: list[str], default_index: int = 0) -> RadioSet:
    buttons = [RadioButton(opt, value=(i == default_index)) for i, opt in enumerate(options)]
    return RadioSet(*buttons)


class ResultsPanel(Vertical):
    def render_result(self, result: Any) -> ComposeResult:
        if hasattr(result, "__dataclass_fields__"):
            for field_name, field_info in result.__dataclass_fields__.items():
                val = getattr(result, field_name)
                if isinstance(val, float):
                    yield Static(f"  {field_name}: {val:.4f}")
                elif isinstance(val, bool):
                    yield Static(f"  {field_name}: {'OK' if val else 'FAIL'}")
                elif isinstance(val, list):
                    n = len(val)
                    if n <= 10:
                        yield Static(f"  {field_name}: {val!r}")
                    else:
                        yield Static(f"  {field_name}: [{n} items]")
                else:
                    yield Static(f"  {field_name}: {val!r}")
        else:
            yield Static(str(result))

    def show_report(self, text: str) -> None:
        for widget in list(self.children):
            widget.remove()
        for line in text.split("\n"):
            if line.strip():
                self.mount(Static(line))

    def clear(self) -> None:
        for w in list(self.children):
            w.remove()


class ColumnScreen(ScrollableContainer):
    _w: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        ct = _radio(["Axial", "Uniaxial", "Biaxial"], 0)
        sh = _radio(["Rectangular", "Circular"], 0)
        self._w = dict(
            ct=ct, sh=sh,
            col_id=_input("e.g. C1"),
            load=_input("0"),
            bx=_input("0"), by=_input("0"),
            dia=_input("0"), depth=_input("0"),
            length=_input("0"), le=_input("0"),
            lex=_input("0"), ley=_input("0"),
            mx=_input("0"), my=_input("0"), moment=_input("0"),
        )
        lbl = " " * 3
        yield Static("Column Design / BS 8110 Clause 3.8")
        yield Horizontal(Static(lbl), ct)
        yield Horizontal(Static(lbl), sh)
        yield Horizontal(Static(lbl), self._w["col_id"])
        yield Horizontal(Static(lbl), self._w["load"], Static("kN"))
        yield Horizontal(Static(lbl), self._w["bx"], Static("mm"), self._w["by"], Static("mm"))
        yield Horizontal(Static(lbl), self._w["dia"], Static("mm"), self._w["depth"], Static("mm"))
        yield Horizontal(Static(lbl), self._w["length"], Static("m"), self._w["le"], Static("m"))
        yield Horizontal(Static(lbl), self._w["lex"], Static("m"), self._w["ley"], Static("m"))
        yield Horizontal(Static(lbl), self._w["mx"], Static("kN.m"), self._w["my"], Static("kN.m"))
        yield Button("Calculate", variant="primary", id="calc-btn")
        yield Button("Clear", id="clear-btn")
        yield Button("Report", id="report-btn")

    def get_inputs(self) -> dict[str, Any]:
        w = self._w
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        return {
            "column_id": w["col_id"].value or "C1",
            "col_type": w["ct"].pressed_index + 1,
            "shape": w["sh"].pressed_index + 1,
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
        return ColumnDesigner().design([ci])[0], d


class BeamScreen(ScrollableContainer):
    _w: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        self._w = dict(
            beam_id=_input("e.g. B1"),
            n_supports=_input("2"),
            n_members=_input("1"),
            b=_input("300"), bf=_input("0"),
            h=_input("500"), hf=_input("0"),
            fcu=_input("25"), fy=_input("460"), fyv=_input("250"),
            ty1=_select([("Pinned", "0"), ("Fixed", "1")], "1"),
            ty2=_select([("Pinned", "0"), ("Fixed", "1")], "1"),
            cant_load_1=_input("0"), cant_moment_1=_input("0"),
            cant_load_2=_input("0"), cant_moment_2=_input("0"),
            member_lengths=_input("6.0"),
            member_udl=_input("0"),
            member_wt=_input("0"), member_wb=_input("0"), member_ab=_input("0"),
            member_npl=_input("0"),
            member_pl=_input("(f,d);(f,d)"),
        )
        w = self._w
        yield Static("Beam Design / BS 8110 Clause 3.4")
        yield Horizontal(Static("   "), w["beam_id"], Static("  Supports:"), w["n_supports"], Static("  Members:"), w["n_members"])
        yield Horizontal(Static("   "), Static("b:"), w["b"], Static("mm"), Static("bf:"), w["bf"], Static("mm"), Static("h:"), w["h"], Static("mm"), Static("hf:"), w["hf"], Static("mm"))
        yield Horizontal(Static("   "), Static("fcu:"), w["fcu"], Static("fy:"), w["fy"], Static("fyv:"), w["fyv"])
        yield Horizontal(Static("   "), Static("End1:"), w["ty1"], Static("End2:"), w["ty2"])
        yield Horizontal(Static("   "), Static("Cant Load1:"), w["cant_load_1"], Static("Moment1:"), w["cant_moment_1"])
        yield Horizontal(Static("   "), Static("Cant Load2:"), w["cant_load_2"], Static("Moment2:"), w["cant_moment_2"])
        yield Horizontal(Static("   "), Static("Lengths:"), w["member_lengths"], Static("UDL:"), w["member_udl"])
        yield Horizontal(Static("   "), Static("wt:"), w["member_wt"], Static("wb:"), w["member_wb"], Static("ab:"), w["member_ab"])
        yield Horizontal(Static("   "), Static("npl:"), w["member_npl"], Static("pt loads:"), w["member_pl"])
        yield Button("Calculate", variant="primary", id="calc-btn")
        yield Button("Clear", id="clear-btn")
        yield Button("Report", id="report-btn")

    def get_inputs(self) -> dict[str, Any]:
        w = self._w
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        def _s(key: str, default: str = "") -> str:
            return w[key].value or default
        return {
            "beam_id": w["beam_id"].value or "B1",
            "n_supports": max(2, round(_f("n_supports", 2))),
            "n_members": max(1, round(_f("n_members", 1))),
            "b": _f("b", 300), "bf": _f("bf", 0),
            "h": _f("h", 500), "hf": _f("hf", 0),
            "fcu": _f("fcu", 25), "fy": _f("fy", 460), "fyv": _f("fyv", 250),
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
        return BeamDesigner(fcu=d["fcu"], fy=d["fy"], fyv=d["fyv"]).design([bi])[0], d


class SlabScreen(ScrollableContainer):
    _w: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        self._w = dict(
            panel_type=_radio(["Cantilever", "Simply Supported", "Continuous", "Two-way"], 0),
            panel_id=_input("e.g. S1"),
            depth=_input("200"), fcu=_input("25"), fy=_input("460"),
            udl=_input("0"), span=_input("0"), ly=_input("0"), ratio=_input("20"),
            npl=_input("0"), point_loads=_input("(f,d);(f,d)"),
            nspan=_input("0"), span_lengths=_input("6.0"),
            span_udls=_input("0"), span_npls=_input("0"),
            span_pls=_input("(f,d);(f,d)/(f,d);(f,d)"),
            cant_moments=_input("0"), cant_loads=_input("0"),
            case=_select([(f"Case {i}", str(i)) for i in range(1, 10)], "1"),
        )
        w = self._w
        yield Static("Slab Design / BS 8110 Clause 3.5 & 3.6")
        yield Horizontal(Static("   "), w["panel_type"])
        yield Horizontal(Static("   "), w["panel_id"], Static("Depth:"), w["depth"], Static("mm"))
        yield Horizontal(Static("   "), Static("fcu:"), w["fcu"], Static("fy:"), w["fy"], Static("Span:"), w["span"], Static("m"))
        yield Horizontal(Static("   "), Static("UDL:"), w["udl"], Static("ly:"), w["ly"], Static("Ratio:"), w["ratio"])
        yield Horizontal(Static("   "), Static("npl:"), w["npl"], Static("pt loads:"), w["point_loads"])
        yield Horizontal(Static("   "), Static("nspan:"), w["nspan"], Static("Lengths:"), w["span_lengths"], Static("UDLs:"), w["span_udls"])
        yield Horizontal(Static("   "), Static("CantsMoments:"), w["cant_moments"], Static("Loads:"), w["cant_loads"])
        yield Horizontal(Static("   "), Static("Case:"), w["case"])
        yield Button("Calculate", variant="primary", id="calc-btn")
        yield Button("Clear", id="clear-btn")
        yield Button("Report", id="report-btn")

    def get_inputs(self) -> dict[str, Any]:
        w = self._w
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        def _s(key: str, default: str = "") -> str:
            return w[key].value or default
        return {
            "panel_id": w["panel_id"].value or "S1",
            "panel_type": w["panel_type"].pressed_index + 1,
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
        return SlabDesigner(fcu=d["fcu"], fy=d["fy"]).design([pi])[0], d


class StairScreen(ScrollableContainer):
    _w: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        self._w = dict(
            stair_id=_input("e.g. ST1"),
            span=_input("0"), tread=_input("0"), rise=_input("0"),
            imposed=_input("0"), spl=_input("0"), wld=_input("0"), cw=_input("25"),
        )
        w = self._w
        yield Static("Stair Design / BS 8110 Clause 3.9")
        yield Horizontal(Static("   "), w["stair_id"])
        yield Horizontal(Static("   "), Static("Span:"), w["span"], Static("m"), Static("Tread:"), w["tread"], Static("mm"), Static("Rise:"), w["rise"], Static("mm"))
        yield Horizontal(Static("   "), Static("Imposed:"), w["imposed"], Static("kN/m2"), Static("Sup.Dead:"), w["spl"], Static("kN/m2"), Static("W.Ld:"), w["wld"])
        yield Horizontal(Static("   "), Static("Conc.Wt:"), w["cw"], Static("kN/m3"))
        yield Button("Calculate", variant="primary", id="calc-btn")
        yield Button("Clear", id="clear-btn")
        yield Button("Report", id="report-btn")

    def get_inputs(self) -> dict[str, Any]:
        w = self._w
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
        return StairDesigner(fcu=25.0, fy=460.0).design([si])[0], d


class BaseScreen(ScrollableContainer):
    _w: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        self._w = dict(
            base_type=_radio(["Square Isolated", "Rect Isolated", "Combined"], 0),
            col_shape=_radio(["Rectangular", "Circular"], 0),
            base_id=_input("e.g. F1"),
            load=_input("0"), pb=_input("150"),
            fcu=_input("25"), fy=_input("460"),
            a1=_input("0"), a2=_input("0"), dia=_input("0"), dowel=_input("0"),
            h=_input("200"), l1=_input("0"), l2=_input("0"),
        )
        w = self._w
        yield Static("Foundation Design / BS 8110 Clause 3.7")
        yield Horizontal(Static("   "), w["base_type"])
        yield Horizontal(Static("   "), w["col_shape"])
        yield Horizontal(Static("   "), w["base_id"], Static("Load:"), w["load"], Static("kN"))
        yield Horizontal(Static("   "), Static("fcu:"), w["fcu"], Static("fy:"), w["fy"], Static("Bearing:"), w["pb"], Static("kN/m2"))
        yield Horizontal(Static("   "), Static("a1:"), w["a1"], Static("mm"), Static("a2:"), w["a2"], Static("mm"), Static("Dia:"), w["dia"], Static("mm"))
        yield Horizontal(Static("   "), Static("Dowel:"), w["dowel"], Static("mm"), Static("h:"), w["h"], Static("mm"), Static("L1:"), w["l1"], Static("m"), Static("L2:"), w["l2"], Static("m"))
        yield Button("Calculate", variant="primary", id="calc-btn")
        yield Button("Clear", id="clear-btn")
        yield Button("Report", id="report-btn")

    def get_inputs(self) -> dict[str, Any]:
        w = self._w
        def _f(key: str, default: float = 0) -> float:
            return float(w[key].value or str(default))
        return {
            "base_id": w["base_id"].value or "F1",
            "base_type": w["base_type"].pressed_index + 1,
            "col_type": w["col_shape"].pressed_index + 1,
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
        return BaseDesigner(pb=d["pb"], fcu=d["fcu"], fy=d["fy"]).design([bi])[0], d


class ContinuousBeamScreen(ScrollableContainer):
    _w: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        self._w = dict(
            n_supports=_input("2"), n_members=_input("1"),
            end1_type=_select([("Pinned", "0"), ("Fixed", "1")], "0"),
            end2_type=_select([("Pinned", "0"), ("Fixed", "1")], "0"),
            end1_cl=_input("0"), end1_cm=_input("0"),
            end2_cl=_input("0"), end2_cm=_input("0"),
            member_lengths=_input("6.0"), member_inertia=_input("0.001"),
            member_e_mod=_input("1.0"), member_udl=_input("0"),
            member_wt=_input("0"), member_wb=_input("0"), member_ab=_input("0"),
            member_npl=_input("0"), member_pl=_input("(f,d);(f,d)"),
        )
        w = self._w
        yield Static("Continuous Beam Analysis / Clapeyron Three-Moment")
        yield Horizontal(Static("   "), Static("Supports:"), w["n_supports"], Static("Members:"), w["n_members"])
        yield Horizontal(Static("   "), Static("End1:"), w["end1_type"], Static("End2:"), w["end2_type"])
        yield Horizontal(Static("   "), Static("Cant1:"), w["end1_cl"], Static("kN"), Static("Moment1:"), w["end1_cm"], Static("kN.m"))
        yield Horizontal(Static("   "), Static("Cant2:"), w["end2_cl"], Static("kN"), Static("Moment2:"), w["end2_cm"], Static("kN.m"))
        yield Horizontal(Static("   "), Static("Lengths:"), w["member_lengths"], Static("m"), Static("I:"), w["member_inertia"], Static("m4"), Static("E/Es:"), w["member_e_mod"])
        yield Horizontal(Static("   "), Static("UDL:"), w["member_udl"], Static("kN/m"), Static("wt:"), w["member_wt"], Static("wb:"), w["member_wb"], Static("ab:"), w["member_ab"], Static("m"))
        yield Horizontal(Static("   "), Static("npl/span:"), w["member_npl"], Static("pt loads:"), w["member_pl"])
        yield Button("Calculate", variant="primary", id="calc-btn")
        yield Button("Clear", id="clear-btn")
        yield Button("Report", id="report-btn")

    def get_inputs(self) -> dict[str, Any]:
        w = self._w
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
        return ContinuousBeamAnalyzer().analyze(cb_in), d


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
        Binding("f1", "action_show_help", "Help"),
        Binding("f2", "action_calculate", "Calculate"),
        Binding("f3", "action_clear_form", "Clear"),
        Binding("f4", "action_toggle_report", "Report"),
        Binding("f10", "quit", "Quit"),
        Binding("q", "quit", "Quit"),
    ]

    current_result: Any | None = None
    current_report_text: str = ""
    current_inputs: dict[str, Any] = {}
    show_report_flag: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static(" RCD2000 v1.0.0 | BS 8110 Design Tool | F1:Help F2:Calc F3:Clear F4:Report F10:Quit", id="header")
        with TabbedContent(id="tabs"):
            for name, screen_cls in SCREENS:
                yield TabPane(name, screen_cls(), id=name.lower().replace(" ", "_"))
        yield Static(" F1:Help  F2:Calculate  F3:Clear  F4:Report  F10:Quit", id="footer")
        yield ResultsPanel(id="results-panel")

    def on_mount(self) -> None:
        self.set_timer(0.1, self._focus_first_input)

    def _focus_first_input(self) -> None:
        try:
            screen = self.get_current_screen()
            first = screen.query(Input).first()
            first.focus()
        except Exception:
            pass

    def get_current_screen(self) -> ScrollableContainer:
        tabs = self.query_one(TabbedContent)
        pane = tabs.active_pane
        if pane is not None:
            return pane.query(ScrollableContainer).first()
        return self.query(ScrollableContainer).first()

    def action_show_help(self) -> None:
        self.notify(
            "RCD2000 TUI\n\n"
            "Tab/Shift-Tab: navigate fields\n"
            "Arrow keys: radio/dropdown\n"
            "F2: Calculate  F3: Clear\n"
            "F4: Toggle report (compact/Full BS 8110 format)\n"
            "F10/Q: Quit",
            title="Help",
            timeout=8,
        )

    def action_calculate(self) -> None:
        try:
            screen = self.get_current_screen()
            result, inputs = screen.calculate()
            self.current_result = result
            self.current_inputs = inputs
            self.current_report_text = self._build_report(result)
            self.show_report_flag = False
            self._refresh_results()
            self.notify("Calculation complete", severity="information")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_clear_form(self) -> None:
        try:
            screen = self.get_current_screen()
            for w in screen.query(Input):
                w.value = ""
        except Exception:
            pass
        self.current_result = None
        self.current_report_text = ""
        self.current_inputs = {}
        self.query_one("#results-panel", ResultsPanel).clear()

    def action_toggle_report(self) -> None:
        if self.current_result is not None:
            self.show_report_flag = not self.show_report_flag
            self._refresh_results()

    def _build_report(self, result: Any) -> str:
        from datetime import date
        try:
            from datetime import date as _date
            if isinstance(self.current_inputs, dict):
                pass
        except Exception:
            pass
        try:
            screen = self.get_current_screen()
            screen_cls = type(screen)
            if screen_cls.__name__ == "ColumnScreen":
                ci = ColumnInput(**self.current_inputs)
                return format_column(ci, result, "RCD2000", str(date.today()), "TUI", 25, 460)
            elif screen_cls.__name__ == "BeamScreen":
                bi = BeamInput(**self.current_inputs)
                return format_beam(bi, result, "RCD2000", str(date.today()), "TUI")
            elif screen_cls.__name__ == "SlabScreen":
                pi = SlabPanelInput(**self.current_inputs)
                return format_slab(pi, result, "RCD2000", str(date.today()), "TUI")
            elif screen_cls.__name__ == "StairScreen":
                si = StairInput(**self.current_inputs)
                return format_stair(si, result, "RCD2000", str(date.today()), "TUI")
            elif screen_cls.__name__ == "BaseScreen":
                bi = BaseInput(**self.current_inputs)
                return format_base(bi, result, "RCD2000", str(date.today()), "TUI")
            elif screen_cls.__name__ == "ContinuousBeamScreen":
                cb = ContinuousBeamInput(**self.current_inputs)
                return format_continuous_beam(cb, result, "RCD2000", str(date.today()), "TUI")
        except Exception:
            return ""
        return ""

    def _refresh_results(self) -> None:
        rp = self.query_one("#results-panel", ResultsPanel)
        rp.clear()
        if self.current_result is None:
            return
        if self.show_report_flag and self.current_report_text:
            rp.show_report(self.current_report_text)
        else:
            for line in rp.render_result(self.current_result):
                rp.mount(line)

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
    RCD2000TUI().run()