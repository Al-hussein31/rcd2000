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
        c1.add_row("Type:", self.slab_type)
        c1.add_row("fcu (N/mm²):", self.slab_fcu)
        c1.add_row("fy (N/mm²):", self.slab_fy)
        layout.addWidget(c1)

        c2 = Card("Panel Geometry & Loading")
        # AUDIT: depth 100–500 mm is fine. But for two-way slabs, ly must be
        # >= span for the coefficient tables to be valid. The page allows
        # ly=0 which would cause a division-by-zero in _design_twoway.
        self.s_depth = spinbox(100, 500, 10, 150, 0)
        # AUDIT: span 0.5–20 m is reasonable. For two-way, lx must be the
        # short span — the engine takes min(span, ly) but the user might
        # enter them backwards with no warning.
        self.s_span = spinbox(0.5, 20, 0.5, 4, 2, " m")
        # AUDIT: ly 0–20 m — ly=0 with two-way selected causes division by
        # zero (k = ly/lx). Should enforce ly >= span for two-way.
        self.s_ly = spinbox(0, 20, 0.5, 5, 2, " m")
        # AUDIT: case 1–9 is valid for two-way only. For other slab types,
        # case is ignored — no harm but potentially confusing.
        self.s_case = spin_int(1, 9, 1)
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

        c3 = Card("Continuous Slab Spans")
        self.cont_nspan = spin_int(1, 8, 3)
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
            le = spinbox(1, 20, 0.5, 4, 2, " m")
            ud = spinbox(0, 100, 5, 10, 1, " kN/m")
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
                ["Support Steel (mm²/m)", fmt(r.steel_support), ""],
            ]
        if ptype == 3 and r.span_moments:
            for i, (m, a) in enumerate(zip(r.span_moments, r.span_steels)):
                rows.append([f"Span {i+1} Moment (kN·m)", fmt2(m), ""])
                rows.append([f"Span {i+1} Steel (mm²)", fmt(a), ""])
        return rows
