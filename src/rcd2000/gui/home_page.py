"""Home screen - the entry point of the app.

A clean launch surface with two paths only:

  · NEW JOB     → job header step → workbench
  · CONTINUE    → full History page (not a modal): search, recent
                  jobs, edit / delete, multi-delete, pagination

Shows a personal welcome using the engineer's name from Settings.
"""

import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
)
from PySide6.QtCore import Qt, Signal

from rcd2000 import __version__
from rcd2000.gui.theme import (
    BG_DARK, BG_MID, BG_LIGHT, BG_CARD, ACCENT, ACCENT_SOFT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_SIZE, SPACE,
    RADIUS_MD,
)
from rcd2000.gui.settings import SettingsStore


class HomePage(QWidget):
    """Welcome screen with New Job + Continue only."""

    new_job_requested = Signal()
    continue_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE[7], SPACE[6], SPACE[7], SPACE[7])
        outer.setSpacing(SPACE[4])

        # Brand mark
        brand = QVBoxLayout()
        brand.setSpacing(SPACE[1])
        logo = QLabel("RCD 2000")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            f"color: {ACCENT}; font-size: 44px; font-weight: 800;"
            f" letter-spacing: 3px; background: transparent;"
        )
        tag = QLabel("Reinforced Concrete Design  ·  BS 8110:1997")
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['md']}px; background: transparent;"
        )
        brand.addWidget(logo)
        brand.addWidget(tag)
        outer.addLayout(brand)
        outer.addSpacing(SPACE[6])

        # Welcome line (personal)
        self._welcome = QLabel()
        self._welcome.setAlignment(Qt.AlignCenter)
        self._welcome.setWordWrap(True)
        self._welcome.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; background: transparent;"
        )
        outer.addWidget(self._welcome)

        self._welcome_sub = QLabel()
        self._welcome_sub.setAlignment(Qt.AlignCenter)
        self._welcome_sub.setWordWrap(True)
        self._welcome_sub.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['base']}px; background: transparent;"
        )
        outer.addWidget(self._welcome_sub)
        outer.addSpacing(SPACE[5])

        # The two actions - big and clean
        new_btn = QPushButton("＋  NEW JOB")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setMinimumHeight(58)
        new_btn.setMinimumWidth(340)
        new_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #17140F; font-size: 18px;"
            f" font-weight: 700; border: none; border-radius: {RADIUS_MD}px;"
            f" padding: 12px 36px; }}"
            f"QPushButton:hover {{ background: #E6A13F; }}"
            f"QPushButton:pressed {{ background: #B8751F; }}"
        )
        new_btn.clicked.connect(self.new_job_requested.emit)

        continue_btn = QPushButton("CONTINUE")
        continue_btn.setCursor(Qt.PointingHandCursor)
        continue_btn.setMinimumHeight(58)
        continue_btn.setMinimumWidth(340)
        continue_btn.setStyleSheet(
            f"QPushButton {{ background: {BG_CARD}; color: {TEXT_PRIMARY};"
            f" font-size: 18px; font-weight: 600; border: 1px solid {BORDER};"
            f" border-radius: {RADIUS_MD}px; padding: 12px 36px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT};"
            f" background: {BG_LIGHT}; }}"
        )
        continue_btn.clicked.connect(self.continue_requested.emit)

        actions = QVBoxLayout()
        actions.setSpacing(SPACE[3])
        actions.addWidget(new_btn, alignment=Qt.AlignCenter)
        actions.addWidget(continue_btn, alignment=Qt.AlignCenter)
        outer.addLayout(actions)

        # Keyboard hint
        hint = QLabel("New Job:   Ctrl+N        Continue:   Ctrl+C     Home:   Ctrl+H")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;"
            f" letter-spacing: 0.4px;"
        )
        outer.addWidget(hint)
        outer.addStretch(1)

        # Settings link at bottom
        bottom = QHBoxLayout()
        bottom.addStretch()
        settings_btn = QToolButton()
        settings_btn.setText("⚙ Settings")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setToolTip("Edit your profile (prefills new jobs)")
        settings_btn.setStyleSheet(
            f"QToolButton {{ background: transparent; color: {TEXT_SECONDARY};"
            f" border: none; padding: 6px 12px; font-size: {FONT_SIZE['sm']}px; }}"
            f"QToolButton:hover {{ color: {ACCENT}; }}"
        )
        settings_btn.clicked.connect(self.settings_requested.emit)
        ver = QLabel(f"v{__version__}")
        ver.setStyleSheet(f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;")
        bottom.addWidget(settings_btn)
        bottom.addWidget(ver)
        outer.addLayout(bottom)

        self.refresh_welcome()

    # ── welcome ────────────────────────────────────────────────────

    def refresh_welcome(self):
        now = datetime.now()
        hour = now.hour
        if hour < 12:
            tod = "Good morning"
        elif hour < 17:
            tod = "Good afternoon"
        else:
            tod = "Good evening"

        profile = SettingsStore.load()
        if profile.full_name.strip():
            greeting = f"Welcome back, {profile.full_name.strip()}!"
            sub = (
                f"{tod}. Set up a new concrete design job, or continue "
                "one of your existing projects."
            )
        else:
            greeting = "Welcome to RCD 2000"
            sub = (
                "Start a new concrete design job, or continue an existing "
                "project. Tip: fill your profile in Settings for faster "
                "job creation."
            )
        self._welcome.setText(greeting)
        self._welcome_sub.setText(sub)