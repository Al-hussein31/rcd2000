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
        # AUDIT: span 1-12 m is fine. The engine assumes waist = span/20,
        # so very short spans produce very thin slabs (<100mm min enforced).
        self.s_span = spinbox(0, 999999999, 0.5, 4, 2, " m")
        # AUDIT: tread 150-400 mm and rise 100-250 mm - rise/tread ratio
        # not enforced. BS 8110 doesn't strictly govern this, but
        # comfort guidelines suggest rise/tread <= 0.75.
        self.s_tread = spinbox(0, 999999999, 5, 250, 0)
        self.s_rise = spinbox(0, 999999999, 5, 175, 0)
        c.add_row("Span (m):", self.s_span)
        c.add_row("Tread (mm):", self.s_tread)
        c.add_row("Rise (mm):", self.s_rise)

        # AUDIT: imposed_load 0-20 kN/m² and spl 0-10 kN/m² are fine.
        # wld 0-50 kN/m³ - default 0 means self-weight is the only DL.
        self.s_imp = spinbox(0, 999999999, 0.5, 1.5, 2, " kN/m²")
        self.s_spl = spinbox(0, 999999999, 0.5, 0, 2, " kN/m²")
        self.s_wld = spinbox(0, 999999999, 1, 0, 1, " kN/m³")
        self.s_imp.setToolTip("Imposed (live) load on the staircase (kN/m²)")
        self.s_spl.setToolTip("Superimposed dead load beyond self-weight (kN/m²), e.g. finishes")
        self.s_wld.setToolTip(
            "Weight density of staircase concrete (kN/m³). "
            "Set to 0 to use the default self-weight calculation based on waist thickness."
        )
        c.add_row("Imposed Load (kN/m²):", self.s_imp)
        c.add_row("Sup. DL (kN/m²):", self.s_spl)
        c.add_row("WLD (kN/m³):", self.s_wld)

        load_w, self.gk, self.qk, self.load_result = load_combo_group()
        c.add_widget(label("Load Combination (for reference)", secondary=True, size=12))
        c.add_widget(load_w)
        layout.addWidget(c)
        self._auto_clear_invalid(self.s_span)
        self._auto_clear_invalid(self.s_tread)
        self._auto_clear_invalid(self.s_rise)
        self._auto_clear_invalid(self.s_imp)
        self._auto_clear_invalid(self.s_spl)
        self._auto_clear_invalid(self.s_wld)
        self._auto_clear_invalid(self.gk)
        self._auto_clear_invalid(self.qk)

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

    def validate(self) -> list[str]:
        errors = []
        ratio = self.s_rise.value() / max(self.s_tread.value(), 1)
        if ratio > 0.75:
            errors.append(f"Rise/tread ratio ({ratio:.2f}) exceeds comfort guideline of 0.75")
            self._mark_invalid(self.s_rise)
            self._mark_invalid(self.s_tread)
        return errors

    def summarize(self, inp) -> str:
        try:
            span = inp.span if hasattr(inp, "span") else inp.get("span", 0)
            tread = inp.tread if hasattr(inp, "tread") else inp.get("tread", 0)
            return f"Span {span:.1f}m, tread {tread}mm"
        except Exception:
            return f"Span {self.s_span.value():.1f}m"

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

    def get_state(self) -> dict:
        return {
            "s_span": self.s_span.value(),
            "s_tread": self.s_tread.value(),
            "s_rise": self.s_rise.value(),
            "s_imp": self.s_imp.value(),
            "s_spl": self.s_spl.value(),
            "s_wld": self.s_wld.value(),
            "gk": self.gk.value(),
            "qk": self.qk.value(),
        }

    def set_state(self, state: dict) -> None:
        if "s_span" in state:
            self.s_span.setValue(state["s_span"])
        if "s_tread" in state:
            self.s_tread.setValue(state["s_tread"])
        if "s_rise" in state:
            self.s_rise.setValue(state["s_rise"])
        if "s_imp" in state:
            self.s_imp.setValue(state["s_imp"])
        if "s_spl" in state:
            self.s_spl.setValue(state["s_spl"])
        if "s_wld" in state:
            self.s_wld.setValue(state["s_wld"])
        if "gk" in state:
            self.gk.setValue(state["gk"])
        if "qk" in state:
            self.qk.setValue(state["qk"])
