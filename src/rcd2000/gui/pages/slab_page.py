"""Slab design form page."""

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.report import format_slab
from rcd2000.gui.theme import fmt, fmt2
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, label, Card, fcu_combo, fy_combo, badge,
    load_combo_group, SpanDiagram,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class SlabPage(DesignFormPage):
    module_name = "Slab"

    def __init__(self):
        self._cont_span_widgets = []
        self._panel_pl_widgets = []
        super().__init__()

    def build_inputs(self, layout):
        c1 = Card("Slab Type & Materials")
        self.slab_type = combo(["Cantilever", "Simply Supported",
                                "Continuous (One-Way)", "Two-Way"])
        self.slab_fcu = fcu_combo()
        self.slab_fy = fy_combo()
        self.slab_fcu.setToolTip("Characteristic concrete cube strength (N/mm²) at 28 days")
        self.slab_fy.setToolTip("Characteristic steel reinforcement yield strength (N/mm²)")
        c1.add_row("Type:", self.slab_type)
        c1.add_row("fcu (N/mm²):", self.slab_fcu)
        c1.add_row("fy (N/mm²):", self.slab_fy)
        layout.addWidget(c1)
        self._auto_clear_invalid(self.slab_type)
        self._auto_clear_invalid(self.slab_fcu)
        self._auto_clear_invalid(self.slab_fy)

        c2 = Card("Panel Geometry & Loading")
        # AUDIT: depth 100-500 mm is fine. But for two-way slabs, ly must be
        # >= span for the coefficient tables to be valid. The page allows
        # ly=0 which would cause a division-by-zero in _design_twoway.
        self.s_depth = spinbox(100, 999999999, 10, 150, 0)
        # AUDIT: span 0.5-20 m is reasonable. For two-way, lx must be the
        # short span - the engine takes min(span, ly) but the user might
        # enter them backwards with no warning.
        self.s_span = spinbox(0.5, 20, 0.5, 4, 2, " m")
        # AUDIT: ly 0-20 m - ly=0 with two-way selected causes division by
        # zero (k = ly/lx). Should enforce ly >= span for two-way.
        self.s_ly = spinbox(0, 20, 0.5, 5, 2, " m")
        # AUDIT: case 1-9 is valid for two-way only. For other slab types,
        # case is ignored - no harm but potentially confusing.
        self.s_case = spin_int(1, 999999999, 1)
        self.s_case.setToolTip(
            "Two-way slab edge restraint case (1-9). Each case corresponds to a "
            "different arrangement of simply supported and continuous edges, "
            "determining the bending moment coefficients. "
            "I'm not certain of the exact 1-9 boundary-condition mapping; "
            "please confirm the correct reference (likely BS 8110 Table 3.13/3.14)."
        )
        # AUDIT: the two-way span/effective-depth ratio was hard-coded to 20
        # in the engine default; expose it (book input SR, default 20).
        self.s_sd = spin_int(5, 60, 20)
        self.s_sd.setToolTip(
            "Two-way slab span/effective-depth ratio (book SR, default 20). "
            "Use 26 for panels continuous over the short span; "
            "lower ratios demand a deeper slab."
        )
        c2.add_row("Depth (mm):", self.s_depth)
        c2.add_row("Span (m):", self.s_span)
        c2.add_row("Ly - long span (m):", self.s_ly)
        c2.add_row("Case (1-9):", self.s_case)
        c2.add_row("Span/Depth Ratio:", self.s_sd)

        load_w, self.gk, self.qk, self.load_result = load_combo_group()

        self.udl_label = label("")
        c2.add_widget(label("Load Combination (factored)", secondary=True, size=12))
        c2.add_widget(load_w)
        c2.add_widget(self.udl_label)
        layout.addWidget(c2)
        self._auto_clear_invalid(self.s_depth)
        self._auto_clear_invalid(self.s_span)
        self._auto_clear_invalid(self.s_ly)
        self._auto_clear_invalid(self.s_case)
        self._auto_clear_invalid(self.s_sd)
        self._auto_clear_invalid(self.gk)
        self._auto_clear_invalid(self.qk)

        # AUDIT: end cantilever moment/load inputs for continuous slabs were
        # missing from the GUI (book CANTMT(1/2), CANTLD(1/2)); the engine
        # already adds them to mtc[0]/mtc[ns-1] and rct[0]/rct[ns-1].
        c2b = Card("End Cantilevers (Continuous)")
        self.s_cant_load_1 = spinbox(0, 999999999, 5, 0, 1, " kN")
        self.s_cant_moment_1 = spinbox(0, 999999999, 5, 0, 1, " kN·m")
        self.s_cant_load_2 = spinbox(0, 999999999, 5, 0, 1, " kN")
        self.s_cant_moment_2 = spinbox(0, 999999999, 5, 0, 1, " kN·m")
        self.s_cant_load_1.setToolTip("Load on the left end cantilever (book CANTLD(1))")
        self.s_cant_moment_1.setToolTip("Moment at the left end support (book CANTMT(1))")
        self.s_cant_load_2.setToolTip("Load on the right end cantilever (book CANTLD(2))")
        self.s_cant_moment_2.setToolTip("Moment at the right end support (book CANTMT(2))")
        c2b.add_row("Left cantilever load:", self.s_cant_load_1)
        c2b.add_row("Left cantilever moment:", self.s_cant_moment_1)
        c2b.add_row("Right cantilever load:", self.s_cant_load_2)
        c2b.add_row("Right cantilever moment:", self.s_cant_moment_2)
        layout.addWidget(c2b)
        self._auto_clear_invalid(self.s_cant_load_1)
        self._auto_clear_invalid(self.s_cant_moment_1)
        self._auto_clear_invalid(self.s_cant_load_2)
        self._auto_clear_invalid(self.s_cant_moment_2)

        # AUDIT: point loads for cantilever / simply supported panels were
        # missing from the GUI (book NPL, PL/APC); the engine already sums
        # them into the moment and shear.
        c2c = Card("Point Loads (Cantilever / Simply Supported)")
        self.panel_npl = spin_int(0, 999999999, 0)
        self.panel_npl.valueChanged.connect(self._sync_panel_pls)
        c2c.add_row("Number of Point Loads:", self.panel_npl)
        self.panel_pl_layout = QVBoxLayout()
        c2c.add_layout(self.panel_pl_layout)
        layout.addWidget(c2c)
        self._auto_clear_invalid(self.panel_npl)

        c3 = Card("Continuous Slab Spans")
        self.cont_nspan = spin_int(1, 999999999, 3)
        self.cont_nspan.valueChanged.connect(self._sync_cont_spans)
        c3.add_row("Number of Spans:", self.cont_nspan)

        self.cont_diagram = SpanDiagram()
        self.cont_diagram.setVisible(False)
        c3.add_widget(self.cont_diagram)

        self.cont_span_layout = QHBoxLayout()
        c3.add_layout(self.cont_span_layout)
        layout.addWidget(c3)

        self._sync_cont_spans()
        self._sync_panel_pls()

    @staticmethod
    def _clear_layout(layout):
        """Remove every widget/layout from a layout (reusable on rebuild)."""
        while layout.count():
            item = layout.takeAt(0)
            if item.layout() is not None:
                lay = item.layout()
                while lay.count():
                    li = lay.takeAt(0)
                    w = li.widget()
                    if w is not None:
                        w.deleteLater()
            elif item.widget() is not None:
                item.widget().deleteLater()

    def _sync_cont_spans(self):
        n = self.cont_nspan.value()
        # Rebuild the span widgets from scratch each time (simpler than
        # tracking add/remove).
        self._clear_layout(self.cont_span_layout)
        self._cont_span_widgets = []
        for i in range(n):
            h = QHBoxLayout()
            h.addWidget(label(f"S{i+1}:", secondary=True, size=12))
            le = spinbox(0, 999999999, 0.5, 4, 2, " m")
            ud = spinbox(0, 999999999, 5, 10, 1, " kN/m")
            pl = spinbox(0, 999999999, 5, 0, 1, " kN")
            ap = spinbox(0, 999999999, 0.5, 0, 2, " m")
            pl.setToolTip("Point load on this span (book PLC) - enter 0 for none")
            ap.setToolTip("Distance (m) of the point load from the left support (book ALC)")
            self._auto_clear_invalid(le)
            self._auto_clear_invalid(ud)
            self._auto_clear_invalid(pl)
            self._auto_clear_invalid(ap)
            h.addWidget(le)
            h.addWidget(ud)
            h.addWidget(pl)
            h.addWidget(ap)
            self.cont_span_layout.addLayout(h)
            self._cont_span_widgets.append((le, ud, pl, ap))
            le.valueChanged.connect(self._update_diagram)
            ud.valueChanged.connect(self._update_diagram)
            pl.valueChanged.connect(self._update_diagram)
            ap.valueChanged.connect(self._update_diagram)

        diagram_data = [
            {"length": w[0].value(), "udl": w[1].value()}
            for w in self._cont_span_widgets
        ]
        self.cont_diagram.set_spans(diagram_data)
        self.cont_diagram.setVisible(n > 1)

    def _sync_panel_pls(self):
        n = self.panel_npl.value()
        self._clear_layout(self.panel_pl_layout)
        self._panel_pl_widgets = []
        for i in range(n):
            h = QHBoxLayout()
            h.addWidget(label(f"P{i+1}:", secondary=True, size=12))
            pl = spinbox(0, 999999999, 5, 0, 1, " kN")
            ap = spinbox(0, 999999999, 0.5, 0, 2, " m")
            pl.setToolTip("Point load on this panel (book PL)")
            ap.setToolTip("Distance (m) of the point load from the free/support edge (book APC)")
            self._auto_clear_invalid(pl)
            self._auto_clear_invalid(ap)
            h.addWidget(pl)
            h.addWidget(ap)
            self.panel_pl_layout.addLayout(h)
            self._panel_pl_widgets.append((pl, ap))

    def _update_diagram(self):
        data = [
            {"length": w[0].value(), "udl": w[1].value()}
            for w in self._cont_span_widgets
        ]
        self.cont_diagram.set_spans(data)

    def calculate(self):
        ptype = self.slab_type.currentIndex() + 1
        fcu = int(self.slab_fcu.currentText())
        fy = int(self.slab_fy.currentText())

        udl = 1.4 * self.gk.value() + 1.6 * self.qk.value()
        self.udl_label.setText(f"Design UDL = {udl:.1f} kN/m²")

        inp = SlabPanelInput(
            panel_id="S1",
            panel_type=ptype,
            depth=self.s_depth.value(),
            fcu=fcu, fy=fy,
            udl=udl,
            span=self.s_span.value(),
            ly=self.s_ly.value(), case=self.s_case.value(),
            span_depth_ratio=self.s_sd.value(),
            npl=self.panel_npl.value(),
            point_loads=[
                (w[0].value(), w[1].value()) for w in self._panel_pl_widgets
            ],
            nspan=self.cont_nspan.value(),
            span_lengths=[w[0].value() for w in self._cont_span_widgets],
            span_udls=[w[1].value() for w in self._cont_span_widgets],
            span_npls=[
                1 if w[2].value() > 0 else 0 for w in self._cont_span_widgets
            ],
            span_pls=[
                [(w[2].value(), w[3].value())] if w[2].value() > 0 else []
                for w in self._cont_span_widgets
            ],
            cant_loads=[
                self.s_cant_load_1.value(), self.s_cant_load_2.value()
            ],
            cant_moments=[
                self.s_cant_moment_1.value(), self.s_cant_moment_2.value()
            ],
        )
        designer = SlabDesigner(fcu=fcu, fy=fy)
        result = designer.design([inp])[0]
        return inp, result

    def validate(self) -> list[str]:
        errors = []
        ptype = self.slab_type.currentIndex()
        if ptype == 3:
            if self.s_ly.value() < self.s_span.value():
                errors.append("For two-way slabs, long span (Ly) must be ≥ short span")
                self._mark_invalid(self.s_ly)
                self._mark_invalid(self.s_span)
            if self.s_ly.value() <= 0:
                errors.append("Ly (long span) must be > 0 for two-way slabs")
                self._mark_invalid(self.s_ly)
            if self.s_case.value() < 1 or self.s_case.value() > 9:
                errors.append("Case must be 1-9 for two-way slabs")
                self._mark_invalid(self.s_case)
        if ptype in (0, 1):
            for i, w in enumerate(self._panel_pl_widgets):
                if w[0].value() > 0 and not (
                    0 < w[1].value() <= self.s_span.value()
                ):
                    errors.append(
                        f"Point load {i+1} distance must be within the panel span"
                    )
                    self._mark_invalid(w[1])
        if ptype == 2:
            for i, w in enumerate(self._cont_span_widgets):
                if w[0].value() <= 0:
                    errors.append(f"Span {i+1} length must be > 0")
                    self._mark_invalid(w[0])
                if w[2].value() > 0 and not (0 < w[3].value() <= w[0].value()):
                    errors.append(
                        f"Span {i+1} point load distance must be within the span"
                    )
                    self._mark_invalid(w[3])
        return errors

    def summarize(self, inp) -> str:
        names = ["Cantilever", "Simply Supported", "Continuous", "Two-Way"]
        try:
            ptype = inp.panel_type if hasattr(inp, "panel_type") else inp.get("panel_type", 1)
            span = inp.span if hasattr(inp, "span") else inp.get("span", 0)
            name = names[ptype - 1] if 1 <= ptype <= 4 else f"Type {ptype}"
            return f"{name}, span {span:.1f}m"
        except Exception:
            return f"{names[self.slab_type.currentIndex()]}"

    def format_report(self, inp, result):
        return format_slab(inp, result)

    def _build_result_rows(self, r):
        rows = [
            ["Design Moment (kN·m/m)", fmt2(r.moment_span), ""],
            ["Steel Required (mm²/m)", fmt(r.steel_span), ""],
            ["Bar Type", r.bar_type, ""],
            ["Bar Diameter (mm)", fmt(r.bar_dia), ""],
            ["Bar Spacing (mm)", fmt(r.bar_spacing), ""],
            ["Deflection", "OK" if r.defl_ok else "FAIL", badge(r.defl_ok)],
        ]
        ptype = self.slab_type.currentIndex() + 1
        if ptype in (1, 2):
            rows.append(["Shear Left (kN/m)", fmt2(r.shear_left), ""])
        if ptype == 2:
            rows.append(["Shear Right (kN/m)", fmt2(r.shear_right), ""])
        if r.defl_required > 0:
            rows.append(["Depth for Deflection (mm)", fmt2(r.defl_required), ""])
        if ptype == 4:
            rows += [
                ["Long Span Moment (kN·m/m)", fmt2(r.moment_long_span), ""],
                ["Long Span Steel (mm²/m)", fmt(r.steel_long_span), ""],
                ["Long Support Moment (kN·m/m)", fmt2(r.moment_long_support), ""],
                ["Long Support Steel (mm²/m)", fmt(r.steel_long_support), ""],
                ["Support Moment (kN·m/m)", fmt2(r.moment_support), ""],
                ["Support Steel (mm²)", fmt(r.steel_support), ""],
            ]
        if ptype == 3 and r.span_moments:
            for i, (m, a) in enumerate(zip(r.span_moments, r.span_steels)):
                rows.append([f"Span {i + 1} Moment (kN·m)", fmt2(m), ""])
                rows.append([f"Span {i + 1} Steel (mm²)", fmt(a), ""])
            for i, rc in enumerate(r.support_reactions):
                rows.append([f"Support {i + 1} Reaction (kN)", fmt2(rc), ""])
            for i, (m, a) in enumerate(zip(r.support_moments, r.support_steels)):
                rows.append([f"Support {i + 1} Moment (kN·m)", fmt2(m), ""])
                rows.append([f"Support {i + 1} Steel (mm²)", fmt(a), ""])
        return rows

    def get_state(self) -> dict:
        return {
            "slab_type": self.slab_type.currentIndex(),
            "slab_fcu": int(self.slab_fcu.currentText()),
            "slab_fy": int(self.slab_fy.currentText()),
            "s_depth": self.s_depth.value(),
            "s_span": self.s_span.value(),
            "s_ly": self.s_ly.value(),
            "s_case": self.s_case.value(),
            "s_sd": self.s_sd.value(),
            "gk": self.gk.value(),
            "qk": self.qk.value(),
            "cant_load_1": self.s_cant_load_1.value(),
            "cant_moment_1": self.s_cant_moment_1.value(),
            "cant_load_2": self.s_cant_load_2.value(),
            "cant_moment_2": self.s_cant_moment_2.value(),
            "panel_npl": self.panel_npl.value(),
            "panel_pls": [
                {"pl": w[0].value(), "ap": w[1].value()}
                for w in self._panel_pl_widgets
            ],
            "cont_nspan": self.cont_nspan.value(),
            "cont_spans": [
                {"length": w[0].value(), "udl": w[1].value(),
                 "pl": w[2].value(), "ap": w[3].value()}
                for w in self._cont_span_widgets
            ],
        }

    def set_state(self, state: dict) -> None:
        if "slab_type" in state:
            self.slab_type.setCurrentIndex(state["slab_type"])
        if "slab_fcu" in state:
            self._set_combo_int(self.slab_fcu, state["slab_fcu"])
        if "slab_fy" in state:
            self._set_combo_int(self.slab_fy, state["slab_fy"])
        if "s_depth" in state:
            self.s_depth.setValue(state["s_depth"])
        if "s_span" in state:
            self.s_span.setValue(state["s_span"])
        if "s_ly" in state:
            self.s_ly.setValue(state["s_ly"])
        if "s_case" in state:
            self.s_case.setValue(state["s_case"])
        if "s_sd" in state:
            self.s_sd.setValue(state["s_sd"])
        if "gk" in state:
            self.gk.setValue(state["gk"])
        if "qk" in state:
            self.qk.setValue(state["qk"])
        if "cant_load_1" in state:
            self.s_cant_load_1.setValue(state["cant_load_1"])
        if "cant_moment_1" in state:
            self.s_cant_moment_1.setValue(state["cant_moment_1"])
        if "cant_load_2" in state:
            self.s_cant_load_2.setValue(state["cant_load_2"])
        if "cant_moment_2" in state:
            self.s_cant_moment_2.setValue(state["cant_moment_2"])
        if "panel_npl" in state:
            self.panel_npl.setValue(state["panel_npl"])
        if "panel_pls" in state and self._panel_pl_widgets:
            for i, w in enumerate(self._panel_pl_widgets):
                if i < len(state["panel_pls"]):
                    s = state["panel_pls"][i]
                    if "pl" in s:
                        w[0].setValue(s["pl"])
                    if "ap" in s:
                        w[1].setValue(s["ap"])
        if "cont_nspan" in state:
            self.cont_nspan.setValue(state["cont_nspan"])
        if "cont_spans" in state and self._cont_span_widgets:
            for i, w in enumerate(self._cont_span_widgets):
                if i < len(state["cont_spans"]):
                    s = state["cont_spans"][i]
                    if "length" in s:
                        w[0].setValue(s["length"])
                    if "udl" in s:
                        w[1].setValue(s["udl"])
                    if "pl" in s:
                        w[2].setValue(s["pl"])
                    if "ap" in s:
                        w[3].setValue(s["ap"])
