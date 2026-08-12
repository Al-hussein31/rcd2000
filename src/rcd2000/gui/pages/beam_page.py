"""Beam design form page."""

import logging

from PySide6.QtWidgets import QHBoxLayout, QGridLayout, QLabel
from PySide6.QtCore import Qt

from rcd2000.beam import BeamDesigner, BeamInput, BeamResult
from rcd2000.report import format_beam
from rcd2000.gui.theme import TEXT_SECONDARY, fmt, fmt2
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, label, Card, fcu_combo, fy_combo, badge,
    SpanDiagram, PointLoadsEditor,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class BeamPage(DesignFormPage):
    input_cls = BeamInput
    result_cls = BeamResult
    module_name = "Beam"

    def __init__(self):
        self._member_widgets = []
        self._member_pls: list = []   # one list of (P, a) per member
        self._pl_current = 0          # scope currently shown in the editor
        super().__init__()

    def build_inputs(self, layout):
        c1 = Card("Material Properties")
        self.beam_fcu = fcu_combo()
        self.beam_fy = fy_combo()
        self.beam_fyv = combo(["250", "410", "460"])
        self.beam_fcu.setToolTip("Characteristic concrete cube strength (N/mm²) at 28 days")
        self.beam_fy.setToolTip("Characteristic steel reinforcement yield strength (N/mm²)")
        self.beam_fyv.setToolTip("Characteristic stirrup (shear link) steel yield strength (N/mm²)")
        c1.add_row("fcu (N/mm²):", self.beam_fcu)
        c1.add_row("fy (N/mm²):", self.beam_fy)
        c1.add_row("fyv (N/mm²):", self.beam_fyv)
        layout.addWidget(c1)
        self._auto_clear_invalid(self.beam_fcu)
        self._auto_clear_invalid(self.beam_fy)
        self._auto_clear_invalid(self.beam_fyv)

        c2 = Card("Section Geometry")
        # AUDIT: bf (flange width) range 100-2000 mm allows bf < b (web width),
        # which is physically invalid for BS 8110 - the engine doesn't guard
        # against this. Consider enforcing bf >= b at design time.
        self.b_b = spinbox(100, 2000, 25, 225, 0)
        self.b_bf = spinbox(100, 2000, 25, 225, 0)
        # AUDIT: h range 100-2000 mm allows h < b+100 (minimum effective depth),
        # which would cause steel_beam to fail or produce nonsensical results.
        self.b_h = spinbox(100, 2000, 25, 450, 0)
        self.b_hf = spinbox(0, 500, 10, 0, 0)
        c2.add_row("b (mm):", self.b_b)
        c2.add_row("bf - flange width (mm):", self.b_bf)
        c2.add_row("h - overall depth (mm):", self.b_h)
        c2.add_row("hf - flange depth (mm):", self.b_hf)
        layout.addWidget(c2)
        self._auto_clear_invalid(self.b_b)
        self._auto_clear_invalid(self.b_bf)
        self._auto_clear_invalid(self.b_h)
        self._auto_clear_invalid(self.b_hf)

        c3 = Card("Supports & Members")
        self.n_supports = spin_int(2, 999999999, 2)
        self.n_members = spin_int(1, 999999999, 1)
        self.ty1 = combo(["Pinned", "Fixed"])
        self.ty2 = combo(["Pinned", "Fixed"])
        self.n_members.valueChanged.connect(self._sync_members)
        c3.add_row("Number of Supports:", self.n_supports)
        c3.add_row("Number of Members:", self.n_members)
        c3.add_row("Left End:", self.ty1)
        c3.add_row("Right End:", self.ty2)
        layout.addWidget(c3)
        self._auto_clear_invalid(self.n_supports)
        self._auto_clear_invalid(self.n_members)
        self._auto_clear_invalid(self.ty1)
        self._auto_clear_invalid(self.ty2)

        c3b = Card("End Cantilevers")
        self.cant_load_1 = spinbox(0, 999999999, 5, 0, 1, " kN")
        self.cant_moment_1 = spinbox(0, 999999999, 5, 0, 1, " kN·m")
        self.cant_load_2 = spinbox(0, 999999999, 5, 0, 1, " kN")
        self.cant_moment_2 = spinbox(0, 999999999, 5, 0, 1, " kN·m")
        self.cant_load_1.setToolTip("Load on the left end cantilever (book CLD1)")
        self.cant_moment_1.setToolTip("Moment applied at the left end support (book CMT1)")
        self.cant_load_2.setToolTip("Load on the right end cantilever (book CLD2)")
        self.cant_moment_2.setToolTip("Moment applied at the right end support (book CMT2)")
        c3b.add_row("Left cantilever load:", self.cant_load_1)
        c3b.add_row("Left cantilever moment:", self.cant_moment_1)
        c3b.add_row("Right cantilever load:", self.cant_load_2)
        c3b.add_row("Right cantilever moment:", self.cant_moment_2)
        layout.addWidget(c3b)
        self._auto_clear_invalid(self.cant_load_1)
        self._auto_clear_invalid(self.cant_moment_1)
        self._auto_clear_invalid(self.cant_load_2)
        self._auto_clear_invalid(self.cant_moment_2)

        self.diagram = SpanDiagram()
        self.diagram.setVisible(False)
        layout.addWidget(self.diagram)

        c5 = Card("Member Data")
        self.member_grid = QGridLayout()
        self.member_grid.setSpacing(6)
        c5.add_layout(self.member_grid)
        layout.addWidget(c5)

        # AUDIT (resolved): the book reads NPL point loads per member
        # (P(I,J)/AP(I,J)) but the GUI only exposed a single P/a pair per
        # grid row. Point loads now live in a scoped editor card so each
        # member can carry the full NPL list.
        c6 = Card("Point Loads (Per Member)")
        self.pl_scope = combo([])
        self.pl_scope.currentIndexChanged.connect(self._on_pl_scope_changed)
        self.pl_editor = PointLoadsEditor()
        c6.add_row("Member:", self.pl_scope)
        c6.add_widget(self.pl_editor)
        layout.addWidget(c6)
        self._auto_clear_invalid(self.pl_scope)

        self._sync_members()

    def _on_pl_scope_changed(self, index):
        # Save the outgoing scope's rows, then load the new scope.
        if 0 <= self._pl_current < len(self._member_pls):
            self._member_pls[self._pl_current] = self.pl_editor.all_loads()
        self._pl_current = index
        if 0 <= index < len(self._member_pls):
            self.pl_editor.set_value(self._member_pls[index])

    def _store_pl_editor(self):
        # Flush the editor rows into the scoped member's store.
        if 0 <= self._pl_current < len(self._member_pls):
            self._member_pls[self._pl_current] = self.pl_editor.all_loads()

    def _sync_members(self):
        nm = self.n_members.value()
        while len(self._member_widgets) < nm:
            row = len(self._member_widgets) + 1
            lbl = QLabel(f"M{row}")
            lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px; "
                f"background: transparent;"
            )
            length = spinbox(0, 999999999, 0.5, 5, 2, " m")
            udl = spinbox(0, 999999999, 5, 0, 1, " kN/m")
            wt = spinbox(0, 999999999, 5, 0, 1)
            wb = spinbox(0, 999999999, 5, 0, 1)
            ab = spinbox(0, 999999999, 0.5, 0, 2)
            wt.setToolTip("Triangularly distributed load magnitude (kN/m), peak at left support")
            wb.setToolTip("Trapezoidally distributed load magnitude (kN/m), varies along member")
            ab.setToolTip("Distance (m) from left support to load application point")
            self._auto_clear_invalid(length)
            self._auto_clear_invalid(udl)
            self._auto_clear_invalid(wt)
            self._auto_clear_invalid(wb)
            self._auto_clear_invalid(ab)
            self.member_grid.addWidget(lbl, row, 0)
            self.member_grid.addWidget(length, row, 1)
            self.member_grid.addWidget(udl, row, 2)
            self.member_grid.addWidget(wt, row, 3)
            self.member_grid.addWidget(wb, row, 4)
            self.member_grid.addWidget(ab, row, 5)
            self._member_widgets.append((lbl, length, udl, wt, wb, ab))
            self._member_pls.append([])

        headers = ["", "Length", "UDL", "Tri (wt)", "Trap (wb)", "Dist (ab)"]
        for col, h in enumerate(headers):
            self.member_grid.addWidget(
                label(h, secondary=True, size=11), 0, col
            )

        # Rebuild the point-load scope combo, keeping the selection.
        prev = self._pl_current
        self.pl_scope.blockSignals(True)
        self.pl_scope.clear()
        self.pl_scope.addItems([f"M{i + 1}" for i in range(nm)])
        if prev >= nm:
            prev = nm - 1
        self.pl_scope.setCurrentIndex(prev)
        self.pl_scope.blockSignals(False)
        self._pl_current = prev
        if 0 <= prev < len(self._member_pls):
            self.pl_editor.set_value(self._member_pls[prev])

        self._update_diagram()

    def _update_diagram(self):
        data = [
            {"length": w[1].value(), "udl": w[2].value()}
            for w in self._member_widgets
        ]
        self.diagram.set_spans(data)
        self.diagram.setVisible(len(self._member_widgets) > 0)

    def calculate(self):
        self._store_pl_editor()
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
            member_npl=[
                len(pls) for pls in self._member_pls
            ],
            member_pl=[list(pls) for pls in self._member_pls],
            ty1=self.ty1.currentIndex(),
            ty2=self.ty2.currentIndex(),
            cant_load_1=self.cant_load_1.value(),
            cant_moment_1=self.cant_moment_1.value(),
            cant_load_2=self.cant_load_2.value(),
            cant_moment_2=self.cant_moment_2.value(),
        )
        designer = BeamDesigner(fcu=fcu, fy=fy, fyv=fyv)
        result = designer.design([inp])[0]
        return inp, result

    def validate(self) -> list[str]:
        errors = []
        self._store_pl_editor()
        if self.b_bf.value() < self.b_b.value():
            errors.append("Flange width (bf) must be ≥ web width (b)")
            self._mark_invalid(self.b_bf)
            self._mark_invalid(self.b_b)
        if self.b_h.value() < self.b_b.value() + 100:
            errors.append("Overall depth (h) should be at least b + 100 mm for effective depth")
            self._mark_invalid(self.b_h)
        for i, w in enumerate(self._member_widgets):
            if w[1].value() <= 0:
                errors.append(f"Member {i+1} length must be > 0")
                self._mark_invalid(w[1])
            if i < len(self._member_pls):
                for j, (p, a) in enumerate(self._member_pls[i]):
                    if p > 0 and not (0 < a <= w[1].value()):
                        errors.append(
                            f"Member {i+1} point load {j+1} distance must be "
                            "within the member span"
                        )
                        if self._pl_current == i:
                            self._mark_invalid(self.pl_editor._rows[j][1])
        return errors

    def summarize(self, inp) -> str:
        try:
            b = inp.b if hasattr(inp, "b") else inp.get("b", 0)
            h = inp.h if hasattr(inp, "h") else inp.get("h", 0)
            nm = inp.n_members if hasattr(inp, "n_members") else inp.get("n_members", 0)
            return f"{nm} spans, {b}×{h}mm"
        except Exception:
            return f"{self.n_members.value()} spans"

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
        # Support results (reaction, moment, top/bottom steel) - the report
        # prints these but the on-screen grid must show them too.
        if r.supports:
            rows.append(["SUPPORT RESULTS", "", "", "", "", "", "", ""])
            for s in r.supports:
                rows.append([s.support_id, fmt2(s.reaction), fmt2(s.moment),
                             fmt(s.steel_top), fmt(s.steel_bot), "", "",
                             ""])
        # heck == 0 means the steel/deflection loop bailed: the section
        # could not be designed at the given depth (over-reinforced).
        if r.heck == 0:
            rows.append(["SECTION", "FAIL - increase beam depth", "", "",
                         "", "", "", badge(False)])
        return rows

    def get_state(self) -> dict:
        self._store_pl_editor()
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
            "cant_load_1": self.cant_load_1.value(),
            "cant_moment_1": self.cant_moment_1.value(),
            "cant_load_2": self.cant_load_2.value(),
            "cant_moment_2": self.cant_moment_2.value(),
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
            "member_pls": [
                list(pls) for pls in self._member_pls
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
        if "cant_load_1" in state:
            self.cant_load_1.setValue(state["cant_load_1"])
        if "cant_moment_1" in state:
            self.cant_moment_1.setValue(state["cant_moment_1"])
        if "cant_load_2" in state:
            self.cant_load_2.setValue(state["cant_load_2"])
        if "cant_moment_2" in state:
            self.cant_moment_2.setValue(state["cant_moment_2"])
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
                    # Legacy single-load keys migrate into the editor store.
                    if "pl" in m and m["pl"] > 0:
                        self._member_pls[i] = [(m["pl"], m.get("ap", 0.0))]
        if "member_pls" in state and self._member_widgets:
            self._member_pls = [
                [tuple(pl) for pl in (m or [])]
                for m in state["member_pls"]
            ]
            self.pl_editor.set_value(self._member_pls[self._pl_current])
