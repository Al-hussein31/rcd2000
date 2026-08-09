"""Column design form page."""

import logging

from rcd2000.column import ColumnDesigner, ColumnInput, ColumnResult
from rcd2000.report import format_column
from rcd2000.gui.theme import fmt
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, label, Card, badge,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class ColumnPage(DesignFormPage):
    input_cls = ColumnInput
    result_cls = ColumnResult
    module_name = "Column"

    def build_inputs(self, layout):
        c1 = Card("Column Type")
        self.col_type = combo(["1 - Axially Loaded", "2 - Uniaxial Bending", "3 - Biaxial Bending"])
        self.shape = combo(["Rectangular", "Circular"])
        c1.add_row("Type:", self.col_type)
        c1.add_row("Shape:", self.shape)
        layout.addWidget(c1)
        self._auto_clear_invalid(self.col_type)
        self._auto_clear_invalid(self.shape)

        c2 = Card("Loads & Geometry")
        # AUDIT (resolved): for circular columns, depth must equal dia for the
        # engine to work correctly. Now enforced: switching to Circular
        # disables b/x, b/y and the depth box, and depth is auto-synced to dia
        # (the book's H input is the diameter for circular sections).
        self.load = spinbox(0, 999999999, 100, 1000)
        self.bx = spinbox(100, 999999999, 25, 300, 0)
        self.by = spinbox(100, 999999999, 25, 300, 0)
        self.dia = spinbox(100, 999999999, 25, 300, 0)
        self.depth = spinbox(100, 999999999, 25, 300, 0)
        c2.add_row("Axial Load (kN):", self.load)
        c2.add_row("b/h width - x (mm):", self.bx)
        c2.add_row("b/h width - y (mm):", self.by)
        c2.add_row("Diameter (mm):", self.dia)
        c2.add_row("Overall depth (mm):", self.depth)
        layout.addWidget(c2)
        self._auto_clear_invalid(self.load)
        self._auto_clear_invalid(self.bx)
        self._auto_clear_invalid(self.by)
        self._auto_clear_invalid(self.dia)
        self._auto_clear_invalid(self.depth)

        c5 = Card("Column Height & Effective Lengths")
        # AUDIT (resolved): book column.f77 reads L, LE, LEX, LEY as inputs.
        # Collected here and carried into the report for slenderness context.
        self.length = spinbox(0, 999999999, 0.1, 3.0, 2)
        self.le = spinbox(0, 999999999, 0.1, 3.0, 2)
        self.lex = spinbox(0, 999999999, 0.1, 3.0, 2)
        self.ley = spinbox(0, 999999999, 0.1, 3.0, 2)
        self.length.setToolTip("Column height L (m) - book input L")
        self.le.setToolTip("Effective length LE (m) - book input LE")
        self.lex.setToolTip("Effective length about x-axis LEX (m) - book input LEX")
        self.ley.setToolTip("Effective length about y-axis LEY (m) - book input LEY")
        c5.add_row("Column height L (m):", self.length)
        c5.add_row("Effective length LE (m):", self.le)
        c5.add_row("Effective length LEX (m):", self.lex)
        c5.add_row("Effective length LEY (m):", self.ley)
        layout.addWidget(c5)
        self._auto_clear_invalid(self.length)
        self._auto_clear_invalid(self.le)
        self._auto_clear_invalid(self.lex)
        self._auto_clear_invalid(self.ley)

        c3 = Card("Materials")
        from rcd2000.gui.widgets import fcu_combo, fy_combo
        self.col_fcu = fcu_combo()
        self.col_fy = fy_combo()
        self.col_fcu.setToolTip("Characteristic concrete cube strength (N/mm²) at 28 days")
        self.col_fy.setToolTip("Characteristic steel reinforcement yield strength (N/mm²)")
        self.col_max_steel = spinbox(0, 25, 0.25, 4.0, 2, " %")
        self.col_dh = spinbox(0, 1, 0.05, 0.85, 2)
        self.col_max_steel.setToolTip(
            "Maximum steel percentage for the column (book input PS). "
            "The job header value is applied when a header is set."
        )
        self.col_dh.setToolTip(
            "Ratio of effective depth d to overall depth h (book input DH). "
            "The job header value is applied when a header is set."
        )
        c3.add_row("fcu (N/mm²):", self.col_fcu)
        c3.add_row("fy (N/mm²):", self.col_fy)
        c3.add_row("Max steel %:", self.col_max_steel)
        c3.add_row("D/H ratio:", self.col_dh)
        layout.addWidget(c3)
        self._auto_clear_invalid(self.col_fcu)
        self._auto_clear_invalid(self.col_fy)
        self._auto_clear_invalid(self.col_max_steel)
        self._auto_clear_invalid(self.col_dh)

        c4 = Card("Moments")
        self.moment_x = spinbox(0, 999999999, 10, 0)
        self.moment_y = spinbox(0, 999999999, 10, 0)
        self.moment = spinbox(0, 999999999, 10, 0)
        c4.add_row("Mx (kN·m):", self.moment_x)
        c4.add_row("My (kN·m):", self.moment_y)
        c4.add_row("M (uniaxial, kN·m):", self.moment)
        layout.addWidget(c4)
        self._auto_clear_invalid(self.moment_x)
        self._auto_clear_invalid(self.moment_y)
        self._auto_clear_invalid(self.moment)

        # Enforce depth == dia for circular columns (book: H is the diameter
        # for circular sections). Switching shape toggles which geometry
        # fields are editable; dia changes mirror into depth while circular.
        self.shape.currentIndexChanged.connect(self._sync_shape_geometry)
        self.dia.valueChanged.connect(self._on_dia_changed)
        self._sync_shape_geometry()

    def _sync_shape_geometry(self):
        circular = self.shape.currentIndex() == 1
        # Rectangular: b/x + b/y + depth editable, dia is ignored by the engine.
        # Circular: dia drives everything; b/x + b/y + depth are locked.
        for w in (self.bx, self.by, self.depth):
            w.setEnabled(not circular)
        self.dia.setEnabled(circular)
        if circular:
            self.depth.setValue(self.dia.value())

    def _on_dia_changed(self, value):
        if self.shape.currentIndex() == 1:
            self.depth.setValue(value)

    def calculate(self):
        col_type = self.col_type.currentIndex() + 1
        fcu = int(self.col_fcu.currentText())
        fy = int(self.col_fy.currentText())

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

        inp = ColumnInput(
            column_id="C1",
            col_type=col_type,
            shape=1 if self.shape.currentIndex() == 0 else 2,
            load=self.load.value(),
            bx=self.bx.value(), by=self.by.value(),
            dia=self.dia.value(), depth=self.depth.value(),
            length=self.length.value(),
            le=self.le.value(), lex=self.lex.value(), ley=self.ley.value(),
            moment_x=self.moment_x.value(),
            moment_y=self.moment_y.value(),
            moment=moment,
        )
        designer = ColumnDesigner(
            fcu=fcu, fy=fy,
            max_steel_pct=self.col_max_steel.value(),
            dh_ratio=self.col_dh.value(),
        )
        result = designer.design([inp])[0]
        return inp, result

    def validate(self) -> list[str]:
        errors = []
        shape = self.shape.currentIndex()
        col_type = self.col_type.currentIndex() + 1
        if shape == 0:
            if self.bx.value() < 100 or self.by.value() < 100:
                errors.append("Rectangular column requires both b/x and b/y dimensions")
                if self.bx.value() < 100:
                    self._mark_invalid(self.bx)
                if self.by.value() < 100:
                    self._mark_invalid(self.by)
        else:
            if self.dia.value() < 100:
                errors.append("Circular column diameter must be at least 100 mm")
                self._mark_invalid(self.dia)
            if abs(self.depth.value() - self.dia.value()) > 1:
                errors.append("Overall depth should equal diameter for circular columns")
                self._mark_invalid(self.depth)
        if col_type == 1 and self.load.value() <= 0:
            errors.append("Axial load must be greater than zero")
            self._mark_invalid(self.load)
        if col_type == 2 and self.moment.value() <= 0:
            errors.append("Uniaxial moment must be greater than zero for uniaxial design")
            self._mark_invalid(self.moment)
        if col_type == 3 and self.moment_x.value() <= 0 and self.moment_y.value() <= 0:
            errors.append("At least one moment (Mx or My) must be > 0 for biaxial design")
            self._mark_invalid(self.moment_x)
            self._mark_invalid(self.moment_y)
        if not (0 < self.col_max_steel.value() <= 25):
            errors.append("Max steel % must be between 0 and 25")
            self._mark_invalid(self.col_max_steel)
        if not (0 < self.col_dh.value() <= 1):
            errors.append("D/H ratio must be between 0 and 1")
            self._mark_invalid(self.col_dh)
        return errors

    def summarize(self, inp) -> str:
        try:
            load = inp.load if hasattr(inp, "load") else inp.get("load", 0)
            shape = inp.shape if hasattr(inp, "shape") else inp.get("shape", 1)
            if shape == 1:
                bx = inp.bx if hasattr(inp, "bx") else inp.get("bx", 0)
                by = inp.by if hasattr(inp, "by") else inp.get("by", 0)
                return f"Rect {bx}×{by}mm, {load:.0f}kN"
            else:
                dia = inp.dia if hasattr(inp, "dia") else inp.get("dia", 0)
                return f"Circ Ø{dia}mm, {load:.0f}kN"
        except Exception:
            return f"Load {self.load.value():.0f}kN"

    def format_report(self, inp, result):
        from rcd2000.gui.theme import fmt as _fmt  # noqa: F811
        return format_column(inp, result)

    def get_state(self) -> dict:
        return {
            "col_type": self.col_type.currentIndex(),
            "shape": self.shape.currentIndex(),
            "load": self.load.value(),
            "bx": self.bx.value(),
            "by": self.by.value(),
            "dia": self.dia.value(),
            "depth": self.depth.value(),
            "length": self.length.value(),
            "le": self.le.value(),
            "lex": self.lex.value(),
            "ley": self.ley.value(),
            "col_fcu": int(self.col_fcu.currentText()),
            "col_fy": int(self.col_fy.currentText()),
            "col_max_steel": self.col_max_steel.value(),
            "col_dh": self.col_dh.value(),
            "moment_x": self.moment_x.value(),
            "moment_y": self.moment_y.value(),
            "moment": self.moment.value(),
        }

    def set_state(self, state: dict) -> None:
        if "col_type" in state:
            self.col_type.setCurrentIndex(state["col_type"])
        if "shape" in state:
            self.shape.setCurrentIndex(state["shape"])
        if "load" in state:
            self.load.setValue(state["load"])
        if "bx" in state:
            self.bx.setValue(state["bx"])
        if "by" in state:
            self.by.setValue(state["by"])
        if "dia" in state:
            self.dia.setValue(state["dia"])
        if "depth" in state:
            self.depth.setValue(state["depth"])
        if "length" in state:
            self.length.setValue(state["length"])
        if "le" in state:
            self.le.setValue(state["le"])
        if "lex" in state:
            self.lex.setValue(state["lex"])
        if "ley" in state:
            self.ley.setValue(state["ley"])
        if "col_fcu" in state:
            self._set_combo_int(self.col_fcu, state["col_fcu"])
        if "col_fy" in state:
            self._set_combo_int(self.col_fy, state["col_fy"])
        if "col_max_steel" in state:
            self.col_max_steel.setValue(state["col_max_steel"])
        if "col_dh" in state:
            self.col_dh.setValue(state["col_dh"])
        if "moment_x" in state:
            self.moment_x.setValue(state["moment_x"])
        if "moment_y" in state:
            self.moment_y.setValue(state["moment_y"])
        if "moment" in state:
            self.moment.setValue(state["moment"])

    def _build_result_rows(self, r):
        ci = self._last_input
        rows = [
            ["Steel Required", f"{r.steel_required:,.0f} mm²", ""],
            ["Steel Percentage", f"{r.steel_percent:.2f}%", ""],
            ["Axial Capacity (Nu)", f"{r.axial_capacity:,.0f} kN",
             badge(r.axial_capacity >= ci.load)],
            ["Moment Capacity (Mux)", f"{r.moment_capacity_x:,.0f} kN·m", ""],
            ["Moment Capacity (Muy)", f"{r.moment_capacity_y:,.0f} kN·m", ""],
        ]
        if ci.col_type == 3:
            rows.append(["Biaxial Check", "OK" if r.biaxial_check_ok else "FAIL",
                         badge(r.biaxial_check_ok)])
        rows.append(["Section Adequate",
                     "OK" if r.heck == 0 else "FAIL - reduce load or enlarge section",
                     badge(r.heck == 0)])
        return rows
