"""RCD2000 GUI — PySide6 desktop application."""

import sys
import math
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QPushButton, QGroupBox,
    QFormLayout, QGridLayout, QDoubleSpinBox, QComboBox, QLineEdit,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QFrame, QSizePolicy, QMessageBox, QStatusBar,
    QTabWidget, QSplitter, QAbstractItemView,
)
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QFont, QIcon, QPixmap, QPalette, QColor, QFontDatabase

from rcd2000 import __version__
from rcd2000.beam import BeamDesigner, BeamInput
from rcd2000.column import ColumnDesigner, ColumnInput
from rcd2000.slab import SlabDesigner, SlabPanelInput
from rcd2000.stair import StairDesigner, StairInput
from rcd2000.base import BaseDesigner, BaseInput, ColumnOnBase
from rcd2000.continuous_beam import (
    ContinuousBeamAnalyzer, ContinuousBeamInput, ContinuousBeamMember,
)
from rcd2000.models import result_to_dict

# ── Theme colours ──────────────────────────────────────────────────
BG_DARK = "#1e1e1e"
BG_MID = "#252526"
BG_LIGHT = "#2d2d2d"
SIDEBAR_BG = "#1a1a1a"
ACCENT = "#d48c28"
ACCENT_HOVER = "#e8a030"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#999999"
BORDER = "#3a3a3a"
SUCCESS = "#4caf50"
ERROR = "#e53935"
TABLE_HEADER = "#333333"
TABLE_ALT = "#2a2a2a"

# ── SpinBox helper ─────────────────────────────────────────────────
def _sb(min_v=0.0, max_v=999999.0, step=1.0, default=0.0, decimals=1, suffix="") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(min_v, max_v)
    s.setSingleStep(step)
    s.setValue(default)
    s.setDecimals(decimals)
    if suffix:
        s.setSuffix(suffix)
    s.setStyleSheet(f"""
        QDoubleSpinBox {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};
                          border: 1px solid {BORDER}; border-radius: 4px;
                          padding: 4px 8px; font-size: 13px; }}
        QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}
    """)
    return s

def _sp(min_v=0, max_v=9999, default=0) -> QSpinBox:
    s = QSpinBox()
    s.setRange(min_v, max_v)
    s.setValue(default)
    s.setStyleSheet(f"""
        QSpinBox {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};
                    border: 1px solid {BORDER}; border-radius: 4px;
                    padding: 4px 8px; font-size: 13px; }}
        QSpinBox:focus {{ border-color: {ACCENT}; }}
    """)
    return s

def _combo(items: list) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    c.setStyleSheet(f"""
        QComboBox {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};
                     border: 1px solid {BORDER}; border-radius: 4px;
                     padding: 4px 8px; font-size: 13px; }}
        QComboBox:hover {{ border-color: {ACCENT}; }}
        QComboBox::drop-down {{ border: none; }}
        QComboBox QAbstractItemView {{ background: {BG_MID}; color: {TEXT_PRIMARY};
                                       selection-background-color: {ACCENT}; }}
    """)
    return c

def _btn(text: str, accent: bool = True) -> QPushButton:
    b = QPushButton(text)
    if accent:
        b.setStyleSheet(f"""
            QPushButton {{ background: {ACCENT}; color: #fff; font-weight: bold;
                           border: none; border-radius: 6px; padding: 10px 32px;
                           font-size: 14px; }}
            QPushButton:hover {{ background: {ACCENT_HOVER}; }}
            QPushButton:pressed {{ background: #b07220; }}
        """)
    else:
        b.setStyleSheet(f"""
            QPushButton {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};
                           border: 1px solid {BORDER}; border-radius: 6px;
                           padding: 8px 24px; font-size: 13px; }}
            QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
        """)
    return b

def _label(text: str, bold=False, secondary=False, size=13) -> QLabel:
    l = QLabel(text)
    color = TEXT_SECONDARY if secondary else TEXT_PRIMARY
    l.setStyleSheet(f"color: {color}; font-size: {size}px; {'font-weight: bold;' if bold else ''}")
    return l

def _header_label(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(f"color: {ACCENT}; font-size: 16px; font-weight: bold; padding: 4px 0;")
    return l

# ── Section divider ────────────────────────────────────────────────
def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"color: {BORDER};")
    return f

# ── Format helpers ─────────────────────────────────────────────────
def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:,.1f}"
    return str(v)

def _fmt2(v) -> str:
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)

# ── Table helper ───────────────────────────────────────────────────
def _make_table(headers: list, rows: list[list]) -> QTableWidget:
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.NoSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    for col, h in enumerate(headers):
        t.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignCenter)
            t.setItem(r, c, item)
    t.setStyleSheet(f"""
        QTableWidget {{ background: {BG_MID}; color: {TEXT_PRIMARY};
                        border: 1px solid {BORDER}; border-radius: 4px;
                        font-size: 12px; gridline-color: {BORDER}; }}
        QTableWidget::item {{ padding: 4px 8px; }}
        QTableWidget::item:alternate {{ background: {TABLE_ALT}; }}
        QHeaderView::section {{ background: {TABLE_HEADER}; color: {ACCENT};
                               font-weight: bold; padding: 6px 8px;
                               border: none; font-size: 12px; }}
    """)
    t.setMinimumHeight(min(len(rows) * 28 + 30, 300))
    return t


# ═══════════════════════════════════════════════════════════════════
# Module Pages
# ═══════════════════════════════════════════════════════════════════

# ── Column Page ──────────────────────────────────────────────────
class ColumnPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(_header_label("Column Design — BS 8110"))

        # Type
        g1 = QGroupBox("Column Type")
        g1.setStyleSheet(f"QGroupBox {{ color: {ACCENT}; font-weight: bold; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}")
        f1 = QFormLayout(g1)
        self.col_type = _combo(["1 - Axially Loaded", "2 - Uniaxial Bending", "3 - Biaxial Bending"])
        self.shape = _combo(["Rectangular", "Circular"])
        f1.addRow("Type:", self.col_type)
        f1.addRow("Shape:", self.shape)

        # Loads & Geometry
        g2 = QGroupBox("Loads & Geometry")
        g2.setStyleSheet(g1.styleSheet())
        f2 = QFormLayout(g2)
        self.load = _sb(0, 50000, 100, 1000)
        self.bx = _sb(100, 2000, 25, 300, 0)
        self.by = _sb(100, 2000, 25, 300, 0)
        self.dia = _sb(100, 2000, 25, 300, 0)
        self.depth = _sb(100, 2000, 25, 300, 0)
        f2.addRow("Axial Load (kN):", self.load)
        f2.addRow("b/h width - x (mm):", self.bx)
        f2.addRow("b/h width - y (mm):", self.by)
        f2.addRow("Diameter (mm):", self.dia)
        f2.addRow("Overall depth (mm):", self.depth)

        # Moments
        g3 = QGroupBox("Moments")
        g3.setStyleSheet(g1.styleSheet())
        f3 = QFormLayout(g3)
        self.moment_x = _sb(0, 5000, 10, 0)
        self.moment_y = _sb(0, 5000, 10, 0)
        self.moment = _sb(0, 5000, 10, 0)
        f3.addRow("Mx (kN·m):", self.moment_x)
        f3.addRow("My (kN·m):", self.moment_y)
        f3.addRow("M (uniaxial, kN·m):", self.moment)

        self.calc_btn = _btn("Design Column")
        self.calc_btn.clicked.connect(self._calculate)

        self.results_area = QVBoxLayout()
        self.results_area.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(g3)
        layout.addWidget(self.calc_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

    def _calculate(self):
        self._clear_results()
        c = ColumnInput(
            column_id="C1",
            col_type=self.col_type.currentIndex() + 1,
            shape=1 if self.shape.currentIndex() == 0 else 2,
            load=self.load.value(),
            bx=self.bx.value(), by=self.by.value(),
            dia=self.dia.value(), depth=self.depth.value(),
            moment_x=self.moment_x.value(),
            moment_y=self.moment_y.value(),
            moment=self.moment.value() or self.moment_x.value(),
        )
        designer = ColumnDesigner()
        result = designer.design([c])[0]

        rows = [
            ["Steel Required", f"{result.steel_required:,.0f} mm²", ""],
            ["Steel Percentage", f"{result.steel_percent:.2f}%", ""],
            ["Axial Capacity (Nu)", f"{result.axial_capacity:,.0f} kN",
             "✓" if result.axial_capacity >= c.load else "✗"],
            ["Moment Capacity (Mux)", f"{result.moment_capacity_x:,.0f} kN·m", ""],
            ["Moment Capacity (Muy)", f"{result.moment_capacity_y:,.0f} kN·m", ""],
        ]
        if c.col_type == 3:
            rows.append(["Biaxial Check", "OK" if result.biaxial_check_ok else "FAIL",
                         "✓" if result.biaxial_check_ok else "✗"])

        t = _make_table(["Parameter", "Value", "Status"], rows)
        self.results_area.addWidget(t)

        if result.heck:
            self.results_area.addWidget(_label("⚠ Section inadequate — increase dimensions", secondary=False, size=13))

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()


# ── Beam Page ────────────────────────────────────────────────────
class BeamPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(_header_label("Beam Design — BS 8110"))

        g1 = QGroupBox("Material Properties")
        g1.setStyleSheet(f"QGroupBox {{ color: {ACCENT}; font-weight: bold; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}")
        f1 = QFormLayout(g1)
        self.beam_fcu = _sb(15, 60, 5, 25)
        self.beam_fy = _sb(250, 600, 10, 460)
        self.beam_fyv = _sb(200, 500, 10, 250)
        f1.addRow("fcu (N/mm²):", self.beam_fcu)
        f1.addRow("fy (N/mm²):", self.beam_fy)
        f1.addRow("fyv (N/mm²):", self.beam_fyv)

        g2 = QGroupBox("Section Geometry")
        g2.setStyleSheet(g1.styleSheet())
        f2 = QFormLayout(g2)
        self.b_b = _sb(100, 2000, 25, 225, 0)
        self.b_bf = _sb(100, 2000, 25, 225, 0)
        self.b_h = _sb(100, 2000, 25, 450, 0)
        self.b_hf = _sb(0, 500, 10, 0, 0)
        f2.addRow("b (mm):", self.b_b)
        f2.addRow("bf — flange width (mm):", self.b_bf)
        f2.addRow("h — overall depth (mm):", self.b_h)
        f2.addRow("hf — flange depth (mm):", self.b_hf)

        g3 = QGroupBox("Supports & Members")
        g3.setStyleSheet(g1.styleSheet())
        f3 = QFormLayout(g3)
        self.n_supports = _sp(2, 10, 2)
        self.n_members = _sp(1, 9, 1)
        self.ty1 = _combo(["Pinned", "Fixed"])
        self.ty2 = _combo(["Pinned", "Fixed"])
        self.n_supports.valueChanged.connect(self._sync_members)
        self.n_members.valueChanged.connect(self._sync_members)
        f3.addRow("Number of Supports:", self.n_supports)
        f3.addRow("Number of Members:", self.n_members)
        f3.addRow("Left End:", self.ty1)
        f3.addRow("Right End:", self.ty2)

        g4 = QGroupBox("Member Data")
        g4.setStyleSheet(g1.styleSheet())
        self.member_grid = QGridLayout(g4)
        self.member_grid.setSpacing(6)
        self._member_widgets = []

        self.calc_btn = _btn("Design Beam")
        self.calc_btn.clicked.connect(self._calculate)
        self.results_area = QVBoxLayout()

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(g3)
        layout.addWidget(g4)
        layout.addWidget(self.calc_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

        self._sync_members()

    def _sync_members(self):
        nm = self.n_members.value()
        while len(self._member_widgets) < nm:
            row = len(self._member_widgets) + 1
            label = QLabel(f"M{row}")
            label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px;")
            length = _sb(1, 50, 0.5, 5, 2, " m")
            udl = _sb(0, 500, 5, 0, 1, " kN/m")
            wt = _sb(0, 200, 5, 0, 1)
            wb = _sb(0, 200, 5, 0, 1)
            ab = _sb(0, 10, 0.5, 0, 2)
            self.member_grid.addWidget(label, row, 0)
            self.member_grid.addWidget(length, row, 1)
            self.member_grid.addWidget(udl, row, 2)
            self.member_grid.addWidget(wt, row, 3)
            self.member_grid.addWidget(wb, row, 4)
            self.member_grid.addWidget(ab, row, 5)
            self._member_widgets.append((label, length, udl, wt, wb, ab))

        # Column headers
        headers = ["", "Length", "UDL", "Tri (wt)", "Trap (wb)", "Dist (ab)"]
        for col, h in enumerate(headers):
            self.member_grid.addWidget(_label(h, secondary=True, size=11), 0, col)

    def _calculate(self):
        self._clear_results()
        nm = self.n_members.value()
        beam = BeamInput(
            beam_id="B1",
            n_supports=self.n_supports.value(),
            n_members=nm,
            b=self.b_b.value(), bf=self.b_bf.value(),
            h=self.b_h.value(), hf=self.b_hf.value(),
            fcu=self.beam_fcu.value(), fy=self.beam_fy.value(),
            fyv=self.beam_fyv.value(),
            member_lengths=[w[1].value() for w in self._member_widgets],
            member_udl=[w[2].value() for w in self._member_widgets],
            member_wt=[w[3].value() for w in self._member_widgets],
            member_wb=[w[4].value() for w in self._member_widgets],
            member_ab=[w[5].value() for w in self._member_widgets],
            ty1=self.ty1.currentIndex(),
            ty2=self.ty2.currentIndex(),
        )
        designer = BeamDesigner(
            fcu=self.beam_fcu.value(), fy=self.beam_fy.value(),
            fyv=self.beam_fyv.value(),
        )
        result = designer.design([beam])[0]

        if result.spans:
            hdrs = ["Span", "L (m)", "M (kN·m)", "As_bot (mm²)", "As_top (mm²)",
                     "V_left (kN)", "V_right (kN)", "Defl OK"]
            rows = []
            for s in result.spans:
                rows.append([
                    s.span_id, _fmt2(s.length), _fmt2(s.moment),
                    _fmt(s.steel_bot), _fmt(s.steel_top),
                    _fmt2(s.shear_left), _fmt2(s.shear_right),
                    "✓" if s.defl_ok else "✗",
                ])
            self.results_area.addWidget(_label("Span Results", bold=True, size=14))
            self.results_area.addWidget(_make_table(hdrs, rows))

        if result.supports:
            hdrs2 = ["Support", "Reaction (kN)", "M (kN·m)", "As_top (mm²)", "As_bot (mm²)"]
            rows2 = []
            for s in result.supports:
                rows2.append([
                    s.support_id, _fmt2(s.reaction), _fmt2(s.moment),
                    _fmt(s.steel_top), _fmt(s.steel_bot),
                ])
            self.results_area.addWidget(_label("Support Results", bold=True, size=14))
            self.results_area.addWidget(_make_table(hdrs2, rows2))

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()


# ── Slab Page ────────────────────────────────────────────────────
class SlabPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(_header_label("Slab Design — BS 8110"))

        g1 = QGroupBox("Slab Type & Materials")
        g1.setStyleSheet(f"QGroupBox {{ color: {ACCENT}; font-weight: bold; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}")
        f1 = QFormLayout(g1)
        self.slab_type = _combo(["Cantilever", "Simply Supported", "Continuous (One-Way)", "Two-Way"])
        self.slab_fcu = _sb(15, 60, 5, 25)
        self.slab_fy = _sb(250, 600, 10, 460)
        f1.addRow("Type:", self.slab_type)
        f1.addRow("fcu (N/mm²):", self.slab_fcu)
        f1.addRow("fy (N/mm²):", self.slab_fy)

        g2 = QGroupBox("Panel Geometry & Loading")
        g2.setStyleSheet(g1.styleSheet())
        f2 = QFormLayout(g2)
        self.s_depth = _sb(100, 500, 10, 150, 0)
        self.s_span = _sb(0.5, 20, 0.5, 4, 2, " m")
        self.s_udl = _sb(0, 100, 5, 10, 1, " kN/m²")
        self.s_ly = _sb(0, 20, 0.5, 5, 2, " m")
        self.s_case = _sp(1, 9, 1)
        f2.addRow("Depth (mm):", self.s_depth)
        f2.addRow("Span (m):", self.s_span)
        f2.addRow("UDL (kN/m²):", self.s_udl)
        f2.addRow("Ly — long span (m):", self.s_ly)
        f2.addRow("Case (1-9):", self.s_case)

        # Continuous slab spans
        g3 = QGroupBox("Continuous Slab Spans (if applicable)")
        g3.setStyleSheet(g1.styleSheet())
        f3 = QFormLayout(g3)
        self.cont_nspan = _sp(1, 8, 3)
        self.cont_nspan.valueChanged.connect(self._sync_cont_spans)
        f3.addRow("Number of Spans:", self.cont_nspan)
        self.cont_span_layout = QVBoxLayout()
        self._cont_span_widgets = []
        f3.addRow(self.cont_span_layout)
        self._sync_cont_spans()

        self.calc_btn = _btn("Design Slab")
        self.calc_btn.clicked.connect(self._calculate)
        self.results_area = QVBoxLayout()

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(g3)
        layout.addWidget(self.calc_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

    def _sync_cont_spans(self):
        n = self.cont_nspan.value()
        while len(self._cont_span_widgets) < n:
            i = len(self._cont_span_widgets)
            h = QHBoxLayout()
            h.addWidget(_label(f"S{i+1}:", secondary=True, size=12))
            le = _sb(1, 20, 0.5, 4, 2, " m")
            ud = _sb(0, 100, 5, 10, 1, " kN/m")
            h.addWidget(le)
            h.addWidget(ud)
            self.cont_span_layout.addLayout(h)
            self._cont_span_widgets.append((le, ud))

    def _calculate(self):
        self._clear_results()
        ptype = self.slab_type.currentIndex() + 1
        p = SlabPanelInput(
            panel_id="S1",
            panel_type=ptype,
            depth=self.s_depth.value(),
            fcu=self.slab_fcu.value(), fy=self.slab_fy.value(),
            udl=self.s_udl.value(),
            span=self.s_span.value(),
            ly=self.s_ly.value(), case=self.s_case.value(),
            nspan=self.cont_nspan.value(),
            span_lengths=[w[0].value() for w in self._cont_span_widgets],
            span_udls=[w[1].value() for w in self._cont_span_widgets],
        )
        designer = SlabDesigner(fcu=self.slab_fcu.value(), fy=self.slab_fy.value())
        r = designer.design([p])[0]

        hdrs = ["Parameter", "Value"]
        rows = [
            ["Design Moment (kN·m/m)", _fmt2(r.moment_span)],
            ["Steel Required (mm²/m)", _fmt(r.steel_span)],
            ["Bar Type", r.bar_type],
            ["Bar Diameter (mm)", _fmt(r.bar_dia)],
            ["Bar Spacing (mm)", _fmt(r.bar_spacing)],
            ["Deflection OK", "✓" if r.defl_ok else "✗"],
        ]
        if ptype == 4:
            rows += [
                ["Long Span Moment (kN·m/m)", _fmt2(r.moment_long_span)],
                ["Long Span Steel (mm²/m)", _fmt(r.steel_long_span)],
                ["Support Moment (kN·m/m)", _fmt2(r.moment_support)],
                ["Support Steel (mm²/m)", _fmt(r.steel_support)],
            ]
        if ptype == 3 and r.span_moments:
            for i, (m, a) in enumerate(zip(r.span_moments, r.span_steels)):
                rows.append([f"Span {i+1} Moment (kN·m)", _fmt2(m)])
                rows.append([f"Span {i+1} Steel (mm²)", _fmt(a)])

        self.results_area.addWidget(_make_table(hdrs, rows))

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()


# ── Stair Page ──────────────────────────────────────────────────
class StairPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(_header_label("Stair Design — BS 8110"))

        g = QGroupBox("Stair Geometry & Loading")
        g.setStyleSheet(f"QGroupBox {{ color: {ACCENT}; font-weight: bold; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}")
        f = QFormLayout(g)
        self.s_span = _sb(1, 12, 0.5, 4, 2, " m")
        self.s_tread = _sb(150, 400, 5, 250, 0, " mm")
        self.s_rise = _sb(100, 250, 5, 175, 0, " mm")
        self.s_imp = _sb(0, 20, 0.5, 1.5, 2, " kN/m²")
        self.s_spl = _sb(0, 10, 0.5, 0, 2, " kN/m²")
        self.s_wld = _sb(0, 50, 1, 0, 1, " kN/m³")
        f.addRow("Span (m):", self.s_span)
        f.addRow("Tread (mm):", self.s_tread)
        f.addRow("Rise (mm):", self.s_rise)
        f.addRow("Imposed Load (kN/m²):", self.s_imp)
        f.addRow("Superimposed DL (kN/m²):", self.s_spl)
        f.addRow("WLD (kN/m³):", self.s_wld)

        self.calc_btn = _btn("Design Stair")
        self.calc_btn.clicked.connect(self._calculate)
        self.results_area = QVBoxLayout()

        layout.addWidget(g)
        layout.addWidget(self.calc_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

    def _calculate(self):
        self._clear_results()
        s = StairInput(
            stair_id="ST1",
            span=self.s_span.value(),
            tread=self.s_tread.value(),
            rise=self.s_rise.value(),
            imposed_load=self.s_imp.value(),
            spl=self.s_spl.value(),
            wld=self.s_wld.value(),
        )
        designer = StairDesigner()
        r = designer.design([s])[0]

        hdrs = ["Parameter", "Value"]
        rows = [
            ["Waist Thickness (mm)", _fmt(r.waist_thickness)],
            ["Total UDL (kN/m)", _fmt2(r.total_udl)],
            ["Design Moment (kN·m)", _fmt2(r.design_moment)],
            ["Effective Depth (mm)", _fmt(r.effective_depth)],
            ["K Value", _fmt2(r.k_value)],
            ["Lever Arm Factor", _fmt2(r.lever_arm_factor)],
            ["Lever Arm z (mm)", _fmt2(r.lever_arm_z)],
            ["Steel Required (mm²)", _fmt(r.steel_required)],
            ["Bar Type", r.bar_type],
            ["Bar Diameter (mm)", _fmt(r.bar_dia)],
            ["Bar Spacing (mm)", _fmt(r.bar_spacing)],
        ]
        self.results_area.addWidget(_make_table(hdrs, rows))

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()


# ── Base Page ───────────────────────────────────────────────────
class BasePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(_header_label("Foundation Design — BS 8110"))

        g1 = QGroupBox("Base Type & Materials")
        g1.setStyleSheet(f"QGroupBox {{ color: {ACCENT}; font-weight: bold; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}")
        f1 = QFormLayout(g1)
        self.base_type = _combo(["Square Isolated", "Rectangular Isolated", "Combined"])
        self.col_shape = _combo(["Rectangular", "Circular"])
        self.base_fcu = _sb(15, 60, 5, 25)
        self.base_fy = _sb(250, 600, 10, 460)
        self.base_pb = _sb(50, 500, 10, 150, 0, " kN/m²")
        f1.addRow("Base Type:", self.base_type)
        f1.addRow("Column Shape:", self.col_shape)
        f1.addRow("fcu (N/mm²):", self.base_fcu)
        f1.addRow("fy (N/mm²):", self.base_fy)
        f1.addRow("Allowable Bearing (kN/m²):", self.base_pb)

        g2 = QGroupBox("Loads & Dimensions")
        g2.setStyleSheet(g1.styleSheet())
        f2 = QFormLayout(g2)
        self.base_load = _sb(0, 50000, 100, 1000)
        self.base_a1 = _sb(100, 2000, 25, 300, 0)
        self.base_a2 = _sb(100, 2000, 25, 300, 0)
        self.base_dia = _sb(100, 2000, 25, 300, 0)
        self.base_h = _sb(100, 2000, 25, 300, 0)
        self.base_l1 = _sb(0, 20, 0.5, 0, 2, " m")
        self.base_l2 = _sb(0, 20, 0.5, 0, 2, " m")
        self.base_dowel = _sb(8, 40, 2, 12, 0)
        f2.addRow("Axial Load (kN):", self.base_load)
        f2.addRow("Col Dim a1 (mm):", self.base_a1)
        f2.addRow("Col Dim a2 (mm):", self.base_a2)
        f2.addRow("Col Diameter (mm):", self.base_dia)
        f2.addRow("Base Thickness h (mm):", self.base_h)
        f2.addRow("Base Length L1 (m):", self.base_l1)
        f2.addRow("Base Width L2 (m):", self.base_l2)
        f2.addRow("Dowel Diameter (mm):", self.base_dowel)

        self.calc_btn = _btn("Design Foundation")
        self.calc_btn.clicked.connect(self._calculate)
        self.results_area = QVBoxLayout()

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(self.calc_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

    def _calculate(self):
        self._clear_results()
        btype = self.base_type.currentIndex() + 1
        b = BaseInput(
            base_id="F1",
            base_type=btype,
            col_type=1 if self.col_shape.currentIndex() == 0 else 2,
            load=self.base_load.value(),
            pb=self.base_pb.value(), fcu=self.base_fcu.value(),
            fy=self.base_fy.value(),
            a1=self.base_a1.value(), a2=self.base_a2.value(),
            dia=self.base_dia.value(), dowel_dia=self.base_dowel.value(),
            h=self.base_h.value(),
            l1=self.base_l1.value(), l2=self.base_l2.value(),
        )
        designer = BaseDesigner(
            pb=self.base_pb.value(), fcu=self.base_fcu.value(),
            fy=self.base_fy.value(),
        )
        r = designer.design([b])[0]

        hdrs = ["Parameter", "Value"]
        rows = [
            ["Base Length L1 (mm)", _fmt(r.l1)],
            ["Base Width L2 (mm)", _fmt(r.l2)],
            ["Base Depth h (mm)", _fmt(r.h)],
            ["Net Upward Pressure (kN/m²)", _fmt2(r.fnet)],
            ["Moment L1 (kN·m)", _fmt2(r.m1)],
            ["Steel L1 (mm²)", _fmt(r.as1)],
            [f"Bar L1", f"Y{r.rd1:.0f} @ {r.sp1:.0f} c/c"],
            ["Moment L2 (kN·m)", _fmt2(r.m2)],
            ["Steel L2 (mm²)", _fmt(r.as2)],
            [f"Bar L2", f"Y{r.rd2:.0f} @ {r.sp2:.0f} c/c"],
            ["Shear Stress (N/mm²)", _fmt2(r.shear_stress)],
            ["Permissible Shear (N/mm²)", _fmt2(r.perm_shear)],
            ["Punching Shear (N/mm²)", _fmt2(r.punching_shear)],
            ["Local Bond (N/mm²)", _fmt2(r.local_bond)],
            ["Permissible Bond (N/mm²)", _fmt2(r.perm_bond)],
        ]
        self.results_area.addWidget(_make_table(hdrs, rows))

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()


# ── Continuous Beam Page ────────────────────────────────────────
class ContinuousBeamPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(_header_label("Continuous Beam Analysis — BS 8110"))

        g1 = QGroupBox("Supports & End Conditions")
        g1.setStyleSheet(f"QGroupBox {{ color: {ACCENT}; font-weight: bold; border: 1px solid {BORDER}; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}")
        f1 = QFormLayout(g1)
        self.cb_ns = _sp(2, 10, 3)
        self.cb_nm = _sp(1, 9, 2)
        self.cb_end1 = _combo(["Pinned", "Fixed"])
        self.cb_end2 = _combo(["Pinned", "Fixed"])
        self.cb_nm.valueChanged.connect(self._sync_members)
        f1.addRow("Number of Supports:", self.cb_ns)
        f1.addRow("Number of Members:", self.cb_nm)
        f1.addRow("Left End:", self.cb_end1)
        f1.addRow("Right End:", self.cb_end2)

        g2 = QGroupBox("Member Data")
        g2.setStyleSheet(g1.styleSheet())
        self.member_grid = QGridLayout(g2)
        self.member_grid.setSpacing(6)
        self._cb_member_widgets = []

        self.calc_btn = _btn("Analyze Beam")
        self.calc_btn.clicked.connect(self._calculate)
        self.results_area = QVBoxLayout()

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(self.calc_btn)
        layout.addLayout(self.results_area)
        layout.addStretch()

        self._sync_members()

    def _sync_members(self):
        nm = self.cb_nm.value()
        while len(self._cb_member_widgets) < nm:
            row = len(self._cb_member_widgets) + 1
            label = QLabel(f"M{row}")
            label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: bold; font-size: 12px;")
            length = _sb(1, 50, 0.5, 5, 2, " m")
            inertia = _sb(0.0001, 10, 0.001, 0.001, 4)
            e_mod = _sb(0.1, 10, 0.1, 1, 1)
            udl = _sb(0, 500, 5, 0, 1, " kN/m")
            wt = _sb(0, 200, 5, 0, 1)
            wb = _sb(0, 200, 5, 0, 1)
            ab = _sb(0, 10, 0.5, 0, 2)
            self.member_grid.addWidget(label, row, 0)
            self.member_grid.addWidget(length, row, 1)
            self.member_grid.addWidget(inertia, row, 2)
            self.member_grid.addWidget(e_mod, row, 3)
            self.member_grid.addWidget(udl, row, 4)
            self.member_grid.addWidget(wt, row, 5)
            self.member_grid.addWidget(wb, row, 6)
            self.member_grid.addWidget(ab, row, 7)
            self._cb_member_widgets.append((label, length, inertia, e_mod, udl, wt, wb, ab))

        headers = ["", "L (m)", "I (m⁴)", "E-rel", "UDL", "Tri", "Trap", "Dist"]
        for col, h in enumerate(headers):
            self.member_grid.addWidget(_label(h, secondary=True, size=11), 0, col)

    def _calculate(self):
        self._clear_results()
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
        beam = ContinuousBeamInput(
            n_supports=self.cb_ns.value(),
            n_members=nm,
            members=members,
            end1_type=self.cb_end1.currentIndex(),
            end2_type=self.cb_end2.currentIndex(),
        )
        analyzer = ContinuousBeamAnalyzer()
        r = analyzer.analyze(beam)

        if r.support_moments:
            hdrs = ["Support", "Moment (kN·m)", "Reaction (kN)"]
            rows = []
            for i, (m, re) in enumerate(zip(r.support_moments, r.support_reactions)):
                rows.append([f"Sup {i+1}", _fmt2(m), _fmt2(re)])
            self.results_area.addWidget(_label("Support Results", bold=True, size=14))
            self.results_area.addWidget(_make_table(hdrs, rows))

        if r.span_moments:
            hdrs2 = ["Span", "M (kN·m)", "Shear L (kN)", "Shear R (kN)"]
            rows2 = []
            for i, (m, sl, sr) in enumerate(zip(r.span_moments, r.span_shear_left, r.span_shear_right)):
                rows2.append([f"Span {i+1}", _fmt2(m), _fmt2(sl), _fmt2(sr)])
            self.results_area.addWidget(_label("Span Results", bold=True, size=14))
            self.results_area.addWidget(_make_table(hdrs2, rows2))

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()


# ═══════════════════════════════════════════════════════════════════
# Main Window
# ═══════════════════════════════════════════════════════════════════

MODULES = [
    ("Column Design", ColumnPage, "c"),
    ("Beam Design", BeamPage, "b"),
    ("Slab Design", SlabPage, "s"),
    ("Stair Design", StairPage, "t"),
    ("Foundation Design", BasePage, "f"),
    ("Continuous Beam", ContinuousBeamPage, "n"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"RCD2000 v{__version__} — BS 8110 Design")
        self.setMinimumSize(1000, 720)
        self._setup_stylesheet()
        self._setup_ui()

    def _setup_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG_DARK}; }}
            QWidget {{ background: {BG_DARK}; color: {TEXT_PRIMARY};
                       font-family: 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
            QScrollBar:vertical {{ background: {BG_MID}; width: 8px; border: none; }}
            QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QGroupBox {{ font-size: 13px; }}
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # ── Header / logo bar (top across entire window) ──
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background: {BG_MID}; border-bottom: 1px solid {BORDER};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        # Logo
        logo_label = QLabel()
        pix = QPixmap("logo.svg")
        if not pix.isNull():
            logo_label.setPixmap(pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_label.setText("RCD")
            logo_label.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: bold;")
        logo_label.setFixedSize(40, 40)
        header_layout.addWidget(logo_label)

        title_label = QLabel("RCD2000")
        title_label.setStyleSheet(f"color: {ACCENT}; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)

        subtitle = QLabel("Reinforced Concrete Design to BS 8110")
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; padding-left: 4px;")
        header_layout.addWidget(subtitle)
        header_layout.addStretch()

        # ── Splitter: sidebar | pages ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet(f"background: {SIDEBAR_BG}; border-right: 1px solid {BORDER};")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 12, 0, 12)
        sb_layout.setSpacing(2)

        sb_label = QLabel("Design Modules")
        sb_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold; padding: 4px 16px; letter-spacing: 1px;")
        sb_layout.addWidget(sb_label)

        self.sidebar_list = QListWidget()
        self.sidebar_list.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; font-size: 13px; }}
            QListWidget::item {{ padding: 10px 16px; color: {TEXT_SECONDARY};
                                border-left: 3px solid transparent; }}
            QListWidget::item:hover {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY}; }}
            QListWidget::item:selected {{ background: {BG_LIGHT}; color: {ACCENT};
                                          border-left: 3px solid {ACCENT}; }}
        """)
        icons_map = {"c": "⬡", "b": "━", "s": "▦", "t": "╱", "f": "▤", "n": "≡"}
        for name, _, key in MODULES:
            self.sidebar_list.addItem(f"  {icons_map.get(key, '•')}  {name}")
        self.sidebar_list.setCurrentRow(0)
        sb_layout.addWidget(self.sidebar_list)

        # Pages stack
        pages_container = QWidget()
        pages_container.setStyleSheet(f"background: {BG_DARK};")
        pages_layout = QVBoxLayout(pages_container)
        pages_layout.setContentsMargins(0, 0, 0, 0)
        pages_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.pages = []
        for _, page_class, _ in MODULES:
            page = page_class()
            scroll = QScrollArea()
            scroll.setWidget(page)
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(f"QScrollArea {{ background: {BG_DARK}; border: none; }}")
            self.stack.addWidget(scroll)
            self.pages.append(page)

        pages_layout.addWidget(self.stack)

        splitter.addWidget(sidebar)
        splitter.addWidget(pages_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Main vertical layout: header + splitter
        main_v = QVBoxLayout()
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.setSpacing(0)
        main_v.addWidget(header)
        main_v.addWidget(splitter)
        h_layout.addLayout(main_v)

        self.sidebar_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        # Status bar
        self.status = QStatusBar()
        self.status.setStyleSheet(f"background: {BG_MID}; color: {TEXT_SECONDARY}; border-top: 1px solid {BORDER}; font-size: 11px; padding: 2px 8px;")
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RCD2000")
    app.setApplicationVersion(__version__)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
