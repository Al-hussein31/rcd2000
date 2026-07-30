"""Formatted text report builder for RCD2000 — MISHA-style output.

Matches the original FORTRAN RCD2000 output format:
  - 80-character width
  - 5-space left margin (5X FORMAT)
  - Centered titles
  - Section headers with underlines
  - Label : value : units layout
  - Bar schedules (Y12 @ 250 c/c Btm)
  - Dashed-line separators
"""

import math
from typing import List, Optional, Tuple


JOB_LABEL = "Job  Ref:"
DATE_LABEL = "Date   :"
DESIGNED_LABEL = "Designed:"
CHECKED_LABEL = "Checked:"


class Report:
    """Build a multi-line fixed-width text report (80 columns)."""

    def __init__(self):
        self.lines: List[str] = []
        self._width = 80

    # ── Low-level ────────────────────────────────────────────────

    def blank(self, n: int = 1):
        for _ in range(n):
            self.lines.append("")

    def line(self, text: str = ""):
        self.lines.append(text)

    def separator(self, char: str = "_", count: int = 74):
        self.lines.append("  " + char * count)

    # ── Title ────────────────────────────────────────────────────

    def title(self, text: str):
        """Centered title matching original: 23 spaces + text."""
        self.blank(2)
        self.lines.append(f"{' ' * 23}{text}")
        self.lines.append(f"{' ' * 23}{'-' * len(text)}")
        self.blank(1)

    # ── Job header ───────────────────────────────────────────────

    def job_header(self, job_ref: str = "", date: str = "",
                   designer: str = "", checker: str = ""):
        """Job reference, date, designer, checker block."""
        self._job_line("Job  Ref:", job_ref, "Date   :", date)
        self._job_line("Designed:", designer, "Checked:", checker)
        self.blank(1)

    def _job_line(self, left_label: str, left_val: str,
                  right_label: str, right_val: str):
        left_pad = 34 - len(left_label)
        right_pad = 29 - len(right_label)
        line = f"   {left_label}{' ' * max(3, left_pad)}{left_val}"
        line += f"{' ' * max(3, right_pad)}{right_label}  {right_val}"
        self.lines.append(line)

    # ── Materials line ───────────────────────────────────────────

    def materials_line(self, fcu: float, fy: float, fyv: Optional[float] = None):
        """Same line: fcu = XX N/sq.mm    fy = XX N/sq.mm"""
        fcu_str = f"{fcu:.1f}N/sq. mm."
        fy_str = f"{fy:.1f}N/sq. mm."
        if fyv is not None:
            extra = f"     fyv = {fyv:.0f}N/sq. mm."
        else:
            extra = ""
        line = f"     fcu = {fcu_str:>16s}{' ' * 21}{'fy =':>6s} {fy_str:>14s}{extra}"
        self.lines.append(line)
        self.blank(1)

    # ── Ident line (Panel/Beam/Column ID + Type) ─────────────────

    def ident_line(self, label: str, value: str, type_label: str = "Type:", type_val: str = ""):
        """Panel No. XX      Type: XXX"""
        line = f"   {label}  {value:<30s}  {type_label} {type_val}"
        self.lines.append(line)

    # ── Sketch/depth line ────────────────────────────────────────

    def sketch_depth(self, depth: float, unit: str = "mm"):
        """Sketch:         Depth: 150.00 mm"""
        self.lines.append(f"   Sketch:{' ' * 37}Depth: {depth:.2f} {unit}")
        self.blank(1)

    # ── Label-value ──────────────────────────────────────────────

    def label_val(self, label: str, value, unit: str = "",
                  indent: int = 5, label_width: int = 24, value_width: int = 10):
        """Label = 1234.56 unit"""
        v = f"{value:>{value_width}.{_decimal_places(value)}f}" if isinstance(value, float) else str(value)
        u = f"  {unit}" if unit else ""
        self.lines.append(f"{' ' * indent}{label:<{label_width}} = {v}{u}")

    def label_blank_val(self, label: str, value: str, indent: int = 5, label_width: int = 24):
        self.lines.append(f"{' ' * indent}{label:<{label_width}} = {value}")

    # ── Bar schedule ─────────────────────────────────────────────

    def bar_schedule(self, prefix: str, bar_type: str, bar_dia: float,
                     spacing: float, position: str = "Btm"):
        """Provide Y12 @ 250 mm c/c Btm"""
        dia = int(round(bar_dia))
        sp = int(round(spacing))
        self.lines.append(f"{' ' * 5}{prefix} {bar_type}{dia}. @ {sp}.mm c/c {position}")

    # ── Bar schedule with value ──────────────────────────────────

    def bar_schedule_val(self, label: str, steel_area: float, bar_type: str,
                         bar_dia: float, spacing: float, position: str = "Btm"):
        """Steel Required =  195.00 sq. mm\n     Provide Y12 @ 250 mm c/c Btm"""
        self.label_val(label, steel_area, "sq. mm")
        dia = int(round(bar_dia))
        sp = int(round(spacing))
        self.lines.append(f"{' ' * 5}Provide {bar_type}{dia}. @ {sp}.mm c/c {position}")

    # ── Section header ───────────────────────────────────────────

    def section(self, letter: str, title: str = ""):
        """A. MOMENTS"""
        t = f"{letter}. {title}" if title else letter
        self.blank(1)
        self.lines.append(f"{' ' * 5}{t}")
        self.lines.append(f"{' ' * 5}{'^' * len(t)}")
        self.blank(1)

    def section_plain(self, text: str):
        """DEFLECTION"""
        self.blank(1)
        self.lines.append(f"{' ' * 5}{text}")
        self.lines.append(f"{' ' * 5}{'^' * len(text)}")

    # ── Sub-section ──────────────────────────────────────────────

    def sub_section(self, text: str, centered: bool = False):
        """SHORT SPAN / LONG SPAN"""
        if centered:
            indent = (self._width - len(text)) // 2 + 10
        else:
            indent = 10
        self.blank(1)
        self.lines.append(f"{' ' * indent}{text}")
        self.lines.append(f"{' ' * indent}{'^' * len(text)}")
        self.blank(1)

    # ── Table ────────────────────────────────────────────────────

    def table(self, headers: List[Tuple[str, int]], rows: List[List[str]],
              indent: int = 10):
        """Fixed-width table.
        
        headers: list of (label, column_width)
        rows: list of lists of cell strings
        """
        header_line = " " * indent
        for label, w in headers:
            header_line += label.rjust(w + 2)
        self.lines.append(header_line)

        for row in rows:
            line = " " * indent
            for cell, (_, w) in zip(row, headers):
                line += str(cell).rjust(w + 2)
            self.lines.append(line)
        self.blank(1)

    # ── Table with sub-header row ────────────────────────────────

    def table_with_sub(self, headers: List[Tuple[str, int]],
                       sub_headers: List[Tuple[str, int]],
                       rows: List[List[str]], indent: int = 10):
        """Table with header + sub-header line."""
        hline = " " * indent
        for label, w in headers:
            hline += label.rjust(w + 2)
        self.lines.append(hline)

        sline = " " * indent
        for label, w in sub_headers:
            sline += label.rjust(w + 2)
        self.lines.append(sline)

        for row in rows:
            line = " " * indent
            for cell, (_, w) in zip(row, headers):
                line += str(cell).rjust(w + 2)
            self.lines.append(line)
        self.blank(1)

    # ── Deflection section (slab) ────────────────────────────────

    def deflection(self, span_depth: float, as_percent: float,
                   fs: float, mod_factor: float, depth_reqd: float):
        self.section_plain("DEFLECTION")
        self.lines.append(
            f"{' ' * 5}Span/Depth = {span_depth:<5.1f}{'%As =':>7s} {as_percent:<5.2f}"
            f"{'Fs =':>5s} {fs:<6.1f}{'Mod. Factor =':>15s} {mod_factor:<5.2f}"
        )
        self.blank(1)
        self.lines.append(f"{' ' * 5}Effective Depth of slab Reqd. = {depth_reqd:.1f}mm")
        self.blank(1)

    # ── Footer ───────────────────────────────────────────────────

    REPO = "https://github.com/Al-hussein31/rcd2000"

    def footer(self, module_name: str = ""):
        self.separator()
        self.blank(1)
        job = module_name or "structural element"
        self.lines.append(f"{' ' * 5}Well done! You've designed a {job} to BS 8110.")
        self.lines.append(f"{' ' * 5}Built with RCD2000 — github.com/Al-hussein31/rcd2000")
        self.blank(2)

    # ── Units block (continuous beam) ────────────────────────────

    def units_block(self, units: List[str]):
        """THE FOLLOWING ARE THE UNITS ASSUMED"""
        self.blank(1)
        self.lines.append(f"{' ' * 5}THE FOLLOWING ARE THE UNITS ASSUMED")
        for u in units:
            self.lines.append(f"{' ' * 5}{u}")

    # ── Build ────────────────────────────────────────────────────

    def build(self) -> str:
        return "\n".join(self.lines) + "\n"


def _decimal_places(v: float) -> int:
    """Determine appropriate decimal places for a value."""
    if abs(v) >= 1000:
        return 0
    elif abs(v) >= 100:
        return 1
    elif abs(v) >= 1:
        return 2
    return 3


def export_pdf(text: str, output_path: str):
    """Export a plain-text report to PDF using QPrinter + QTextDocument."""
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QTextDocument
        from PySide6.QtPrintSupport import QPrinter
    except ImportError:
        raise ImportError("PySide6 is required for PDF export. Install with: pip install rcd2000[gui]")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    doc = QTextDocument()
    html = (
        "<html><head><style>"
        "body { font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; "
        "       font-size: 9pt; color: #1a1a1a; line-height: 1.15; }"
        "pre { white-space: pre; }"
        "</style></head><body><pre>" + _escape_html(text) + "</pre></body></html>"
    )
    doc.setHtml(html)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(output_path)
    printer.setPageSize(QPrinter.A4)
    printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)

    doc.setPageSize(printer.pageRect(QPrinter.DevicePixel).size())
    doc.print(printer)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ═══════════════════════════════════════════════════════════════════
# Module-specific formatters
# ═══════════════════════════════════════════════════════════════════

def format_slab(p, r, job: str = "", date: str = "",
                designer: str = "") -> str:
    """Formatted report for a slab result — matches MISHA1/MISHA2."""
    types = {1: "Cantilever Slab", 2: "Simply Supported",
             3: "Continuous (One-Way)", 4: "Two Way Case"}
    ptype = types.get(r.panel_type, "Unknown")

    rep = Report()
    rep.title("SLAB ANALYSIS AND DESIGN - BS 8110")
    rep.job_header(job, date, designer)
    rep.materials_line(p.fcu, p.fy)

    rep.ident_line("Panel No.", p.panel_id, "Type:", ptype)
    rep.sketch_depth(p.depth)
    rep.blank(2)

    if r.panel_type == 2:
        # Simply supported — matches MISHA1
        rep.label_val("Span  Length", p.span * 1000, "mm", label_width=20)
        rep.label_val("Span  UDL", p.udl, "kN/m", label_width=20)
        rep.label_val("No. of Point Loads", p.npl, "", label_width=20)
        rep.blank(2)
        rep.label_val("Moment", r.moment_span, "kN.m", value_width=8)
        rep.bar_schedule_val("Steel Required", r.steel_span,
                             r.bar_type, r.bar_dia, r.bar_spacing, "Btm")
        rep.blank(1)
        rep.label_val("Left  Shear on Beam/Wall", r.shear_left, "kN/m", value_width=8)
        rep.blank(1)
        rep.label_val("Right Shear on Beam/Wall", r.shear_right, "kN/m", value_width=8)
        rep.blank(1)

    elif r.panel_type == 4:
        # Two-way — matches MISHA2
        rep.label_val("lx", p.span * 1000, "mm", label_width=8, value_width=8)
        rep.label_val("ly", p.ly * 1000, "mm", label_width=8, value_width=8)
        rep.label_val("ly/lx", p.ly / p.span if p.span else 0, "", label_width=8, value_width=8)
        rep.blank(1)
        rep.lines.append(
            f"{' ' * 5}Short Span Coeff. {r.coeff_short_support:.3f} & {r.coeff_short_span:.3f}"
            f"   Long Span Coeff. {r.coeff_long_support:.3f} & {r.coeff_long_span:.3f}"
        )
        rep.label_val("Uniformly Distributed Load", p.udl, "kN/m")
        rep.blank(2)

        # Short span
        rep.sub_section("SHORT SPAN", centered=True)
        rep.table(
            [("Section", 16), ("Moment (kN.m)", 14), ("Steel (sq. mm)", 14), ("PROVIDE", 20)],
            [
                ["Span", f"{r.moment_span:.2f}", f"{r.steel_span:.2f}",
                 f"Y{int(r.bar_dia)}. @ {int(r.bar_spacing)}.mm c/c B"],
                ["Cont. Edge", f"{r.moment_support:.2f}", f"{r.steel_support:.2f}",
                 f"Y{int(r.bar_dia)}. @ {int(r.bar_spacing)}.mm c/c T"],
            ],
            indent=10,
        )
        rep.label_val("Equivalent Udl on Beam", r.eq_udl_short, "kN/m")
        rep.blank(1)

        # Long span
        rep.sub_section("LONG SPAN", centered=True)
        rep.table(
            [("Section", 16), ("Moment (kN.m)", 14), ("Steel (sq. mm)", 14), ("PROVIDE", 20)],
            [
                ["Span", f"{r.moment_long_span:.2f}", f"{r.steel_long_span:.2f}",
                 f"Y{int(r.bar_dia)}. @ {int(r.bar_spacing)}.mm c/c B"],
                ["Cont. Edge", f"{r.moment_long_support:.2f}", f"{r.steel_long_support:.2f}",
                 f"Y{int(r.bar_dia)}. @ {int(r.bar_spacing)}.mm c/c T"],
            ],
            indent=10,
        )
        rep.label_val("Equivalent Udl on Beam", r.eq_udl_long, "kN/m")
        rep.blank(1)

        # Torsional bars
        rep.lines.append(
            f"{' ' * 5}*Torsional Bars. if any. is {r.torsional_steel:.3f} sq. mm"
        )
        rep.bar_schedule("Provide", r.bar_type, r.bar_dia, r.bar_spacing, "T")
        rep.blank(1)

    # ── Deflection (all types) ───────────────────────────────────
    as_percent = r.steel_span / (p.depth * 1000) * 100 if p.depth else 0
    rep.deflection(
        p.span / (p.depth / 1000) if p.depth else 0,
        as_percent, 273.5, 1.76, r.defl_required,
    )

    rep.footer("slab")
    return rep.build()


def format_column(ci, r, job: str = "", date: str = "",
                  designer: str = "", fcu: float = 25, fy: float = 460) -> str:
    """Formatted report for a column result."""
    col_types = {1: "Axially Loaded", 2: "Uniaxial Bending", 3: "Biaxial Bending"}
    ctype = col_types.get(ci.col_type, "Unknown")

    rep = Report()
    rep.title("COLUMN ANALYSIS AND DESIGN - BS 8110")
    rep.title("Reinforced Concrete Design")
    rep.job_header(job, date, designer)
    rep.materials_line(fcu, fy)

    rep.ident_line("COLUMN ID.", ci.column_id, "Type:", ctype)
    if ci.shape == 1:
        rep.lines.append(
            f"{' ' * 5}SIZE : {int(ci.bx)} BY {int(ci.by)} mm     Type : {ctype}"
        )
    else:
        rep.lines.append(
            f"{' ' * 5}SIZE : {int(ci.dia)} mm DIA.     Type : {ctype}"
        )
    rep.blank(2)

    rep.section("A", "INPUT DATA")
    rep.label_val("AXIAL LOAD", ci.load, "kN")
    rep.label_val("MOMENT ABOUT X - AXIS", ci.moment_x, "kN.m")
    rep.label_val("MOMENT ABOUT Y-AXIS", ci.moment_y, "kN.m")
    rep.blank(1)

    if ci.col_type != 1:
        rep.section("B", "FINAL INPUT MOMENTS")
        rep.label_val("MOMENT ABOUT X - AXIS", ci.moment_x or ci.moment, "kN.m")
        rep.label_val("MOMENT ABOUT Y-AXIS", ci.moment_y, "kN.m")
        rep.blank(1)

    rep.section("C", "OUTPUT DATA")
    rep.label_val("AREA OF STEEL REQUIRED", r.steel_required, "Sq.mm")
    rep.label_blank_val("MAIN BARS: Provide", "_____ BARS")
    rep.label_blank_val("LINKS : Provide", "___@___c/c")
    rep.label_val("ULTIMATE AXIAL LOAD", r.axial_capacity, "kN")

    if ci.col_type != 1:
        rep.label_val("ULTIMATE MOMENT ABOUT X-AXIS", r.moment_capacity_x, "kN.m")
        rep.label_val("ULTIMATE MOMENT ABOUT Y-AXIS", r.moment_capacity_y, "kN.m")

    rep.label_blank_val("*STEEL PERCENTAGE", f"{r.steel_percent:.1f}%")
    rep.blank(1)
    rep.lines.append(f"{' ' * 5}*NOTE:- Steel % based on area required please")
    rep.separator("-", 74)
    rep.blank(1)
    rep.footer("column")
    return rep.build()


def format_beam(bi, r, job: str = "", date: str = "",
                designer: str = "") -> str:
    """Formatted report for a beam result."""
    rep = Report()
    rep.title("BEAM ANALYSIS AND DESIGN BS 8110")
    rep.blank(1)
    rep.line(f"{' ' * 5}BEAM DESIGN OUTPUT FOR {bi.beam_id}")
    rep.blank(1)
    rep.job_header(job, date, designer)

    rep.ident_line("BEAM ID:", bi.beam_id, "SIZE:",
                   f"{int(bi.h)} BY {int(bi.b)} mm")
    rep.line(f"{' ' * 5}SKETCH:")
    rep.materials_line(bi.fcu, bi.fy, bi.fyv)

    mu = (0.156 * bi.fcu * bi.b * (bi.h - 50) ** 2) / 1.0e6
    rep.lines.append(f"{' ' * 5}Mu = {mu:.3f} kN.m")
    rep.blank(1)

    # Beam loading table
    rep.lines.append(f"{' ' * 5}Beam Loading")
    rep.table(
        [("SPAN", 8), ("UDL", 8), ("TRIANG.", 10), ("TRAPEZ.", 10),
         ("TR.DIST.", 10), ("NPL", 6), ("LOADS", 10)],
        [[s.span_id, f"{s.udl:.2f}" if s.udl else "---", "---", "---",
          "---", "0", "---"] for s in r.spans],
        indent=5,
    )

    # A. MOMENTS — Span reinforcement
    rep.section("A", "MOMENTS")
    rep.sub_section("SPAN REINFORCEMENTS")
    rep.table_with_sub(
        [("Span", 8), ("Length", 10), ("Moment", 10), ("Steel (Sq. mm)", 16),
         ("Provide", 14)],
        [("S/N", 8), ("(m)", 10), ("(kN.m)", 10), ("Bottom", 16), ("Top", 14)],
        [[s.span_id, f"{s.length:.2f}", f"{s.moment:.2f}",
          f"{s.steel_bot:.0f}", f"{s.steel_top:.0f}"] for s in r.spans],
        indent=5,
    )

    # Support reinforcement
    rep.sub_section("SUPPORT REINFORCEMENTS")
    rep.table_with_sub(
        [("Supt", 8), ("Reaction", 12), ("Moment", 10), ("Steel (Sq. mm)", 16),
         ("Provide", 14)],
        [("S/N", 8), ("(kN)", 12), ("(kN.m)", 10), ("Top", 16), ("Bottom", 14)],
        [[s.support_id, f"{s.reaction:.2f}", f"{s.moment:.2f}",
          f"{s.steel_top:.0f}", f"{s.steel_bot:.0f}"] for s in r.supports],
        indent=5,
    )

    # B. SHEAR
    rep.section("B", "SHEAR")
    rep.lines.append(f"{' ' * 5}SPAN        LEFT SUPPORT    RIGHT SUPPORT")
    rep.table_with_sub(
        [("S/N", 8), ("Shear", 10), ("Spacing", 10), ("Shear", 10), ("Spacing", 10)],
        [("", 8), ("(kN)", 10), ("(mm)", 10), ("(kN)", 10), ("(mm)", 10)],
        [[s.span_id, f"{s.shear_left:.2f}", f"{s.sv_left:.0f}",
          f"{s.shear_right:.2f}", f"{s.sv_right:.0f}"] for s in r.spans],
        indent=5,
    )
    rep.lines.append(
        f"{' ' * 5}NOTE: Spacing Based on 2 Legs 10mm Dia. Bar with FY = {bi.fyv:.0f} N/Sq.mm"
    )
    rep.blank(1)

    rep.footer("beam")
    return rep.build()


def format_stair(si, r, job: str = "", date: str = "",
                 designer: str = "") -> str:
    """Formatted report for a stair result."""
    rep = Report()
    rep.title("STAIR DESIGN - Straight Flight")
    rep.blank(1)
    rep.job_header(job, date, designer)
    rep.line(f"{' ' * 5}---")

    rep.lines.append(f"{' ' * 5}Stair No. 1")
    rep.lines.append(f"{' ' * 5}Type: Straight Flight")
    rep.blank(1)

    rep.label_val("Span", si.span, "m", label_width=20, value_width=8)
    rep.label_val("Waist thickness", r.waist_thickness, "mm", label_width=20, value_width=8)
    rep.label_val("Total ultimate load", r.total_udl, "kN/m", label_width=20, value_width=8)
    rep.label_val("Design moment", r.design_moment, "kNm/m", label_width=20, value_width=8)
    rep.label_val("Effective depth", r.effective_depth, "mm", label_width=20, value_width=8)
    rep.label_val("K-value", r.k_value, "", label_width=20, value_width=8)
    rep.label_val("Lever arm factor z/d", r.lever_arm_factor, "", label_width=20, value_width=8)
    rep.label_val("Lever arm z", r.lever_arm_z, "mm", label_width=20, value_width=8)
    rep.label_val("Required As", r.steel_required, "mm2/m", label_width=20, value_width=8)
    rep.blank(1)

    rep.bar_schedule("Provide", r.bar_type, r.bar_dia, r.bar_spacing, "Btm")
    rep.blank(1)

    rep.footer("stair")
    return rep.build()


def format_base(bi, r, job: str = "", date: str = "",
                designer: str = "") -> str:
    """Formatted report for a foundation result."""
    base_types = {1: "SQUARE ISOLATED", 2: "RECTANGULAR ISOLATED", 3: "COMBINED"}
    btype = base_types.get(bi.base_type, "UNKNOWN")

    rep = Report()
    rep.title("BASE ANALYSIS AND DESIGN TO BS8110")
    rep.job_header(job, date, designer)
    rep.materials_line(bi.fcu, bi.fy)

    rep.ident_line("BASE ID.", bi.base_id, "Type:", btype)
    rep.blank(1)

    if bi.base_type == 3:
        rep.label_val("No. of Columns", 2, "", label_width=20)
        rep.blank(1)

    rep.section("A", "FOOTING DIMENSIONS")
    rep.label_val("Footing Length (L1)", r.l1, "mm")
    rep.label_val("Footing Width (L2)", r.l2, "mm")
    rep.label_val("Footing Depth (h)", r.h, "mm")
    rep.label_val("Allowable Bearing Pressure", bi.pb, "kN/m2")
    rep.label_val("Net Upward Pressure (fnet)", r.fnet, "kN/m2")
    rep.blank(1)

    rep.section("B", "REINFORCEMENT DESIGN")
    rep.label_val("Moment about L1", r.m1, "kN.m")
    rep.label_val("Steel Required (L1)", r.as1, "sq. mm")
    rep.bar_schedule("Provide", r.bar_type1, r.rd1, r.sp1, "Btm")
    rep.blank(1)
    rep.label_val("Moment about L2", r.m2, "kN.m")
    rep.label_val("Steel Required (L2)", r.as2, "sq. mm")
    rep.bar_schedule("Provide", r.bar_type2, r.rd2, r.sp2, "Btm")
    rep.blank(1)

    rep.section("C", "SHEAR CHECKS")
    rep.label_val("Shear Stress", r.shear_stress, "N/mm2")
    rep.label_val("Permissible Shear", r.perm_shear, "N/mm2")
    rep.label_val("Punching Shear", r.punching_shear, "N/mm2")
    rep.label_val("Local Bond", r.local_bond, "N/mm2")
    rep.label_val("Permissible Bond", r.perm_bond, "N/mm2")
    rep.blank(1)

    rep.footer("footing base")
    return rep.build()


def format_continuous_beam(cb_input, r, job: str = "",
                           date: str = "", designer: str = "") -> str:
    """Formatted report for a continuous beam analysis result."""
    rep = Report()
    rep.title("CONTINUOUS BEAM ANALYSIS - BS 8110")
    rep.job_header(job, date, designer)

    rep.lines.append(f"{' ' * 5}THE FOLLOWING ARE THE RESULTS")
    rep.units_block([
        "    LENGTHS OR DISTANCES IN METRES",
        "    ALL MOMENTS IN kN.m",
        "    SHEAR FORCES, REACTIONS IN kN",
        "    INERTIA IN m TO POWER 4",
        "    YOUNG MODULUS IN kN PER SQ.m",
        "    POINT LOADS IN kN",
        "    OTHER LOADS IN kN PER m",
    ])
    rep.blank(1)

    if r.support_moments:
        rep.sub_section("SUPPORT REACTIONS")
        rep.table(
            [("S/N", 8), ("REACTION", 14), ("MOMENT", 14)],
            [[f"{i+1}", f"{r.support_reactions[i]:.3f}", f"{r.support_moments[i]:.3f}"]
             for i in range(len(r.support_moments))],
            indent=5,
        )

    if r.span_moments:
        rep.sub_section("BEAM FORCES")
        rep.table(
            [("S/N", 6), ("LENGTH", 10), ("NODE 1", 8), ("SHEAR", 10),
             ("MOMENT", 10), ("NODE 2", 8), ("SHEAR", 10), ("MOMENT", 10),
             ("MAX SPAN MOMENT", 14)],
            [[f"{i+1}", f"{r.members[i].length:.3f}", f"{i+1}",
              f"{r.span_shear_left[i]:.3f}", f"{r.support_moments[i]:.3f}",
              f"{i+2}", f"{r.span_shear_right[i]:.3f}", f"{r.support_moments[i+1]:.3f}",
              f"{r.span_moments[i]:.3f}"]
             for i in range(len(r.span_moments))],
            indent=5,
        )

    rep.blank(1)
    rep.lines.append(f"{' ' * 5}Well done! You've analysed a continuous beam to BS 8110.")
    rep.lines.append(f"{' ' * 5}Built with RCD2000 — github.com/Al-hussein31/rcd2000")
    rep.blank(2)
    return rep.build()
