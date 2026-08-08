"""DesignPanel - one design item in the workbench.

Wraps a ``DesignFormPage`` (the form for a beam, column, slab …) in a
card with a title bar carrying:

  · the item's editable label (e.g. "1ST FLOOR BEAM 1.A-F")
  · the module name + type glyph
  · a "designed" badge once a calculation has run
  · Focus button (expand to full area) and Remove button

The panel is the unit the responsive grid and the focus view manage.
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QToolButton,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from rcd2000.gui.theme import (
    BG_CARD, BG_LIGHT, ACCENT, ACCENT_SOFT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER, FONT_SIZE, SPACE, RADIUS_MD,
)
from rcd2000.gui.modules import MODULE_BY_KEY


class DesignPanel(QFrame):
    """A titled card hosting one design form page."""

    focus_requested = Signal(object)      # DesignPanel
    remove_requested = Signal(object)     # DesignPanel
    label_changed = Signal(object)        # DesignPanel
    state_changed = Signal(object)        # DesignPanel (for autosave)

    def __init__(self, type_key: str, label_text: str, page, uid: str,
                 parent=None):
        super().__init__(parent)
        self.type_key = type_key
        self.uid = uid
        self.page = page
        self._designed = False

        entry = MODULE_BY_KEY[type_key]
        self.module_name, _glyph = entry[0], entry[3]

        self.setObjectName("designPanel")
        self.setStyleSheet(
            f"QFrame#designPanel {{ background: {BG_CARD};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px; }}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Title bar ──────────────────────────────────────────────
        bar = QFrame()
        bar.setStyleSheet(
            f"background: {BG_LIGHT}; border-top-left-radius: {RADIUS_MD}px;"
            f" border-top-right-radius: {RADIUS_MD}px; border: none;"
        )
        bar.setFixedHeight(44)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(SPACE[3], 0, SPACE[2], 0)
        bar_layout.setSpacing(SPACE[2])

        glyph_lbl = QLabel(_glyph)
        glyph_lbl.setFixedWidth(22)
        glyph_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 15px; font-weight: 700; background: transparent;"
        )
        bar_layout.addWidget(glyph_lbl)

        self.label_edit = QLineEdit(label_text)
        self.label_edit.setStyleSheet(
            f"QLineEdit {{ background: transparent; color: {TEXT_PRIMARY};"
            f" border: 1px solid transparent; border-radius: 4px;"
            f" font-size: {FONT_SIZE['md']}px; font-weight: 600; padding: 2px 4px; }}"
            f"QLineEdit:hover {{ border-color: {BORDER}; }}"
            f"QLineEdit:focus {{ background: {BG_CARD}; border-color: {ACCENT}; }}"
        )
        self.label_edit.setToolTip("Design identification - shown in reports")
        bar_layout.addWidget(self.label_edit, 1)

        self.badge = QLabel("")
        self.badge.setStyleSheet(
            f"color: {ACCENT}; font-size: {FONT_SIZE['xs']}px; font-weight: 700;"
            f" background: {ACCENT_SOFT}; border-radius: 8px; padding: 2px 8px;"
        )
        bar_layout.addWidget(self.badge)

        focus_btn = QToolButton()
        focus_btn.setText("\u26f6")
        focus_btn.setToolTip("Focus - expand this design to full area (toggle)")
        focus_btn.setCursor(Qt.PointingHandCursor)
        focus_btn.clicked.connect(lambda: self.focus_requested.emit(self))
        focus_btn.setStyleSheet(self._bar_btn_style())
        bar_layout.addWidget(focus_btn)

        remove_btn = QToolButton()
        remove_btn.setText("\u00d7")
        remove_btn.setToolTip("Remove this design")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        remove_btn.setStyleSheet(self._bar_btn_style())
        bar_layout.addWidget(remove_btn)

        outer.addWidget(bar)

        # ── Scrollable form ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {BG_CARD}; border: none; }}"
        )
        scroll.setWidget(page)
        outer.addWidget(scroll, 1)
        self.scroll_area = scroll

        # ── wiring ─────────────────────────────────────────────────
        self.label_edit.editingFinished.connect(
            lambda: self.label_changed.emit(self)
        )
        # notify autosave when the user runs a calculation
        if hasattr(page, "_on_calculate"):
            original = page._on_calculate

            def wrapped(*a, **k):
                original(*a, **k)
                self._designed = page._last_result is not None
                self._update_badge()
                self.state_changed.emit(self)

            page._on_calculate = wrapped

    # ── API ────────────────────────────────────────────────────────

    @property
    def label(self) -> str:
        return self.label_edit.text().strip() or self.label_edit.text()

    def set_label(self, text: str) -> None:
        self.label_edit.setText(text)

    def get_state(self) -> dict:
        try:
            return self.page.get_state()
        except Exception:
            return {}

    def set_state(self, state: dict) -> None:
        try:
            self.page.set_state(state)
        except Exception:
            pass

    def apply_header_defaults(self, header: dict) -> None:
        """Push global job materials into the page (only if unset)."""
        page = self.page
        try:
            if header.get("fcu") is not None and hasattr(page, "_set_combo_int"):
                for attr in ("col_fcu", "beam_fcu", "slab_fcu", "base_fcu", "s_fcu"):
                    w = getattr(page, attr, None)
                    if w is not None:
                        page._set_combo_int(w, header["fcu"])
                        break
            if header.get("fy") is not None and hasattr(page, "_set_combo_int"):
                for attr in ("col_fy", "beam_fy", "slab_fy", "base_fy", "s_fy"):
                    w = getattr(page, attr, None)
                    if w is not None:
                        page._set_combo_int(w, header["fy"])
                        break
            if header.get("fyv") is not None and hasattr(page, "_set_combo_int"):
                w = getattr(page, "beam_fyv", None)
                if w is not None:
                    page._set_combo_int(w, header["fyv"])
            if header.get("soil_pressure") is not None:
                w = getattr(page, "base_pb", None)
                if w is not None:
                    w.setValue(header["soil_pressure"])
        except Exception:
            pass

    def is_designed(self) -> bool:
        return self._designed or self.page._last_result is not None

    def report_text(self, header: dict) -> str:
        """Render the full report: job header block + design report."""
        from rcd2000.gui.modules import HEADING
        lines = [
            HEADING.get(self.type_key, f"{self.module_name.upper()} - BS 8110"),
            "=" * 46,
        ]
        jr = header.get("job_ref", "") or ""
        dt = header.get("date", "") or ""
        eng = header.get("engineer", "") or ""
        co = header.get("company", "") or ""
        lines.append(f"JOB REF: {jr:<24} DATE: {dt}")
        lines.append(f"DESIGNED: {eng:<22} CHECKED:")
        if co:
            lines.append(f"COMPANY: {co}")
        lines.append("-" * 46)
        lines.append(f"{self.module_name.upper()} ID.: {self.label}")
        lines.append("")
        if self.page._last_input is not None and self.page._last_result is not None:
            body = self.page.format_report(
                self.page._last_input, self.page._last_result,
            )
            lines.append(self._strip_page_chrome(body))
        else:
            lines.append("(No calculation yet - run the design first.)")
        return "\n".join(lines)

    @staticmethod
    def _strip_page_chrome(text: str) -> str:
        """Remove a page's own title block and footer.

        The panel writes the single title + job header block; pages only
        contribute the design body (materials + sections + results), so
        the duplicated centered title and the trailing "Well done" footer
        are dropped.
        """
        lines = text.split("\n")
        # drop the leading title block: blank lines and centered
        # title/underline pairs (23-space indent) until real content
        out = []
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.strip() == "":
                i += 1
                continue
            is_title = ln.startswith(" " * 23) and ln.strip() != ""
            if is_title and i + 1 < len(lines):
                nxt = lines[i + 1]
                is_underline = nxt.strip().startswith("-") and nxt.strip() != ""
                if is_underline:
                    i += 2
                    continue
            break
        out = lines[i:]
        # drop the trailing footer: from the separator before "Well done"
        # to the end of the body
        end = len(out)
        for j in range(len(out) - 1, -1, -1):
            if "Well done!" in out[j]:
                # keep everything before the footer separator line
                end = j
                while end > 0 and (out[end - 1].strip() == ""
                                   or out[end - 1].strip().startswith("_")):
                    end -= 1
                break
        body = "\n".join(out[:end]).strip("\n")
        return body + "\n"

    # ── visuals ────────────────────────────────────────────────────

    def _update_badge(self):
        self.badge.setText("DESIGNED" if self.is_designed() else "")

    @staticmethod
    def _bar_btn_style() -> str:
        return (
            f"QToolButton {{ background: transparent; color: {TEXT_SECONDARY};"
            f" border: none; border-radius: 4px; padding: 3px 8px;"
            f" font-size: {FONT_SIZE['md']}px; font-weight: 700; }}"
            f"QToolButton:hover {{ background: {BG_CARD}; color: {ACCENT}; }}"
        )
