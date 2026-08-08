"""Main window and application entry point.

Flow:  Home → New Job (header dialog) → Workbench → Home
        Home → Recent Job → Workbench (resume)

The window is a thin shell: it shows the home page or the workbench in
a root QStackedWidget, wires the job header dialog, and autosaves the
active job to the job store.
"""

import sys
import os
import time
import logging
from importlib.resources import files

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
    QStatusBar, QSplashScreen, QDialog, QLabel, QToolButton, QHBoxLayout,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QIcon, QAction, QKeySequence, QColor

try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False

from rcd2000 import __version__
from rcd2000.gui.theme import (
    BG_DARK, BG_MID, BG_LIGHT, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER, FONT_SIZE, SPACE, RADIUS_SM,
)
from rcd2000.gui.job import Job, JobStore, make_slug
from rcd2000.gui.settings import SettingsStore
from rcd2000.gui.home_page import HomePage
from rcd2000.gui.history_page import HistoryPage
from rcd2000.gui.settings_page import SettingsPage
from rcd2000.gui.job_header_dialog import JobHeaderDialog
from rcd2000.gui.workbench import Workbench


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

        ver = QLabel(f"Version {__version__} - Multi-Design Workbench")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; background: transparent;")
        layout.addWidget(ver)

        desc = QLabel(
            "Reinforced Concrete Design to BS 8110:1997\n"
            "Python port of Oyenuga's RCD2000 FORTRAN programs.\n\n"
            "Work on any number of designs - columns, beams, slabs, stairs,\n"
            "foundations and continuous beams - under one job header,\n"
            "with up to four on screen at a time.\n\n"
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"RCD2000 v{__version__} - BS 8110 Design")
        self.setMinimumSize(1100, 760)
        self._current_job: Job | None = None
        self._workbench = None
        self._persist_timer: QTimer | None = None
        self._track_timer: QTimer | None = None
        self._setup_icon()
        self._setup_stylesheet()
        self._setup_ui()
        self._setup_shortcuts()
        self._maybe_show_first_run()

    # ── plumbing ────────────────────────────────────────────────────

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

        self._root = QStackedWidget()
        self.home = HomePage()
        self.home.new_job_requested.connect(self._new_job)
        self.home.continue_requested.connect(self._show_history)
        self.home.settings_requested.connect(self._show_settings)
        self._root.addWidget(self.home)

        self.history = HistoryPage()
        self.history.back_requested.connect(self._go_home)
        self.history.open_job_requested.connect(self._open_job)
        self.history.new_job_requested.connect(self._new_job)
        self.history.status_message.connect(self.show_message)
        self._root.addWidget(self.history)

        self.settings_page = SettingsPage()
        self.settings_page.back_requested.connect(self._go_home)
        self.settings_page.profile_changed.connect(self._on_profile_changed)
        self.settings_page.status_message.connect(self.show_message)
        self._root.addWidget(self.settings_page)

        outer.addWidget(self._root, 1)

        self.status = QStatusBar()
        self.status.setStyleSheet(
            f"background: {BG_MID}; color: {TEXT_SECONDARY};"
            f" border-top: 1px solid {BORDER}; font-size: {FONT_SIZE['xs']}px; padding: 3px 10px;"
        )
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

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
        self._title_label = QLabel("RCD2000")
        self._title_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700; background: transparent;"
        )
        self._header_subtitle = QLabel("Reinforced Concrete Design · BS 8110")
        self._header_subtitle.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;"
        )
        title_block.addWidget(self._title_label)
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
        help_btn.setToolTip(
            "Shortcuts:  Ctrl+N new job · Ctrl+J edit job header · "
            "Ctrl+H home · Ctrl+I about"
        )
        help_btn.setStyleSheet(
            "QToolButton { background: transparent; border: none; padding: 4px; }"
            f"QToolButton:hover {{ background: {BG_LIGHT}; border-radius: {RADIUS_SM}px; }}"
        )
        help_btn.clicked.connect(self._show_about)
        h.addWidget(help_btn)
        return header

    def _setup_shortcuts(self):
        about_action = QAction("About", self)
        about_action.setShortcut(QKeySequence("Ctrl+I"))
        about_action.triggered.connect(self._show_about)
        self.addAction(about_action)

        new_action = QAction("New Job", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._new_job)
        self.addAction(new_action)

        continue_action = QAction("Continue", self)
        continue_action.setShortcut(QKeySequence("Ctrl+C"))
        continue_action.triggered.connect(self._show_history)
        self.addAction(continue_action)

        home_action = QAction("Home", self)
        home_action.setShortcut(QKeySequence("Ctrl+H"))
        home_action.triggered.connect(self._go_home)
        self.addAction(home_action)

        settings_action = QAction("Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+S"))
        settings_action.triggered.connect(self._show_settings)
        self.addAction(settings_action)

        # Esc exits focus mode when inside the workbench
        esc_action = QAction("Exit Focus", self)
        esc_action.setShortcut(QKeySequence("Esc"))
        esc_action.triggered.connect(self._exit_focus_if_focused)
        self.addAction(esc_action)

    def _maybe_show_first_run(self):
        """First run: take the user straight to Settings so the profile
        exists before any job is created (job headers prefill from it)."""
        profile = SettingsStore.load()
        if not profile.is_complete():
            self.settings_page.load_profile()
            self._root.setCurrentWidget(self.settings_page)
            self._header_subtitle.setText("Welcome - Set Up Your Profile · BS 8110")
            self.status.showMessage(
                "Tell us who you are - it pre-fills every new job header."
            )

    def _on_profile_changed(self):
        self.home.refresh_welcome()
        # Saved → go Home instantly so the personalized greeting shows.
        self._header_subtitle.setText("Reinforced Concrete Design · BS 8110")
        self._root.setCurrentWidget(self.home)

    # ── job lifecycle ───────────────────────────────────────────────

    def _new_job(self):
        header = JobHeaderDialog.ask(self)
        if header is None:
            return
        n_items = (header.get("job_ref") or "Untitled Job").strip() or "Untitled Job"
        job = Job(slug=make_slug(n_items), name=n_items, header=header)
        self._open_workbench(job)

    def _open_job(self, slug: str):
        job = JobStore.load(slug)
        if job is None:
            self.show_status_banner("Could not load that job - file may be missing.", True)
            self.history.refresh()
            return
        self._open_workbench(job)

    def _open_workbench(self, job: Job):
        self._save_current_job()
        self._current_job = job
        job.last_opened = time.time()
        self._replace_workbench(job)
        self._root.setCurrentWidget(self._workbench)
        self._header_subtitle.setText(f"{job.name} · BS 8110")
        self.status.showMessage(f"Working on: {job.name}")
        self._start_time_tracking()
        self._schedule_persist()

    def _replace_workbench(self, job):
        """Rebuild the workbench for a job without leaking old connections."""
        if self._workbench is not None:
            self._root.removeWidget(self._workbench)
            self._workbench.deleteLater()
            self._workbench = None
        from rcd2000.gui.workbench import Workbench
        self._workbench = Workbench(job)
        self._workbench.back_requested.connect(self._go_home)
        self._workbench.edit_job_requested.connect(self._edit_job_header)
        self._workbench.job_changed.connect(self._schedule_persist)
        self._workbench.status_message.connect(self.show_message)
        self._root.addWidget(self._workbench)

    def _edit_job_header(self):
        if self._current_job is None:
            return
        header = JobHeaderDialog.ask(self, existing=self._current_job.header)
        if header is None:
            return
        self._current_job.header = header
        if not self._current_job.name:
            self._current_job.name = header.get("job_ref") or "Untitled Job"
        # push new materials into existing panels
        for panel in self._workbench._panels.values():
            panel.apply_header_defaults(header)
        self._workbench.refresh_all()
        self._header_subtitle.setText(f"{self._current_job.name} · BS 8110")
        self.show_message("Job header updated - will appear on all reports.", False)
        self._schedule_persist()

    def _go_home(self):
        self._stop_time_tracking()
        self._save_current_job()
        self._current_job = None
        self._root.setCurrentWidget(self.home)
        self.home.refresh_welcome()
        self._header_subtitle.setText("Reinforced Concrete Design · BS 8110")
        self.status.showMessage("Ready")

    def _show_history(self):
        self._save_current_job()
        self.history.refresh()
        self._root.setCurrentWidget(self.history)
        self._header_subtitle.setText("Your Jobs · BS 8110")
        self.status.showMessage("History")

    def _show_settings(self):
        self.settings_page.load_profile()
        self._root.setCurrentWidget(self.settings_page)
        self._header_subtitle.setText("Settings · BS 8110")
        self.status.showMessage("Settings")

    def _exit_focus_if_focused(self):
        if self._workbench is not None and self._workbench._focused is not None:
            self._workbench.exit_focus()

    # ── persistence ─────────────────────────────────────────────────

    _TRACK_INTERVAL = 30  # seconds of work time credited per tick

    def _start_time_tracking(self):
        """Accumulate active work time while the workbench is open."""
        if self._track_timer is None:
            self._track_timer = QTimer(self)
            self._track_timer.setInterval(self._TRACK_INTERVAL * 1000)
            self._track_timer.timeout.connect(self._tick_work_time)
        self._track_timer.start()

    def _stop_time_tracking(self):
        if self._track_timer is not None:
            self._track_timer.stop()

    def _tick_work_time(self):
        if self._current_job is None:
            return
        self._current_job.add_time(self._TRACK_INTERVAL)
        self._schedule_persist()

    def _schedule_persist(self):
        if self._persist_timer is None:
            self._persist_timer = QTimer(self)
            self._persist_timer.setSingleShot(True)
            self._persist_timer.timeout.connect(self._save_current_job)
        self._persist_timer.start(2000)

    def _save_current_job(self):
        if self._current_job is None or self._workbench is None:
            return
        # sync panel state back into items
        for uid, panel in self._workbench._panels.items():
            item = self._current_job.item(uid)
            if item is not None:
                item.label = panel.label
                item.state = panel.get_state()
        try:
            JobStore.save(self._current_job)
        except Exception:
            logging.error("Failed to save job", exc_info=True)

    # ── misc ────────────────────────────────────────────────────────

    def show_message(self, message: str, is_error: bool = False):
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

    def show_status_banner(self, message: str, is_error: bool = False):
        """Alias kept for page status callbacks."""
        self.show_message(message, is_error)

    def _show_about(self):
        AboutDialog(self).exec()

    def closeEvent(self, event):
        self._stop_time_tracking()
        self._save_current_job()
        super().closeEvent(event)


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