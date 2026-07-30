"""Beam design form page."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGridLayout, QGroupBox, QLabel,
)

from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.gui.theme import GROUP_BOX_STYLE, TEXT_SECONDARY, fmt, fmt2
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, button, label, header_label, make_table,
)


class BeamPage(QWidget):
    def __init__(self):
        super().__init__()
        self._member_widgets = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(header_label("Beam Design — BS 8110"))

        g1 = QGroupBox("Material Properties")
        g1.setStyleSheet(GROUP_BOX_STYLE)
        f1 = QFormLayout(g1)
        self.beam_fcu = spinbox(15, 60, 5, 25)
        self.beam_fy = spinbox(250, 600, 10, 460)
        self.beam_fyv = spinbox(200, 500, 10, 250)
        f1.addRow("fcu (N/mm²):", self.beam_fcu)
        f1.addRow("fy (N/mm²):", self.beam_fy)
        f1.addRow("fyv (N/mm²):", self.beam_fyv)

        g2 = QGroupBox("Section Geometry")
        g2.setStyleSheet(GROUP_BOX_STYLE)
        f2 = QFormLayout(g2)
        self.b_b = spinbox(100, 2000, 25, 225, 0)
        self.b_bf = spinbox(100, 2000, 25, 225, 0)
        self.b_h = spinbox(100, 2000, 25, 450, 0)
        self.b_hf = spinbox(0, 500, 10, 0, 0)
        f2.addRow("b (mm):", self.b_b)
        f2.addRow("bf — flange width (mm):", self.b_bf)
        f2.addRow("h — overall depth (mm):", self.b_h)
        f2.addRow("hf — flange depth (mm):", self.b_hf)

        g3 = QGroupBox("Supports & Members")
        g3.setStyleSheet(GROUP_BOX_STYLE)
        f3 = QFormLayout(g3)
        self.n_supports = spin_int(2, 10, 2)
        self.n_members = spin_int(1, 9, 1)
        self.ty1 = combo(["Pinned", "Fixed"])
        self.ty2 = combo(["Pinned", "Fixed"])
        self.n_members.valueChanged.connect(self._sync_members)
        f3.addRow("Number of Supports:", self.n_supports)
        f3.addRow("Number of Members:", self.n_members)
        f3.addRow("Left End:", self.ty1)
        f3.addRow("Right End:", self.ty2)

        g4 = QGroupBox("Member Data")
        g4.setStyleSheet(GROUP_BOX_STYLE)
        self.member_grid = QGridLayout(g4)
        self.member_grid.setSpacing(6)

        self.calc_btn = button("Design Beam")
        self.calc_btn.clicked.connect(self._calculate)
        self.results_area = QVBoxLayout()

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(g3)
        layout.addWidget(g4)
        layout.addWidget(self.calc_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

        self._sync_members()

    def _sync_members(self):
        nm = self.n_members.value()
        while len(self._member_widgets) < nm:
            row = len(self._member_widgets) + 1
            lbl = QLabel(f"M{row}")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px;")
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

    def _calculate(self):
        self._clear_results()
        nm = self.n_members.value()
        beam = BeamInput(
            beam_id="B1",
            n_supports=self.n_supports.value(),
            n_members=nm,
            b=self.b_b.value(), bf=self.b_bf.value(),
            h=self.b_h.value(), hf=self.b_hf.value(),
            fcu=self.beam_fcu.value(), fy=self.beam_fy.value(),
            fyv=self.beam_fyv.value(),
            member_lengths=[w[1].value() for w in self._member_widgets],
            member_udl=[w[2].value() for w in self._member_widgets],
            member_wt=[w[3].value() for w in self._member_widgets],
            member_wb=[w[4].value() for w in self._member_widgets],
            member_ab=[w[5].value() for w in self._member_widgets],
            ty1=self.ty1.currentIndex(),
            ty2=self.ty2.currentIndex(),
        )
        designer = BeamDesigner(
            fcu=self.beam_fcu.value(), fy=self.beam_fy.value(),
            fyv=self.beam_fyv.value(),
        )
        result = designer.design([beam])[0]

        if result.spans:
            hdrs = ["Span", "L (m)", "M (kN·m)", "As_bot (mm²)", "As_top (mm²)",
                     "V_left (kN)", "V_right (kN)", "Defl OK"]
            rows = [
                [s.span_id, fmt2(s.length), fmt2(s.moment),
                 fmt(s.steel_bot), fmt(s.steel_top),
                 fmt2(s.shear_left), fmt2(s.shear_right),
                 "✓" if s.defl_ok else "✗"]
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

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()
