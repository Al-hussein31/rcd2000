"""Reusable widget factories for the RCD2000 GUI."""

from PySide6.QtWidgets import (
    QDoubleSpinBox, QSpinBox, QComboBox, QPushButton, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt

from rcd2000.gui.theme import (
    BG_LIGHT, BG_MID, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT,
    ACCENT_HOVER, BORDER, TABLE_HEADER, TABLE_ALT,
)


def spinbox(min_v=0.0, max_v=999999.0, step=1.0, default=0.0, decimals=1, suffix="") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(min_v, max_v)
    s.setSingleStep(step)
    s.setValue(default)
    s.setDecimals(decimals)
    if suffix:
        s.setSuffix(suffix)
    s.setStyleSheet(
        f"QDoubleSpinBox {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
        f"  border: 1px solid {BORDER}; border-radius: 4px;"
        f"  padding: 4px 8px; font-size: 13px; }}"
        f"QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}"
    )
    return s


def spin_int(min_v=0, max_v=9999, default=0) -> QSpinBox:
    s = QSpinBox()
    s.setRange(min_v, max_v)
    s.setValue(default)
    s.setStyleSheet(
        f"QSpinBox {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
        f"  border: 1px solid {BORDER}; border-radius: 4px;"
        f"  padding: 4px 8px; font-size: 13px; }}"
        f"QSpinBox:focus {{ border-color: {ACCENT}; }}"
    )
    return s


def combo(items: list) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    c.setStyleSheet(
        f"QComboBox {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
        f"  border: 1px solid {BORDER}; border-radius: 4px;"
        f"  padding: 4px 8px; font-size: 13px; }}"
        f"QComboBox:hover {{ border-color: {ACCENT}; }}"
        f"QComboBox::drop-down {{ border: none; }}"
        f"QComboBox QAbstractItemView {{ background: {BG_MID}; color: {TEXT_PRIMARY};"
        f"  selection-background-color: {ACCENT}; }}"
    )
    return c


def button(text: str, accent: bool = True) -> QPushButton:
    b = QPushButton(text)
    if accent:
        b.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #fff; font-weight: bold;"
            f"  border: none; border-radius: 6px; padding: 10px 32px; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
            f"QPushButton:pressed {{ background: #b07220; }}"
        )
    else:
        b.setStyleSheet(
            f"QPushButton {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f"  border: 1px solid {BORDER}; border-radius: 6px;"
            f"  padding: 8px 24px; font-size: 13px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
        )
    return b


def label(text: str, bold=False, secondary=False, size=13) -> QLabel:
    l = QLabel(text)
    color = TEXT_SECONDARY if secondary else TEXT_PRIMARY
    weight = "font-weight: bold;" if bold else ""
    l.setStyleSheet(f"color: {color}; font-size: {size}px; {weight}")
    return l


def header_label(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(f"color: {ACCENT}; font-size: 16px; font-weight: bold; padding: 4px 0;")
    return l


def divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"color: {BORDER};")
    return f


def make_table(headers: list, rows: list[list]) -> QTableWidget:
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.NoSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    for col in range(len(headers)):
        t.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignCenter)
            t.setItem(r, c, item)
    t.setStyleSheet(
        f"QTableWidget {{ background: {BG_MID}; color: {TEXT_PRIMARY};"
        f"  border: 1px solid {BORDER}; border-radius: 4px;"
        f"  font-size: 12px; gridline-color: {BORDER}; }}"
        f"QTableWidget::item {{ padding: 4px 8px; }}"
        f"QTableWidget::item:alternate {{ background: {TABLE_ALT}; }}"
        f"QHeaderView::section {{ background: {TABLE_HEADER}; color: {ACCENT};"
        f"  font-weight: bold; padding: 6px 8px;"
        f"  border: none; font-size: 12px; }}"
    )
    t.setMinimumHeight(min(len(rows) * 28 + 30, 300))
    return t
