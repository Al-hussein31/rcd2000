"""Settings page - edit your profile so new jobs prefill faster.

Profile values are saved to the settings store and used to prefill the
New Job header dialog. The user can still change any prefilled value
per job.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt, Signal

from rcd2000.gui.theme import (
    BG_LIGHT, ACCENT, TEXT_PRIMARY,
    TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_SIZE, SPACE, RADIUS_MD,
)
from rcd2000.gui.settings import UserProfile, SettingsStore
from rcd2000.gui.widgets import Card
#: Card is a flat QFrame with subtle border, on-brand
_CardWidget = Card


class SettingsPage(QWidget):
    """User profile editor; prefill source for the job header dialog."""

    back_requested = Signal()
    status_message = Signal(str, bool)
    profile_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _input_style(self) -> str:
        return (
            f"QLineEdit {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;"
            f" padding: 9px 12px; font-size: {FONT_SIZE['base']}px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE[6], SPACE[5], SPACE[6], SPACE[5])
        outer.setSpacing(SPACE[3])

        top = QHBoxLayout()
        title = QLabel("SETTINGS")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 700; background: transparent;"
        )
        back = QLabel()
        back_l = QHBoxLayout(back)
        back.setText("← Back")
        back.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent; font-size: {FONT_SIZE['base']}px;"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px; padding: 8px 18px;"
        )
        back.setCursor(Qt.PointingHandCursor)
        back.mousePressEvent = lambda e: self.back_requested.emit()
        top.addWidget(title)
        top.addStretch()
        top.addWidget(back)
        outer.addLayout(top)

        sub = QLabel(
            "Your profile is used to prefill every new job header. "
            "You can still change the prefilled details per job."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['base']}px; background: transparent;"
        )
        outer.addWidget(sub)
        outer.addSpacing(SPACE[2])

        # Profile card
        card = _CardWidget()
        card_lay = card.content()
        card_lay.setSpacing(SPACE[2])
        heading = QLabel("PROFILE")
        heading.setStyleSheet(
            f"color: {ACCENT}; font-size: {FONT_SIZE['sm']}px; font-weight: 700;"
            f" letter-spacing: 0.6px; background: transparent;"
        )
        card_lay.addWidget(heading)

        self.full_name = QLineEdit()
        self.company_in = QLineEdit()
        self.engineer_in = QLineEdit()
        self.prefix_in = QLineEdit()
        self.outdir_in = QLineEdit()
        self.datefmt_in = QLineEdit()
        self.city_in = QLineEdit()
        for w, lbl, ph in [
            (self.full_name, "Full name", "e.g. Eng. Ade Oyenuga"),
            (self.company_in, "Company", "e.g. ACME Engineering Ltd."),
            (self.engineer_in, "Design Engineer", "e.g. A. Oyenuga (used as Designed by)"),
            (self.prefix_in, "Job Ref Prefix", "e.g. FG-2026 (first part of JOB REF)"),
            (self.outdir_in, "Default Output Folder", "e.g. /Users/you/Documents/designs (optional)"),
            (self.datefmt_in, "Date Format", "%a. %d/%m/%y."),
            (self.city_in, "City (for home greeting weather)", "e.g. Lagos (optional)"),
        ]:
            lab = QLabel(lbl)
            lab.setStyleSheet(
                f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['sm']}px; background: transparent;"
            )
            w.setPlaceholderText(ph)
            w.setStyleSheet(self._input_style())
            card_lay.addWidget(lab)
            card_lay.addWidget(w)

        date_hint = QLabel(
            "Date format uses Python strftime codes: %a weekday, %d day, "
            "%m month, %y year."
        )
        date_hint.setWordWrap(True)
        date_hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;"
        )
        card_lay.addWidget(date_hint)
        outer.addWidget(card, 1)

        # Save row
        row = QHBoxLayout()
        self.save_btn = QPushButton("Save Profile")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setMinimumHeight(42)
        self.save_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #17140F; font-weight: 700;"
            f" font-size: 15px; border: none; border-radius: {RADIUS_MD}px;"
            f" padding: 10px 30px; }}"
            f"QPushButton:hover {{ background: #E6A13F; }}"
        )
        self.save_btn.clicked.connect(self._save)
        row.addStretch()
        row.addWidget(self.save_btn)
        outer.addLayout(row)

        self.load_profile()

    def load_profile(self):
        p = SettingsStore.load()
        self.full_name.setText(p.full_name)
        self.company_in.setText(p.company)
        self.engineer_in.setText(p.engineer)
        self.prefix_in.setText(p.job_ref_prefix)
        self.outdir_in.setText(p.default_output_dir)
        self.datefmt_in.setText(p.date_format)
        self.city_in.setText(p.city)

    def _save(self):
        profile = UserProfile(
            full_name=self.full_name.text().strip(),
            company=self.company_in.text().strip(),
            engineer=self.engineer_in.text().strip(),
            job_ref_prefix=self.prefix_in.text().strip(),
            default_output_dir=self.outdir_in.text().strip(),
            date_format=self.datefmt_in.text().strip() or "%a. %d/%m/%y.",
            city=self.city_in.text().strip(),
        )
        SettingsStore.save(profile)
        self.profile_changed.emit()
        self.status_message.emit("Profile saved. New jobs will prefill with these details.", False)