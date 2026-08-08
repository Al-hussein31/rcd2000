"""Slab design form page."""

from PySide6.QtWidgets import QHBoxLayout

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
        c2.add_row("Depth (mm):", self.s_depth)
        c2.add_row("Span (m):", self.s_span)
        c2.add_row("Ly - long span (m):", self.s_ly)
        c2.add_row("Case (1-9):", self.s_case)

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
        self._auto_clear_invalid(self.gk)
        self._auto_clear_invalid(self.qk)

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

    def _sync_cont_spans(self):
        from PySide6.QtWidgets import QVBoxLayout
        n = self.cont_nspan.value()
        # Rebuild the span widgets from scratch each time (simpler than
        # tracking add/remove).
        self._cont_span_widgets = []
        for i in range(n):
            h = QHBoxLayout()
            h.addWidget(label(f"S{i+1}:", secondary=True, size=12))
            le = spinbox(0, 999999999, 0.5, 4, 2, " m")
            ud = spinbox(0, 999999999, 5, 10, 1, " kN/m")
            self._auto_clear_invalid(le)
            self._auto_clear_invalid(ud)
            h.addWidget(le)
            h.addWidget(ud)
            self.cont_span_layout.addLayout(h)
            self._cont_span_widgets.append((le, ud))
            le.valueChanged.connect(self._update_diagram)
            ud.valueChanged.connect(self._update_diagram)

        diagram_data = [
            {"length": w[0].value(), "udl": w[1].value()}
            for w in self._cont_span_widgets
        ]
        self.cont_diagram.set_spans(diagram_data)
        self.cont_diagram.setVisible(n > 1)

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
            nspan=self.cont_nspan.value(),
            span_lengths=[w[0].value() for w in self._cont_span_widgets],
            span_udls=[w[1].value() for w in self._cont_span_widgets],
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
        if ptype == 2:
            for i, w in enumerate(self._cont_span_widgets):
                if w[0].value() <= 0:
                    errors.append(f"Span {i+1} length must be > 0")
                    self._mark_invalid(w[0])
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
        if ptype == 4:
            rows += [
                ["Long Span Moment (kN·m/m)", fmt2(r.moment_long_span), ""],
                ["Long Span Steel (mm²/m)", fmt(r.steel_long_span), ""],
                ["Support Moment (kN·m/m)", fmt2(r.moment_support), ""],
                ["Support Steel (mm²)", fmt(r.steel_support), ""],
            ]
        if ptype == 3 and r.span_moments:
            for i, (m, a) in enumerate(zip(r.span_moments, r.span_steels)):
                rows.append([f"Span {i+1} Moment (kN·m)", fmt2(m), ""])
                rows.append([f"Span {i+1} Steel (mm²)", fmt(a), ""])
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
            "gk": self.gk.value(),
            "qk": self.qk.value(),
            "cont_nspan": self.cont_nspan.value(),
            "cont_spans": [
                {"length": w[0].value(), "udl": w[1].value()}
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
        if "gk" in state:
            self.gk.setValue(state["gk"])
        if "qk" in state:
            self.qk.setValue(state["qk"])
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
