"""Beam design form page."""

import logging

from PySide6.QtWidgets import QHBoxLayout, QGridLayout, QLabel
from PySide6.QtCore import Qt

from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.report import format_beam
from rcd2000.gui.theme import TEXT_SECONDARY, fmt, fmt2
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, label, Card, fcu_combo, fy_combo, badge,
    SpanDiagram,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class BeamPage(DesignFormPage):
    module_name = "Beam"

    def __init__(self):
        self._member_widgets = []
        super().__init__()

    def build_inputs(self, layout):
        c1 = Card("Material Properties")
        self.beam_fcu = fcu_combo()
        self.beam_fy = fy_combo()
        self.beam_fyv = combo(["250", "410", "460"])
        c1.add_row("fcu (N/mm²):", self.beam_fcu)
        c1.add_row("fy (N/mm²):", self.beam_fy)
        c1.add_row("fyv (N/mm²):", self.beam_fyv)
        layout.addWidget(c1)

        c2 = Card("Section Geometry")
        # AUDIT: bf (flange width) range 100–2000 mm allows bf < b (web width),
        # which is physically invalid for BS 8110 — the engine doesn't guard
        # against this. Consider enforcing bf >= b at design time.
        self.b_b = spinbox(100, 2000, 25, 225, 0)
        self.b_bf = spinbox(100, 2000, 25, 225, 0)
        # AUDIT: h range 100–2000 mm allows h < b+100 (minimum effective depth),
        # which would cause steel_beam to fail or produce nonsensical results.
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
        from rcd2000.gui.widgets import load_combo_group
        load_w, self.gk, self.qk, self.load_result = load_combo_group()
        c4.add_widget(load_w)
        layout.addWidget(c4)

        c5 = Card("Member Data")
        self.member_grid = QGridLayout()
        self.member_grid.setSpacing(6)
        c5.add_layout(self.member_grid)
        layout.addWidget(c5)

        self._sync_members()

    def _sync_members(self):
        nm = self.n_members.value()
        while len(self._member_widgets) < nm:
            row = len(self._member_widgets) + 1
            lbl = QLabel(f"M{row}")
            lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px; "
                f"background: transparent;"
            )
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
            self.member_grid.addWidget(
                label(h, secondary=True, size=11), 0, col
            )

        self._update_diagram()

    def _update_diagram(self):
        data = [
            {"length": w[1].value(), "udl": w[2].value()}
            for w in self._member_widgets
        ]
        self.diagram.set_spans(data)
        self.diagram.setVisible(len(self._member_widgets) > 0)

    def calculate(self):
        nm = self.n_members.value()
        fcu = int(self.beam_fcu.currentText())
        fy = int(self.beam_fy.currentText())
        fyv = int(self.beam_fyv.currentText())

        inp = BeamInput(
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
        result = designer.design([inp])[0]
        return inp, result

    def format_report(self, inp, result):
        return format_beam(inp, result)

    def _build_result_rows(self, r):
        # Span results
        rows = []
        for s in r.spans:
            rows.append([s.span_id, fmt2(s.length), fmt2(s.moment),
                         fmt(s.steel_bot), fmt(s.steel_top),
                         fmt2(s.shear_left), fmt2(s.shear_right),
                         badge(s.defl_ok)])
        return rows

    def get_state(self) -> dict:
        return {
            "beam_fcu": int(self.beam_fcu.currentText()),
            "beam_fy": int(self.beam_fy.currentText()),
            "beam_fyv": int(self.beam_fyv.currentText()),
            "b_b": self.b_b.value(),
            "b_bf": self.b_bf.value(),
            "b_h": self.b_h.value(),
            "b_hf": self.b_hf.value(),
            "n_supports": self.n_supports.value(),
            "n_members": self.n_members.value(),
            "ty1": self.ty1.currentIndex(),
            "ty2": self.ty2.currentIndex(),
            "gk": self.gk.value(),
            "qk": self.qk.value(),
            "members": [
                {
                    "length": w[1].value(),
                    "udl": w[2].value(),
                    "wt": w[3].value(),
                    "wb": w[4].value(),
                    "ab": w[5].value(),
                }
                for w in self._member_widgets
            ],
        }

    def set_state(self, state: dict) -> None:
        if "beam_fcu" in state:
            self._set_combo_int(self.beam_fcu, state["beam_fcu"])
        if "beam_fy" in state:
            self._set_combo_int(self.beam_fy, state["beam_fy"])
        if "beam_fyv" in state:
            self._set_combo_int(self.beam_fyv, state["beam_fyv"])
        if "b_b" in state:
            self.b_b.setValue(state["b_b"])
        if "b_bf" in state:
            self.b_bf.setValue(state["b_bf"])
        if "b_h" in state:
            self.b_h.setValue(state["b_h"])
        if "b_hf" in state:
            self.b_hf.setValue(state["b_hf"])
        if "n_supports" in state:
            self.n_supports.setValue(state["n_supports"])
        if "n_members" in state:
            self.n_members.setValue(state["n_members"])
        if "ty1" in state:
            self.ty1.setCurrentIndex(state["ty1"])
        if "ty2" in state:
            self.ty2.setCurrentIndex(state["ty2"])
        if "gk" in state:
            self.gk.setValue(state["gk"])
        if "qk" in state:
            self.qk.setValue(state["qk"])
        if "members" in state and self._member_widgets:
            for i, w in enumerate(self._member_widgets):
                if i < len(state["members"]):
                    m = state["members"][i]
                    if "length" in m:
                        w[1].setValue(m["length"])
                    if "udl" in m:
                        w[2].setValue(m["udl"])
                    if "wt" in m:
                        w[3].setValue(m["wt"])
                    if "wb" in m:
                        w[4].setValue(m["wb"])
                    if "ab" in m:
                        w[5].setValue(m["ab"])
