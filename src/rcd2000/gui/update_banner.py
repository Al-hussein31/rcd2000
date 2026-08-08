"""Background update check and the 'update available' banner.

Pattern (like VS Code / Slack / Discord): on startup the app checks the
GitHub Releases API in a background thread, then shows a persistent,
non-blocking banner at the top of the window when a newer release
exists.  The banner offers one action - open the releases page - and a
close button that remembers the dismissed version so the same release
is never nagged about again.
"""

import webbrowser

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton,
)

from rcd2000.updater import latest_release_tag, is_newer, RELEASES_URL
from rcd2000.gui.theme import (
    BG_MID, ACCENT, ACCENT_SOFT, ACCENT_SOFT_BORDER, TEXT_PRIMARY,
    TEXT_MUTED, RADIUS_SM,
)
from rcd2000.gui.widgets import icon as get_icon


class UpdateChecker(QThread):
    """Check the GitHub API off the UI thread; emit the result."""

    result = Signal(bool, str)  # (update_available, latest_tag)

    def __init__(self, local_version: str, parent=None):
        super().__init__(parent)
        self._local = local_version

    def run(self):
        tag = latest_release_tag()
        if tag is None:
            self.result.emit(False, "")
            return
        self.result.emit(is_newer(self._local, tag), tag)


class UpdateBanner(QWidget):
    """Persistent 'New version available' strip shown under the header.

    Non-blocking: it never interrupts work, it only offers an action.
    """

    dismissed = Signal(str)  # latest_tag - caller persists this

    def __init__(self, latest_tag: str, parent=None):
        super().__init__(parent)
        self.latest_tag = latest_tag
        self.setStyleSheet(f"background: {BG_MID};")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 6, 16, 6)
        lay.setSpacing(8)

        bell = QLabel()
        _bi = get_icon("fa5s.sync-alt", ACCENT, 14)
        if _bi is not None:
            bell.setPixmap(_bi.pixmap(14, 14))
        lay.addWidget(bell)

        text = QLabel(
            f"RCD2000 {latest_tag} is available - "
            f"you are on an older build."
        )
        text.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; background: transparent;")
        lay.addWidget(text, 1)

        btn = QToolButton()
        btn.setText("Get Update")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QToolButton {{ background: {ACCENT_SOFT}; color: {ACCENT};"
            f" border: 1px solid {ACCENT_SOFT_BORDER}; border-radius: {RADIUS_SM}px;"
            f" padding: 4px 12px; font-size: 12px; font-weight: 600; }}"
            f"QToolButton:hover {{ background: {ACCENT}; color: #FFFFFF; }}"
        )
        btn.clicked.connect(self._open_releases)
        lay.addWidget(btn)

        close_btn = QToolButton()
        _ci = get_icon("fa5s.times", TEXT_MUTED, 14)
        if _ci is not None:
            close_btn.setIcon(_ci)
        else:
            close_btn.setText("×")
        close_btn.setToolTip("Dismiss this update notice")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QToolButton {{ background: transparent; color: {TEXT_MUTED};"
            f" border: none; padding: 4px 8px; font-size: 14px; }}"
            f"QToolButton:hover {{ color: {ACCENT}; }}"
        )
        close_btn.clicked.connect(self._dismiss)
        lay.addWidget(close_btn)

    def _open_releases(self):
        webbrowser.open(RELEASES_URL)

    def _dismiss(self):
        self.dismissed.emit(self.latest_tag)
        self.hide()
