"""Main window and application entry point."""

import sys
import os
from importlib.resources import files

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QScrollArea, QSplitter,
    QStatusBar, QSplashScreen, QDialog, QMenuBar, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon, QAction, QKeySequence, QColor, QFont

from rcd2000 import __version__
from rcd2000.gui.theme import (
    BG_DARK, BG_MID, BG_LIGHT, SIDEBAR_BG, ACCENT, TEXT_PRIMARY,
    TEXT_SECONDARY, BORDER, TEXT_MUTED, BG_CARD,
)
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

SHORTCUT_KEYS = {
    Qt.Key_1: 0, Qt.Key_2: 1, Qt.Key_3: 2,
    Qt.Key_4: 3, Qt.Key_5: 4, Qt.Key_6: 5,
}


def _find_icon(name: str) -> str:
    """Find icon file in gui/icons/ via importlib.resources."""
    try:
        pkg = files("rcd2000.gui.icons")
        return str(pkg.joinpath(name))
    except (ModuleNotFoundError, TypeError):
        # fallback for development
        base = os.path.join(os.path.dirname(__file__), "icons")
        return os.path.join(base, name)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About RCD2000")
        self.setFixedSize(400, 280)
        self.setStyleSheet(f"background: {BG_MID}; color: {TEXT_PRIMARY};")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("RCD2000")
        title.setStyleSheet(
            f"color: {ACCENT}; font-size: 24px; font-weight: bold; background: transparent;"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        ver = QLabel(f"Version {__version__}")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color: #999; font-size: 13px; background: transparent;")
        layout.addWidget(ver)

        desc = QLabel(
            "Reinforced Concrete Design to BS 8110:1997\n"
            "Python port of Oyenuga's RCD2000 FORTRAN programs.\n\n"
            "Engine: Clapeyron three-moment equation, strain compatibility\n"
            "interaction curves, and BS 8110 moment/ shear coefficients."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #ccc; font-size: 12px; background: transparent;")
        layout.addWidget(desc)

        link = QLabel(
            '<a href="https://github.com/Al-hussein31/rcd2000" '
            'style="color: #d48c28;">github.com/Al-hussein31/rcd2000</a>'
        )
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignCenter)
        link.setStyleSheet("background: transparent;")
        layout.addWidget(link)

        btn = QLabel("Press Esc to close")
        btn.setAlignment(Qt.AlignCenter)
        btn.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        layout.addWidget(btn)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.accept()
        super().keyPressEvent(event)


class HistoryList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QListWidget {{ background: {SIDEBAR_BG}; border: 1px solid {BORDER};"
            f"  border-radius: 6px; font-size: 11px; color: {TEXT_SECONDARY}; }}"
            f"QListWidget::item {{ padding: 6px 10px; border-bottom: 1px solid {BORDER}; }}"
            f"QListWidget::item:hover {{ background: {BG_LIGHT}; }}"
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"RCD2000 v{__version__} - BS 8110 Design")
        self.setMinimumSize(1000, 720)
        self._history = []
        self._setup_icon()
        self._setup_stylesheet()
        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()

    def _setup_icon(self):
        icon_path = _find_icon("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _setup_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG_DARK}; }}
            QWidget {{ background: {BG_DARK}; color: {TEXT_PRIMARY};
                       font-family: 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
            QScrollBar:vertical {{ background: {BG_MID}; width: 8px; border: none; }}
            QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
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
        logo_path = _find_icon("logo-32.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("RCD")
            logo_label.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: bold;")
        logo_label.setFixedSize(36, 36)
        header_layout.addWidget(logo_label)

        title_label = QLabel("RCD2000")
        title_label.setStyleSheet(f"color: {ACCENT}; font-size: 18px; font-weight: bold; background: transparent;")
        header_layout.addWidget(title_label)

        subtitle = QLabel("Reinforced Concrete Design to BS 8110")
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; padding-left: 4px; background: transparent;")
        header_layout.addWidget(subtitle)
        header_layout.addStretch()

        help_btn = QLabel("Cmd+I  About  |  Cmd+H  History")
        help_btn.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        header_layout.addWidget(help_btn)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        sidebar = QWidget()
        sidebar.setMinimumWidth(160)
        sidebar.setMaximumWidth(300)
        sidebar.setStyleSheet(f"background: {SIDEBAR_BG}; border-right: 1px solid {BORDER};")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 12, 0, 12)
        sb_layout.setSpacing(2)

        sb_label = QLabel("Design Modules")
        sb_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: bold;"
            f" padding: 4px 16px; letter-spacing: 1px; background: transparent;"
        )
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
        icons_map = {"c": "\u25b2", "b": "\u2501", "s": "\u25a6", "t": "\u2571", "f": "\u25a4", "n": "\u2261"}
        for name, _, key in MODULES:
            self.sidebar_list.addItem(f"  {icons_map.get(key, '\u2022')}  {name}")
        self.sidebar_list.setCurrentRow(0)
        sb_layout.addWidget(self.sidebar_list)

        # History section in sidebar
        sb_layout.addSpacing(16)
        hist_label = QLabel("Recent Calculations")
        hist_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold;"
            f" padding: 4px 16px; letter-spacing: 1px; background: transparent;"
        )
        sb_layout.addWidget(hist_label)
        self.history_list = HistoryList()
        self.history_list.itemClicked.connect(self._history_clicked)
        sb_layout.addWidget(self.history_list, 1)

        pages_container = QWidget()
        pages_container.setStyleSheet(f"background: {BG_DARK};")
        pages_layout = QVBoxLayout(pages_container)
        pages_layout.setContentsMargins(0, 0, 0, 0)
        pages_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.pages = []
        for _, page_class, _ in MODULES:
            page = page_class()
            page._history_cb = self._add_history
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
        splitter.setSizes([180, 820])

        main_v = QVBoxLayout()
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.setSpacing(0)
        main_v.addWidget(header)
        main_v.addWidget(splitter)
        h_layout.addLayout(main_v)

        self.sidebar_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        self.status = QStatusBar()
        self.status.setStyleSheet(
            f"background: {BG_MID}; color: {TEXT_SECONDARY};"
            f" border-top: 1px solid {BORDER}; font-size: 11px; padding: 2px 8px;"
        )
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    def _setup_menu(self):
        bar = self.menuBar()
        bar.setStyleSheet(
            f"QMenuBar {{ background: {BG_MID}; color: {TEXT_SECONDARY};"
            f"  border-bottom: 1px solid {BORDER}; font-size: 12px; }}"
            f"QMenuBar::item:selected {{ background: {BG_LIGHT}; }}"
            f"QMenu {{ background: {BG_MID}; color: {TEXT_PRIMARY};"
            f"  border: 1px solid {BORDER}; }}"
            f"QMenu::item:selected {{ background: {ACCENT}; }}"
        )
        # Hide the menu bar since we use keyboard shortcuts
        bar.setVisible(False)

    def _setup_shortcuts(self):
        about_action = QAction("About", self)
        about_action.setShortcut(QKeySequence("Ctrl+I"))
        about_action.triggered.connect(self._show_about)
        self.addAction(about_action)

        about_action2 = QAction("About Cmd", self)
        about_action2.setShortcut(QKeySequence("Meta+I"))
        about_action2.triggered.connect(self._show_about)
        self.addAction(about_action2)

        hide_action = QAction("Hide History", self)
        hide_action.setShortcut(QKeySequence("Ctrl+H"))
        hide_action.triggered.connect(self._toggle_history)
        self.addAction(hide_action)

        hide_action2 = QAction("Hide History Cmd", self)
        hide_action2.setShortcut(QKeySequence("Meta+H"))
        hide_action2.triggered.connect(self._toggle_history)
        self.addAction(hide_action2)

    def keyPressEvent(self, event):
        if event.key() in SHORTCUT_KEYS and event.modifiers() & Qt.ControlModifier:
            idx = SHORTCUT_KEYS[event.key()]
            if idx < len(MODULES):
                self.sidebar_list.setCurrentRow(idx)
                self.status.showMessage(f"Switched to {MODULES[idx][0]}")
        super().keyPressEvent(event)

    def _add_history(self, module_name: str, inp, result):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        display = f"[{module_name}] {ts}"
        self._history.append((module_name, inp, result))
        self.history_list.insertItem(0, display)
        while self.history_list.count() > 20:
            self.history_list.takeItem(self.history_list.count() - 1)
        self.status.showMessage(f"{module_name} designed - {ts}")

    def _history_clicked(self, item):
        idx = self.history_list.row(item)
        entry = self._history[idx] if idx < len(self._history) else None
        if entry:
            module_name, inp, result = entry
            # Navigate to the module
            for i, (name, _, _) in enumerate(MODULES):
                if name == module_name:
                    self.sidebar_list.setCurrentRow(i)
                    self.status.showMessage(f"Recalled {module_name} from history")
                    break

    def _toggle_history(self):
        # History is always visible in sidebar; this could hide/show
        self.history_list.setVisible(not self.history_list.isVisible())

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()


def splash_screen(app):
    splash_path = _find_icon("logo.png")
    if os.path.exists(splash_path):
        pix = QPixmap(splash_path)
        splash = QSplashScreen(pix)
        splash.setStyleSheet(
            f"color: {ACCENT}; font-size: 14px; font-weight: bold;"
        )
        splash.show()
        splash.showMessage("  Loading RCD2000 ...", Qt.AlignBottom | Qt.AlignCenter, QColor(ACCENT))
        app.processEvents()
        QTimer.singleShot(800, splash.close)
        return splash
    return None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RCD2000")
    app.setApplicationVersion(__version__)

    # Set app icon
    icon_path = _find_icon("logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    splash = splash_screen(app)
    window = MainWindow()
    window.show()
    if splash:
        splash.finish(window)
    sys.exit(app.exec())
