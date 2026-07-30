"""Slab design form page."""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QFileDialog, QScrollArea,
)
from PySide6.QtCore import Qt

from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.report import format_slab
from rcd2000.gui.theme import GROUP_BOX_STYLE, fmt, fmt2, ACCENT, TEXT_SECONDARY
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, button, label, header_label, make_table,
    Card, fcu_combo, fy_combo, badge, load_combo_group, SpanDiagram,
)


class SlabPage(QWidget):
    def __init__(self):
        super().__init__()
        self._cont_span_widgets = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        layout.addWidget(header_label("Slab Design - BS 8110"))

        c1 = Card("Slab Type & Materials")
        self.slab_type = combo(["Cantilever", "Simply Supported", "Continuous (One-Way)", "Two-Way"])
        self.slab_fcu = fcu_combo()
        self.slab_fy = fy_combo()
        c1.add_row("Type:", self.slab_type)
        c1.add_row("fcu (N/mm²):", self.slab_fcu)
        c1.add_row("fy (N/mm²):", self.slab_fy)
        layout.addWidget(c1)

        c2 = Card("Panel Geometry & Loading")
        self.s_depth = spinbox(100, 500, 10, 150, 0)
        self.s_span = spinbox(0.5, 20, 0.5, 4, 2, " m")
        self.s_ly = spinbox(0, 20, 0.5, 5, 2, " m")
        self.s_case = spin_int(1, 9, 1)

        load_w, self.gk, self.qk, self.load_result = load_combo_group()

        c2.add_row("Depth (mm):", self.s_depth)
        c2.add_row("Span (m):", self.s_span)
        c2.add_row("Ly - long span (m):", self.s_ly)
        c2.add_row("Case (1-9):", self.s_case)

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

        self.cont_span_layout = QVBoxLayout()
        c3.add_layout(self.cont_span_layout)
        layout.addWidget(c3)

        self.calc_btn = button("Design Slab")
        self.calc_btn.clicked.connect(self._calculate)
        layout.addWidget(self.calc_btn)

        self.btn_row = QHBoxLayout()
        self.save_btn = button("Save .txt Report")
        self.save_btn.clicked.connect(lambda: self._save_report("txt"))
        self.save_btn.setVisible(False)
        self.pdf_btn = button("Save .pdf Report")
        self.pdf_btn.clicked.connect(lambda: self._save_report("pdf"))
        self.pdf_btn.setVisible(False)
        self.btn_row.addWidget(self.save_btn)
        self.btn_row.addWidget(self.pdf_btn)
        layout.addLayout(self.btn_row)

        self.results_area = QVBoxLayout()
        layout.addLayout(self.results_area)
        layout.addStretch()

        self._sync_cont_spans()

    def _sync_cont_spans(self):
        n = self.cont_nspan.value()
        old_n = len(self._cont_span_widgets)
        while len(self._cont_span_widgets) < n:
            i = len(self._cont_span_widgets)
            h = QHBoxLayout()
            h.addWidget(label(f"S{i+1}:", secondary=True, size=12))
            le = spinbox(1, 20, 0.5, 4, 2, " m")
            ud = spinbox(0, 100, 5, 10, 1, " kN/m")
            h.addWidget(le)
            h.addWidget(ud)
            self.cont_span_layout.addLayout(h)
            self._cont_span_widgets.append((le, ud))

        diagram_data = [
            {"length": w[0].value(), "udl": w[1].value()}
            for w in self._cont_span_widgets
        ]
        self.cont_diagram.set_spans(diagram_data)
        self.cont_diagram.setVisible(n > 1)
        # Connect signals for new spans only
        for le, ud in self._cont_span_widgets[old_n:]:
            le.valueChanged.connect(self._update_diagram)
            ud.valueChanged.connect(self._update_diagram)

    def _update_diagram(self):
        data = [
            {"length": w[0].value(), "udl": w[1].value()}
            for w in self._cont_span_widgets
        ]
        self.cont_diagram.set_spans(data)

    def _calculate(self):
        self._clear_results()
        ptype = self.slab_type.currentIndex() + 1
        fcu = int(self.slab_fcu.currentText())
        fy = int(self.slab_fy.currentText())

        udl = 1.4 * self.gk.value() + 1.6 * self.qk.value()
        self.udl_label.setText(f"Design UDL = {udl:.1f} kN/m²")
        self._last_input = SlabPanelInput(
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
        self._last_result = designer.design([self._last_input])[0]
        r = self._last_result

        rows = [
            ["Design Moment (kN·m/m)", fmt2(r.moment_span), ""],
            ["Steel Required (mm²/m)", fmt(r.steel_span), ""],
            ["Bar Type", r.bar_type, ""],
            ["Bar Diameter (mm)", fmt(r.bar_dia), ""],
            ["Bar Spacing (mm)", fmt(r.bar_spacing), ""],
            ["Deflection", "OK" if r.defl_ok else "FAIL", badge(r.defl_ok)],
        ]
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

        self.results_area.addWidget(make_table(["Parameter", "Value", "Status"], rows))
        self.save_btn.setVisible(True)
        self.pdf_btn.setVisible(True)
        if hasattr(self, '_history_cb') and self._history_cb:
            self._history_cb("Slab", self._last_input, self._last_result)

    def _save_report(self, fmt_type="txt"):
        if fmt_type == "txt":
            text = format_slab(self._last_input, self._last_result)
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_SLAB.txt"),
                "Text Files (*.txt)",
            )
            if path:
                with open(path, "w") as f:
                    f.write(text)
        else:
            text = format_slab(self._last_input, self._last_result)
            from rcd2000.report import export_pdf
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report", os.path.expanduser("~/Desktop/RCD2000_SLAB.pdf"),
                "PDF Files (*.pdf)",
            )
            if path:
                export_pdf(text, path)

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.save_btn.setVisible(False)
        self.pdf_btn.setVisible(False)
