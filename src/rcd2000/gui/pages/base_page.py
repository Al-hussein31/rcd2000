"""Foundation design form page."""

import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QGroupBox, QFileDialog

from rcd2000.base import BaseDesigner, BaseInput
from rcd2000.report import format_base
from rcd2000.gui.theme import GROUP_BOX_STYLE, fmt, fmt2
from rcd2000.gui.widgets import spinbox, combo, button, label, header_label, make_table


class BasePage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(header_label("Foundation Design — BS 8110"))

        g1 = QGroupBox("Base Type & Materials")
        g1.setStyleSheet(GROUP_BOX_STYLE)
        f1 = QFormLayout(g1)
        self.base_type = combo(["Square Isolated", "Rectangular Isolated", "Combined"])
        self.col_shape = combo(["Rectangular", "Circular"])
        self.base_fcu = spinbox(15, 60, 5, 25)
        self.base_fy = spinbox(250, 600, 10, 460)
        self.base_pb = spinbox(50, 500, 10, 150, 0, " kN/m²")
        f1.addRow("Base Type:", self.base_type)
        f1.addRow("Column Shape:", self.col_shape)
        f1.addRow("fcu (N/mm²):", self.base_fcu)
        f1.addRow("fy (N/mm²):", self.base_fy)
        f1.addRow("Allowable Bearing (kN/m²):", self.base_pb)

        g2 = QGroupBox("Loads & Dimensions")
        g2.setStyleSheet(GROUP_BOX_STYLE)
        f2 = QFormLayout(g2)
        self.base_load = spinbox(0, 50000, 100, 1000)
        self.base_a1 = spinbox(100, 2000, 25, 300, 0)
        self.base_a2 = spinbox(100, 2000, 25, 300, 0)
        self.base_dia = spinbox(100, 2000, 25, 300, 0)
        self.base_h = spinbox(100, 2000, 25, 300, 0)
        self.base_l1 = spinbox(0, 20, 0.5, 0, 2, " m")
        self.base_l2 = spinbox(0, 20, 0.5, 0, 2, " m")
        self.base_dowel = spinbox(8, 40, 2, 12, 0)
        f2.addRow("Axial Load (kN):", self.base_load)
        f2.addRow("Col Dim a1 (mm):", self.base_a1)
        f2.addRow("Col Dim a2 (mm):", self.base_a2)
        f2.addRow("Col Diameter (mm):", self.base_dia)
        f2.addRow("Base Thickness h (mm):", self.base_h)
        f2.addRow("Base Length L1 (m):", self.base_l1)
        f2.addRow("Base Width L2 (m):", self.base_l2)
        f2.addRow("Dowel Diameter (mm):", self.base_dowel)

        self.calc_btn = button("Design Foundation")
        self.calc_btn.clicked.connect(self._calculate)
        self.save_btn = button("Save Report to Desktop")
        self.save_btn.clicked.connect(self._save_report)
        self.save_btn.setVisible(False)
        self.results_area = QVBoxLayout()

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(self.calc_btn)
        layout.addWidget(self.save_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

    def _calculate(self):
        self._clear_results()
        btype = self.base_type.currentIndex() + 1
        self._last_input = BaseInput(
            base_id="F1",
            base_type=btype,
            col_type=1 if self.col_shape.currentIndex() == 0 else 2,
            load=self.base_load.value(),
            pb=self.base_pb.value(), fcu=self.base_fcu.value(),
            fy=self.base_fy.value(),
            a1=self.base_a1.value(), a2=self.base_a2.value(),
            dia=self.base_dia.value(), dowel_dia=self.base_dowel.value(),
            h=self.base_h.value(),
            l1=self.base_l1.value(), l2=self.base_l2.value(),
        )
        designer = BaseDesigner(
            pb=self.base_pb.value(), fcu=self.base_fcu.value(),
            fy=self.base_fy.value(),
        )
        self._last_result = designer.design([self._last_input])[0]
        r = self._last_result

        rows = [
            ["Base Length L1 (mm)", fmt(r.l1)],
            ["Base Width L2 (mm)", fmt(r.l2)],
            ["Base Depth h (mm)", fmt(r.h)],
            ["Net Upward Pressure (kN/m²)", fmt2(r.fnet)],
            ["Moment L1 (kN·m)", fmt2(r.m1)],
            ["Steel L1 (mm²)", fmt(r.as1)],
            [f"Bar L1", f"Y{r.rd1:.0f} @ {r.sp1:.0f} c/c"],
            ["Moment L2 (kN·m)", fmt2(r.m2)],
            ["Steel L2 (mm²)", fmt(r.as2)],
            [f"Bar L2", f"Y{r.rd2:.0f} @ {r.sp2:.0f} c/c"],
            ["Shear Stress (N/mm²)", fmt2(r.shear_stress)],
            ["Permissible Shear (N/mm²)", fmt2(r.perm_shear)],
            ["Punching Shear (N/mm²)", fmt2(r.punching_shear)],
            ["Local Bond (N/mm²)", fmt2(r.local_bond)],
            ["Permissible Bond (N/mm²)", fmt2(r.perm_bond)],
        ]
        self.results_area.addWidget(make_table(["Parameter", "Value"], rows))
        self.save_btn.setVisible(True)

    def _save_report(self):
        text = format_base(self._last_input, self._last_result)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_BASE.txt"),
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
