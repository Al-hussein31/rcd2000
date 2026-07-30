"""Reusable widget factories for the RCD2000 GUI.

API-compatible with the previous version — every function page files
already import (spinbox, combo, button, Card, make_table, etc.) keeps
the same name and signature. Only the visuals underneath changed, so
existing pages get the refresh for free.
"""

from PySide6.QtWidgets import (
    QDoubleSpinBox, QSpinBox, QComboBox, QPushButton, QLabel,
    QFrame, QVBoxLayout, QHBoxLayout, QProgressBar, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSizePolicy, QToolButton,
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF, QFont

try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False

from rcd2000.gui.theme import (
    BG_DARK, BG_MID, BG_LIGHT, BG_CARD, BG_CARD_ALT, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT, ACCENT_HOVER, ACCENT_PRESS, ACCENT_MUTED, ACCENT_SOFT, ACCENT_SOFT_BORDER,
    BORDER, BORDER_LIGHT, CARD_STYLE, RADIUS_SM, RADIUS_MD, RADIUS_LG,
    SUCCESS, SUCCESS_BG, ERROR, ERROR_BG, WARNING, WARNING_BG, TEXT_MUTED,
    FONT_FAMILY, PAINTER_FONT, FONT_SIZE, SPACE,
)


def icon(name: str, color: str = TEXT_SECONDARY, size: int = 16):
    """Return a QIcon via qtawesome if available, else None (caller falls
    back to a text glyph). Keeps the app usable even without the dep."""
    if not _HAS_QTA:
        return None
    try:
        return qta.icon(name, color=color)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
# Validated spinboxes
# ═══════════════════════════════════════════════════════════════════

def _base_spin_style(invalid: bool = False) -> str:
    border = ERROR if invalid else BORDER
    return (
        f"background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
        f" border: 1px solid {border}; border-radius: {RADIUS_SM}px;"
        f" padding: 6px 10px; font-size: {FONT_SIZE['base']}px;"
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
    s.setMinimumHeight(30)
    s.setStyleSheet(
        f"QDoubleSpinBox {{ {_base_spin_style()} }}"
        f"QDoubleSpinBox:hover {{ border-color: {BORDER_LIGHT}; }}"
        f"QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}"
        f"QDoubleSpinBox[invalid=\"true\"] {{ border-color: {ERROR}; }}"
    )
    return s


def spin_int(min_v=0, max_v=9999, default=0) -> QSpinBox:
    s = QSpinBox()
    s.setRange(min_v, max_v)
    s.setValue(default)
    s.setProperty("invalid", False)
    s.setMinimumHeight(30)
    s.setStyleSheet(
        f"QSpinBox {{ {_base_spin_style()} }}"
        f"QSpinBox:hover {{ border-color: {BORDER_LIGHT}; }}"
        f"QSpinBox:focus {{ border-color: {ACCENT}; }}"
        f"QSpinBox[invalid=\"true\"] {{ border-color: {ERROR}; }}"
    )
    return s


def mark_invalid(widget, flag: bool = True):
    """Toggle the red-border invalid state. Call this from input
    validation to actually surface bad values to the user."""
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
        f"  padding: 6px 10px; font-size: {FONT_SIZE['base']}px; min-width: 80px; }}"
        f"QComboBox:hover {{ border-color: {BORDER_LIGHT}; }}"
        f"QComboBox:focus {{ border-color: {ACCENT}; }}"
        f"QComboBox::drop-down {{ border: none; width: 26px; }}"
        f"QComboBox::down-arrow {{ image: none; border-left: 4px solid transparent;"
        f"  border-right: 4px solid transparent; border-top: 5px solid {TEXT_SECONDARY};"
        f"  width: 0; height: 0; margin-right: 8px; }}"
        f"QComboBox QAbstractItemView {{ background: {BG_MID}; color: {TEXT_PRIMARY};"
        f"  selection-background-color: {ACCENT_SOFT}; selection-color: {ACCENT};"
        f"  border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px; outline: none;"
        f"  padding: 4px; }}"
    )


def combo(items: list) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    c.setMinimumHeight(30)
    c.setStyleSheet(_combo_style())
    return c


def material_combo(values: list) -> QComboBox:
    c = QComboBox()
    c.addItems([str(v) for v in values])
    c.setEditable(False)
    c.setCurrentIndex(0)
    c.setMinimumHeight(30)
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
    b.setMinimumHeight(38)
    if accent:
        b.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #17140F; font-weight: 600;"
            f"  border: none; border-radius: {RADIUS_MD}px; padding: 9px 28px;"
            f"  font-size: {FONT_SIZE['md']}px; }}"
            f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
            f"QPushButton:pressed {{ background: {ACCENT_PRESS}; }}"
            f"QPushButton:disabled {{ background: {BORDER}; color: {TEXT_MUTED}; }}"
        )
    else:
        b.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_PRIMARY};"
            f"  border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;"
            f"  padding: 8px 22px; font-size: {FONT_SIZE['base']}px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
            f"QPushButton:disabled {{ color: {TEXT_MUTED}; border-color: {BORDER}; }}"
        )
    return b


# ═══════════════════════════════════════════════════════════════════
# Labels
# ═══════════════════════════════════════════════════════════════════

def label(text: str, bold=False, secondary=False, size=13) -> QLabel:
    l = QLabel(text)
    color = TEXT_SECONDARY if secondary else TEXT_PRIMARY
    weight = "font-weight: 600;" if bold else ""
    l.setStyleSheet(f"color: {color}; font-size: {size}px; {weight} background: transparent;")
    return l


def header_label(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE['xxl']}px; font-weight: 700;"
        f" padding: 2px 0 {SPACE[2]}px 0; background: transparent;"
    )
    return l


def divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"color: {BORDER}; background: {BORDER}; max-height: 1px; border: none;")
    return f


# ═══════════════════════════════════════════════════════════════════
# Card — flat surface, subtle border (color reserved for real signals)
# ═══════════════════════════════════════════════════════════════════

class Card(QFrame):
    """Styled card with optional title and content area."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(SPACE[5], SPACE[4], SPACE[5], SPACE[4])
        self._layout.setSpacing(SPACE[3])
        if title:
            self._title_lbl = QLabel(title)
            self._title_lbl.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-weight: 600; font-size: {FONT_SIZE['md']}px;"
                f" background: transparent; letter-spacing: 0.2px;"
            )
            self._layout.addWidget(self._title_lbl)
            self._layout.addSpacing(2)

    def add_row(self, form_label: str, widget):
        row = QHBoxLayout()
        row.setSpacing(SPACE[3])
        lbl = QLabel(form_label)
        lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['base']}px;"
            f" background: transparent; min-width: 150px;"
        )
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
# Collapsible section — click header to expand/collapse, no animation
# (per design brief: clear and instant beats flashy motion)
# ═══════════════════════════════════════════════════════════════════

class CollapsibleSection(QWidget):
    """A titled section whose body can be toggled open/closed by
    clicking the header. Use for sidebar history, optional advanced
    inputs, etc. Starts expanded by default."""

    def __init__(self, title: str, content: QWidget, expanded: bool = True, parent=None):
        super().__init__(parent)
        self._expanded = expanded
        self._content = content

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._header = QToolButton()
        self._header.setText(title)
        self._header.setCursor(Qt.PointingHandCursor)
        self._header.setCheckable(True)
        self._header.setChecked(expanded)
        self._header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._header.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self._header.setStyleSheet(
            f"QToolButton {{ background: transparent; color: {TEXT_MUTED};"
            f"  border: none; font-size: {FONT_SIZE['xs']}px; font-weight: 700;"
            f"  letter-spacing: 0.6px; padding: {SPACE[2]}px {SPACE[4]}px; text-align: left; }}"
            f"QToolButton:hover {{ color: {TEXT_SECONDARY}; }}"
        )
        self._header.clicked.connect(self._toggle)

        outer.addWidget(self._header)
        outer.addWidget(self._content)
        self._content.setVisible(expanded)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._header.setArrowType(Qt.DownArrow if self._expanded else Qt.RightArrow)

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._header.setChecked(expanded)
        self._content.setVisible(expanded)
        self._header.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)


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
            f"background: {SUCCESS_BG}; color: {SUCCESS}; font-weight: 600;"
            f" border-radius: 11px; padding: 2px 12px; font-size: {FONT_SIZE['xs']}px;"
        )
    else:
        lbl.setStyleSheet(
            f"background: {ERROR_BG}; color: {ERROR}; font-weight: 600;"
            f" border-radius: 11px; padding: 2px 12px; font-size: {FONT_SIZE['xs']}px;"
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
        f"  color: {TEXT_PRIMARY}; font-size: {FONT_SIZE['xs']}px; }}"
        f"QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}"
    )
    return bar


# ═══════════════════════════════════════════════════════════════════
# Load combination widget
# ═══════════════════════════════════════════════════════════════════

def load_combo_group(gk_default=0.0, qk_default=0.0):
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACE[2])

    gk_row = QHBoxLayout()
    gk_lbl = label("Gk (dead):", secondary=True, size=FONT_SIZE["sm"])
    gk_lbl.setFixedWidth(90)
    gk_spin = spinbox(0, 500, 1, gk_default, 1, " kN/m²")
    gk_row.addWidget(gk_lbl)
    gk_row.addWidget(gk_spin, 1)

    qk_row = QHBoxLayout()
    qk_lbl = label("Qk (imposed):", secondary=True, size=FONT_SIZE["sm"])
    qk_lbl.setFixedWidth(90)
    qk_spin = spinbox(0, 500, 1, qk_default, 1, " kN/m²")
    qk_row.addWidget(qk_lbl)
    qk_row.addWidget(qk_spin, 1)

    result_lbl = label("Ultimate: 1.4Gk + 1.6Qk = 0.0 kN/m²", secondary=True, size=FONT_SIZE["xs"])
    result_lbl.setStyleSheet(
        result_lbl.styleSheet() + f"padding: {SPACE[1]}px {SPACE[2]}px; background: {ACCENT_SOFT};"
        f" border-radius: {RADIUS_SM}px;"
    )

    def _update():
        gk = gk_spin.value()
        qk = qk_spin.value()
        ult = 1.4 * gk + 1.6 * qk
        result_lbl.setText(f"Ultimate: 1.4({gk:.1f}) + 1.6({qk:.1f}) = {ult:.1f} kN/m²")

    gk_spin.valueChanged.connect(_update)
    qk_spin.valueChanged.connect(_update)
    _update()

    layout.addLayout(gk_row)
    layout.addLayout(qk_row)
    layout.addWidget(result_lbl)

    return w, gk_spin, qk_spin, result_lbl


# ═══════════════════════════════════════════════════════════════════
# Results panel — replaces QTableWidget with a lighter, on-brand
# label/value/status layout (your data isn't spreadsheet data, so it
# shouldn't carry a spreadsheet widget's weight or default chrome).
# ═══════════════════════════════════════════════════════════════════

def make_table(headers: list, rows: list) -> QWidget:
    """Kept the same name/signature as before so existing pages need
    zero changes — but now builds a lightweight custom panel instead
    of QTableWidget, which is faster to render and easier to theme
    consistently with the rest of the app."""
    panel = QFrame()
    panel.setStyleSheet(
        f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;"
    )
    outer = QVBoxLayout(panel)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    # Header
    head = QFrame()
    head.setStyleSheet(f"background: {BG_MID}; border-top-left-radius: {RADIUS_MD}px;"
                        f" border-top-right-radius: {RADIUS_MD}px; border: none;")
    head_l = QHBoxLayout(head)
    head_l.setContentsMargins(SPACE[4], SPACE[2], SPACE[4], SPACE[2])
    n = max(len(headers), 1)
    for i, h in enumerate(headers):
        lbl = QLabel(h)
        stretch = 2 if i == 0 else 1
        align = Qt.AlignLeft if i == 0 else Qt.AlignCenter
        lbl.setAlignment(align | Qt.AlignVCenter)
        lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-weight: 700; font-size: {FONT_SIZE['xs']}px;"
            f" background: transparent; letter-spacing: 0.4px;"
        )
        head_l.addWidget(lbl, stretch)
    outer.addWidget(head)

    # Rows
    for r, row in enumerate(rows):
        row_frame = QFrame()
        bg = BG_CARD_ALT if r % 2 else BG_CARD
        row_frame.setStyleSheet(f"background: {bg}; border: none;")
        row_l = QHBoxLayout(row_frame)
        row_l.setContentsMargins(SPACE[4], SPACE[2] + 2, SPACE[4], SPACE[2] + 2)
        for c, val in enumerate(row):
            stretch = 2 if c == 0 else 1
            align = Qt.AlignLeft if c == 0 else Qt.AlignCenter
            if isinstance(val, QWidget):
                cell = QWidget()
                cell_l = QHBoxLayout(cell)
                cell_l.setContentsMargins(0, 0, 0, 0)
                cell_l.setAlignment(align | Qt.AlignVCenter)
                cell_l.addWidget(val)
                row_l.addWidget(cell, stretch)
            else:
                lbl = QLabel(str(val) if val != "" else "—")
                lbl.setAlignment(align | Qt.AlignVCenter)
                weight = "font-weight: 600;" if c == 0 else ""
                color = TEXT_PRIMARY if c == 0 else TEXT_SECONDARY
                lbl.setStyleSheet(
                    f"color: {color}; font-size: {FONT_SIZE['base']}px;"
                    f" background: transparent; {weight}"
                )
                row_l.addWidget(lbl, stretch)
        outer.addWidget(row_frame)

    # Round the bottom corners on the very last row via a spacer trick
    outer.addSpacing(1)
    return panel


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

            painter.setBrush(QColor(BG_CARD_ALT))
            painter.setPen(QPen(QColor(ACCENT), 1))
            rect = QRectF(x, y_beam, span_w, beam_h)
            painter.drawRoundedRect(rect, 3, 3)

            painter.setPen(QColor(TEXT_PRIMARY))
            painter.setFont(QFont(PAINTER_FONT, 10, QFont.Bold))
            painter.drawText(QRectF(x, y_beam - 20, span_w, 16), Qt.AlignCenter, f"S{i+1}")

            painter.setPen(QColor(TEXT_SECONDARY))
            painter.setFont(QFont(PAINTER_FONT, 9))
            lbl = f'{span.get("length", 0):.1f}m'
            if span.get("udl", 0):
                lbl += f' / {span["udl"]:.0f} kN/m'
            painter.drawText(QRectF(x, y_beam + beam_h + 2, span_w, 16), Qt.AlignCenter, lbl)

            x += span_w

        def _support(sx):
            painter.setBrush(QColor(ACCENT))
            painter.setPen(QPen(QColor(ACCENT_MUTED), 1))
            tri = QPolygonF([
                QRectF(sx - 6, y_beam + beam_h, 0, 0).topLeft(),
                QRectF(sx + 6, y_beam + beam_h, 0, 0).topLeft(),
                QRectF(sx, y_beam + beam_h + 14, 0, 0).topLeft(),
            ])
            painter.drawPolygon(tri)

        _support(pad)
        x = pad
        for i, span in enumerate(self.spans):
            span_w = max(30, usable * span.get("length", 1) / total_len)
            if i < len(self.spans) - 1:
                _support(x + span_w)
            x += span_w
        _support(x)
