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
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFileDialog,
    QPushButton, QComboBox, QWidget,
)
from PySide6.QtCore import Qt, QStandardPaths

from rcd2000.gui.theme import (
    BG_MID, BG_LIGHT, BG_CARD, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER, ERROR, FONT_SIZE, SPACE, RADIUS_MD, RADIUS_SM,
)
from rcd2000.gui.widgets import (
    button, label, Card, fcu_combo, fy_combo, combo, spinbox, icon,
)
from rcd2000.gui.settings import SettingsStore, UserProfile

#: Default date format used by the original tool:  TUE. 14/09/26.
_DEFAULT_DATE = lambda: datetime.now().strftime("%a. %d/%m/%y.")

#: Name of the folder created inside the user's Documents folder.
DEFAULT_OUTPUT_FOLDER = "RCD2000_output"


def default_output_dir() -> Path:
    """Return the default output folder, creating it if missing.

    Uses Qt's DocumentsLocation (localization- and sandbox-aware on macOS,
    e.g. ``~/Documents``) instead of a hardcoded path, so reports always
    land somewhere the user can actually find.
    """
    docs = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    base = Path(docs) if docs else Path.home() / "Documents"
    folder = base / DEFAULT_OUTPUT_FOLDER
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Last resort: never let a read-only Documents block the dialog.
        folder = Path.home() / DEFAULT_OUTPUT_FOLDER
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolve_output_path(text: str, base_dir: Path | None = None) -> str:
    """Resolve a typed output file name to an absolute path.

    Rules:
    - empty text            -> "" (the field stays optional)
    - absolute path         -> used exactly as typed (e.g. Browse results)
    - bare name / relative  -> joined under the default output folder,
                               NEVER the process working directory.
    """
    t = (text or "").strip()
    if not t:
        return ""
    p = Path(os.path.expanduser(t))
    if p.is_absolute():
        return str(p)
    base = base_dir if base_dir is not None else default_output_dir()
    return str(base / p)



def _today() -> str:
    return _DEFAULT_DATE()


def check_output_path(text: str, base_dir: Path | None = None) -> tuple[bool, str]:
    """Validate a typed output file path.

    Returns ``(ok, message)``.  Empty text is valid (the field is
    optional - export simply warns).  Relative names resolve under the
    default output folder (auto-created, so always valid).  An absolute
    path is valid when its parent directory exists and is writable.
    """
    t = (text or "").strip()
    if not t:
        return True, ""
    resolved = resolve_output_path(t, base_dir)
    parent = Path(resolved).parent
    if not parent.exists() or not parent.is_dir():
        return False, f"Folder does not exist: {parent}"
    if not os.access(parent, os.W_OK):
        return False, f"Folder is not writable: {parent}"
    return True, ""


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
        note_row = QHBoxLayout()
        note_row.setSpacing(SPACE[3])
        note_icon = QLabel()
        _ni = icon("fa5s.sticky-note", TEXT_SECONDARY, 16)
        if _ni is not None:
            note_icon.setPixmap(_ni.pixmap(16, 16))
        note_icon.setStyleSheet("background: transparent;")
        note_icon.setAlignment(Qt.AlignCenter)
        note_row.addWidget(note_icon, 0, Qt.AlignCenter)
        note_row.addWidget(self.note, 1)
        c1b.add_layout(note_row)
        layout.addWidget(c1b)

        # ── Output file ────────────────────────────────────────────
        # Split control: a solid, read-only folder prefix (only Browse…
        # or Default changes it) joined to an editable file-name field,
        # all inside one bordered container so it reads as a single input.
        c2 = Card("OUTPUT FILE")
        self._folder = QLineEdit()
        self._folder.setReadOnly(True)
        self._folder.setFrame(False)
        self._folder.setCursor(Qt.ArrowCursor)
        self._folder.setToolTip(
            f"Folder for reports - change it with Browse… only.\n"
            f"Default: Documents/{DEFAULT_OUTPUT_FOLDER}"
        )
        self._folder.setStyleSheet(
            f"background: transparent; color: {TEXT_MUTED};"
            f" font-size: 12px; border: none;"
            f" padding: 0 {SPACE[1]}px;"
        )
        self.output_file = QLineEdit()  # file name only
        self.output_file.setFrame(False)
        self.output_file.setPlaceholderText("report name, e.g. job1.txt")
        self.output_file.setToolTip(
            "Type just a name - it lands in the folder shown on the left. "
            "Use Browse… to save somewhere else."
        )
        self.output_file.setStyleSheet(
            f"background: transparent; color: {TEXT_PRIMARY};"
            f" font-size: 13px; border: none;"
            f" padding: 0 {SPACE[1]}px;"
        )
        split = QWidget()
        split.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-radius: {RADIUS_SM}px;"
        )
        split_row = QHBoxLayout(split)
        split_row.setContentsMargins(SPACE[2], 0, SPACE[2], 0)
        split_row.setSpacing(0)
        split_row.addWidget(self._folder, 0)
        split_row.addWidget(self.output_file, 1)

        browse = button("Browse…", accent=False)
        browse.clicked.connect(self._browse_output)
        default_btn = button("Default", accent=False)
        default_btn.setToolTip(
            f"Reset the folder to Documents/{DEFAULT_OUTPUT_FOLDER}"
        )
        default_btn.clicked.connect(self._reset_output_folder)
        file_row = QHBoxLayout()
        file_row.setSpacing(SPACE[2])
        file_row.addWidget(split, 1)
        file_row.addWidget(browse)
        file_row.addWidget(default_btn)
        c2.add_layout(file_row)
        self._output_error = label("", secondary=True, size=11)
        self._output_error.setWordWrap(True)
        self._output_error.setStyleSheet(
            f"color: {ERROR}; background: transparent;"
        )
        self._output_error.hide()
        c2.add_row("", self._output_error)
        c2.add_row("", label(
            f"Reports are written here when you export the job. A bare name "
            f"goes to Documents/{DEFAULT_OUTPUT_FOLDER} - use Browse… to "
            f"save anywhere else.",
            secondary=True, size=11,
        ))
        self.output_file.editingFinished.connect(self._validate_output_path)
        layout.addWidget(c2)
        # Prefill from a stored job: split the saved full path back into
        # folder + name, keeping any folder the user browsed to.
        existing_path = self._existing.get("output_file", "").strip()
        if existing_path:
            ep = Path(os.path.expanduser(existing_path))
            self._folder.setText(self._display_folder(ep.parent))
            self.output_file.setText(ep.name)
        else:
            self._folder.setText(self._display_folder(default_output_dir()))

        # ── Concrete & steel stresses ──────────────────────────────
        # Required inputs: the original book programs read these with
        # READ(1,*) and no defaults - a design cannot proceed without
        # them.  We preset sensible values but block creation if the
        # user clears any of them.
        c3 = Card("CONCRETE & STEEL STRESSES*")
        self.fcu = fcu_combo()
        self.fy = fy_combo()
        self.fyv = combo(["250", "410", "460"])
        # Materials should not be fixed lists - make them editable
        for cb in (self.fcu, self.fy, self.fyv):
            cb.setEditable(True)
            cb.setInsertPolicy(QComboBox.NoInsert)
            cb.currentTextChanged.connect(self._validate)
        self.soil_pressure = spinbox(0, 999999999, 5, 150, 1, " kN/m²")
        self.max_steel_pct = spinbox(0, 999999999, 0.25, 6.0, 2, " %")
        self.dh = spinbox(0, 999999999, 0.05, 0.95, 2)
        c3.add_row("fcu (N/mm²):*", self.fcu)
        c3.add_row("fy (N/mm²):*", self.fy)
        c3.add_row("fyv - stirrup (N/mm²):*", self.fyv)
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
        """Required: company + job reference + material stresses (the
        book's programs never default these).  Disable Yes until filled."""
        company_ok = bool(self.company.text().strip())
        ref_ok = bool(self.job_ref.text().strip())
        stresses_ok = (
            self._combo_num_ok(self.fcu)
            and self._combo_num_ok(self.fy)
            and self._combo_num_ok(self.fyv)
        )
        self.ok_btn.setEnabled(company_ok and ref_ok and stresses_ok)
        for w, req in ((self.company, True), (self.job_ref, True)):
            border = f"1px solid {ACCENT}" if req and not w.text().strip() else f"1px solid {BORDER}"
            w.setStyleSheet(
                f"QLineEdit {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
                f" border: {border}; border-radius: {RADIUS_MD}px;"
                f" padding: 7px 10px; font-size: {FONT_SIZE['base']}px; }}"
                f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
            )

    @staticmethod
    def _combo_num_ok(cb) -> bool:
        text = cb.currentText().strip()
        if not text:
            return False
        try:
            return float(text) > 0
        except ValueError:
            return False

    def _on_ok(self):
        if not (self.company.text().strip() and self.job_ref.text().strip()):
            return
        if not (self._combo_num_ok(self.fcu) and self._combo_num_ok(self.fy)
                and self._combo_num_ok(self.fyv)):
            return
        self.accept()

    # ── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _input_style(invalid: bool = False) -> str:
        border = ERROR if invalid else BORDER
        return (
            f"QLineEdit {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {border}; border-radius: {RADIUS_MD}px;"
            f" padding: 7px 10px; font-size: {FONT_SIZE['base']}px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )

    def _display_folder(self, folder: Path) -> str:
        """Show the folder with ~ shorthand when it is under the home dir."""
        s = str(folder)
        home = str(Path.home())
        if s == home:
            return "~"
        if s.startswith(home + os.sep):
            return "~" + s[len(home):]
        return s

    def _joined_text(self) -> str:
        """The full (possibly ~-shorthand) path as the user sees it."""
        folder = self._folder.text().strip()
        name = self.output_file.text().strip()
        if not folder:
            folder = str(default_output_dir())
        return os.path.join(folder, name) if name else folder

    def _validate_output_path(self):
        """Run the path checks on the resolved output path; update the
        field is optional and export warns instead."""
        ok, message = check_output_path(self._joined_text())
        if not ok:
            self.output_file.setStyleSheet(
                f"background: transparent; color: {ERROR};"
                f" font-size: 13px; border: none;"
                f" padding: 0 {SPACE[1]}px;"
            )
            self._output_error.setText(message)
            self._output_error.show()
        else:
            self.output_file.setStyleSheet(
                f"background: transparent; color: {TEXT_PRIMARY};"
                f" font-size: 13px; border: none;"
                f" padding: 0 {SPACE[1]}px;"
            )
            self._output_error.hide()

    def _browse_output(self):
        folder = os.path.expanduser(self._folder.text().strip())
        if not folder:
            folder = str(default_output_dir())
        start = os.path.join(folder, self.output_file.text().strip())
        path, _ = QFileDialog.getSaveFileName(
            self, "Output File Name", start,
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            p = Path(path)
            self._folder.setText(self._display_folder(p.parent))
            self.output_file.setText(p.name)
            self._validate_output_path()

    def _reset_output_folder(self):
        self._folder.setText(self._display_folder(default_output_dir()))
        self._validate_output_path()

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
        """Return the validated header dict.

        ``output_file`` is always the RESOLVED absolute path: a bare name
        becomes ``<Documents>/RCD2000_output/<name>`` so export can never
        lose the file in the process working directory.
        """
        return {
            "company": self.company.text().strip(),
            "job_ref": self.job_ref.text().strip(),
            "engineer": self.engineer.text().strip(),
            "date": self.date.text().strip() or _today(),
            "output_file": resolve_output_path(self._joined_text()),
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
