"""Import preview dialog + New Job menu (M2 of the file-import feature).

The dialog shows the parsed file as an editable values table (one row per
design), a design-type selector (enabled when the type is ambiguous or the
user wants to override the auto-detection), and a warnings panel.  Cells
whose value failed to map are highlighted and carry a tooltip; editing a
cell re-parses the value with the canonical unit and re-validates it.

The "New Job" dropdown (Blank Job… | Import from File… | Download
Template…) is built by :func:`new_job_menu` and owned by the calling
window, which must provide the ``_new_blank_job`` / ``_import_file`` /
``_download_template`` slots.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QListWidget, QMenu, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from rcd2000.gui import importer as I
from rcd2000.gui.job import Job, JobStore, make_slug
from rcd2000.gui.job_header_dialog import JobHeaderDialog, resolve_output_path
from rcd2000.gui.modules import MODULE_BY_KEY, MODULES
from rcd2000.gui.settings import SettingsStore
from rcd2000.gui.theme import ACCENT, ERROR, ERROR_BG, WARNING
from rcd2000.gui.widgets import button, label

#: max designs before the dialog asks for confirmation
MAX_BATCH = 200

#: member/span containers per module → (container key, (display, mfield, unit))
_MEMBER_COLS: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "beam": ("members", [
        ("L", "length", "m"), ("UDL", "udl", "kN/m"), ("WT", "wt", "kN/m"),
        ("WB", "wb", "kN/m"), ("AB", "ab", "m"), ("PL", "pl", "kN"),
        ("AP", "ap", "m"),
    ]),
    "cont_beam": ("members", [
        ("L", "length", "m"), ("INERTIA", "inertia", "m4"),
        ("E", "e_mod", "ratio"), ("UDL", "udl", "kN/m"), ("WT", "wt", "kN/m"),
        ("WB", "wb", "kN/m"), ("AB", "ab", "m"), ("PL", "pl", "kN"),
        ("AP", "ap", "m"),
    ]),
    # slab PL/AP route by slab type: continuous (3) → cont_spans, else panel_pls
    "slab": ("slab_mixed", [
        ("SPAN LENGTH", "length", "m"), ("UDL", "udl", "kN/m"),
        ("PL", "pl", "kN"), ("AP", "ap", "m"),
    ]),
    "column": ("combined_columns", [
        ("COL LOAD", "combined_col_load", "kN"),
        ("COL DIST", "combined_col_dist", "m"),
    ]),
}

#: per-module required fields — missing ones are listed as non-blocking warnings
_REQUIRED: dict[str, tuple[str, ...]] = {
    "column":    ("load", "bx", "by", "depth"),
    "beam":      ("b_b", "b_h", "beam_fcu", "beam_fy"),
    "slab":      ("s_depth", "s_span", "slab_fcu", "slab_fy"),
    "stair":     ("s_span", "s_tread", "s_rise"),
    "base":      ("base_load", "base_a1", "base_a2", "base_h", "base_fcu"),
    "cont_beam": ("cb_ns", "members"),
}

_INVALID_BG = QColor(224, 85, 79, 60)


# ── Column model ─────────────────────────────────────────────────────────

class _Col:
    """One preview-table column descriptor."""

    def __init__(self, display: str, kind: str, key: str | None = None,
                 container: str | None = None, mfield: str | None = None,
                 unit: str | None = None, index: int = 0):
        self.display = display      # header text
        self.kind = kind            # "label" | "scalar" | "member"
        self.key = key              # scalar state key (scalar cols)
        self.container = container  # member container (member cols)
        self.mfield = mfield        # member field (member cols)
        self.unit = unit            # member unit (member cols)
        self.index = index          # 1-based member index (member cols)


def _member_columns(module: str, states: list[dict]) -> list[_Col]:
    """Build member columns, indices 1..max seen across the mapped states.

    Skipped when a module has no member container or no row populated it.
    """
    spec = _MEMBER_COLS.get(module)
    if spec is None:
        return []
    container, fields = spec
    max_idx = 0
    for st in states:
        if container == "slab_mixed":
            n = max(len(st.get("cont_spans", [])), len(st.get("panel_pls", [])))
        else:
            n = len(st.get(container, []))
        max_idx = max(max_idx, n)
    if max_idx == 0:
        return []
    cols = []
    for display, mfield, unit in fields:
        for i in range(1, max_idx + 1):
            cols.append(_Col(f"{display}{i} [{unit}]", "member",
                             container=container, mfield=mfield,
                             unit=unit, index=i))
    return cols


def _slab_container(state: dict) -> str:
    """Which member container a slab row maps into (by its combo index)."""
    return "cont_spans" if state.get("slab_type") == 2 else "panel_pls"


# ── Dialog ──────────────────────────────────────────────────────────────

class ImportPreviewDialog(QDialog):
    """Editable preview of a parsed import file → Job (or None on cancel)."""

    def __init__(self, parsed: I.ParsedFile, parent=None):
        super().__init__(parent)
        self._parsed = parsed
        self._module: str | None = parsed.module_key
        self._states: list[dict] = []
        self._labels: list[str | None] = []
        self._row_warnings: list[list[str]] = []
        self._job: Job | None = None

        self.setWindowTitle("Import Preview")
        self.resize(980, 620)
        self._build_ui()
        self._map_all()
        self._rebuild_table()
        self._refresh_warnings()

    # ── construction ────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        head = QHBoxLayout()
        self._module_combo = QComboBox()
        if self._module is None:
            self._module_combo.addItem("— choose design type —", None)
        for name, key, *_ in MODULES:
            self._module_combo.addItem(name, key)
        idx = self._module_combo.findData(self._module)
        if idx >= 0:
            self._module_combo.setCurrentIndex(idx)
        self._module_combo.currentIndexChanged.connect(self._on_module_changed)
        hint = ("Design type (auto-detected — change if the file is mixed "
                "or the detection is wrong)")
        head.addWidget(label("Design type", bold=True))
        head.addWidget(self._module_combo)
        head.addWidget(label(hint, secondary=True))
        head.addStretch(1)
        root.addLayout(head)

        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.DoubleClicked
                                    | QTableWidget.EditKeyPressed
                                    | QTableWidget.SelectedClicked)
        self._table.setSelectionBehavior(QTableWidget.SelectItems)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self._table, 1)

        warn_head = label("Warnings (non-blocking — fix values in the table or click Create)", bold=True)
        root.addWidget(warn_head)
        self._warnings = QListWidget()
        self._warnings.setMaximumHeight(120)
        root.addWidget(self._warnings)

        footer = QHBoxLayout()
        footer.addWidget(label(f"Source: {os.path.basename(self._parsed.name)}"
                               f"  ·  {len(self._parsed.table.rows)} design(s)",
                               secondary=True))
        footer.addStretch(1)
        cancel = button("Cancel", accent=False)
        cancel.clicked.connect(self.reject)
        self._create_btn = button("Create Job", accent=True)
        self._create_btn.setEnabled(self._module is not None)
        self._create_btn.clicked.connect(self._create_job)
        footer.addWidget(cancel)
        footer.addWidget(self._create_btn)
        root.addLayout(footer)

    # ── mapping ─────────────────────────────────────────────────────

    @staticmethod
    def _strip_derived(state: dict) -> dict:
        """Drop derived keys so the preview shows only source-mapped fields.

        ``n_members`` / ``n_supports`` / ``n_spans`` are recomputed by the
        pages from the member arrays; showing them as editable cells would
        be misleading.
        """
        return {k: v for k, v in state.items() if k not in I._DERIVED_KEYS}

    def _map_all(self):
        if self._module is None:
            self._states, self._labels, self._row_warnings = [], [], []
            return
        row_labels = self._parsed.table.row_labels or [None] * len(
            self._parsed.table.rows)
        states, labels, warnings = [], [], []
        for i, row in enumerate(self._parsed.table.rows):
            st, lb, ws = I.map_row(self._module, row)
            ws = [f"Row {i + 1}: {w}" for w in ws]
            st = self._strip_derived(st)
            states.append(st)
            labels.append(lb or row_labels[i])
            warnings.append(ws)
        self._states = states
        self._labels = labels
        self._row_warnings = warnings

    def _on_module_changed(self):
        self._module = self._module_combo.currentData()
        self._map_all()
        self._rebuild_table()
        self._refresh_warnings()
        self._create_btn.setEnabled(self._module is not None)

    # ── table ───────────────────────────────────────────────────────

    def _rebuild_table(self):
        self._table.blockSignals(True)
        try:
            self._table.clear()
            self._cols = self._make_columns()
            self._table.setColumnCount(len(self._cols))
            self._table.setRowCount(len(self._states))
            self._table.setHorizontalHeaderLabels([c.display for c in self._cols])
            for r, st in enumerate(self._states):
                for c_idx, col in enumerate(self._cols):
                    item = self._cell_for(col, r, st)
                    self._table.setItem(r, c_idx, item)
            self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self._table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeToContents)
        finally:
            self._table.blockSignals(False)

    def _make_columns(self):
        cols = [_Col("Label", "label")]
        if self._module is not None:
            for display, key in I.scalar_columns(self._module):
                cols.append(_Col(display, "scalar", key=key))
            cols.extend(_member_columns(self._module, self._states))
        return cols

    def _cell_for(self, col: _Col, row: int, state: dict) -> QTableWidgetItem:
        if col.kind == "label":
            text = self._labels[row] or ""
            return self._make_item(text)
        if col.kind == "scalar":
            value = state.get(col.key)
            item = self._make_item(_fmt(value) if value is not None else "")
            if value is None and self._raw_had_value(row, col.key):
                self._mark_invalid(item, self._row_warnings[row])
            return item
        # member
        value = self._member_get(state, col.container, col.mfield, col.index)
        item = self._make_item(_fmt(value) if value is not None else "")
        if value is None and self._raw_had_member(row, col.mfield, col.index):
            self._mark_invalid(item, self._row_warnings[row])
        return item

    def _make_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        return item

    def _mark_invalid(self, item: QTableWidgetItem, warnings: list[str]):
        item.setBackground(_INVALID_BG)
        item.setToolTip(warnings[0] if warnings else "Could not map this value")

    def _member_get(self, state: dict, container: str | None, mfield: str | None,
                    index: int) -> float | None:
        if container is None or mfield is None:
            return None
        if container == "slab_mixed":
            container = _slab_container(state)
        arr = state.get(container, [])
        if index - 1 >= len(arr):
            return None
        return arr[index - 1].get(mfield)

    def _raw_had_value(self, row: int, key: str | None) -> bool:
        if key is None:
            return False
        raw = self._parsed.table.rows[row]
        aliases = set(I._ALIASES.get(self._module, {}).get(key, "").split())
        aliases.add(key)
        return any(k in aliases for k in raw if raw[k])

    def _raw_had_member(self, row: int, mfield: str | None, index: int) -> bool:
        if mfield is None:
            return False
        for h in self._parsed.table.rows[row]:
            for pat, f, _ in I._MEMBER_PATTERNS:
                if f == mfield:
                    m = pat.match(h)
                    if m and int(m.group(1)) == index:
                        return True
        return False

    # ── editing ─────────────────────────────────────────────────────

    def _on_item_changed(self, item: QTableWidgetItem):
        self._table.blockSignals(True)
        try:
            col = self._column_at(item.column())
            row = item.row()
            text = item.text().strip()
            item.setBackground(QColor(Qt.transparent))
            item.setToolTip("")
            if col.kind == "label":
                self._labels[row] = text or None
                return
            if col.kind == "scalar":
                value, err = I.coerce(self._module, col.key, text)
                if err:
                    self._mark_invalid(item, [err])
                    return
                if value is None:
                    self._states[row].pop(col.key, None)
                else:
                    self._states[row][col.key] = value
                return
            container, mfield, unit, index = col.container, col.mfield, col.unit, col.index
            value, err = I.coerce_member(mfield, unit, text)
            if err:
                self._mark_invalid(item, [err])
                return
            self._member_set(row, container, mfield, index, value)
        finally:
            self._table.blockSignals(False)

    def _member_set(self, row: int, container: str, mfield: str,
                    index: int, value: float | None):
        state = self._states[row]
        if container == "slab_mixed":
            container = _slab_container(state)
        arr = state.setdefault(container, [])
        while len(arr) < index:
            arr.append({})
        if value is None:
            arr[index - 1].pop(mfield, None)
        else:
            arr[index - 1][mfield] = value

    def _column_at(self, index: int) -> _Col:
        return self._cols[index]

    # ── warnings ────────────────────────────────────────────────────

    def _refresh_warnings(self):
        self._warnings.clear()
        for w in self._parsed.warnings:
            self._warnings.addItem(w)
        for i, ws in enumerate(self._row_warnings):
            for w in ws:
                self._warnings.addItem(w)
        if self._module is not None:
            for i, st in enumerate(self._states):
                for field in _REQUIRED.get(self._module, ()):
                    if field == "members" and not st.get("members"):
                        self._warnings.addItem(
                            f"Row {i + 1}: no member spans - add L1, L2… or pick another type")
                    elif field not in st:
                        self._warnings.addItem(f"Row {i + 1}: missing {field}")
        if self._warnings.count() == 0:
            self._warnings.addItem("No warnings — clean import.")

    # ── create job ──────────────────────────────────────────────────

    def _create_job(self):
        name = self._job_name()
        header = self._make_header(name)
        items = [(self._module, st, lb)
                 for st, lb in zip(self._states, self._labels) if st]
        if not items:
            QMessageBox.warning(self, "Nothing to Import",
                                "No rows could be mapped. Fix the values or "
                                "pick a different design type.")
            return
        self._job = I.build_job(name, header, items)
        self.accept()

    def _job_name(self) -> str:
        stem = self._parsed.name or "Imported Job"
        return stem.replace("_", " ").replace("-", " ").title()

    def _make_header(self, name: str) -> dict:
        header = JobHeaderDialog._profile_prefill({})
        header.update({
            "job_ref": self._parsed.job_ref or self._parsed.name,
            "fcu": 30, "fy": 460, "fyv": 250,
            "soil_pressure": 150, "max_steel_pct": 6.0, "dh": 0.95,
        })
        header.update(I.header_materials(self._states))
        header["output_file"] = resolve_output_path(f"{name}.txt")
        return header

    @property
    def job(self) -> Job | None:
        return self._job

    # ── entry point ─────────────────────────────────────────────────

    @staticmethod
    def ask(parent, parsed: I.ParsedFile) -> Job | None:
        """Show the preview for *parsed*; return the created Job or None."""
        if len(parsed.table.rows) > MAX_BATCH:
            ret = QMessageBox.question(
                parent, "Large Import",
                f"This file contains {len(parsed.table.rows)} designs. "
                f"Continue anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret != QMessageBox.Yes:
                return None
        dlg = ImportPreviewDialog(parsed, parent)
        if dlg.exec() == QDialog.Accepted:
            return dlg.job
        return None


# ── helpers ─────────────────────────────────────────────────────────────

def _fmt(value) -> str:
    if isinstance(value, float):
        return ("%g" % value)
    return str(value)


# ── New Job menu ────────────────────────────────────────────────────────

def new_job_menu(parent) -> QMenu:
    """Build the New Job dropdown; parent must expose the three slots."""
    menu = QMenu(parent)
    menu.addAction("Blank Job…", parent._new_blank_job)
    menu.addAction("Import from File…", parent._import_file)
    tmpl = menu.addMenu("Download Template…")
    for name, key, *_ in MODULES:
        tmpl.addAction(name, lambda k=key: parent._download_template(k))
    return menu
