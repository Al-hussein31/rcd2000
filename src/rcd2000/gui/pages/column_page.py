"""Column design form page."""

import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
)

from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.report import format_column
from rcd2000.gui.theme import fmt, ACCENT
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, button, label, header_label, make_table,
    Card, badge,
)


class ColumnPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(header_label("Column Design - BS 8110"))

        c1 = Card("Column Type")
        self.col_type = combo(["1 - Axially Loaded", "2 - Uniaxial Bending", "3 - Biaxial Bending"])
        self.shape = combo(["Rectangular", "Circular"])
        c1.add_row("Type:", self.col_type)
        c1.add_row("Shape:", self.shape)
        layout.addWidget(c1)

        c2 = Card("Loads & Geometry")
        # AUDIT: load range 0–50000 kN may exceed what a rectangular column
        # of the given dimensions can carry — the engine will return heck=1,
        # but the user gets no early guidance. Consider adding a pre-check.
        self.load = spinbox(0, 50000, 100, 1000)
        # AUDIT: bx/by range 100–2000 mm is fine, but for circular columns
        # these are ignored — dia is used instead. No conflict.
        self.bx = spinbox(100, 2000, 25, 300, 0)
        self.by = spinbox(100, 2000, 25, 300, 0)
        # AUDIT: dia 100–2000 mm is physically large but not invalid.
        self.dia = spinbox(100, 2000, 25, 300, 0)
        # AUDIT: depth 100–2000 mm — for circular columns, depth must equal
        # dia for the engine to work correctly. The page doesn't enforce this.
        self.depth = spinbox(100, 2000, 25, 300, 0)
        c2.add_row("Axial Load (kN):", self.load)
        c2.add_row("b/h width - x (mm):", self.bx)
        c2.add_row("b/h width - y (mm):", self.by)
        c2.add_row("Diameter (mm):", self.dia)
        c2.add_row("Overall depth (mm):", self.depth)
        layout.addWidget(c2)

        c3 = Card("Moments")
        self.moment_x = spinbox(0, 5000, 10, 0)
        self.moment_y = spinbox(0, 5000, 10, 0)
        self.moment = spinbox(0, 5000, 10, 0)
        c3.add_row("Mx (kN·m):", self.moment_x)
        c3.add_row("My (kN·m):", self.moment_y)
        c3.add_row("M (uniaxial, kN·m):", self.moment)
        layout.addWidget(c3)

        self.calc_btn = button("Design Column")
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

    def _calculate(self):
        self._clear_results()
        try:
            col_type = self.col_type.currentIndex() + 1
            # For axial columns (col_type=1), moment is not applicable.
            # For uniaxial (col_type=2), use the dedicated moment field.
            # For biaxial (col_type=3), use moment_x / moment_y.
            # Only fall back to moment_x when the uniaxial moment field is
            # genuinely not provided (i.e., col_type != 2), so that a
            # legitimate 0.0 input is respected.
            if col_type == 2:
                moment = self.moment.value()
            elif col_type == 3:
                moment = self.moment_x.value()
            else:
                moment = 0.0

            self._last_input = ColumnInput(
                column_id="C1",
                col_type=col_type,
                shape=1 if self.shape.currentIndex() == 0 else 2,
                load=self.load.value(),
                bx=self.bx.value(), by=self.by.value(),
                dia=self.dia.value(), depth=self.depth.value(),
                moment_x=self.moment_x.value(),
                moment_y=self.moment_y.value(),
                moment=moment,
            )
            designer = ColumnDesigner()
            self._last_result = designer.design([self._last_input])[0]
        except Exception as exc:
            logging.error("Column design failed", exc_info=True)
            QMessageBox.warning(
                self, "Design Error",
                f"Could not complete the design — check your inputs: {exc}",
            )
            return

        r = self._last_result
        ci = self._last_input

        rows = [
            ["Steel Required", f"{result.steel_required:,.0f} mm²", ""],
            ["Steel Percentage", f"{result.steel_percent:.2f}%", ""],
            ["Axial Capacity (Nu)", f"{result.axial_capacity:,.0f} kN",
             badge(result.axial_capacity >= ci.load)],
            ["Moment Capacity (Mux)", f"{result.moment_capacity_x:,.0f} kN·m", ""],
            ["Moment Capacity (Muy)", f"{result.moment_capacity_y:,.0f} kN·m", ""],
        ]
        if ci.col_type == 3:
            ok = result.biaxial_check_ok
            rows.append(["Biaxial Check", "OK" if ok else "FAIL", badge(ok)])

        self.results_area.addWidget(make_table(["Parameter", "Value", "Status"], rows))
        if result.heck:
            self.results_area.addWidget(
                label("Section inadequate - increase dimensions", size=13)
            )
        self.save_btn.setVisible(True)
        self.pdf_btn.setVisible(True)
        if hasattr(self, '_history_cb') and self._history_cb:
            self._history_cb("Column", self._last_input, self._last_result)

    def _save_report(self, fmt_type="txt"):
        text = format_column(self._last_input, self._last_result)
        if fmt_type == "txt":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_COLUMN.txt"),
                "Text Files (*.txt)",
            )
            if path:
                with open(path, "w") as f:
                    f.write(text)
        else:
            from rcd2000.report import export_pdf
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report", os.path.expanduser("~/Desktop/RCD2000_COLUMN.pdf"),
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
