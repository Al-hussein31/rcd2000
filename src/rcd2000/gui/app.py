"""Main window and application entry point."""

import sys
import os
from importlib.resources import files

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel, QScrollArea,
    QStatusBar, QSplashScreen, QDialog, QMessageBox, QToolButton, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QIcon, QAction, QKeySequence, QColor, QFont

try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False

from rcd2000 import __version__
from rcd2000.gui.theme import (
    BG_DARK, BG_MID, BG_LIGHT, SIDEBAR_BG, ACCENT, ACCENT_SOFT, TEXT_PRIMARY,
    TEXT_SECONDARY, BORDER, TEXT_MUTED, BG_CARD, FONT_SIZE, SPACE, RADIUS_SM, RADIUS_MD,
)
from rcd2000.gui.widgets import CollapsibleSection
from rcd2000.gui.pages import (
    ColumnPage, BeamPage, SlabPage, StairPage, BasePage, ContinuousBeamPage,
)

SIDEBAR_EXPANDED = 220
SIDEBAR_COLLAPSED = 64

MODULES = [
    ("Column Design", ColumnPage, "c", "fa5s.ruler-vertical", "\u25b2"),
    ("Beam Design", BeamPage, "b", "fa5s.ruler-horizontal", "\u2501"),
    ("Slab Design", SlabPage, "s", "fa5s.th-large", "\u25a6"),
    ("Stair Design", StairPage, "t", "fa5s.grip-lines", "\u2571"),
    ("Foundation Design", BasePage, "f", "fa5s.university", "\u25a4"),
    ("Continuous Beam", ContinuousBeamPage, "n", "fa5s.link", "\u2261"),
]

SHORTCUT_KEYS = {
    Qt.Key_1: 0, Qt.Key_2: 1, Qt.Key_3: 2,
    Qt.Key_4: 3, Qt.Key_5: 4, Qt.Key_6: 5,
}


def _find_icon(name: str) -> str:
    try:
        pkg = files("rcd2000.gui.icons")
        return str(pkg.joinpath(name))
    except (ModuleNotFoundError, TypeError):
        base = os.path.join(os.path.dirname(__file__), "icons")
        return os.path.join(base, name)


def _qta_icon(name: str, color: str = TEXT_SECONDARY):
    if not _HAS_QTA:
        return None
    try:
        return qta.icon(name, color=color)
    except Exception:
        return None


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
            f"color: {ACCENT}; font-size: 24px; font-weight: 700; background: transparent;"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        ver = QLabel(f"Version {__version__}")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; background: transparent;")
        layout.addWidget(ver)

        desc = QLabel(
            "Reinforced Concrete Design to BS 8110:1997\n"
            "Python port of Oyenuga's RCD2000 FORTRAN programs.\n\n"
            "Engine: Clapeyron three-moment equation, strain compatibility\n"
            "interaction curves, and BS 8110 moment/shear coefficients."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        layout.addWidget(desc)

        link = QLabel(
            '<a href="https://github.com/Al-hussein31/rcd2000" '
            f'style="color: {ACCENT};">github.com/Al-hussein31/rcd2000</a>'
        )
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignCenter)
        link.setStyleSheet("background: transparent;")
        layout.addWidget(link)

        hint = QLabel("Press Esc to close")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        layout.addWidget(hint)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.accept()
        super().keyPressEvent(event)


class HistoryList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none;"
            f"  font-size: {FONT_SIZE['xs']}px; color: {TEXT_SECONDARY}; }}"
            f"QListWidget::item {{ padding: 7px 16px; border-radius: {RADIUS_SM}px; }}"
            f"QListWidget::item:hover {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY}; }}"
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"RCD2000 v{__version__} - BS 8110 Design")
        self.setMinimumSize(1000, 720)
        self._history = []
        self._sidebar_expanded = True
        self._setup_icon()
        self._setup_stylesheet()
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_icon(self):
        icon_path = _find_icon("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _setup_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG_DARK}; }}
            QWidget {{ background: {BG_DARK}; color: {TEXT_PRIMARY};
                       font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; border: none; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QToolTip {{ background: {BG_MID}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER};
                        padding: 4px 8px; border-radius: {RADIUS_SM}px; }}
        """)

    # ── UI construction ──────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        body_layout.addWidget(self._build_sidebar())
        body_layout.addWidget(self._build_pages(), 1)
        outer.addWidget(body, 1)

        self.status = QStatusBar()
        self.status.setStyleSheet(
            f"background: {BG_MID}; color: {TEXT_SECONDARY};"
            f" border-top: 1px solid {BORDER}; font-size: {FONT_SIZE['xs']}px; padding: 3px 10px;"
        )
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

        self.sidebar_list.currentRowChanged.connect(self.stack.setCurrentIndex)

    def _build_header(self):
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background: {BG_MID}; border-bottom: 1px solid {BORDER};")
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 8, 16, 8)
        h.setSpacing(SPACE[3])

        logo_label = QLabel()
        logo_path = _find_icon("logo-32.png")
        if os.path.exists(logo_path):
            logo_label.setPixmap(QPixmap(logo_path))
        else:
            logo_label.setText("RCD")
            logo_label.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 700;")
        logo_label.setFixedSize(32, 32)
        h.addWidget(logo_label)

        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        title_label = QLabel("RCD2000")
        title_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700; background: transparent;")
        subtitle = QLabel("Reinforced Concrete Design · BS 8110")
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        title_block.addWidget(title_label)
        title_block.addWidget(subtitle)
        h.addLayout(title_block)
        h.addStretch()

        help_btn = QToolButton()
        help_icon = _qta_icon("fa5s.info-circle", TEXT_MUTED)
        if help_icon:
            help_btn.setIcon(help_icon)
        else:
            help_btn.setText("?")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setToolTip("Shortcuts:  Ctrl+1..6 switch module   ·   Ctrl+I about   ·   Ctrl+H toggle history")
        help_btn.setStyleSheet(
            "QToolButton { background: transparent; border: none; padding: 4px; }"
            f"QToolButton:hover {{ background: {BG_LIGHT}; border-radius: {RADIUS_SM}px; }}"
        )
        h.addWidget(help_btn)
        return header

    def _build_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(SIDEBAR_EXPANDED)
        self.sidebar.setStyleSheet(f"background: {SIDEBAR_BG}; border-right: 1px solid {BORDER};")
        sb = QVBoxLayout(self.sidebar)
        sb.setContentsMargins(0, SPACE[3], 0, SPACE[3])
        sb.setSpacing(SPACE[1])

        # Collapse toggle
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(SPACE[3], 0, SPACE[3], SPACE[2])
        self._sidebar_title = QLabel("DESIGN MODULES")
        self._sidebar_title.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; font-weight: 700;"
            f" letter-spacing: 0.8px; background: transparent;"
        )
        toggle_row.addWidget(self._sidebar_title)
        toggle_row.addStretch()

        self.collapse_btn = QToolButton()
        collapse_icon = _qta_icon("fa5s.angle-double-left", TEXT_MUTED)
        if collapse_icon:
            self.collapse_btn.setIcon(collapse_icon)
        else:
            self.collapse_btn.setText("«")
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.setToolTip("Collapse sidebar")
        self.collapse_btn.setStyleSheet(
            "QToolButton { background: transparent; border: none; padding: 2px; }"
            f"QToolButton:hover {{ background: {BG_LIGHT}; border-radius: {RADIUS_SM}px; }}"
        )
        self.collapse_btn.clicked.connect(self._toggle_sidebar)
        toggle_row.addWidget(self.collapse_btn)
        sb.addLayout(toggle_row)

        self.sidebar_list = QListWidget()
        self.sidebar_list.setIconSize(QSize(16, 16))
        self.sidebar_list.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; font-size: {FONT_SIZE['base']}px; }}
            QListWidget::item {{ padding: 10px 16px; color: {TEXT_SECONDARY};
                                border-left: 3px solid transparent; margin: 1px 6px; border-radius: {RADIUS_SM}px; }}
            QListWidget::item:hover {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY}; }}
            QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {ACCENT};
                                          border-left: 3px solid {ACCENT}; }}
        """)
        for name, _, key, qta_name, glyph in MODULES:
            qicon = _qta_icon(qta_name, TEXT_SECONDARY)
            item = QListWidgetItem(f"  {name}")
            if qicon:
                item.setIcon(qicon)
            else:
                item.setText(f"  {glyph}  {name}")
            self.sidebar_list.addItem(item)
        self.sidebar_list.setCurrentRow(0)
        sb.addWidget(self.sidebar_list)

        # Collapsible "Recent Calculations" section
        self.history_list = HistoryList()
        self.history_list.itemClicked.connect(self._history_clicked)
        self.history_section = CollapsibleSection(
            "RECENT CALCULATIONS", self.history_list, expanded=True,
        )
        sb.addSpacing(SPACE[3])
        sb.addWidget(self.history_section, 1)

        return self.sidebar

    def _build_pages(self):
        pages_container = QWidget()
        pages_container.setStyleSheet(f"background: {BG_DARK};")
        pages_layout = QVBoxLayout(pages_container)
        pages_layout.setContentsMargins(0, 0, 0, 0)
        pages_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.pages = []
        for _, page_class, *_rest in MODULES:
            page = page_class()
            page._history_cb = self._add_history
            scroll = QScrollArea()
            scroll.setWidget(page)
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(f"QScrollArea {{ background: {BG_DARK}; border: none; }}")
            self.stack.addWidget(scroll)
            self.pages.append(page)

        pages_layout.addWidget(self.stack)
        return pages_container

    # ── Sidebar collapse (instant — no animation, per design brief) ─
    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        if self._sidebar_expanded:
            self.sidebar.setFixedWidth(SIDEBAR_EXPANDED)
            self._sidebar_title.setVisible(True)
            self.history_section.setVisible(True)
            for i, (name, _, key, qta_name, glyph) in enumerate(MODULES):
                item = self.sidebar_list.item(i)
                item.setText(f"  {name}")
            new_icon = _qta_icon("fa5s.angle-double-left", TEXT_MUTED)
            self.collapse_btn.setToolTip("Collapse sidebar")
        else:
            self.sidebar.setFixedWidth(SIDEBAR_COLLAPSED)
            self._sidebar_title.setVisible(False)
            self.history_section.setVisible(False)
            for i, (name, _, key, qta_name, glyph) in enumerate(MODULES):
                item = self.sidebar_list.item(i)
                item.setText("")
            new_icon = _qta_icon("fa5s.angle-double-right", TEXT_MUTED)
            self.collapse_btn.setToolTip("Expand sidebar")
        if new_icon:
            self.collapse_btn.setIcon(new_icon)
        else:
            self.collapse_btn.setText("»" if not self._sidebar_expanded else "«")

    def _setup_shortcuts(self):
        about_action = QAction("About", self)
        about_action.setShortcut(QKeySequence("Ctrl+I"))
        about_action.triggered.connect(self._show_about)
        self.addAction(about_action)

        hide_action = QAction("Toggle History", self)
        hide_action.setShortcut(QKeySequence("Ctrl+H"))
        hide_action.triggered.connect(self._toggle_history)
        self.addAction(hide_action)

        collapse_action = QAction("Toggle Sidebar", self)
        collapse_action.setShortcut(QKeySequence("Ctrl+B"))
        collapse_action.triggered.connect(self._toggle_sidebar)
        self.addAction(collapse_action)

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
        display = f"{module_name}  ·  {ts}"
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
            for i, mod in enumerate(MODULES):
                if mod[0] == module_name:
                    self.sidebar_list.setCurrentRow(i)
                    self.status.showMessage(f"Recalled {module_name} from history")
                    break

    def _toggle_history(self):
        self.history_section.set_expanded(not self.history_section._expanded)

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()


def splash_screen(app):
    splash_path = _find_icon("logo.png")
    if os.path.exists(splash_path):
        pix = QPixmap(splash_path)
        splash = QSplashScreen(pix)
        splash.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: 700;")
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

    icon_path = _find_icon("logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    splash = splash_screen(app)
    window = MainWindow()
    window.show()
    if splash:
        splash.finish(window)
    sys.exit(app.exec())
