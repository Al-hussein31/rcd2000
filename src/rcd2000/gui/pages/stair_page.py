"""Stair design form page."""

import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
)

from rcd2000.stair import StairDesigner, StairInput
from rcd2000.report import format_stair
from rcd2000.gui.theme import fmt, fmt2
from rcd2000.gui.widgets import (
    spinbox, button, label, header_label, make_table,
    Card, badge, load_combo_group,
)


class StairPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(header_label("Stair Design - BS 8110"))

        c = Card("Stair Geometry & Loading")
        # AUDIT: span 1–12 m is fine. The engine assumes waist = span/20,
        # so very short spans produce very thin slabs (<100mm min enforced).
        self.s_span = spinbox(1, 12, 0.5, 4, 2, " m")
        # AUDIT: tread 150–400 mm and rise 100–250 mm — rise/tread ratio
        # not enforced. BS 8110 doesn't strictly govern this, but
        # comfort guidelines suggest rise/tread <= 0.75.
        self.s_tread = spinbox(150, 400, 5, 250, 0)
        self.s_rise = spinbox(100, 250, 5, 175, 0)
        c.add_row("Span (m):", self.s_span)
        c.add_row("Tread (mm):", self.s_tread)
        c.add_row("Rise (mm):", self.s_rise)

        # AUDIT: imposed_load 0–20 kN/m² and spl 0–10 kN/m² are fine.
        # wld 0–50 kN/m³ — default 0 means self-weight is the only DL.
        self.s_imp = spinbox(0, 20, 0.5, 1.5, 2, " kN/m²")
        self.s_spl = spinbox(0, 10, 0.5, 0, 2, " kN/m²")
        self.s_wld = spinbox(0, 50, 1, 0, 1, " kN/m³")
        c.add_row("Imposed Load (kN/m²):", self.s_imp)
        c.add_row("Sup. DL (kN/m²):", self.s_spl)
        c.add_row("WLD (kN/m³):", self.s_wld)

        load_w, self.gk, self.qk, self.load_result = load_combo_group()
        c.add_widget(label("Load Combination (for reference)", secondary=True, size=12))
        c.add_widget(load_w)
        layout.addWidget(c)

        self.calc_btn = button("Design Stair")
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
        try:
            self._last_result = designer.design([self._last_input])[0]
        except Exception as exc:
            logging.error("Stair design failed", exc_info=True)
            QMessageBox.warning(
                self, "Design Error",
                f"Could not complete the design — check your inputs: {exc}",
            )
            return

        r = self._last_result

        rows = [
            ["Waist Thickness (mm)", fmt(r.waist_thickness), ""],
            ["Total UDL (kN/m)", fmt2(r.total_udl), ""],
            ["Design Moment (kN·m)", fmt2(r.design_moment), ""],
            ["Effective Depth (mm)", fmt(r.effective_depth), ""],
            ["K Value", fmt2(r.k_value), ""],
            ["Lever Arm Factor", fmt2(r.lever_arm_factor), ""],
            ["Lever Arm z (mm)", fmt2(r.lever_arm_z), ""],
            ["Steel Required (mm²)", fmt(r.steel_required), ""],
            ["Bar Type", r.bar_type, ""],
            ["Bar Diameter (mm)", fmt(r.bar_dia), ""],
            ["Bar Spacing (mm)", fmt(r.bar_spacing), ""],
        ]
        self.results_area.addWidget(make_table(["Parameter", "Value", "Status"], rows))
        self.save_btn.setVisible(True)
        self.pdf_btn.setVisible(True)
        if hasattr(self, '_history_cb') and self._history_cb:
            self._history_cb("Stair", self._last_input, self._last_result)

    def _save_report(self, fmt_type="txt"):
        text = format_stair(self._last_input, self._last_result)
        if fmt_type == "txt":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_STAIR.txt"),
                "Text Files (*.txt)",
            )
            if path:
                with open(path, "w") as f:
                    f.write(text)
        else:
            from rcd2000.report import export_pdf
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report", os.path.expanduser("~/Desktop/RCD2000_STAIR.pdf"),
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
