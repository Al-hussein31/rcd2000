"""Stair design form page."""

from rcd2000.stair import StairDesigner, StairInput
from rcd2000.report import format_stair
from rcd2000.gui.theme import fmt, fmt2
from rcd2000.gui.widgets import (
    spinbox, label, Card, badge, load_combo_group,
)
from rcd2000.gui.pages.form_page import DesignFormPage


class StairPage(DesignFormPage):
    module_name = "Stair"

    def build_inputs(self, layout):
        c = Card("Stair Geometry & Loading")
        # AUDIT: span 1–12 m is fine. The engine assumes waist = span/20,
        # so very short spans produce very thin slabs (<100mm min enforced).
        self.s_span = spinbox(1, 12, 0.5, 4, 2, " m")
        # AUDIT: tread 150–400 mm and rise 100–250 mm — rise/tread ratio
        # not enforced. BS 8110 doesn't strictly govern this, but
        # comfort guidelines suggest rise/tread <= 0.75.
        self.s_tread = spinbox(150, 400, 5, 250, 0)
        self.s_rise = spinbox(100, 250, 5, 175, 0)
        c.add_row("Span (m):", self.s_span)
        c.add_row("Tread (mm):", self.s_tread)
        c.add_row("Rise (mm):", self.s_rise)

        # AUDIT: imposed_load 0–20 kN/m² and spl 0–10 kN/m² are fine.
        # wld 0–50 kN/m³ — default 0 means self-weight is the only DL.
        self.s_imp = spinbox(0, 20, 0.5, 1.5, 2, " kN/m²")
        self.s_spl = spinbox(0, 10, 0.5, 0, 2, " kN/m²")
        self.s_wld = spinbox(0, 50, 1, 0, 1, " kN/m³")
        c.add_row("Imposed Load (kN/m²):", self.s_imp)
        c.add_row("Sup. DL (kN/m²):", self.s_spl)
        c.add_row("WLD (kN/m³):", self.s_wld)

        load_w, self.gk, self.qk, self.load_result = load_combo_group()
        c.add_widget(label("Load Combination (for reference)", secondary=True, size=12))
        c.add_widget(load_w)
        layout.addWidget(c)

    def calculate(self):
        inp = StairInput(
            stair_id="ST1",
            span=self.s_span.value(),
            tread=self.s_tread.value(),
            rise=self.s_rise.value(),
            imposed_load=self.s_imp.value(),
            spl=self.s_spl.value(),
            wld=self.s_wld.value(),
        )
        designer = StairDesigner()
        result = designer.design([inp])[0]
        return inp, result

    def format_report(self, inp, result):
        return format_stair(inp, result)

    def _build_result_rows(self, r):
        rows = [
            ["Waist Thickness (mm)", fmt(r.waist_thickness), ""],
            ["Total UDL (kN/m)", fmt2(r.total_udl), ""],
            ["Design Moment (kN·m)", fmt2(r.design_moment), ""],
            ["Effective Depth (mm)", fmt(r.effective_depth), ""],
            ["K Value", fmt2(r.k_value), ""],
            ["Lever Arm Factor", fmt2(r.lever_arm_factor), ""],
            ["Lever Arm z (mm)", fmt2(r.lever_arm_z), ""],
            ["Steel Required (mm²)", fmt(r.steel_required), ""],
            ["Bar Type", r.bar_type, ""],
            ["Bar Diameter (mm)", fmt(r.bar_dia), ""],
            ["Bar Spacing (mm)", fmt(r.bar_spacing), ""],
        ]
        return rows
