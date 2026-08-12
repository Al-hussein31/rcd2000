"""Export dialog for the RCD2000 workbench.

Lets the user export designs from a job in one of several formats:

  · TXT / PDF  - text or PDF report(s)
  · DXF        - AutoCAD drawing sheet(s)
  · DWG        - native AutoCAD (needs ODA File Converter or APS)
  · IFC        - IFC4 BIM model (needs IfcOpenShell)

Two scopes:
  · "This design"  - the panel the export was launched from
  · "All designed" - every designed item in the job

DXF/DWG write one file per design into a chosen folder (plus an optional
combined multi-sheet file). IFC always writes one model file.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QCheckBox,
    QFrame,
)

from rcd2000.gui.theme import (
    ACCENT,
    BG_CARD,
    BG_MID,
    BORDER,
    ERROR,
    ERROR_BG,
    FONT_SIZE,
    SPACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from rcd2000.gui.widgets import label, combo, Card


# Format descriptors: (label, extension, needs_extra)
FORMATS = [
    ("Text report (.txt)", "txt", None),
    ("PDF report (.pdf)", "pdf", None),
    ("DXF drawing (.dxf)", "dxf", None),
    ("DWG drawing (.dwg)", "dwg", None),
    ("IFC4 BIM model (.ifc)", "ifc", "ifc"),
]

# Which module keys have a CAD adapter (beam/column/slab/base/stair)
CAD_ADAPTER_KEYS = {"beam", "column", "slab", "base", "stair"}


class ExportDialog(QDialog):
    """Choose scope + format + destination for a job export."""

    def __init__(self, scope_items: list, header: dict, parent=None,
                 default_scope: str = "all"):
        """``scope_items``: list of (uid, label, type_key, designed, stale)
        for every item in the job. ``header`` is the job header dict."""
        super().__init__(parent)
        self._scope_items = scope_items
        self._header = header
        self._default_scope = default_scope
        self._out_dir = ""

        self.setWindowTitle("Export")
        self.resize(560, 460)
        self._build_ui()
        self._on_format_changed()

    # ── construction ────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE[5], SPACE[4], SPACE[5], SPACE[4])
        root.setSpacing(SPACE[3])

        # ── Scope ──────────────────────────────────────────────────
        scope_card = Card("Scope")
        scope_v = QVBoxLayout()
        scope_v.setContentsMargins(SPACE[3], SPACE[2], SPACE[3], SPACE[3])
        scope_v.setSpacing(SPACE[2])

        self.this_radio = QRadioButton("This design only")
        self.all_radio = QRadioButton("All designed items in job")
        if self._default_scope == "this":
            self.this_radio.setChecked(True)
        else:
            self.all_radio.setChecked(True)
        self.this_radio.toggled.connect(self._refresh_summary)
        self.all_radio.toggled.connect(self._refresh_summary)

        scope_v.addWidget(self.this_radio)
        scope_v.addWidget(self.all_radio)

        self._scope_summary = QLabel("")
        self._scope_summary.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['xs']}px;"
            f" background: transparent;"
        )
        self._scope_summary.setWordWrap(True)
        scope_v.addWidget(self._scope_summary)
        scope_card.add_layout(scope_v)
        root.addWidget(scope_card)

        # ── Format ─────────────────────────────────────────────────
        fmt_card = Card("Format")
        fmt_v = QVBoxLayout()
        fmt_v.setContentsMargins(SPACE[3], SPACE[2], SPACE[3], SPACE[3])
        fmt_v.setSpacing(SPACE[2])

        row = QHBoxLayout()
        row.addWidget(label("Format:", bold=True))
        self.format_combo = QComboBox()
        for fmt_label, ext, _extra in FORMATS:
            self.format_combo.addItem(fmt_label, ext)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        row.addWidget(self.format_combo, 1)
        fmt_v.addLayout(row)

        self._fmt_hint = QLabel("")
        self._fmt_hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px;"
            f" background: transparent;"
        )
        self._fmt_hint.setWordWrap(True)
        fmt_v.addWidget(self._fmt_hint)

        self.combined_check = QCheckBox(
            "Also write one combined multi-element DXF file (_all.dxf)"
        )
        self.combined_check.setChecked(True)
        fmt_v.addWidget(self.combined_check)

        fmt_card.add_layout(fmt_v)
        root.addWidget(fmt_card)

        # ── Destination ────────────────────────────────────────────
        dest_card = Card("Destination")
        dest_v = QVBoxLayout()
        dest_v.setContentsMargins(SPACE[3], SPACE[2], SPACE[3], SPACE[3])
        dest_v.setSpacing(SPACE[2])

        dest_row = QHBoxLayout()
        dest_row.addWidget(label("Folder:", bold=True))
        self.folder_edit = QPushButton("Choose folder…")
        self.folder_edit.setCursor(Qt.PointingHandCursor)
        self.folder_edit.setStyleSheet(self._folder_btn_style())
        self.folder_edit.clicked.connect(self._browse_folder)
        dest_row.addWidget(self.folder_edit, 1)
        dest_v.addLayout(dest_row)

        self._dest_label = QLabel("")
        self._dest_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['xs']}px;"
            f" background: transparent;"
        )
        self._dest_label.setWordWrap(True)
        dest_v.addWidget(self._dest_label)

        dest_card.add_layout(dest_v)
        root.addWidget(dest_card)

        # ── Warnings (stale / undesigned / unsupported) ─────────────
        self._warn_label = QLabel("")
        self._warn_label.setStyleSheet(
            f"color: {ERROR}; font-size: {FONT_SIZE['xs']}px;"
            f" background: {ERROR_BG}; border-radius: 8px;"
            f" padding: {SPACE[2]}px;"
        )
        self._warn_label.setWordWrap(True)
        self._warn_label.setVisible(False)
        root.addWidget(self._warn_label)

        # ── Buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet(self._primary_btn_style())
        self.export_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.export_btn)
        root.addLayout(btn_row)

        self._refresh_summary()
        self._set_default_folder()

    # ── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _folder_btn_style() -> str:
        return (
            f"QPushButton {{ background: {BG_MID}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: 8px;"
            f" padding: 6px 12px; font-size: {FONT_SIZE['base']}px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
        )

    @staticmethod
    def _primary_btn_style() -> str:
        return (
            f"QPushButton {{ background: {ACCENT}; color: #141414;"
            f" border: none; border-radius: 8px; padding: 8px 22px;"
            f" font-size: {FONT_SIZE['base']}px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: #E6A13F; }}"
        )

    def _set_default_folder(self):
        """Pre-fill the output folder from the job header's output file."""
        out = (self._header or {}).get("output_file", "")
        if out:
            base = os.path.dirname(os.path.abspath(os.path.expanduser(out)))
            if base:
                self._out_dir = base
        if not self._out_dir:
            from rcd2000.gui.job_header_dialog import default_output_dir
            self._out_dir = str(default_output_dir())
        self._refresh_dest()

    def _browse_folder(self):
        start = self._out_dir or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, "Export folder", start,
        )
        if folder:
            self._out_dir = folder
            self._refresh_dest()

    def _refresh_dest(self):
        self._dest_label.setText(
            f"Files will be written to:\n{self._out_dir}"
        )

    # ── format / scope state ───────────────────────────────────────

    def _on_format_changed(self):
        ext = self.format_combo.currentData()
        self.combined_check.setVisible(ext == "dxf" or ext == "dwg")
        hints = {
            "txt": "Writes every selected design's text report.",
            "pdf": "Writes every selected design's PDF report "
                   "(one file per design).",
            "dxf": "Writes one DXF detail sheet per design (plan, elevation, "
                   "section, BBS where supported).",
            "dwg": "Writes native AutoCAD DWG (AC1032) — requires the ODA "
                   "File Converter, or APS credentials for cloud conversion.",
            "ifc": "Writes a single IFC4 BIM model containing all selected "
                   "elements with their reinforcement.",
        }
        self._fmt_hint.setText(hints.get(ext, ""))
        self._refresh_summary()

    def _refresh_summary(self):
        scope_this = self.this_radio.isChecked()
        items = self._scope_items
        if scope_this:
            n_designed = sum(1 for _uid, _lbl, _tk, designed, _stale in items
                             if designed)
            n_total = len(items)
            self._scope_summary.setText(
                f"{n_total} design{'s' if n_total != 1 else ''} in this job · "
                f"export targets the panel you launched from"
            )
        else:
            n_designed = sum(1 for _uid, _lbl, _tk, designed, _stale in items
                             if designed)
            n_stale = sum(1 for _uid, _lbl, _tk, _d, stale in items if stale)
            self._scope_summary.setText(
                f"{n_designed} designed · {n_stale} outdated will be skipped"
            )

    # ── result accessors ───────────────────────────────────────────

    @property
    def scope_this(self) -> bool:
        return self.this_radio.isChecked()

    @property
    def format_ext(self) -> str:
        return self.format_combo.currentData()

    @property
    def destination_dir(self) -> str:
        return self._out_dir

    @property
    def include_combined(self) -> bool:
        return self.combined_check.isChecked()

    @property
    def scope_uid(self) -> str | None:
        """The target item uid when scope = 'this design'."""
        if self.this_radio.isChecked():
            for uid, _lbl, _tk, _d, _s in self._scope_items:
                return uid
        return None
