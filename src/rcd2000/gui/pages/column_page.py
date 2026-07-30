"""Column design form page."""

import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QGroupBox, QFileDialog

from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.report import format_column
from rcd2000.gui.theme import GROUP_BOX_STYLE, fmt
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, button, label, header_label, make_table,
)


class ColumnPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(header_label("Column Design - BS 8110"))

        g1 = QGroupBox("Column Type")
        g1.setStyleSheet(GROUP_BOX_STYLE)
        f1 = QFormLayout(g1)
        self.col_type = combo(["1 - Axially Loaded", "2 - Uniaxial Bending", "3 - Biaxial Bending"])
        self.shape = combo(["Rectangular", "Circular"])
        f1.addRow("Type:", self.col_type)
        f1.addRow("Shape:", self.shape)

        g2 = QGroupBox("Loads & Geometry")
        g2.setStyleSheet(GROUP_BOX_STYLE)
        f2 = QFormLayout(g2)
        self.load = spinbox(0, 50000, 100, 1000)
        self.bx = spinbox(100, 2000, 25, 300, 0)
        self.by = spinbox(100, 2000, 25, 300, 0)
        self.dia = spinbox(100, 2000, 25, 300, 0)
        self.depth = spinbox(100, 2000, 25, 300, 0)
        f2.addRow("Axial Load (kN):", self.load)
        f2.addRow("b/h width - x (mm):", self.bx)
        f2.addRow("b/h width - y (mm):", self.by)
        f2.addRow("Diameter (mm):", self.dia)
        f2.addRow("Overall depth (mm):", self.depth)

        g3 = QGroupBox("Moments")
        g3.setStyleSheet(GROUP_BOX_STYLE)
        f3 = QFormLayout(g3)
        self.moment_x = spinbox(0, 5000, 10, 0)
        self.moment_y = spinbox(0, 5000, 10, 0)
        self.moment = spinbox(0, 5000, 10, 0)
        f3.addRow("Mx (kN·m):", self.moment_x)
        f3.addRow("My (kN·m):", self.moment_y)
        f3.addRow("M (uniaxial, kN·m):", self.moment)

        self.calc_btn = button("Design Column")
        self.calc_btn.clicked.connect(self._calculate)
        self.save_btn = button("Save Report to Desktop")
        self.save_btn.clicked.connect(self._save_report)
        self.save_btn.setVisible(False)

        self.results_area = QVBoxLayout()
        self.results_area.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(g3)
        layout.addWidget(self.calc_btn)
        layout.addWidget(self.save_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

    def _calculate(self):
        self._clear_results()
        self._last_input = ColumnInput(
            column_id="C1",
            col_type=self.col_type.currentIndex() + 1,
            shape=1 if self.shape.currentIndex() == 0 else 2,
            load=self.load.value(),
            bx=self.bx.value(), by=self.by.value(),
            dia=self.dia.value(), depth=self.depth.value(),
            moment_x=self.moment_x.value(),
            moment_y=self.moment_y.value(),
            moment=self.moment.value() or self.moment_x.value(),
        )
        designer = ColumnDesigner()
        self._last_result = designer.design([self._last_input])[0]
        result = self._last_result
        c = self._last_input

        rows = [
            ["Steel Required", f"{result.steel_required:,.0f} mm²", ""],
            ["Steel Percentage", f"{result.steel_percent:.2f}%", ""],
            ["Axial Capacity (Nu)", f"{result.axial_capacity:,.0f} kN",
             "✓" if result.axial_capacity >= c.load else "✗"],
            ["Moment Capacity (Mux)", f"{result.moment_capacity_x:,.0f} kN·m", ""],
            ["Moment Capacity (Muy)", f"{result.moment_capacity_y:,.0f} kN·m", ""],
        ]
        if c.col_type == 3:
            rows.append(["Biaxial Check", "OK" if result.biaxial_check_ok else "FAIL",
                         "✓" if result.biaxial_check_ok else "✗"])

        self.results_area.addWidget(make_table(["Parameter", "Value", "Status"], rows))
        if result.heck:
            self.results_area.addWidget(label("Section inadequate - increase dimensions", size=13))
        self.save_btn.setVisible(True)

    def _save_report(self):
        text = format_column(self._last_input, self._last_result)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_COLUMN.txt"),
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
