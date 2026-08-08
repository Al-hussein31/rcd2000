"""Job Header dialog - the pre-design step of the original RCD2000 flow.

Mirrors the FORTRAN prompts from Oyenuga's book:

    ENTER YOUR COMPANY'S NAME
    ENTER JOB REFERENCE
    ENTER DESIGN ENGINEER
    ENTER DESIGNING DATE
    ENTER CONCRETE & STEEL STRESSES   (fcu, fy, + fyv / soil pressure / steel %)

plus the output file name (asked before any design work in the original
programs) and the closing confirmation:

    Are the above Info. correct? - Y/N
"""

import os
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFileDialog,
    QPushButton, QComboBox,
)
from PySide6.QtCore import Qt

from rcd2000.gui.theme import (
    BG_MID, BG_LIGHT, BG_CARD, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER, FONT_SIZE, SPACE, RADIUS_MD,
)
from rcd2000.gui.widgets import (
    button, label, Card, fcu_combo, fy_combo, combo, spinbox,
)
from rcd2000.gui.settings import SettingsStore, UserProfile

#: Default date format used by the original tool:  TUE. 14/09/26.
_DEFAULT_DATE = lambda: datetime.now().strftime("%a. %d/%m/%y.")


def _today() -> str:
    return _DEFAULT_DATE()


class JobHeaderDialog(QDialog):
    """Collect the job header.  Returns a plain dict via ``header()``."""

    def __init__(self, parent=None, existing: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("New Job - Project & Design Details")
        self.setMinimumWidth(560)
        self.setStyleSheet(f"background: {BG_MID}; color: {TEXT_PRIMARY};")
        self._existing = existing or {}
        prefill = self._profile_prefill(self._existing)

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE[3])

        title = label("NEW JOB - PROJECT & DESIGN DETAILS", bold=True, size=15)
        title.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        layout.addWidget(title)

        sub = label(
            "These details appear at the top of every output report.",
            secondary=True, size=12,
        )
        layout.addWidget(sub)

        # ── Project / job details ──────────────────────────────────
        c1 = Card("PROJECT DETAILS")
        self.company = QLineEdit(prefill.get("company", ""))
        self.job_ref = QLineEdit(prefill.get("job_ref", ""))
        self.engineer = QLineEdit(prefill.get("engineer", ""))
        self.date = QLineEdit(prefill.get("date", _today()))
        c1.add_row("Company's Name:*", self.company)
        c1.add_row("Job Reference:*", self.job_ref)
        c1.add_row("Design Engineer:", self.engineer)
        c1.add_row("Designing Date:", self.date)
        for w in (self.company, self.job_ref, self.engineer, self.date):
            w.setPlaceholderText("-")
            w.setStyleSheet(self._input_style())
        self.company.textChanged.connect(self._validate)
        self.job_ref.textChanged.connect(self._validate)
        layout.addWidget(c1)

        # ── Note (optional) ────────────────────────────────────────
        c1b = Card("JOB NOTE (OPTIONAL)")
        self.note = QLineEdit(prefill.get("note", ""))
        self.note.setPlaceholderText("e.g. Block A - ground floor columns")
        self.note.setStyleSheet(self._input_style())
        c1b.add_row("", self.note)
        layout.addWidget(c1b)

        # ── Output file ────────────────────────────────────────────
        c2 = Card("OUTPUT FILE")
        file_row = QHBoxLayout()
        file_row.setSpacing(SPACE[2])
        self.output_file = QLineEdit(self._existing.get("output_file", ""))
        self.output_file.setPlaceholderText("e.g. C:/designs/job1.txt")
        self.output_file.setStyleSheet(self._input_style())
        browse = button("Browse…", accent=False)
        browse.clicked.connect(self._browse_output)
        file_row.addWidget(self.output_file, 1)
        file_row.addWidget(browse)
        c2.add_layout(file_row)
        c2.add_row("", label(
            "Reports are written here when you export the job.",
            secondary=True, size=11,
        ))
        layout.addWidget(c2)

        # ── Concrete & steel stresses ──────────────────────────────
        c3 = Card("CONCRETE & STEEL STRESSES")
        self.fcu = fcu_combo()
        self.fy = fy_combo()
        self.fyv = combo(["250", "410", "460"])
        # Materials should not be fixed lists - make them editable
        for cb in (self.fcu, self.fy, self.fyv):
            cb.setEditable(True)
            cb.setInsertPolicy(QComboBox.NoInsert)
        self.soil_pressure = spinbox(0, 999999999, 5, 150, 1, " kN/m²")
        self.max_steel_pct = spinbox(0, 999999999, 0.25, 6.0, 2, " %")
        self.dh = spinbox(0, 999999999, 0.05, 0.95, 2)
        c3.add_row("fcu (N/mm²):", self.fcu)
        c3.add_row("fy (N/mm²):", self.fy)
        c3.add_row("fyv - stirrup (N/mm²):", self.fyv)
        c3.add_row("Allowable soil pressure (bases):", self.soil_pressure)
        c3.add_row("Max. steel % (columns):", self.max_steel_pct)
        c3.add_row("D/H ratio (columns):", self.dh)
        layout.addWidget(c3)

        # ── Confirmation (Y/N, like the original) ───────────────────
        confirm_hint = label(
            "Are the above info correct?", bold=True, size=13,
        )
        confirm_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(confirm_hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACE[2])
        cancel_btn = button("No - Cancel", accent=False)
        cancel_btn.clicked.connect(self.reject)
        self.ok_btn = button("Yes - Start Design")
        self.ok_btn.clicked.connect(self._on_ok)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.ok_btn)
        layout.addLayout(btn_row)

        self._restore_existing()
        self.company.setFocus()
        self._validate()

    # ── profile prefill ───────────────────────────────────────────

    @staticmethod
    def _profile_prefill(existing: dict | None) -> dict:
        """Start from the user profile, then layer existing values on top."""
        profile = SettingsStore.load()
        base = {
            "company": profile.company,
            "job_ref": "",
            "engineer": profile.engineer or profile.full_name,
            "date": _today(),
        }
        if profile.job_ref_prefix:
            base["job_ref"] = f"{profile.job_ref_prefix}-"
        if existing:
            base.update(existing)
        return base

    def _validate(self):
        """Required: company + job reference. Disable Yes until filled."""
        ok = bool(self.company.text().strip() and self.job_ref.text().strip())
        self.ok_btn.setEnabled(ok)
        for w, req in ((self.company, True), (self.job_ref, True)):
            border = f"1px solid {ACCENT}" if req and not w.text().strip() else f"1px solid {BORDER}"
            w.setStyleSheet(
                f"QLineEdit {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
                f" border: {border}; border-radius: {RADIUS_MD}px;"
                f" padding: 7px 10px; font-size: {FONT_SIZE['base']}px; }}"
                f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
            )

    def _on_ok(self):
        if not (self.company.text().strip() and self.job_ref.text().strip()):
            return
        self.accept()

    # ── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _input_style() -> str:
        return (
            f"QLineEdit {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;"
            f" padding: 7px 10px; font-size: {FONT_SIZE['base']}px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )

    def _browse_output(self):
        start = self.output_file.text().strip()
        start_dir = os.path.dirname(start) if start else os.path.expanduser("~")
        path, _ = QFileDialog.getSaveFileName(
            self, "Output File Name", start_dir,
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            self.output_file.setText(path)

    def _restore_existing(self):
        # We already layered existing values into the fields at build;
        # this pass only handles the material/spin widgets from existing.
        ex = self._existing if hasattr(self, "_existing") else {}
        if not ex:
            return
        if ex.get("fcu") is not None:
            self._set_combo_int(self.fcu, ex["fcu"])
        if ex.get("fy") is not None:
            self._set_combo_int(self.fy, ex["fy"])
        if ex.get("fyv") is not None:
            self._set_combo_int(self.fyv, ex["fyv"])
        if ex.get("soil_pressure") is not None:
            self.soil_pressure.setValue(ex["soil_pressure"])
        if ex.get("max_steel_pct") is not None:
            self.max_steel_pct.setValue(ex["max_steel_pct"])
        if ex.get("dh") is not None:
            self.dh.setValue(ex["dh"])

    @staticmethod
    def _set_combo_int(cb, value):
        # Editable combos: set the text, or select the matching preset
        idx = cb.findText(str(int(value)))
        if idx >= 0:
            cb.setCurrentIndex(idx)
        else:
            cb.setCurrentText(str(int(value)))

    def header(self) -> dict:
        """Return the validated header dict."""
        return {
            "company": self.company.text().strip(),
            "job_ref": self.job_ref.text().strip(),
            "engineer": self.engineer.text().strip(),
            "date": self.date.text().strip() or _today(),
            "output_file": self.output_file.text().strip(),
            "fcu": self._combo_num(self.fcu, 30),
            "fy": self._combo_num(self.fy, 460),
            "fyv": self._combo_num(self.fyv, 250),
            "soil_pressure": self.soil_pressure.value(),
            "max_steel_pct": self.max_steel_pct.value(),
            "dh": self.dh.value(),
            "note": self.note.text().strip(),
        }

    @staticmethod
    def _combo_num(cb, default: int) -> int:
        """Read an editable combo as a number; fall back to *default*."""
        try:
            return int(float(cb.currentText().strip()))
        except (ValueError, TypeError):
            return default

    # ── convenience ────────────────────────────────────────────────

    @staticmethod
    def ask(parent=None, existing: dict | None = None) -> dict | None:
        """Show the dialog; return the header dict or None if cancelled."""
        dlg = JobHeaderDialog(parent=parent, existing=existing)
        if dlg.exec() == QDialog.Accepted:
            return dlg.header()
        return None
