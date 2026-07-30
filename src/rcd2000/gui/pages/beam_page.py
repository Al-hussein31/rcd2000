"""Beam design form page."""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QLabel, QFileDialog,
)
from PySide6.QtCore import Qt

from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.report import format_beam
from rcd2000.gui.theme import GROUP_BOX_STYLE, TEXT_SECONDARY, fmt, fmt2, ACCENT, BG_CARD, BORDER
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, button, label, header_label, make_table,
    Card, fcu_combo, fy_combo, badge, load_combo_group, SpanDiagram, divider,
)


class BeamPage(QWidget):
    def __init__(self):
        super().__init__()
        self._member_widgets = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(header_label("Beam Design - BS 8110"))

        c1 = Card("Material Properties")
        self.beam_fcu = fcu_combo()
        self.beam_fy = fy_combo()
        self.beam_fyv = combo(["250", "410", "460"])
        c1.add_row("fcu (N/mm²):", self.beam_fcu)
        c1.add_row("fy (N/mm²):", self.beam_fy)
        c1.add_row("fyv (N/mm²):", self.beam_fyv)
        layout.addWidget(c1)

        c2 = Card("Section Geometry")
        self.b_b = spinbox(100, 2000, 25, 225, 0)
        self.b_bf = spinbox(100, 2000, 25, 225, 0)
        self.b_h = spinbox(100, 2000, 25, 450, 0)
        self.b_hf = spinbox(0, 500, 10, 0, 0)
        c2.add_row("b (mm):", self.b_b)
        c2.add_row("bf - flange width (mm):", self.b_bf)
        c2.add_row("h - overall depth (mm):", self.b_h)
        c2.add_row("hf - flange depth (mm):", self.b_hf)
        layout.addWidget(c2)

        c3 = Card("Supports & Members")
        self.n_supports = spin_int(2, 10, 2)
        self.n_members = spin_int(1, 9, 1)
        self.ty1 = combo(["Pinned", "Fixed"])
        self.ty2 = combo(["Pinned", "Fixed"])
        self.n_members.valueChanged.connect(self._sync_members)
        c3.add_row("Number of Supports:", self.n_supports)
        c3.add_row("Number of Members:", self.n_members)
        c3.add_row("Left End:", self.ty1)
        c3.add_row("Right End:", self.ty2)
        layout.addWidget(c3)

        self.diagram = SpanDiagram()
        self.diagram.setVisible(False)
        layout.addWidget(self.diagram)

        c4 = Card("Loads")
        load_w, self.gk, self.qk, self.load_result = load_combo_group()
        c4.add_widget(load_w)
        layout.addWidget(c4)

        c5 = Card("Member Data")
        self.member_grid = QGridLayout()
        self.member_grid.setSpacing(6)
        c5.add_layout(self.member_grid)
        layout.addWidget(c5)

        self.calc_btn = button("Design Beam")
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

        self._sync_members()

    def _sync_members(self):
        nm = self.n_members.value()
        while len(self._member_widgets) < nm:
            row = len(self._member_widgets) + 1
            lbl = QLabel(f"M{row}")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px; background: transparent;")
            length = spinbox(1, 50, 0.5, 5, 2, " m")
            udl = spinbox(0, 500, 5, 0, 1, " kN/m")
            wt = spinbox(0, 200, 5, 0, 1)
            wb = spinbox(0, 200, 5, 0, 1)
            ab = spinbox(0, 10, 0.5, 0, 2)
            self.member_grid.addWidget(lbl, row, 0)
            self.member_grid.addWidget(length, row, 1)
            self.member_grid.addWidget(udl, row, 2)
            self.member_grid.addWidget(wt, row, 3)
            self.member_grid.addWidget(wb, row, 4)
            self.member_grid.addWidget(ab, row, 5)
            self._member_widgets.append((lbl, length, udl, wt, wb, ab))

        headers = ["", "Length", "UDL", "Tri (wt)", "Trap (wb)", "Dist (ab)"]
        for col, h in enumerate(headers):
            self.member_grid.addWidget(label(h, secondary=True, size=11), 0, col)

        self._update_diagram()

    def _update_diagram(self):
        data = [
            {"length": w[1].value(), "udl": w[2].value()}
            for w in self._member_widgets
        ]
        self.diagram.set_spans(data)
        self.diagram.setVisible(len(self._member_widgets) > 0)

    def _calculate(self):
        self._clear_results()
        nm = self.n_members.value()
        fcu = int(self.beam_fcu.currentText())
        fy = int(self.beam_fy.currentText())
        fyv = int(self.beam_fyv.currentText())

        self._last_input = BeamInput(
            beam_id="B1",
            n_supports=self.n_supports.value(),
            n_members=nm,
            b=self.b_b.value(), bf=self.b_bf.value(),
            h=self.b_h.value(), hf=self.b_hf.value(),
            fcu=fcu, fy=fy, fyv=fyv,
            member_lengths=[w[1].value() for w in self._member_widgets],
            member_udl=[w[2].value() for w in self._member_widgets],
            member_wt=[w[3].value() for w in self._member_widgets],
            member_wb=[w[4].value() for w in self._member_widgets],
            member_ab=[w[5].value() for w in self._member_widgets],
            ty1=self.ty1.currentIndex(),
            ty2=self.ty2.currentIndex(),
        )
        designer = BeamDesigner(fcu=fcu, fy=fy, fyv=fyv)
        self._last_result = designer.design([self._last_input])[0]
        result = self._last_result

        if result.spans:
            hdrs = ["Span", "L (m)", "M (kN·m)", "As_bot (mm²)", "As_top (mm²)",
                     "V_left (kN)", "V_right (kN)", "Defl"]
            rows = [
                [s.span_id, fmt2(s.length), fmt2(s.moment),
                 fmt(s.steel_bot), fmt(s.steel_top),
                 fmt2(s.shear_left), fmt2(s.shear_right),
                 badge(s.defl_ok)]
                for s in result.spans
            ]
            self.results_area.addWidget(label("Span Results", bold=True, size=14))
            self.results_area.addWidget(make_table(hdrs, rows))

        if result.supports:
            hdrs2 = ["Support", "Reaction (kN)", "M (kN·m)", "As_top (mm²)", "As_bot (mm²)"]
            rows2 = [
                [s.support_id, fmt2(s.reaction), fmt2(s.moment),
                 fmt(s.steel_top), fmt(s.steel_bot)]
                for s in result.supports
            ]
            self.results_area.addWidget(label("Support Results", bold=True, size=14))
            self.results_area.addWidget(make_table(hdrs2, rows2))

        self.save_btn.setVisible(True)
        self.pdf_btn.setVisible(True)
        if hasattr(self, '_history_cb') and self._history_cb:
            self._history_cb("Beam", self._last_input, self._last_result)

    def _save_report(self, fmt_type="txt"):
        text = format_beam(self._last_input, self._last_result)
        if fmt_type == "txt":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_BEAM.txt"),
                "Text Files (*.txt)",
            )
            if path:
                with open(path, "w") as f:
                    f.write(text)
        else:
            from rcd2000.report import export_pdf
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report", os.path.expanduser("~/Desktop/RCD2000_BEAM.pdf"),
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
