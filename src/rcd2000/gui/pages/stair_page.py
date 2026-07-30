"""Stair design form page."""

import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QGroupBox, QFileDialog

from rcd2000.stair import StairDesigner, StairInput
from rcd2000.report import format_stair
from rcd2000.gui.theme import GROUP_BOX_STYLE, fmt, fmt2
from rcd2000.gui.widgets import spinbox, button, label, header_label, make_table


class StairPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(header_label("Stair Design — BS 8110"))

        g = QGroupBox("Stair Geometry & Loading")
        g.setStyleSheet(GROUP_BOX_STYLE)
        f = QFormLayout(g)
        self.s_span = spinbox(1, 12, 0.5, 4, 2, " m")
        self.s_tread = spinbox(150, 400, 5, 250, 0, " mm")
        self.s_rise = spinbox(100, 250, 5, 175, 0, " mm")
        self.s_imp = spinbox(0, 20, 0.5, 1.5, 2, " kN/m²")
        self.s_spl = spinbox(0, 10, 0.5, 0, 2, " kN/m²")
        self.s_wld = spinbox(0, 50, 1, 0, 1, " kN/m³")
        f.addRow("Span (m):", self.s_span)
        f.addRow("Tread (mm):", self.s_tread)
        f.addRow("Rise (mm):", self.s_rise)
        f.addRow("Imposed Load (kN/m²):", self.s_imp)
        f.addRow("Superimposed DL (kN/m²):", self.s_spl)
        f.addRow("WLD (kN/m³):", self.s_wld)

        self.calc_btn = button("Design Stair")
        self.calc_btn.clicked.connect(self._calculate)
        self.save_btn = button("Save Report to Desktop")
        self.save_btn.clicked.connect(self._save_report)
        self.save_btn.setVisible(False)
        self.results_area = QVBoxLayout()

        layout.addWidget(g)
        layout.addWidget(self.calc_btn)
        layout.addWidget(self.save_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

    def _calculate(self):
        self._clear_results()
        self._last_input = StairInput(
            stair_id="ST1",
            span=self.s_span.value(),
            tread=self.s_tread.value(),
            rise=self.s_rise.value(),
            imposed_load=self.s_imp.value(),
            spl=self.s_spl.value(),
            wld=self.s_wld.value(),
        )
        designer = StairDesigner()
        self._last_result = designer.design([self._last_input])[0]
        r = self._last_result

        rows = [
            ["Waist Thickness (mm)", fmt(r.waist_thickness)],
            ["Total UDL (kN/m)", fmt2(r.total_udl)],
            ["Design Moment (kN·m)", fmt2(r.design_moment)],
            ["Effective Depth (mm)", fmt(r.effective_depth)],
            ["K Value", fmt2(r.k_value)],
            ["Lever Arm Factor", fmt2(r.lever_arm_factor)],
            ["Lever Arm z (mm)", fmt2(r.lever_arm_z)],
            ["Steel Required (mm²)", fmt(r.steel_required)],
            ["Bar Type", r.bar_type],
            ["Bar Diameter (mm)", fmt(r.bar_dia)],
            ["Bar Spacing (mm)", fmt(r.bar_spacing)],
        ]
        self.results_area.addWidget(make_table(["Parameter", "Value"], rows))
        self.save_btn.setVisible(True)

    def _save_report(self):
        text = format_stair(self._last_input, self._last_result)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_STAIR.txt"),
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
