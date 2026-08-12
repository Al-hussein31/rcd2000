"""Continuous beam analysis form page."""

from PySide6.QtWidgets import QGridLayout, QLabel

from rcd2000.continuous_beam import (
    ContinuousBeamAnalyzer, ContinuousBeamInput, ContinuousBeamMember,
    ContinuousBeamResult,
)
from rcd2000.report import format_continuous_beam
from rcd2000.gui.theme import TEXT_SECONDARY, fmt2
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, label, Card, SpanDiagram,
    PointLoadsEditor,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class ContinuousBeamPage(DesignFormPage):
    input_cls = ContinuousBeamInput
    result_cls = ContinuousBeamResult
    module_name = "Continuous Beam"

    def __init__(self):
        self._cb_member_widgets = []
        self._cb_pls: list = []   # extra point loads per member
        self._pl_current = 0      # scope currently shown in the editor
        super().__init__()

    def _page_title(self):
        return "Continuous Beam Analysis - BS 8110"

    def _calc_button_text(self):
        return "Analyze Beam"

    def build_inputs(self, layout):
        c1 = Card("Supports & End Conditions")
        self.cb_ns = spin_int(0, 999999999, 3)
        self.cb_nm = spin_int(0, 999999999, 2)
        self.cb_end1 = combo(["Pinned", "Fixed"])
        self.cb_end2 = combo(["Pinned", "Fixed"])
        self.cb_nm.valueChanged.connect(self._sync_members)
        c1.add_row("Number of Supports:", self.cb_ns)
        c1.add_row("Number of Members:", self.cb_nm)
        c1.add_row("Left End:", self.cb_end1)
        c1.add_row("Right End:", self.cb_end2)
        layout.addWidget(c1)
        self._auto_clear_invalid(self.cb_ns)
        self._auto_clear_invalid(self.cb_nm)
        self._auto_clear_invalid(self.cb_end1)
        self._auto_clear_invalid(self.cb_end2)

        # AUDIT: end cantilever load/moment inputs were missing from the
        # GUI (book CANTW/CANTMT read per end support). The engine adds
        # CANTW to the end reactions (book line: REACTN(I) = REACTN(I) +
        # CANTW(I)); CANTMT is read but only counted (KC) in the book and
        # never applied to the moments - kept faithful to that behaviour.
        c1b = Card("End Cantilevers")
        self.cb_cant_load_1 = spinbox(0, 999999999, 5, 0, 1, " kN")
        self.cb_cant_moment_1 = spinbox(0, 999999999, 5, 0, 1, " kN·m")
        self.cb_cant_load_2 = spinbox(0, 999999999, 5, 0, 1, " kN")
        self.cb_cant_moment_2 = spinbox(0, 999999999, 5, 0, 1, " kN·m")
        self.cb_cant_load_1.setToolTip("Load on the left end cantilever (book CANTW(1)) - added to the end reaction")
        self.cb_cant_moment_1.setToolTip(
            "Moment at the left end support (book CANTMT(1)). "
            "The book only counts it (KC) and never applies it to the "
            "moments - recorded here for completeness."
        )
        self.cb_cant_load_2.setToolTip("Load on the right end cantilever (book CANTW(NS)) - added to the end reaction")
        self.cb_cant_moment_2.setToolTip(
            "Moment at the right end support (book CANTMT(NS)). "
            "The book only counts it (KC) and never applies it to the "
            "moments - recorded here for completeness."
        )
        c1b.add_row("Left cantilever load:", self.cb_cant_load_1)
        c1b.add_row("Left cantilever moment:", self.cb_cant_moment_1)
        c1b.add_row("Right cantilever load:", self.cb_cant_load_2)
        c1b.add_row("Right cantilever moment:", self.cb_cant_moment_2)
        layout.addWidget(c1b)
        self._auto_clear_invalid(self.cb_cant_load_1)
        self._auto_clear_invalid(self.cb_cant_moment_1)
        self._auto_clear_invalid(self.cb_cant_load_2)
        self._auto_clear_invalid(self.cb_cant_moment_2)

        self.diagram = SpanDiagram()
        self.diagram.setVisible(False)
        layout.addWidget(self.diagram)

        c2 = Card("Member Data")
        self.member_grid = QGridLayout()
        self.member_grid.setSpacing(6)
        c2.add_layout(self.member_grid)
        layout.addWidget(c2)

        # AUDIT (resolved): the book reads NPL point loads per member and
        # N1/N2 nodes per member span (P(I,J)/AP(I,J), N1(I), N2(I)); the
        # GUI only exposed a single P/a pair. Point loads now live in a
        # scoped editor card so each member carries the full NPL list.
        c2b = Card("Point Loads (Per Member)")
        self.pl_scope = combo([])
        self.pl_scope.currentIndexChanged.connect(self._on_pl_scope_changed)
        self.pl_editor = PointLoadsEditor()
        c2b.add_row("Member:", self.pl_scope)
        c2b.add_widget(self.pl_editor)
        layout.addWidget(c2b)
        self._auto_clear_invalid(self.pl_scope)

        self._sync_members()

    def _on_pl_scope_changed(self, index):
        # Save the outgoing scope's rows, then load the new scope.
        if 0 <= self._pl_current < len(self._cb_pls):
            self._cb_pls[self._pl_current] = self.pl_editor.all_loads()
        self._pl_current = index
        if 0 <= index < len(self._cb_pls):
            self.pl_editor.set_value(self._cb_pls[index])

    def _store_pl_editor(self):
        # Flush the editor rows into the scoped member's store.
        if 0 <= self._pl_current < len(self._cb_pls):
            self._cb_pls[self._pl_current] = self.pl_editor.all_loads()

    def _merge_pls(self, i, w):
        # Primary grid load plus the editor's NPL extra loads.
        loads = [(w[8].value(), w[9].value())] if w[8].value() > 0 else []
        if i < len(self._cb_pls):
            loads += [tuple(pl) for pl in self._cb_pls[i] if pl[0] > 0]
        return loads

    def _sync_members(self):
        nm = self.cb_nm.value()
        while len(self._cb_member_widgets) < nm:
            row = len(self._cb_member_widgets) + 1
            lbl = QLabel(f"M{row}")
            lbl.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px; "
                f"background: transparent;"
            )
            length = spinbox(0, 999999999, 0.5, 5, 2, " m")
            inertia = spinbox(0, 999999999, 0.001, 0.001, 4)
            inertia.setToolTip("Second moment of area (m⁴) for stiffness calculations")
            e_mod = spinbox(0, 999999999, 0.1, 1, 1)
            e_mod.setToolTip("Relative modulus of elasticity (E / E_concrete)")
            udl = spinbox(0, 999999999, 5, 0, 1, " kN/m")
            wt = spinbox(0, 999999999, 5, 0, 1)
            wb = spinbox(0, 999999999, 5, 0, 1)
            wt.setToolTip("Triangularly distributed load magnitude (kN/m), peak at left support")
            wb.setToolTip("Trapezoidally distributed load magnitude (kN/m), varies along member")
            # AUDIT: ab 0-10 m - trapezoidal load position. If ab > length,
            # the load is outside the member. The engine clamps alpha =
            # ab/l which could exceed 1.0, producing invalid results.
            ab = spinbox(0, 999999999, 0.5, 0, 2)
            ab.setToolTip("Distance (m) from left support to load application point")
            # AUDIT: per-member point loads were missing from the GUI
            # (book P(I,J)/AP(I,J) read per member; the engine already
            # adds PAF terms to the Clapeyron RHS).
            pl = spinbox(0, 999999999, 5, 0, 1, " kN")
            ap = spinbox(0, 999999999, 0.5, 0, 2, " m")
            pl.setToolTip("Point load on this member (book P) - enter 0 for none")
            ap.setToolTip("Distance (m) of the point load from the left support (book AP)")
            self._auto_clear_invalid(length)
            self._auto_clear_invalid(inertia)
            self._auto_clear_invalid(e_mod)
            self._auto_clear_invalid(udl)
            self._auto_clear_invalid(wt)
            self._auto_clear_invalid(wb)
            self._auto_clear_invalid(ab)
            self._auto_clear_invalid(pl)
            self._auto_clear_invalid(ap)
            _mi = len(self._cb_member_widgets)
            n1 = spin_int(1, 999999999, _mi + 1)
            n2 = spin_int(1, 999999999, min(_mi + 2, self.cb_ns.value()))
            n1.setToolTip("Left node of this member (book N1(I))")
            n2.setToolTip("Right node of this member (book N2(I))")
            self._auto_clear_invalid(n1)
            self._auto_clear_invalid(n2)
            self.member_grid.addWidget(lbl, row, 0)
            self.member_grid.addWidget(length, row, 1)
            self.member_grid.addWidget(inertia, row, 2)
            self.member_grid.addWidget(e_mod, row, 3)
            self.member_grid.addWidget(udl, row, 4)
            self.member_grid.addWidget(wt, row, 5)
            self.member_grid.addWidget(wb, row, 6)
            self.member_grid.addWidget(ab, row, 7)
            self.member_grid.addWidget(pl, row, 8)
            self.member_grid.addWidget(ap, row, 9)
            self.member_grid.addWidget(n1, row, 10)
            self.member_grid.addWidget(n2, row, 11)
            self._cb_member_widgets.append(
                (lbl, length, inertia, e_mod, udl, wt, wb, ab, pl, ap, n1, n2)
            )
            self._cb_pls.append([])

        headers = ["", "L (m)", "I (m⁴)", "E-rel", "UDL", "Tri", "Trap",
                   "Dist", "P (kN)", "a (m)", "N1", "N2"]
        for col, h in enumerate(headers):
            self.member_grid.addWidget(
                label(h, secondary=True, size=11), 0, col
            )

        # Rebuild the point-load scope combo, keeping the selection.
        prev = self._pl_current
        self.pl_scope.blockSignals(True)
        self.pl_scope.clear()
        self.pl_scope.addItems([f"M{i+1}" for i in range(self.cb_nm.value())])
        if prev >= self.cb_nm.value():
            prev = self.cb_nm.value() - 1
        self.pl_scope.setCurrentIndex(prev)
        self.pl_scope.blockSignals(False)
        self._pl_current = prev
        if 0 <= prev < len(self._cb_pls):
            self.pl_editor.set_value(self._cb_pls[prev])

        self._update_diagram()

    def _update_diagram(self):
        data = [
            {"length": w[1].value(), "udl": w[4].value()}
            for w in self._cb_member_widgets
        ]
        self.diagram.set_spans(data)
        self.diagram.setVisible(len(self._cb_member_widgets) > 0)

    def calculate(self):
        self._store_pl_editor()
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
                npl=len(self._merge_pls(i, w)),
                point_loads=self._merge_pls(i, w),
                n1=w[10].value(),
                n2=w[11].value(),
            ))
        inp = ContinuousBeamInput(
            n_supports=self.cb_ns.value(),
            n_members=nm,
            members=members,
            end1_type=self.cb_end1.currentIndex(),
            end2_type=self.cb_end2.currentIndex(),
            end1_cant_load=self.cb_cant_load_1.value(),
            end1_cant_moment=self.cb_cant_moment_1.value(),
            end2_cant_load=self.cb_cant_load_2.value(),
            end2_cant_moment=self.cb_cant_moment_2.value(),
        )
        analyzer = ContinuousBeamAnalyzer()
        result = analyzer.analyze(inp)
        return inp, result

    def validate(self) -> list[str]:
        errors = []
        self._store_pl_editor()
        if self.cb_nm.value() < 1:
            errors.append("At least one member is required")
            self._mark_invalid(self.cb_nm)
        for i, w in enumerate(self._cb_member_widgets):
            if w[1].value() <= 0:
                errors.append(f"Member {i+1} length must be > 0")
                self._mark_invalid(w[1])
            if w[7].value() > w[1].value():
                errors.append(f"Member {i+1}: distance (ab) exceeds member length")
                self._mark_invalid(w[7])
                self._mark_invalid(w[1])
            if w[8].value() > 0 and not (0 < w[9].value() <= w[1].value()):
                errors.append(
                    f"Member {i+1} point load distance must be within the member span"
                )
                self._mark_invalid(w[9])
            for jj, (pp, aa) in enumerate(self._cb_pls[i]):
                if pp > 0 and not (0 < aa <= w[1].value()):
                    errors.append(
                        f"Member {i+1} point load {jj+1} distance must be "
                        "within the member span"
                    )
                    if self._pl_current == i:
                        self._mark_invalid(self.pl_editor._rows[jj][1])
            if w[10].value() >= w[11].value():
                errors.append(f"Member {i+1}: N1 must be less than N2")
                self._mark_invalid(w[10])
                self._mark_invalid(w[11])
            if w[11].value() > self.cb_ns.value():
                errors.append(
                    f"Member {i+1}: N2 exceeds the number of supports"
                )
                self._mark_invalid(w[11])
        return errors

    def summarize(self, inp) -> str:
        try:
            nm = inp.n_members if hasattr(inp, "n_members") else inp.get("n_members", 0)
            ns = inp.n_supports if hasattr(inp, "n_supports") else inp.get("n_supports", 0)
            return f"{nm} spans, {ns} supports"
        except Exception:
            return f"{self.cb_nm.value()} spans"

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

    def get_state(self) -> dict:
        self._store_pl_editor()
        return {
            "cb_ns": self.cb_ns.value(),
            "cb_nm": self.cb_nm.value(),
            "cb_end1": self.cb_end1.currentIndex(),
            "cb_end2": self.cb_end2.currentIndex(),
            "cant_load_1": self.cb_cant_load_1.value(),
            "cant_moment_1": self.cb_cant_moment_1.value(),
            "cant_load_2": self.cb_cant_load_2.value(),
            "cant_moment_2": self.cb_cant_moment_2.value(),
            "members": [
                {
                    "length": w[1].value(),
                    "inertia": w[2].value(),
                    "e_mod": w[3].value(),
                    "udl": w[4].value(),
                    "wt": w[5].value(),
                    "wb": w[6].value(),
                    "ab": w[7].value(),
                    "pl": w[8].value(),
                    "ap": w[9].value(),
                    "n1": w[10].value(),
                    "n2": w[11].value(),
                }
                for w in self._cb_member_widgets
            ],
            "cb_member_pls": [
                [list(pls) for pls in mp] for mp in self._cb_pls
            ],
        }

    def set_state(self, state: dict) -> None:
        if "cb_ns" in state:
            self.cb_ns.setValue(state["cb_ns"])
        if "cb_nm" in state:
            self.cb_nm.setValue(state["cb_nm"])
        if "cb_end1" in state:
            self.cb_end1.setCurrentIndex(state["cb_end1"])
        if "cb_end2" in state:
            self.cb_end2.setCurrentIndex(state["cb_end2"])
        if "cant_load_1" in state:
            self.cb_cant_load_1.setValue(state["cant_load_1"])
        if "cant_moment_1" in state:
            self.cb_cant_moment_1.setValue(state["cant_moment_1"])
        if "cant_load_2" in state:
            self.cb_cant_load_2.setValue(state["cant_load_2"])
        if "cant_moment_2" in state:
            self.cb_cant_moment_2.setValue(state["cant_moment_2"])
        if "members" in state and self._cb_member_widgets:
            for i, w in enumerate(self._cb_member_widgets):
                if i < len(state["members"]):
                    m = state["members"][i]
                    if "length" in m:
                        w[1].setValue(m["length"])
                    if "inertia" in m:
                        w[2].setValue(m["inertia"])
                    if "e_mod" in m:
                        w[3].setValue(m["e_mod"])
                    if "udl" in m:
                        w[4].setValue(m["udl"])
                    if "wt" in m:
                        w[5].setValue(m["wt"])
                    if "wb" in m:
                        w[6].setValue(m["wb"])
                    if "ab" in m:
                        w[7].setValue(m["ab"])
                    if "pl" in m:
                        w[8].setValue(m["pl"])
                    if "ap" in m:
                        w[9].setValue(m["ap"])
                    if "n1" in m:
                        w[10].setValue(m["n1"])
                    if "n2" in m:
                        w[11].setValue(m["n2"])
        if "cb_member_pls" in state:
            self._cb_pls = [
                [tuple(pl) for pl in (x or [])]
                for x in state["cb_member_pls"]
            ]
            if self._pl_current < len(self._cb_pls):
                self.pl_editor.set_value(self._cb_pls[self._pl_current])
