"""Main window and application entry point."""

import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QScrollArea, QSplitter,
    QStatusBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from rcd2000 import __version__
from rcd2000.gui.theme import BG_DARK, BG_MID, BG_LIGHT, SIDEBAR_BG, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, BORDER
from rcd2000.gui.pages import (
    ColumnPage, BeamPage, SlabPage, StairPage, BasePage, ContinuousBeamPage,
)

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

        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background: {BG_MID}; border-bottom: 1px solid {BORDER};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

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

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

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
        icons_map = {"c": "\u2b21", "b": "\u2501", "s": "\u25a6", "t": "\u2571", "f": "\u25a4", "n": "\u2261"}
        for name, _, key in MODULES:
            self.sidebar_list.addItem(f"  {icons_map.get(key, '\u2022')}  {name}")
        self.sidebar_list.setCurrentRow(0)
        sb_layout.addWidget(self.sidebar_list)

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

        main_v = QVBoxLayout()
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.setSpacing(0)
        main_v.addWidget(header)
        main_v.addWidget(splitter)
        h_layout.addLayout(main_v)

        self.sidebar_list.currentRowChanged.connect(self.stack.setCurrentIndex)

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
