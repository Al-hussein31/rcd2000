"""Continuous beam analysis form page."""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFileDialog,
)
from PySide6.QtCore import Qt

from rcd2000.continuous_beam import (
    ContinuousBeamAnalyzer, ContinuousBeamInput, ContinuousBeamMember,
)
from rcd2000.report import format_continuous_beam
from rcd2000.gui.theme import TEXT_SECONDARY, fmt2, ACCENT
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, button, label, header_label, make_table,
    Card, SpanDiagram,
)


class ContinuousBeamPage(QWidget):
    def __init__(self):
        super().__init__()
        self._cb_member_widgets = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(header_label("Continuous Beam Analysis - BS 8110"))

        c1 = Card("Supports & End Conditions")
        self.cb_ns = spin_int(2, 10, 3)
        self.cb_nm = spin_int(1, 9, 2)
        self.cb_end1 = combo(["Pinned", "Fixed"])
        self.cb_end2 = combo(["Pinned", "Fixed"])
        self.cb_nm.valueChanged.connect(self._sync_members)
        c1.add_row("Number of Supports:", self.cb_ns)
        c1.add_row("Number of Members:", self.cb_nm)
        c1.add_row("Left End:", self.cb_end1)
        c1.add_row("Right End:", self.cb_end2)
        layout.addWidget(c1)

        self.diagram = SpanDiagram()
        self.diagram.setVisible(False)
        layout.addWidget(self.diagram)

        c2 = Card("Member Data")
        self.member_grid = QGridLayout()
        self.member_grid.setSpacing(6)
        c2.add_layout(self.member_grid)
        layout.addWidget(c2)

        self.calc_btn = button("Analyze Beam")
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
        nm = self.cb_nm.value()
        while len(self._cb_member_widgets) < nm:
            row = len(self._cb_member_widgets) + 1
            lbl = QLabel(f"M{row}")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px; background: transparent;")
            length = spinbox(1, 50, 0.5, 5, 2, " m")
            inertia = spinbox(0.0001, 10, 0.001, 0.001, 4)
            e_mod = spinbox(0.1, 10, 0.1, 1, 1)
            udl = spinbox(0, 500, 5, 0, 1, " kN/m")
            wt = spinbox(0, 200, 5, 0, 1)
            wb = spinbox(0, 200, 5, 0, 1)
            ab = spinbox(0, 10, 0.5, 0, 2)
            self.member_grid.addWidget(lbl, row, 0)
            self.member_grid.addWidget(length, row, 1)
            self.member_grid.addWidget(inertia, row, 2)
            self.member_grid.addWidget(e_mod, row, 3)
            self.member_grid.addWidget(udl, row, 4)
            self.member_grid.addWidget(wt, row, 5)
            self.member_grid.addWidget(wb, row, 6)
            self.member_grid.addWidget(ab, row, 7)
            self._cb_member_widgets.append((lbl, length, inertia, e_mod, udl, wt, wb, ab))

        headers = ["", "L (m)", "I (m⁴)", "E-rel", "UDL", "Tri", "Trap", "Dist"]
        for col, h in enumerate(headers):
            self.member_grid.addWidget(label(h, secondary=True, size=11), 0, col)

        self._update_diagram()

    def _update_diagram(self):
        data = [
            {"length": w[1].value(), "udl": w[4].value()}
            for w in self._cb_member_widgets
        ]
        self.diagram.set_spans(data)
        self.diagram.setVisible(len(self._cb_member_widgets) > 0)

    def _calculate(self):
        self._clear_results()
        nm = self.cb_nm.value()
        members = []
        for i, w in enumerate(self._cb_member_widgets):
            members.append(ContinuousBeamMember(
                member_id=f"M{i+1}",
                length=w[1].value(),
                inertia=w[2].value(),
                e_mod=w[3].value(),
                udl=w[4].value(),
                wt=w[5].value(),
                wb=w[6].value(),
                ab=w[7].value(),
            ))
        self._last_input = ContinuousBeamInput(
            n_supports=self.cb_ns.value(),
            n_members=nm,
            members=members,
            end1_type=self.cb_end1.currentIndex(),
            end2_type=self.cb_end2.currentIndex(),
        )
        analyzer = ContinuousBeamAnalyzer()
        self._last_result = analyzer.analyze(self._last_input)
        r = self._last_result

        if r.support_moments:
            hdrs = ["Support", "Moment (kN·m)", "Reaction (kN)"]
            rows = [[f"Sup {i+1}", fmt2(m), fmt2(re)]
                    for i, (m, re) in enumerate(zip(r.support_moments, r.support_reactions))]
            self.results_area.addWidget(label("Support Results", bold=True, size=14))
            self.results_area.addWidget(make_table(hdrs, rows))

        if r.span_moments:
            hdrs = ["Span", "M (kN·m)", "Shear L (kN)", "Shear R (kN)"]
            rows = [[f"Span {i+1}", fmt2(m), fmt2(sl), fmt2(sr)]
                    for i, (m, sl, sr) in enumerate(zip(r.span_moments, r.span_shear_left, r.span_shear_right))]
            self.results_area.addWidget(label("Span Results", bold=True, size=14))
            self.results_area.addWidget(make_table(hdrs, rows))

        self.save_btn.setVisible(True)
        self.pdf_btn.setVisible(True)
        if hasattr(self, '_history_cb') and self._history_cb:
            self._history_cb("Continuous Beam", self._last_input, self._last_result)

    def _save_report(self, fmt_type="txt"):
        text = format_continuous_beam(self._last_input, self._last_result)
        if fmt_type == "txt":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Report", os.path.expanduser("~/Desktop/RCD2000_CBEAM.txt"),
                "Text Files (*.txt)",
            )
            if path:
                with open(path, "w") as f:
                    f.write(text)
        else:
            from rcd2000.report import export_pdf
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report", os.path.expanduser("~/Desktop/RCD2000_CBEAM.pdf"),
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
