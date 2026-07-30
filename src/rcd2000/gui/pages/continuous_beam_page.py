"""Continuous beam analysis form page."""

from PySide6.QtWidgets import QGridLayout, QLabel

from rcd2000.continuous_beam import (
    ContinuousBeamAnalyzer, ContinuousBeamInput, ContinuousBeamMember,
)
from rcd2000.report import format_continuous_beam
from rcd2000.gui.theme import TEXT_SECONDARY, fmt2
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, label, Card, SpanDiagram,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class ContinuousBeamPage(DesignFormPage):
    module_name = "Continuous Beam"

    def __init__(self):
        self._cb_member_widgets = []
        super().__init__()

    def _page_title(self):
        return "Continuous Beam Analysis - BS 8110"

    def _calc_button_text(self):
        return "Analyze Beam"

    def build_inputs(self, layout):
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

        self._sync_members()

    def _sync_members(self):
        nm = self.cb_nm.value()
        while len(self._cb_member_widgets) < nm:
            row = len(self._cb_member_widgets) + 1
            lbl = QLabel(f"M{row}")
            lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px; "
                f"background: transparent;"
            )
            # AUDIT: length 1–50 m is fine. inertia 0.0001–10 m⁴ is
            # very small but the engine uses it directly in the stiffness
            # matrix — zero would cause division-by-zero, but the min
            # prevents that.
            length = spinbox(1, 50, 0.5, 5, 2, " m")
            inertia = spinbox(0.0001, 10, 0.001, 0.001, 4)
            # AUDIT: e_mod 0.1–10 — relative modulus, fine as-is.
            e_mod = spinbox(0.1, 10, 0.1, 1, 1)
            udl = spinbox(0, 500, 5, 0, 1, " kN/m")
            wt = spinbox(0, 200, 5, 0, 1)
            wb = spinbox(0, 200, 5, 0, 1)
            # AUDIT: ab 0–10 m — trapezoidal load position. If ab > length,
            # the load is outside the member. The engine clamps alpha =
            # ab/l which could exceed 1.0, producing invalid results.
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
            self.member_grid.addWidget(
                label(h, secondary=True, size=11), 0, col
            )

        self._update_diagram()

    def _update_diagram(self):
        data = [
            {"length": w[1].value(), "udl": w[4].value()}
            for w in self._cb_member_widgets
        ]
        self.diagram.set_spans(data)
        self.diagram.setVisible(len(self._cb_member_widgets) > 0)

    def calculate(self):
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
        inp = ContinuousBeamInput(
            n_supports=self.cb_ns.value(),
            n_members=nm,
            members=members,
            end1_type=self.cb_end1.currentIndex(),
            end2_type=self.cb_end2.currentIndex(),
        )
        analyzer = ContinuousBeamAnalyzer()
        result = analyzer.analyze(inp)
        return inp, result

    def format_report(self, inp, result):
        return format_continuous_beam(inp, result)

    def _build_result_rows(self, r):
        rows = []
        if r.support_moments:
            for i, (m, re) in enumerate(
                zip(r.support_moments, r.support_reactions)
            ):
                rows.append([f"Sup {i+1}", fmt2(m), fmt2(re)])
        if r.span_moments:
            for i, (m, sl, sr) in enumerate(
                zip(r.span_moments, r.span_shear_left, r.span_shear_right)
            ):
                rows.append([f"Span {i+1}", fmt2(m), fmt2(sl), fmt2(sr)])
        return rows
