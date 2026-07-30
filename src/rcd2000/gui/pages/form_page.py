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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QStandardPaths

from rcd2000.gui.theme import TEXT_MUTED, FONT_SIZE
from rcd2000.gui.widgets import button, header_label, mark_invalid


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
        self._error_widgets: list = []
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        layout.addWidget(header_label(self._page_title()))

        # --- page-specific input cards ---
        self.build_inputs(layout)

        # --- validation error banner ---
        self._validation_banner = QLabel()
        self._validation_banner.setWordWrap(True)
        self._validation_banner.setVisible(False)
        self._validation_banner.setStyleSheet(
            "background: #5c1a1a; color: #ff6b6b; font-size: 12px;"
            " font-weight: 600; padding: 10px 14px; border-radius: 6px;"
        )
        layout.addWidget(self._validation_banner)

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

        btn_text = self._calc_button_text()
        self._results_placeholder = QLabel(
            f"Enter your inputs and click \"{btn_text}\" to see results"
        )
        self._results_placeholder.setWordWrap(True)
        self._results_placeholder.setAlignment(Qt.AlignCenter)
        self._results_placeholder.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['md']}px;"
            f" padding: 40px 20px; background: transparent;"
        )
        layout.addWidget(self._results_placeholder)
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

    # ── Validation ──────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return a list of human-readable error messages.

        Override in subclass to perform sanity checks before calculation
        runs.  Return an empty list when inputs are valid.
        """
        return []

    def _clear_validation(self):
        """Clear the validation error banner and red borders."""
        self._validation_banner.setVisible(False)
        for w in self._error_widgets:
            try:
                mark_invalid(w, False)
            except Exception:
                pass
        self._error_widgets.clear()

    def _mark_invalid(self, widget):
        """Mark a widget as invalid and track it for later clearing."""
        self._error_widgets.append(widget)
        try:
            mark_invalid(widget, True)
        except Exception:
            pass

    def _auto_clear_invalid(self, widget):
        """Connect a widget's change signal to clear its own invalid flag.

        Call this for every input widget so red borders disappear as
        soon as the user edits the field.
        """
        if hasattr(widget, "valueChanged"):
            widget.valueChanged.connect(lambda v=None, w=widget: mark_invalid(w, False))
        elif hasattr(widget, "currentIndexChanged"):
            widget.currentIndexChanged.connect(lambda i=None, w=widget: mark_invalid(w, False))

    # ── History summarizer ──────────────────────────────────────────

    def summarize(self, inp) -> str:
        """Return a short one-line summary of key inputs for history.

        Override in subclass.  *inp* is the input dataclass (or a plain
        dict when loaded from disk).  Default returns the module name.
        """
        return self.module_name

    # ── Event handlers ───────────────────────────────────────────────

    def _on_calculate(self):
        self._clear_results()
        self._clear_validation()
        self._history_viewed = False

        errors = self.validate()
        if errors:
            self._validation_banner.setText("\n".join(f"• {e}" for e in errors))
            self._validation_banner.setVisible(True)
            return

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
        self._results_placeholder.setVisible(False)

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
        self._results_placeholder.setVisible(False)

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

        if os.path.exists(path):
            reply = QMessageBox.question(
                self, "Confirm Overwrite",
                f"The file \"{os.path.basename(path)}\" already exists.\n\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
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
        self._results_placeholder.setVisible(True)

    def set_history_callback(self, cb):
        """Set the callback invoked after a successful calculation."""
        self._history_cb = cb

    def set_status_callback(self, cb):
        """Set the callback invoked for save-status messages (msg, is_error)."""
        self._status_cb = cb
