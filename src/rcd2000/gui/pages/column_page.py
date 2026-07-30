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

        c3 = Card("Materials")
        from rcd2000.gui.widgets import fcu_combo, fy_combo
        self.col_fcu = fcu_combo()
        self.col_fy = fy_combo()
        c3.add_row("fcu (N/mm²):", self.col_fcu)
        c3.add_row("fy (N/mm²):", self.col_fy)
        layout.addWidget(c3)

        c4 = Card("Moments")
        self.moment_x = spinbox(0, 5000, 10, 0)
        self.moment_y = spinbox(0, 5000, 10, 0)
        self.moment = spinbox(0, 5000, 10, 0)
        c4.add_row("Mx (kN·m):", self.moment_x)
        c4.add_row("My (kN·m):", self.moment_y)
        c4.add_row("M (uniaxial, kN·m):", self.moment)
        layout.addWidget(c4)

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
