"""Slab design form page."""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QFileDialog,
)

from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.report import format_slab
from rcd2000.gui.theme import GROUP_BOX_STYLE, fmt, fmt2
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, button, label, header_label, make_table,
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

        g1 = QGroupBox("Slab Type & Materials")
        g1.setStyleSheet(GROUP_BOX_STYLE)
        f1 = QFormLayout(g1)
        self.slab_type = combo(["Cantilever", "Simply Supported", "Continuous (One-Way)", "Two-Way"])
        self.slab_fcu = spinbox(15, 60, 5, 25)
        self.slab_fy = spinbox(250, 600, 10, 460)
        f1.addRow("Type:", self.slab_type)
        f1.addRow("fcu (N/mm²):", self.slab_fcu)
        f1.addRow("fy (N/mm²):", self.slab_fy)

        g2 = QGroupBox("Panel Geometry & Loading")
        g2.setStyleSheet(GROUP_BOX_STYLE)
        f2 = QFormLayout(g2)
        self.s_depth = spinbox(100, 500, 10, 150, 0)
        self.s_span = spinbox(0.5, 20, 0.5, 4, 2, " m")
        self.s_udl = spinbox(0, 100, 5, 10, 1, " kN/m²")
        self.s_ly = spinbox(0, 20, 0.5, 5, 2, " m")
        self.s_case = spin_int(1, 9, 1)
        f2.addRow("Depth (mm):", self.s_depth)
        f2.addRow("Span (m):", self.s_span)
        f2.addRow("UDL (kN/m²):", self.s_udl)
        f2.addRow("Ly - long span (m):", self.s_ly)
        f2.addRow("Case (1-9):", self.s_case)

        g3 = QGroupBox("Continuous Slab Spans (if applicable)")
        g3.setStyleSheet(GROUP_BOX_STYLE)
        f3 = QFormLayout(g3)
        self.cont_nspan = spin_int(1, 8, 3)
        self.cont_nspan.valueChanged.connect(self._sync_cont_spans)
        f3.addRow("Number of Spans:", self.cont_nspan)
        self.cont_span_layout = QVBoxLayout()
        f3.addRow(self.cont_span_layout)

        self.calc_btn = button("Design Slab")
        self.calc_btn.clicked.connect(self._calculate)
        self.save_btn = button("Save Report to Desktop")
        self.save_btn.clicked.connect(self._save_report)
        self.save_btn.setVisible(False)
        self.results_area = QVBoxLayout()

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(g3)
        layout.addWidget(self.calc_btn)
        layout.addWidget(self.save_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

        self._sync_cont_spans()

    def _sync_cont_spans(self):
        n = self.cont_nspan.value()
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

    def _calculate(self):
        self._clear_results()
        ptype = self.slab_type.currentIndex() + 1
        self._last_input = SlabPanelInput(
            panel_id="S1",
            panel_type=ptype,
            depth=self.s_depth.value(),
            fcu=self.slab_fcu.value(), fy=self.slab_fy.value(),
            udl=self.s_udl.value(),
            span=self.s_span.value(),
            ly=self.s_ly.value(), case=self.s_case.value(),
            nspan=self.cont_nspan.value(),
            span_lengths=[w[0].value() for w in self._cont_span_widgets],
            span_udls=[w[1].value() for w in self._cont_span_widgets],
        )
        designer = SlabDesigner(fcu=self.slab_fcu.value(), fy=self.slab_fy.value())
        self._last_result = designer.design([self._last_input])[0]
        r = self._last_result

        rows = [
            ["Design Moment (kN·m/m)", fmt2(r.moment_span)],
            ["Steel Required (mm²/m)", fmt(r.steel_span)],
            ["Bar Type", r.bar_type],
            ["Bar Diameter (mm)", fmt(r.bar_dia)],
            ["Bar Spacing (mm)", fmt(r.bar_spacing)],
            ["Deflection OK", "✓" if r.defl_ok else "✗"],
        ]
        if ptype == 4:
            rows += [
                ["Long Span Moment (kN·m/m)", fmt2(r.moment_long_span)],
                ["Long Span Steel (mm²/m)", fmt(r.steel_long_span)],
                ["Support Moment (kN·m/m)", fmt2(r.moment_support)],
                ["Support Steel (mm²/m)", fmt(r.steel_support)],
            ]
        if ptype == 3 and r.span_moments:
            for i, (m, a) in enumerate(zip(r.span_moments, r.span_steels)):
                rows.append([f"Span {i+1} Moment (kN·m)", fmt2(m)])
                rows.append([f"Span {i+1} Steel (mm²)", fmt(a)])

        self.results_area.addWidget(make_table(["Parameter", "Value"], rows))
        self.save_btn.setVisible(True)

    def _save_report(self):
        text = format_slab(self._last_input, self._last_result)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_SLAB.txt"),
            "Text Files (*.txt)",
        )
        if path:
            with open(path, "w") as f:
                f.write(text)

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.save_btn.setVisible(False)
