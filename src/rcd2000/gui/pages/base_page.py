"""Foundation design form page."""

from rcd2000.base import BaseDesigner, BaseInput
from rcd2000.report import format_base
from rcd2000.gui.theme import fmt, fmt2
from rcd2000.gui.widgets import (
    spinbox, combo, label, Card, badge, fcu_combo, fy_combo, load_combo_group,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class BasePage(DesignFormPage):
    module_name = "Base"

    def build_inputs(self, layout):
        c1 = Card("Base Type & Materials")
        self.base_type = combo(["Square Isolated", "Rectangular Isolated", "Combined"])
        self.col_shape = combo(["Rectangular", "Circular"])
        self.base_fcu = fcu_combo()
        self.base_fy = fy_combo()
        self.base_pb = spinbox(50, 500, 10, 150, 0, " kN/m²")
        c1.add_row("Base Type:", self.base_type)
        c1.add_row("Column Shape:", self.col_shape)
        c1.add_row("fcu (N/mm²):", self.base_fcu)
        c1.add_row("fy (N/mm²):", self.base_fy)
        c1.add_row("Allowable Bearing (kN/m²):", self.base_pb)
        layout.addWidget(c1)

        c2 = Card("Loads & Dimensions")
        # AUDIT: load 0–50000 kN is large but not invalid. However, load=0
        # would produce a zero-area footing (sqrt(0)) — the engine handles
        # this but the result is meaningless.
        self.base_load = spinbox(0, 50000, 100, 1000)
        # AUDIT: column dims 100–2000 mm — for a 100mm column, the base
        # projection could be negative (base smaller than column). The
        # engine doesn't guard against this.
        self.base_a1 = spinbox(100, 2000, 25, 300, 0)
        self.base_a2 = spinbox(100, 2000, 25, 300, 0)
        # AUDIT: dia 100–2000 mm is fine for circular columns.
        self.base_dia = spinbox(100, 2000, 25, 300, 0)
        # AUDIT: base thickness h 100–2000 mm — minimum 100mm is too low
        # for any real footing (crushing/bond checks will fail, but engine
        # iterates h up by 50mm until OK, so it self-corrects).
        self.base_h = spinbox(100, 2000, 25, 300, 0)
        # AUDIT: L1/L2 0–20 m — for isolated footings, L1/L2=0 means
        # auto-calculate from area. For combined footings, L2=0 defaults
        # to 2.0m in the engine. No critical issue.
        self.base_l1 = spinbox(0, 20, 0.5, 0, 2, " m")
        self.base_l2 = spinbox(0, 20, 0.5, 0, 2, " m")
        # AUDIT: dowel_dia 8–40 mm is fine.
        self.base_dowel = spinbox(8, 40, 2, 12, 0)
        c2.add_row("Axial Load (kN):", self.base_load)
        c2.add_row("Col Dim a1 (mm):", self.base_a1)
        c2.add_row("Col Dim a2 (mm):", self.base_a2)
        c2.add_row("Col Diameter (mm):", self.base_dia)
        c2.add_row("Base Thickness h (mm):", self.base_h)
        c2.add_row("Base Length L1 (m):", self.base_l1)
        c2.add_row("Base Width L2 (m):", self.base_l2)
        c2.add_row("Dowel Diameter (mm):", self.base_dowel)

        load_w, self.gk, self.qk, self.load_result = load_combo_group()
        c2.add_widget(label("Loads"))
        c2.add_widget(load_w)
        layout.addWidget(c2)

    def calculate(self):
        btype = self.base_type.currentIndex() + 1
        fcu = int(self.base_fcu.currentText())
        fy = int(self.base_fy.currentText())

        inp = BaseInput(
            base_id="F1",
            base_type=btype,
            col_type=1 if self.col_shape.currentIndex() == 0 else 2,
            load=self.base_load.value(),
            pb=self.base_pb.value(), fcu=fcu, fy=fy,
            a1=self.base_a1.value(), a2=self.base_a2.value(),
            dia=self.base_dia.value(), dowel_dia=self.base_dowel.value(),
            h=self.base_h.value(),
            l1=self.base_l1.value(), l2=self.base_l2.value(),
        )
        designer = BaseDesigner(
            pb=self.base_pb.value(), fcu=fcu, fy=fy,
        )
        result = designer.design([inp])[0]
        return inp, result

    def format_report(self, inp, result):
        return format_base(inp, result)

    def _build_result_rows(self, r):
        rows = [
            ["Base Length L1 (mm)", fmt(r.l1), ""],
            ["Base Width L2 (mm)", fmt(r.l2), ""],
            ["Base Depth h (mm)", fmt(r.h), ""],
            ["Net Upward Pressure (kN/m²)", fmt2(r.fnet), ""],
            ["Moment L1 (kN·m)", fmt2(r.m1), ""],
            ["Steel L1 (mm²)", fmt(r.as1), ""],
            [f"Bar L1", f"Y{r.rd1:.0f} @ {r.sp1:.0f} c/c", ""],
            ["Moment L2 (kN·m)", fmt2(r.m2), ""],
            ["Steel L2 (mm²)", fmt(r.as2), ""],
            [f"Bar L2", f"Y{r.rd2:.0f} @ {r.sp2:.0f} c/c", ""],
            ["Shear Stress (N/mm²)", fmt2(r.shear_stress),
             badge(r.shear_stress <= r.perm_shear)],
            ["Permissible Shear (N/mm²)", fmt2(r.perm_shear), ""],
            ["Punching Shear (N/mm²)", fmt2(r.punching_shear), ""],
            ["Local Bond (N/mm²)", fmt2(r.local_bond),
             badge(r.local_bond <= r.perm_bond)],
            ["Permissible Bond (N/mm²)", fmt2(r.perm_bond), ""],
        ]
        return rows
