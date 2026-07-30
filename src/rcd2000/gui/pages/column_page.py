"""Column design form page."""

import logging

from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.report import format_column
from rcd2000.gui.theme import fmt
from rcd2000.gui.widgets import (
    spinbox, spin_int, combo, label, Card, badge,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class ColumnPage(DesignFormPage):
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
        self._auto_clear_invalid(self.load)
        self._auto_clear_invalid(self.bx)
        self._auto_clear_invalid(self.by)
        self._auto_clear_invalid(self.dia)
        self._auto_clear_invalid(self.depth)

        c3 = Card("Materials")
        from rcd2000.gui.widgets import fcu_combo, fy_combo
        self.col_fcu = fcu_combo()
        self.col_fy = fy_combo()
        self.col_fcu.setToolTip("Characteristic concrete cube strength (N/mm²) at 28 days")
        self.col_fy.setToolTip("Characteristic steel reinforcement yield strength (N/mm²)")
        c3.add_row("fcu (N/mm²):", self.col_fcu)
        c3.add_row("fy (N/mm²):", self.col_fy)
        layout.addWidget(c3)
        self._auto_clear_invalid(self.col_fcu)
        self._auto_clear_invalid(self.col_fy)

        c4 = Card("Moments")
        self.moment_x = spinbox(0, 5000, 10, 0)
        self.moment_y = spinbox(0, 5000, 10, 0)
        self.moment = spinbox(0, 5000, 10, 0)
        c4.add_row("Mx (kN·m):", self.moment_x)
        c4.add_row("My (kN·m):", self.moment_y)
        c4.add_row("M (uniaxial, kN·m):", self.moment)
        layout.addWidget(c4)
        self._auto_clear_invalid(self.moment_x)
        self._auto_clear_invalid(self.moment_y)
        self._auto_clear_invalid(self.moment)

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
            moment_x=self.moment_x.value(),
            moment_y=self.moment_y.value(),
            moment=moment,
        )
        designer = ColumnDesigner(fcu=fcu, fy=fy)
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
            "col_fcu": int(self.col_fcu.currentText()),
            "col_fy": int(self.col_fy.currentText()),
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
        if "col_fcu" in state:
            self._set_combo_int(self.col_fcu, state["col_fcu"])
        if "col_fy" in state:
            self._set_combo_int(self.col_fy, state["col_fy"])
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
        return rows
