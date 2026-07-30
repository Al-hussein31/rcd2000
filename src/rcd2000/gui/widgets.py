"""Reusable widget factories for the RCD2000 GUI."""

from PySide6.QtWidgets import (
    QDoubleSpinBox, QSpinBox, QComboBox, QPushButton, QLabel,
    QFrame, QVBoxLayout, QHBoxLayout, QProgressBar, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF, QFont

from rcd2000.gui.theme import (
    BG_DARK, BG_MID, BG_LIGHT, BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT, ACCENT_HOVER, ACCENT_MUTED, BORDER, CARD_STYLE, RADIUS_SM, RADIUS_MD,
    SUCCESS, SUCCESS_BG, ERROR, ERROR_BG, WARNING, WARNING_BG, TEXT_MUTED,
    FONT_FAMILY, PAINTER_FONT,
)


# ═══════════════════════════════════════════════════════════════════
# Validated spinboxes
# ═══════════════════════════════════════════════════════════════════

def _base_spin_style(invalid: bool = False) -> str:
    border = ERROR if invalid else BORDER
    return (
        f"background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
        f" border: 1px solid {border}; border-radius: {RADIUS_SM}px;"
        f" padding: 4px 8px; font-size: 13px;"
    )


def spinbox(
    min_v=0.0, max_v=999999.0, step=1.0, default=0.0,
    decimals=1, suffix="",
) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(min_v, max_v)
    s.setSingleStep(step)
    s.setValue(default)
    s.setDecimals(decimals)
    if suffix:
        s.setSuffix(suffix)
    s.setProperty("invalid", False)
    s.setStyleSheet(
        f"QDoubleSpinBox {{ {_base_spin_style()} }}"
        f"QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}"
        f"QDoubleSpinBox[invalid=\"true\"] {{ border-color: {ERROR}; }}"
    )
    return s


def spin_int(min_v=0, max_v=9999, default=0) -> QSpinBox:
    s = QSpinBox()
    s.setRange(min_v, max_v)
    s.setValue(default)
    s.setProperty("invalid", False)
    s.setStyleSheet(
        f"QSpinBox {{ {_base_spin_style()} }}"
        f"QSpinBox:focus {{ border-color: {ACCENT}; }}"
        f"QSpinBox[invalid=\"true\"] {{ border-color: {ERROR}; }}"
    )
    return s


def mark_invalid(widget, flag: bool = True):
    widget.setProperty("invalid", flag)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# ═══════════════════════════════════════════════════════════════════
# Material / standard combos
# ═══════════════════════════════════════════════════════════════════

def _combo_style() -> str:
    return (
        f"QComboBox {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
        f"  border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px;"
        f"  padding: 4px 8px; font-size: 13px; min-width: 80px; }}"
        f"QComboBox:hover {{ border-color: {ACCENT}; }}"
        f"QComboBox:focus {{ border-color: {ACCENT}; }}"
        f"QComboBox::drop-down {{ border: none; width: 24px; }}"
        f"QComboBox::down-arrow {{ image: none; }}"
        f"QComboBox QAbstractItemView {{ background: {BG_MID}; color: {TEXT_PRIMARY};"
        f"  selection-background-color: {ACCENT}; border: 1px solid {BORDER};"
        f"  border-radius: {RADIUS_SM}px; outline: none; }}"
    )


def combo(items: list) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    c.setStyleSheet(_combo_style())
    return c


def material_combo(values: list) -> QComboBox:
    c = QComboBox()
    c.addItems([str(v) for v in values])
    c.setEditable(False)
    c.setCurrentIndex(0)
    c.setStyleSheet(_combo_style())
    return c


def fcu_combo() -> QComboBox:
    return material_combo([20, 25, 30, 35, 40, 45, 50])


def fy_combo() -> QComboBox:
    return material_combo([250, 410, 460, 500])


# ═══════════════════════════════════════════════════════════════════
# Buttons
# ═══════════════════════════════════════════════════════════════════

def button(text: str, accent: bool = True) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    if accent:
        b.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #fff; font-weight: bold;"
            f"  border: none; border-radius: {RADIUS_MD}px; padding: 10px 32px;"
            f"  font-size: 14px; }}"
            f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
            f"QPushButton:pressed {{ background: #b07220; }}"
            f"QPushButton:disabled {{ background: {BORDER}; color: {TEXT_MUTED}; }}"
        )
    else:
        b.setStyleSheet(
            f"QPushButton {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f"  border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;"
            f"  padding: 8px 24px; font-size: 13px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
            f"QPushButton:disabled {{ color: {TEXT_MUTED}; }}"
        )
    return b


# ═══════════════════════════════════════════════════════════════════
# Labels
# ═══════════════════════════════════════════════════════════════════

def label(text: str, bold=False, secondary=False, size=13) -> QLabel:
    l = QLabel(text)
    color = TEXT_SECONDARY if secondary else TEXT_PRIMARY
    weight = "font-weight: bold;" if bold else ""
    l.setStyleSheet(f"color: {color}; font-size: {size}px; {weight} background: transparent;")
    return l


def header_label(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"color: {ACCENT}; font-size: 18px; font-weight: bold; padding: 4px 0; background: transparent;"
    )
    return l


def divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"color: {BORDER}; background: {BORDER}; max-height: 1px;")
    return f


# ═══════════════════════════════════════════════════════════════════
# Card
# ═══════════════════════════════════════════════════════════════════

class Card(QFrame):
    """Styled card with optional title and content area."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)
        if title:
            self._title_lbl = QLabel(title)
            self._title_lbl.setStyleSheet(
                f"color: {ACCENT}; font-weight: bold; font-size: 14px; background: transparent;"
            )
            self._layout.addWidget(self._title_lbl)

    def add_row(self, form_label: str, widget):
        """Convenience: QHBoxLayout label + widget row."""
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = QLabel(form_label)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; background: transparent; min-width: 140px;")
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        self._layout.addLayout(row)

    def add_layout(self, layout):
        self._layout.addLayout(layout)

    def add_widget(self, widget):
        self._layout.addWidget(widget)

    def content(self):
        return self._layout


# ═══════════════════════════════════════════════════════════════════
# PASS/FAIL badge
# ═══════════════════════════════════════════════════════════════════

def badge(ok: bool, text: str = "") -> QLabel:
    t = text if text else ("PASS" if ok else "FAIL")
    lbl = QLabel(t)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFixedHeight(22)
    if ok:
        lbl.setStyleSheet(
            f"background: {SUCCESS_BG}; color: {SUCCESS}; font-weight: bold;"
            f" border-radius: 11px; padding: 2px 12px; font-size: 11px;"
        )
    else:
        lbl.setStyleSheet(
            f"background: {ERROR_BG}; color: {ERROR}; font-weight: bold;"
            f" border-radius: 11px; padding: 2px 12px; font-size: 11px;"
        )
    return lbl


# ═══════════════════════════════════════════════════════════════════
# Utilization bar
# ═══════════════════════════════════════════════════════════════════

def util_bar(value: float, max_val: float, text: str = "") -> QProgressBar:
    bar = QProgressBar()
    bar.setRange(0, int(max_val * 100))
    bar.setValue(int(value * 100))
    bar.setTextVisible(True)
    ratio = value / max_val if max_val else 0
    if ratio < 0.5:
        color = SUCCESS
    elif ratio < 0.8:
        color = ACCENT
    else:
        color = ERROR
    bar.setFormat(text if text else f"{ratio:.0%}")
    bar.setStyleSheet(
        f"QProgressBar {{ background: {BG_LIGHT}; border: 1px solid {BORDER};"
        f"  border-radius: 4px; height: 20px; text-align: center;"
        f"  color: {TEXT_PRIMARY}; font-size: 11px; }}"
        f"QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}"
    )
    return bar


# ═══════════════════════════════════════════════════════════════════
# Load combination widget
# ═══════════════════════════════════════════════════════════════════

def load_combo_group(gk_default=0.0, qk_default=0.0) -> QWidget:
    """Returns a widget with Gk, Qk spinboxes + auto-factored result.
    
    Returns:
        tuple: (widget, gk_spinbox, qk_spinbox, result_label)
    """
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    gk_row = QHBoxLayout()
    gk_lbl = label("Gk (dead):", secondary=True, size=12)
    gk_lbl.setFixedWidth(80)
    gk_spin = spinbox(0, 500, 1, gk_default, 1, " kN/m²")
    gk_row.addWidget(gk_lbl)
    gk_row.addWidget(gk_spin, 1)

    qk_row = QHBoxLayout()
    qk_lbl = label("Qk (imposed):", secondary=True, size=12)
    qk_lbl.setFixedWidth(80)
    qk_spin = spinbox(0, 500, 1, qk_default, 1, " kN/m²")
    qk_row.addWidget(qk_lbl)
    qk_row.addWidget(qk_spin, 1)

    result_lbl = label("Ultimate: 1.4Gk + 1.6Qk = 0.0 kN/m²", secondary=True, size=11)

    def _update():
        gk = gk_spin.value()
        qk = qk_spin.value()
        ult = 1.4 * gk + 1.6 * qk
        result_lbl.setText(
            f"Ultimate: 1.4({gk:.1f}) + 1.6({qk:.1f}) = {ult:.1f} kN/m²"
        )

    gk_spin.valueChanged.connect(_update)
    qk_spin.valueChanged.connect(_update)
    _update()

    layout.addLayout(gk_row)
    layout.addLayout(qk_row)
    layout.addWidget(result_lbl)

    return w, gk_spin, qk_spin, result_lbl


# ═══════════════════════════════════════════════════════════════════
# Tables
# ═══════════════════════════════════════════════════════════════════

def make_table(headers: list, rows: list[list]) -> QTableWidget:
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.NoSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    for col in range(1, len(headers)):
        t.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignCenter)
            if isinstance(val, QLabel):
                t.setCellWidget(r, c, val)
            else:
                t.setItem(r, c, item)
    t.setStyleSheet(
        f"QTableWidget {{ background: {BG_MID}; color: {TEXT_PRIMARY};"
        f"  border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px;"
        f"  font-size: 12px; gridline-color: {BORDER}; }}"
        f"QTableWidget::item {{ padding: 4px 8px; }}"
        f"QTableWidget::item:alternate {{ background: {BG_CARD}; }}"
        f"QHeaderView::section {{ background: {BG_DARK}; color: {ACCENT};"
        f"  font-weight: bold; padding: 6px 8px;"
        f"  border: none; font-size: 12px; }}"
    )
    h = min(len(rows) * 28 + 30, 300)
    t.setMinimumHeight(h)
    return t


# ═══════════════════════════════════════════════════════════════════
# Multi-span diagram
# ═══════════════════════════════════════════════════════════════════

class SpanDiagram(QWidget):
    """Draws a horizontal multi-span beam diagram."""

    def __init__(self, spans=None, parent=None):
        super().__init__(parent)
        self.spans = spans or []
        self.setMinimumHeight(110)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent;")

    def set_spans(self, spans: list):
        self.spans = spans
        self.update()

    def paintEvent(self, event):
        if not self.spans:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        try:
            self._do_paint(painter)
        finally:
            painter.end()

    def _do_paint(self, painter):
        w = self.width()
        h = self.height()
        pad = 24
        y_beam = int(h * 0.45)
        beam_h = 18
        total_len = max(sum(s.get("length", 1) for s in self.spans), 0.1)
        usable = w - 2 * pad

        x = pad
        for i, span in enumerate(self.spans):
            span_w = max(30, usable * span.get("length", 1) / total_len)

            # Beam rectangle
            painter.setBrush(QColor(BG_CARD))
            painter.setPen(QPen(QColor(ACCENT), 1))
            rect = QRectF(x, y_beam, span_w, beam_h)
            painter.drawRoundedRect(rect, 3, 3)

            # Span label above
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.setFont(QFont(PAINTER_FONT, 10, QFont.Bold))
            painter.drawText(QRectF(x, y_beam - 20, span_w, 16), Qt.AlignCenter, f"S{i+1}")

            # Length below
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.setFont(QFont(PAINTER_FONT, 9))
            lbl = f'{span.get("length", 0):.1f}m'
            if span.get("udl", 0):
                lbl += f' / {span["udl"]:.0f} kN/m'
            painter.drawText(QRectF(x, y_beam + beam_h + 2, span_w, 16), Qt.AlignCenter, lbl)

            x += span_w

        # First support
        sx = pad
        painter.setBrush(QColor(ACCENT))
        painter.setPen(QPen(QColor(ACCENT_MUTED), 1))
        tri = QPolygonF([
            QRectF(sx - 6, y_beam + beam_h, 0, 0).topLeft(),
            QRectF(sx + 6, y_beam + beam_h, 0, 0).topLeft(),
            QRectF(sx, y_beam + beam_h + 14, 0, 0).topLeft(),
        ])
        painter.drawPolygon(tri)

        # Intermediate supports
        x = pad
        for i, span in enumerate(self.spans):
            span_w = max(30, usable * span.get("length", 1) / total_len)
            if i < len(self.spans) - 1:
                sx = x + span_w
                painter.setBrush(QColor(ACCENT))
                painter.setPen(QPen(QColor(ACCENT_MUTED), 1))
                tri = QPolygonF([
                    QRectF(sx - 6, y_beam + beam_h, 0, 0).topLeft(),
                    QRectF(sx + 6, y_beam + beam_h, 0, 0).topLeft(),
                    QRectF(sx, y_beam + beam_h + 14, 0, 0).topLeft(),
                ])
                painter.drawPolygon(tri)
            x += span_w

        # Last support
        sx = x
        painter.setBrush(QColor(ACCENT))
        painter.setPen(QPen(QColor(ACCENT_MUTED), 1))
        tri = QPolygonF([
            QRectF(sx - 6, y_beam + beam_h, 0, 0).topLeft(),
            QRectF(sx + 6, y_beam + beam_h, 0, 0).topLeft(),
            QRectF(sx, y_beam + beam_h + 14, 0, 0).topLeft(),
        ])
        painter.drawPolygon(tri)
