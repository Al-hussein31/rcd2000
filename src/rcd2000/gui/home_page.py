"""Home screen - the entry point of the app.

A clean launch surface with two paths only:

  · NEW JOB     → job header step → workbench
  · CONTINUE    → full History page (not a modal): search, recent
                  jobs, edit / delete, multi-delete, pagination

The two actions sit side by side and the whole block is centred in the
page.  CONTINUE is hidden until there is at least one saved job, and the
greeting is personalised with the time of day, the engineer's name from
Settings, and (when a city is configured and the network is up) the
current weather via Open-Meteo.
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
)
from PySide6.QtCore import Qt, Signal

from rcd2000 import __version__
from rcd2000.gui.theme import (
    BG_LIGHT, BG_CARD, ACCENT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_SIZE, SPACE,
    RADIUS_MD,
)
from rcd2000.gui.settings import SettingsStore
from rcd2000.gui.job import JobStore


def time_greeting(hour: int) -> str:
    if hour < 5:
        return "Working late"
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


class HomePage(QWidget):
    """Welcome screen with New Job + Continue only."""

    new_job_requested = Signal()
    continue_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._weather = None

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE[7], 0, SPACE[7], 0)
        outer.setSpacing(0)

        # Vertical centring: the content block floats mid-page.
        outer.addStretch(1)

        content = QVBoxLayout()
        content.setSpacing(SPACE[4])

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
        content.addLayout(brand)
        content.addSpacing(SPACE[6])

        # Welcome line (personal + time of day + weather)
        self._welcome = QLabel()
        self._welcome.setAlignment(Qt.AlignCenter)
        self._welcome.setWordWrap(True)
        self._welcome.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; background: transparent;"
        )
        content.addWidget(self._welcome)

        self._welcome_sub = QLabel()
        self._welcome_sub.setAlignment(Qt.AlignCenter)
        self._welcome_sub.setWordWrap(True)
        self._welcome_sub.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['base']}px; background: transparent;"
        )
        content.addWidget(self._welcome_sub)
        content.addSpacing(SPACE[5])

        # The two actions - side by side, big and clean
        self.new_btn = QPushButton("＋  NEW JOB")
        self.new_btn.setCursor(Qt.PointingHandCursor)
        self.new_btn.setMinimumHeight(58)
        self.new_btn.setMinimumWidth(240)
        self.new_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #17140F; font-size: 18px;"
            f" font-weight: 700; border: none; border-radius: {RADIUS_MD}px;"
            f" padding: 12px 36px; }}"
            f"QPushButton:hover {{ background: #E6A13F; }}"
            f"QPushButton:pressed {{ background: #B8751F; }}"
        )
        self.new_btn.clicked.connect(self.new_job_requested.emit)

        self.continue_btn = QPushButton("CONTINUE")
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setMinimumHeight(58)
        self.continue_btn.setMinimumWidth(240)
        self.continue_btn.setStyleSheet(
            f"QPushButton {{ background: {BG_CARD}; color: {TEXT_PRIMARY};"
            f" font-size: 18px; font-weight: 600; border: 1px solid {BORDER};"
            f" border-radius: {RADIUS_MD}px; padding: 12px 36px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT};"
            f" background: {BG_LIGHT}; }}"
        )
        self.continue_btn.clicked.connect(self.continue_requested.emit)

        actions = QHBoxLayout()
        actions.setSpacing(SPACE[3])
        actions.addWidget(self.new_btn, alignment=Qt.AlignCenter)
        actions.addWidget(self.continue_btn, alignment=Qt.AlignCenter)
        content.addLayout(actions)

        # Keyboard hint
        hint = QLabel("New Job:   Ctrl+N        Continue:   Ctrl+C     Home:   Ctrl+H")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;"
            f" letter-spacing: 0.4px;"
        )
        content.addWidget(hint)

        content.addStretch(1)

        # Settings link at bottom of the content block
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
        content.addLayout(bottom)

        outer.addLayout(content)
        outer.addStretch(1)

        self.refresh_welcome()

    # ── welcome ────────────────────────────────────────────────────

    def refresh_welcome(self):
        self._refresh_actions_visibility()
        now = datetime.now()
        tod = time_greeting(now.hour)

        profile = SettingsStore.load()
        name = profile.full_name.strip()
        greeting = f"{tod}, {name}!" if name else f"{tod}!"

        # Weather is optional and non-blocking: configured city + network
        if profile.city.strip():
            weather = self._get_weather(profile.city.strip())
            if weather:
                cond = weather.get("condition", "")
                loc = weather.get("city", profile.city).title()
                extra = f" · {weather['temp_c']}°C"
                if cond:
                    extra += f", {cond}"
                greeting = f"{greeting[:-1]}  -  {loc}{extra}!"

        has_jobs = bool(JobStore.list_jobs())
        if name:
            sub = (
                "Set up a new concrete design job, or continue one of your "
                "existing projects."
            )
        else:
            sub = (
                "Start a new concrete design job, or continue an existing "
                "project. Tip: fill your profile in Settings for faster "
                "job creation."
            )
        if not has_jobs:
            sub = "Set up your first concrete design job to get going."
        self._welcome.setText(greeting)
        self._welcome_sub.setText(sub)

    def _get_weather(self, city: str):
        """Fetch weather once per home visit; degrade silently offline."""
        from rcd2000.gui import weather as weather_mod
        return weather_mod.fetch_weather(city)

    def _refresh_actions_visibility(self):
        """Hide CONTINUE until there is at least one saved job."""
        has_jobs = bool(JobStore.list_jobs())
        self.continue_btn.setVisible(has_jobs)
