"""Shared base class for all design form pages.

Provides the common widget scaffolding (calc button, save/PDF buttons,
results area, history callback) and a template-method pattern so
subclasses only implement:

  - build_inputs(self, layout)  – add page-specific input Cards
  - calculate(self) -> (input_obj, result_obj)  – run the design engine
  - format_report(self, input_obj, result_obj) -> str  – delegate to report

Subclasses must also set ``self.module_name`` (used for save filenames
and history labels).
"""

import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
)
from PySide6.QtCore import QStandardPaths

from rcd2000.gui.widgets import button, header_label


class DesignFormPage(QWidget):
    """Base class for all design form pages.

    Subclasses implement ``build_inputs``, ``calculate``, and
    ``format_report``.  Everything else — button wiring, result display,
    save-to-file, PDF export, history callback — is handled here.
    """

    #: Human-readable name used for save filenames and history labels.
    #: Subclasses should override this.
    module_name: str = "Design"

    def __init__(self):
        super().__init__()
        self._last_input = None
        self._last_result = None
        self._history_cb = None
        self._status_cb = None
        self._last_save_dir = None
        self._history_viewed = False
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        layout.addWidget(header_label(self._page_title()))

        # --- page-specific input cards ---
        self.build_inputs(layout)

        # --- calculate button ---
        self.calc_btn = button(self._calc_button_text())
        self.calc_btn.clicked.connect(self._on_calculate)
        layout.addWidget(self.calc_btn)

        # --- save / PDF buttons ---
        self.btn_row = QHBoxLayout()
        self.save_btn = button("Save .txt Report")
        self.save_btn.clicked.connect(lambda: self._save_report("txt"))
        self.save_btn.setVisible(False)
        self.pdf_btn = button("Save .pdf Report")
        self.pdf_btn.clicked.connect(lambda: self._save_report("pdf"))
        self.pdf_btn.setVisible(False)
        self.btn_row.addWidget(self.save_btn)
        self.btn_row.addWidget(self.pdf_btn)
        layout.addLayout(self.btn_row)

        # --- results area ---
        self.results_area = QVBoxLayout()
        layout.addLayout(self.results_area)
        layout.addStretch()

    # ── Template methods (overridden by subclasses) ─────────────────

    def _page_title(self) -> str:
        return f"{self.module_name} Design - BS 8110"

    def _calc_button_text(self) -> str:
        return f"Design {self.module_name}"

    def build_inputs(self, layout):
        """Add page-specific input cards to *layout*.  Override in subclass."""
        raise NotImplementedError

    def calculate(self):
        """Run the design engine.

        Returns ``(input_obj, result_obj)`` or raises on error.
        Override in subclass.
        """
        raise NotImplementedError

    def format_report(self, input_obj, result_obj) -> str:
        """Return a formatted text report string.  Override in subclass."""
        raise NotImplementedError

    def get_state(self) -> dict:
        """Return a plain-dict snapshot of all input widget values.

        Keys are stable field names (str); values are primitives
        (int, float, str, list[dict]).  No Qt objects are returned.

        Override in subclass.
        """
        raise NotImplementedError

    def set_state(self, state: dict) -> None:
        """Restore widget values from a state dict.

        Unknown keys are silently ignored so that old saved states
        remain forward-compatible when new fields are added.

        Override in subclass.
        """
        raise NotImplementedError

    def _build_result_rows(self, result_obj) -> list:
        """Return ``[[label, value, status], ...]`` for the results table.

        Override in subclass to customise the displayed rows.  The default
        returns an empty list.
        """
        return []

    def _set_combo_int(self, combo_widget, value: int) -> None:
        """Set a QComboBox to the item whose text matches *value*."""
        for i in range(combo_widget.count()):
            try:
                if int(combo_widget.itemText(i)) == value:
                    combo_widget.setCurrentIndex(i)
                    return
            except (ValueError, TypeError):
                pass

    # ── Event handlers ───────────────────────────────────────────────

    def _on_calculate(self):
        self._clear_results()
        self._history_viewed = False
        try:
            self._last_input, self._last_result = self.calculate()
        except Exception as exc:
            logging.error(f"{self.module_name} design failed", exc_info=True)
            QMessageBox.warning(
                self, "Design Error",
                f"Could not complete the design — check your inputs: {exc}",
            )
            return

        r = self._last_result
        rows = self._build_result_rows(r)
        if rows:
            from rcd2000.gui.widgets import make_table
            self.results_area.addWidget(
                make_table(["Parameter", "Value", "Status"], rows)
            )

        self.save_btn.setVisible(True)
        self.pdf_btn.setVisible(True)

        if self._history_cb:
            self._history_cb(self.module_name, self._last_input, self._last_result)

    def _show_result(self, result):
        """Display a stored result dict without re-running the calculation."""
        self._clear_results()
        rows = self._build_result_rows(result)
        if rows:
            from rcd2000.gui.widgets import make_table
            self.results_area.addWidget(
                make_table(["Parameter", "Value", "Status"], rows)
            )
        self.save_btn.setVisible(True)
        self.pdf_btn.setVisible(True)

    # ── Save / export ────────────────────────────────────────────────

    def _default_save_filename(self, ext: str) -> str:
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        if not docs:
            docs = os.path.expanduser("~")
        return os.path.join(docs, f"RCD2000_{self.module_name.upper()}.{ext}")

    def _save_report(self, fmt_type: str = "txt"):
        if self._last_input is None or self._last_result is None:
            return

        text = self.format_report(self._last_input, self._last_result)

        ext = "txt" if fmt_type == "txt" else "pdf"
        default_path = self._default_save_filename(ext)

        start_dir = self._last_save_dir or os.path.dirname(default_path)
        default_name = os.path.basename(default_path)

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            os.path.join(start_dir, default_name),
            "Text Files (*.txt)" if fmt_type == "txt" else "PDF Files (*.pdf)",
        )
        if not path:
            return

        self._last_save_dir = os.path.dirname(path)

        try:
            if fmt_type == "txt":
                with open(path, "w") as f:
                    f.write(text)
            else:
                from rcd2000.report import export_pdf

                export_pdf(text, path)
            label = fmt_type.upper()
            msg = f"{label} saved: {os.path.basename(path)}"
            if self._status_cb:
                self._status_cb(msg, False)
        except Exception as exc:
            msg = f"Save failed: {exc}"
            if self._status_cb:
                self._status_cb(msg, True)

    # ── Helpers ──────────────────────────────────────────────────────

    def _clear_results(self):
        while self.results_area.count():
            w = self.results_area.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.save_btn.setVisible(False)
        self.pdf_btn.setVisible(False)

    def set_history_callback(self, cb):
        """Set the callback invoked after a successful calculation."""
        self._history_cb = cb

    def set_status_callback(self, cb):
        """Set the callback invoked for save-status messages (msg, is_error)."""
        self._status_cb = cb
