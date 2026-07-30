"""Main window and application entry point."""

import sys
import os
import json
import logging
from dataclasses import asdict, is_dataclass
from importlib.resources import files

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel, QScrollArea,
    QStatusBar, QSplashScreen, QDialog, QMessageBox, QToolButton, QSizePolicy,
    QLineEdit,
)
from PySide6.QtCore import Qt, QTimer, QSize, QStandardPaths
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

_PERSIST_FILE = "rcd2000_state.json"


def _persist_path() -> str:
    """Return the platform-appropriate path for the state JSON file."""
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not base:
        base = os.path.expanduser("~")
    full = os.path.join(base, "RCD2000")
    os.makedirs(full, exist_ok=True)
    return os.path.join(full, _PERSIST_FILE)


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
        self._drafts: dict[str, dict] = {}
        self._dirty_modules: set[str] = set()
        self._last_active_page: int | None = None
        self._persist_timer: QTimer | None = None
        self._sidebar_expanded = True
        self._setup_icon()
        self._setup_stylesheet()
        self._setup_ui()
        self._setup_shortcuts()
        self._last_active_page = 0
        self._load_state()
        self._refresh_sidebar_labels()

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

        self._status_banner = QLabel()
        self._status_banner.setFixedHeight(36)
        self._status_banner.setAlignment(Qt.AlignCenter)
        self._status_banner.setVisible(False)
        self._status_banner.setStyleSheet(
            "font-size: 13px; font-weight: 600; background: transparent;"
        )
        outer.addWidget(self._status_banner)

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

        self.sidebar_list.currentRowChanged.connect(self._on_page_switched)
        self.stack.currentChanged.connect(self._on_stack_changed)

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
        self._header_subtitle = QLabel("Reinforced Concrete Design · BS 8110")
        self._header_subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        title_block.addWidget(title_label)
        title_block.addWidget(self._header_subtitle)
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
        self.history_placeholder = QLabel("  No calculations yet")
        self.history_placeholder.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px;"
            f" padding: 8px 16px; background: transparent;"
        )
        history_container = QWidget()
        history_container.setStyleSheet("background: transparent;")
        hc_layout = QVBoxLayout(history_container)
        hc_layout.setContentsMargins(0, 0, 0, 0)
        hc_layout.setSpacing(0)
        hc_layout.addWidget(self.history_list)
        hc_layout.addWidget(self.history_placeholder)
        self.history_section = CollapsibleSection(
            "RECENT CALCULATIONS", history_container, expanded=True,
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
            page._status_cb = self.show_status_banner
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
            self.history_placeholder.setVisible(self.history_list.count() == 0)
        else:
            self.sidebar.setFixedWidth(SIDEBAR_COLLAPSED)
            self._sidebar_title.setVisible(False)
            self.history_section.setVisible(False)
        self._refresh_sidebar_labels()
        new_icon = _qta_icon(
            "fa5s.angle-double-left" if self._sidebar_expanded else "fa5s.angle-double-right",
            TEXT_MUTED,
        )
        if new_icon:
            self.collapse_btn.setIcon(new_icon)
        else:
            self.collapse_btn.setText("«" if self._sidebar_expanded else "»")
        self.collapse_btn.setToolTip(
            "Collapse sidebar" if self._sidebar_expanded else "Expand sidebar"
        )

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

        switcher_action = QAction("Quick Switch Module", self)
        switcher_action.setShortcut(QKeySequence("Ctrl+K"))
        switcher_action.triggered.connect(self._show_quick_switcher)
        self.addAction(switcher_action)

    def keyPressEvent(self, event):
        if event.key() in SHORTCUT_KEYS and event.modifiers() & Qt.ControlModifier:
            idx = SHORTCUT_KEYS[event.key()]
            if idx < len(MODULES):
                self.sidebar_list.setCurrentRow(idx)
                self.status.showMessage(f"Switched to {MODULES[idx][0]}")
        super().keyPressEvent(event)

    # ── Draft autosave ────────────────────────────────────────────────

    def _on_page_switched(self, new_idx: int):
        """Save the old page's draft and restore the new page's draft."""
        old_idx = self._last_active_page
        if old_idx is not None and old_idx != new_idx:
            self._save_draft(old_idx)
        self.stack.setCurrentIndex(new_idx)
        self._restore_draft(new_idx)
        self._last_active_page = new_idx
        self._header_subtitle.setText(f"{MODULES[new_idx][0]} · BS 8110")

    def _on_stack_changed(self, idx: int):
        """Sync sidebar selection when stack changes programmatically."""
        if self.sidebar_list.currentRow() != idx:
            self.sidebar_list.setCurrentRow(idx)

    def _save_draft(self, idx: int):
        """Capture the current page's state into self._drafts."""
        if idx < 0 or idx >= len(self.pages):
            return
        page = self.pages[idx]
        name = MODULES[idx][0]
        try:
            state = page.get_state()
            self._drafts[name] = state
            # Mark as having unsaved draft if any non-default values exist
            if any(v not in (0, 0.0, "", 0.0) for v in state.values() if not isinstance(v, (list, dict))):
                self._dirty_modules.add(name)
                self._refresh_sidebar_labels()
        except Exception:
            logging.error(f"Failed to capture draft for {name}", exc_info=True)
        self._schedule_persist()

    def _restore_draft(self, idx: int):
        """Restore a page's draft from self._drafts, if one exists."""
        if idx < 0 or idx >= len(self.pages):
            return
        page = self.pages[idx]
        name = MODULES[idx][0]
        state = self._drafts.get(name)
        if state is None:
            return
        try:
            page.set_state(state)
            self._clear_invalid_flags(page)
        except Exception:
            logging.error(f"Failed to restore draft for {name}", exc_info=True)

    def _clear_invalid_flags(self, page):
        """Clear any 'invalid' property flags on spinboxes after restore."""
        from rcd2000.gui.widgets import mark_invalid
        for attr_name in dir(page):
            widget = getattr(page, attr_name, None)
            if hasattr(widget, "setProperty"):
                try:
                    mark_invalid(widget, False)
                except Exception:
                    pass

    # ── History persistence ──────────────────────────────────────────

    def _history_to_serializable(self):
        """Convert history entries to JSON-serializable dicts."""
        out = []
        for entry in self._history:
            module_name, inp, result = entry[:3]
            state_dict = entry[3] if len(entry) > 3 else None
            rec = {"module": module_name}
            if is_dataclass(inp):
                rec["input"] = asdict(inp)
            if is_dataclass(result):
                rec["result"] = asdict(result)
            if state_dict:
                rec["state"] = state_dict
            out.append(rec)
        return out

    def _history_from_serializable(self, data):
        """Rebuild history entries from JSON-serializable dicts.

        Uses the raw dicts (not dataclass instances) so that the history
        display still works without needing to reconstruct the dataclasses.
        """
        self._history = []
        self.history_list.clear()
        self._dirty_modules.clear()
        self._refresh_sidebar_labels()
        from datetime import datetime
        for rec in data:
            module_name = rec.get("module", "Unknown")
            ts = rec.get("timestamp", "??")
            state_dict = rec.get("state")
            inp_dict = rec.get("input")
            result_dict = rec.get("result")
            # Try to use summarize() for a descriptive label
            summary = ""
            inp_for_summary = result_dict or inp_dict or {}
            for i, mod in enumerate(MODULES):
                if mod[0] == module_name:
                    try:
                        summary = self.pages[i].summarize(inp_for_summary)
                    except Exception:
                        summary = ""
                    break
            if summary:
                display = f"{module_name} · {summary} · {ts}"
            else:
                display = f"{module_name}  ·  {ts}"
            self._history.append((module_name, inp_dict, result_dict, state_dict))
            self.history_list.insertItem(0, display)
            while self.history_list.count() > 20:
                self.history_list.takeItem(self.history_list.count() - 1)
        self.history_placeholder.setVisible(len(data) == 0)

    # ── Disk persistence ──────────────────────────────────────────────

    def _schedule_persist(self):
        """Debounced write: restart the timer for 2 s."""
        if self._persist_timer is None:
            self._persist_timer = QTimer(self)
            self._persist_timer.setSingleShot(True)
            self._persist_timer.timeout.connect(self._write_state)
        self._persist_timer.start(2000)

    def _write_state(self):
        """Write drafts + history to the JSON state file."""
        try:
            path = _persist_path()
            from datetime import datetime
            history_serializable = []
            for entry in self._history:
                module_name, inp, result = entry[:3]
                state_dict = entry[3] if len(entry) > 3 else None
                rec = {"module": module_name, "timestamp": datetime.now().strftime("%H:%M:%S")}
                if is_dataclass(inp):
                    rec["input"] = asdict(inp)
                if is_dataclass(result):
                    rec["result"] = asdict(result)
                if state_dict:
                    rec["state"] = state_dict
                history_serializable.append(rec)
            payload = {
                "drafts": self._drafts,
                "history": history_serializable,
                "last_page": self._last_active_page,
            }
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            logging.error("Failed to write state file", exc_info=True)

    def _load_state(self):
        """Load drafts + history from the JSON state file on startup."""
        path = _persist_path()
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                payload = json.load(f)
            self._drafts = payload.get("drafts", {})
            last_page = payload.get("last_page")
            self._history_from_serializable(payload.get("history", []))
            # Restore the last-active page's draft
            if last_page is not None and 0 <= last_page < len(self.pages):
                self._restore_draft(last_page)
                self._last_active_page = last_page
        except (json.JSONDecodeError, KeyError, TypeError):
            logging.error("State file corrupt — starting fresh", exc_info=True)
            self._drafts = {}
            self._history = []

    def closeEvent(self, event):
        """Persist state on close."""
        self._write_state()
        super().closeEvent(event)

    def show_status_banner(self, message: str, is_error: bool = False):
        """Show a temporary status banner above the page content."""
        self._status_banner.setText(f"  {message}  ")
        if is_error:
            self._status_banner.setStyleSheet(
                f"background: #5c1a1a; color: #ff6b6b; font-size: 13px;"
                f" font-weight: 600; border-bottom: 1px solid #8b2525;"
            )
        else:
            self._status_banner.setStyleSheet(
                f"background: #1a3d1a; color: #6bff6b; font-size: 13px;"
                f" font-weight: 600; border-bottom: 1px solid #2a5c2a;"
            )
        self._status_banner.setVisible(True)
        QTimer.singleShot(4000, lambda: self._status_banner.setVisible(False))

    def _add_history(self, module_name: str, inp, result):
        from datetime import datetime
        # Map short module_name (e.g. "Column") to display name (e.g. "Column Design")
        display_name = module_name
        page = None
        for mod in MODULES:
            if mod[1].module_name == module_name:
                display_name = mod[0]
                break
        # Capture the current widget state for exact history restore
        state_dict = None
        for i, mod in enumerate(MODULES):
            if mod[0] == display_name:
                try:
                    state_dict = self.pages[i].get_state()
                except Exception:
                    pass
                break
        ts = datetime.now().strftime("%H:%M")
        # Build one-line summary via the page's summarize() method
        summary = ""
        for i, mod in enumerate(MODULES):
            if mod[0] == display_name:
                try:
                    summary = self.pages[i].summarize(inp)
                except Exception:
                    summary = ""
                break
        label = f"{display_name} · {summary} · {ts}" if summary else f"{display_name}  ·  {ts}"
        self._history.append((display_name, inp, result, state_dict))
        self.history_list.insertItem(0, label)
        self.history_placeholder.setVisible(False)
        while self.history_list.count() > 20:
            self.history_list.takeItem(self.history_list.count() - 1)
        self._dirty_modules.discard(display_name)
        self._refresh_sidebar_labels()
        self.status.showMessage(f"{display_name} designed - {ts}")
        self._schedule_persist()

    def _history_clicked(self, item):
        # Save current page draft before switching
        if self._last_active_page is not None:
            self._save_draft(self._last_active_page)
        idx = self.history_list.row(item)
        entry = self._history[idx] if idx < len(self._history) else None
        if entry:
            module_name, inp, result, state_dict = entry
            for i, mod in enumerate(MODULES):
                if mod[0] == module_name:
                    # Pop draft so _restore_draft won't reapply it on nav
                    self._drafts.pop(module_name, None)
                    # Switch page (triggers _on_page_switched → _restore_draft,
                    # which will skip because draft is gone)
                    self.sidebar_list.setCurrentRow(i)
                    # Restore exact history state
                    page = self.pages[i]
                    try:
                        page._history_viewed = True
                        if state_dict:
                            page.set_state(state_dict)
                        page._show_result(result)
                    except Exception as exc:
                        logging.error(
                            f"Failed to restore history for {module_name}", exc_info=True
                        )
                    self.status.showMessage(f"Recalled {module_name} from history")
                    break

    def _show_quick_switcher(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Quick Switch Module")
        dlg.setFixedSize(360, 280)
        dlg.setStyleSheet(f"background: {BG_MID}; color: {TEXT_PRIMARY};")
        layout = QVBoxLayout(dlg)
        layout.setSpacing(SPACE[2])

        search = QLineEdit()
        search.setPlaceholderText("Type to filter…")
        search.setStyleSheet(
            f"background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px;"
            f" padding: 8px 12px; font-size: {FONT_SIZE['base']}px;"
        )
        layout.addWidget(search)

        lst = QListWidget()
        lst.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none;"
            f"  font-size: {FONT_SIZE['base']}px; }}"
            f"QListWidget::item {{ padding: 8px 12px; color: {TEXT_SECONDARY};"
            f"  border-radius: {RADIUS_SM}px; }}"
            f"QListWidget::item:hover {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY}; }}"
            f"QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}"
        )
        for name, *_ in MODULES:
            lst.addItem(f"  {name}")
        lst.setCurrentRow(0)
        layout.addWidget(lst)

        hint = QLabel("Esc to close  ·  Enter to switch")
        hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;"
        )
        hint.setAlignment(Qt.AlignRight)
        layout.addWidget(hint)

        def _filter(text):
            for i in range(lst.count()):
                item = lst.item(i)
                match = text.lower() in item.text().lower()
                item.setHidden(not match)
            for i in range(lst.count()):
                if not lst.item(i).isHidden():
                    lst.setCurrentRow(i)
                    break

        search.textChanged.connect(_filter)
        search.returnPressed.connect(
            lambda: dlg.accept() if lst.currentItem() and not lst.currentItem().isHidden() else None
        )
        lst.itemDoubleClicked.connect(lambda: dlg.accept())

        search.setFocus()
        if dlg.exec() == QDialog.Accepted:
            idx = lst.currentRow()
            if 0 <= idx < len(MODULES) and not lst.currentItem().isHidden():
                self.sidebar_list.setCurrentRow(idx)
                self.status.showMessage(f"Switched to {MODULES[idx][0]}")

    def _refresh_sidebar_labels(self):
        for idx in range(len(MODULES)):
            name = MODULES[idx][0]
            item = self.sidebar_list.item(idx)
            if self._sidebar_expanded:
                prefix = "• " if name in self._dirty_modules else "  "
                item.setText(f"{prefix}{name}")
            else:
                item.setText("")

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
