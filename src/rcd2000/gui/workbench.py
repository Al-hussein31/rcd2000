"""Workbench - the multi-design workspace.

Layout (top → bottom):

  ┌─────────────────────────────────────────────────────────────┐
  │ Job bar:  COMPANY · JOB REF · DESIGNER · DATE · OUT  [Edit] │
  │ Type navbar:  [Column(2)] [Beam(1)] [Slab] …  [+ Home]      │
  │ Mini-navbar:  [C1] [C2] [C3]  [+ New Column]   [Focus]      │
  ├─────────────────────────────────────────────────────────────┤
  │ Responsive grid  - up to 4 design panels (2×2 → 1×4)        │
  │   · pagination ‹ 1/3 › when more than 4 items               │
  │   · focus mode replaces the grid with a single panel        │
  └─────────────────────────────────────────────────────────────┘

The type navbar is the global navigation (sidebar → navbar), each tab
shows its item count, and the mini-navbar lists the designs of the
active type with a "+" button to add new work for that design.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
    QStackedWidget, QGridLayout, QFrame, QSizePolicy, QMessageBox,
)
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt, QTimer, Signal

from rcd2000.gui.theme import (
    BG_DARK, BG_MID, BG_LIGHT, BG_CARD, ACCENT, ACCENT_SOFT,
    ACCENT_SOFT_BORDER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER,
    BORDER_LIGHT, FONT_SIZE, SPACE, RADIUS_SM, RADIUS_MD,
)
from rcd2000.gui.modules import MODULES, MODULE_BY_KEY, LABEL_PREFIX
from rcd2000.gui.design_panel import DesignPanel

#: Items per grid page (2×2 - the "only fit 4" rule)
PAGE_SIZE = 4

#: Below this width the grid drops to a single column
SINGLE_COL_WIDTH = 900


class ResponsiveGrid(QWidget):
    """A grid of design panels that adapts its column count on resize."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(SPACE[3], SPACE[3], SPACE[3], SPACE[3])
        self._grid.setSpacing(SPACE[3])
        self._panels: list[DesignPanel] = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_panels(self, panels: list[DesignPanel]):
        # Detach any current panels without destroying them.
        # takeAt is the safe idiom: the returned layout item is valid even
        # while the layout is changing underneath us.
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self._panels = panels
        self._relayout()

    def clear_panels(self):
        """Detach all panels from the grid (used by focus mode)."""
        self.set_panels([])

    def _relayout(self):
        if not self._panels:
            return
        # Reset lingering row geometry from earlier layout passes. A grid
        # built before the widget had its real size (constructor restore)
        # may leave empty rows with stretch=1, which splits the height
        # 50/50 and halves every panel.
        for r in range(self._grid.rowCount()):
            self._grid.setRowStretch(r, 0)
            self._grid.setRowMinimumHeight(r, 0)
        cols = 1 if self.width() < SINGLE_COL_WIDTH else 2
        rows = (len(self._panels) + cols - 1) // cols
        for i, panel in enumerate(self._panels):
            r, c = divmod(i, cols)
            self._grid.addWidget(panel, r, c)
            panel.show()
            self._grid.setRowStretch(r, 1)
            self._grid.setColumnStretch(c, 1)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)
        # Clear any extra rows left by a previous taller grid
        for r in range(rows, 16):
            for c in range(2):
                item = self._grid.itemAtPosition(r, c)
                if item is not None:
                    w = item.widget()
                    if w is not None:
                        self._grid.removeWidget(w)
                        w.setParent(None)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._panels:
            self._relayout()


class Workbench(QWidget):
    """Multi-design workbench bound to one job."""

    back_requested = Signal()              # → home
    edit_job_requested = Signal()          # → header dialog
    job_changed = Signal()                 # → autosave
    status_message = Signal(str, bool)     # (message, is_error)

    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.job = job
        self._panels: dict[str, DesignPanel] = {}   # uid → panel
        self._page = 0
        self._focused: DesignPanel | None = None
        self._chip_buttons: list[QPushButton] = []
        self._type_buttons: dict[str, QPushButton] = {}
        self._header_rows: list[QWidget] = []       # collapsed in focus mode
        self._header_expanded = True
        # In focus mode the header rows collapse to a slim hover strip;
        # a timer checks whether the cursor is over the strip so the
        # headers re-appear on hover and collapse again when it leaves.
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(120)
        self._hover_timer.timeout.connect(self._poll_header_hover)
        # ESC always exits focus mode (works even when a form field has focus)
        self._esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._esc.activated.connect(self.exit_focus)
        self._build_ui()
        self._restore_items()
        self.refresh_all()

    # ════════════════════════════════════════════════════════════════
    # UI construction
    # ════════════════════════════════════════════════════════════════

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        job_bar = self._build_job_bar()
        type_bar = self._build_type_navbar()
        mini_bar = self._build_mini_navbar()
        self._header_rows = [mini_bar, type_bar, job_bar]

        # Header zone: wraps the nav rows plus a slim hover strip. In focus
        # mode the rows collapse away and only the strip remains; hovering
        # the strip (or the expanded rows) keeps the headers visible, and
        # moving the mouse away collapses them again.
        self._header_zone = QWidget()
        self._header_zone.setObjectName("headerZone")
        self._header_zone.setStyleSheet(f"background: {BG_MID};")
        hz = QVBoxLayout(self._header_zone)
        hz.setContentsMargins(0, 0, 0, 0)
        hz.setSpacing(0)
        self._hover_strip = QWidget()
        self._hover_strip.setFixedHeight(12)
        self._hover_strip.setStyleSheet(
            f"background: {BG_MID}; border-bottom: 1px solid {BORDER};"
        )
        hz.addWidget(self._hover_strip)
        for row in self._header_rows:
            hz.addWidget(row)
        outer.addWidget(self._header_zone)

        # Body: grid view ↔ focus view (empty state lives in grid view)
        self._body = QStackedWidget()
        self._body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Grid body: empty state + actual panels grid
        self._grid_page = QWidget()
        self._grid_page.setStyleSheet(f"background: {BG_DARK};")
        gpl = QVBoxLayout(self._grid_page)
        gpl.setContentsMargins(0, 0, 0, 0)
        gpl.setSpacing(0)

        self._empty_state = QWidget()
        self._empty_state.setStyleSheet(f"background: {BG_DARK};")
        es = QVBoxLayout(self._empty_state)
        es.setContentsMargins(SPACE[4], 0, SPACE[4], 0)
        es.setSpacing(SPACE[3])
        es.addStretch(1)
        empty_hint = QLabel("No designs yet for this job.")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['lg']}px; background: transparent;"
        )
        es.addWidget(empty_hint)
        create_btn = QPushButton("+ Create First Design")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #FFFFFF;"
            f" border: none; border-radius: {RADIUS_MD}px;"
            f" padding: 12px 26px; font-size: {FONT_SIZE['base']}px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: {ACCENT};; }}"
        )
        create_btn.clicked.connect(lambda: self.add_item(self.job.active_type))
        es.addWidget(create_btn, 0, Qt.AlignCenter)
        es.addStretch(2)
        gpl.addWidget(self._empty_state, 1)

        self._grid_view = ResponsiveGrid()
        self._grid_view.setStyleSheet(f"background: {BG_DARK};")
        gpl.addWidget(self._grid_view, 1)

        self._focus_view = QWidget()
        self._focus_view.setStyleSheet(f"background: {BG_DARK};")
        fv = QVBoxLayout(self._focus_view)
        fv.setContentsMargins(SPACE[3], SPACE[3], SPACE[3], SPACE[3])
        fv.setSpacing(SPACE[2])
        self._focus_bar = QHBoxLayout()
        self._focus_hint = QLabel("FOCUS MODE")
        self._focus_hint.setStyleSheet(
            f"color: {ACCENT}; font-weight: 700; font-size: {FONT_SIZE['sm']}px;"
            f" background: transparent; letter-spacing: 1px;"
        )
        self._focus_panel_holder = QLabel("")  # shows focused panel name
        self._focus_panel_holder.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['base']}px;"
            f" background: transparent;"
        )
        exit_focus = QPushButton("Exit Focus")
        exit_focus.setCursor(Qt.PointingHandCursor)
        exit_focus.setStyleSheet(self._chip_style(active=True))
        exit_focus.clicked.connect(self.exit_focus)
        self._focus_bar.addWidget(self._focus_hint)
        self._focus_bar.addWidget(self._focus_panel_holder)
        self._focus_bar.addStretch()
        self._focus_bar.addWidget(exit_focus)
        fv.addLayout(self._focus_bar)
        self._focus_container = QFrame()
        self._focus_container.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-radius: {RADIUS_MD}px;"
        )
        self._focus_container_layout = QVBoxLayout(self._focus_container)
        self._focus_container_layout.setContentsMargins(0, 0, 0, 0)
        fv.addWidget(self._focus_container, 1)

        self._body.addWidget(self._grid_page)
        self._body.addWidget(self._focus_view)
        self._body.setCurrentWidget(self._grid_page)
        outer.addWidget(self._body, 1)

        # Pagination bar
        self._pagination = self._build_pagination()
        outer.addWidget(self._pagination)

    def _build_job_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"background: {BG_MID}; border-bottom: 1px solid {BORDER};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(SPACE[4], 0, SPACE[4], 0)
        h.setSpacing(SPACE[3])

        self._job_summary = QLabel()
        self._job_summary.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE['base']}px;"
            f" background: transparent;"
        )
        h.addWidget(self._job_summary, 1)

        edit_btn = QToolButton()
        edit_btn.setText("Edit Job")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.clicked.connect(self.edit_job_requested.emit)
        edit_btn.setStyleSheet(self._tool_btn_style())
        h.addWidget(edit_btn)

        export_btn = QToolButton()
        export_btn.setText("Export All")
        export_btn.setToolTip("Write all reports to the job output file")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_all)
        export_btn.setStyleSheet(self._tool_btn_style())
        h.addWidget(export_btn)

        home_btn = QToolButton()
        home_btn.setText("\u2302 Home")
        home_btn.setCursor(Qt.PointingHandCursor)
        home_btn.clicked.connect(self.back_requested.emit)
        home_btn.setStyleSheet(self._tool_btn_style())
        h.addWidget(home_btn)
        return bar

    def _build_type_navbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(50)
        bar.setStyleSheet(
            f"background: {BG_MID}; border-bottom: 1px solid {BORDER_LIGHT};"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(SPACE[4], 0, SPACE[4], 0)
        h.setSpacing(SPACE[2])

        section = QLabel("DESIGN TYPES")
        section.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; font-weight: 700;"
            f" letter-spacing: 0.8px; background: transparent;"
        )
        h.addWidget(section)

        for name, key, _cls, glyph, _qta in MODULES:
            btn = QPushButton(f"  {glyph}  {name}")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._tab_style())
            btn.clicked.connect(lambda _=False, k=key: self._set_active_type(k))
            self._type_buttons[key] = btn
            h.addWidget(btn)
        h.addStretch()
        return bar

    def _build_mini_navbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"background: {BG_DARK}; border-bottom: 1px solid {BORDER};"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(SPACE[4], 0, SPACE[4], 0)
        h.setSpacing(SPACE[2])

        self._mini_section = QLabel("")
        self._mini_section.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['sm']}px;"
            f" font-weight: 600; background: transparent;"
        )
        h.addWidget(self._mini_section)

        self._chips_row = QHBoxLayout()
        self._chips_row.setSpacing(SPACE[2])
        h.addLayout(self._chips_row, 1)

        self._add_btn = QPushButton("+ New Design")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.clicked.connect(lambda: self.add_item(self.job.active_type))
        h.addWidget(self._add_btn)
        return bar

    def _build_pagination(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet(f"background: {BG_MID}; border-top: 1px solid {BORDER};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(SPACE[4], 0, SPACE[4], 0)
        h.setSpacing(SPACE[2])

        self._prev_btn = QToolButton()
        self._prev_btn.setText("\u2039")
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(lambda: self._goto_page(self._page - 1))
        self._prev_btn.setStyleSheet(self._page_btn_style())

        self._page_lbl = QLabel("1 / 1")
        self._page_lbl.setAlignment(Qt.AlignCenter)
        self._page_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['sm']}px;"
            f" background: transparent; min-width: 90px;"
        )

        self._next_btn = QToolButton()
        self._next_btn.setText("\u203a")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(lambda: self._goto_page(self._page + 1))
        self._next_btn.setStyleSheet(self._page_btn_style())

        self._dots = QLabel("")
        self._dots.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;"
        )

        h.addStretch()
        h.addWidget(self._prev_btn)
        h.addWidget(self._page_lbl)
        h.addWidget(self._next_btn)
        h.addWidget(self._dots)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;"
        )
        h.addWidget(self._count_lbl)
        h.addStretch()
        return bar

    # ════════════════════════════════════════════════════════════════
    # Item lifecycle
    # ════════════════════════════════════════════════════════════════

    def _make_panel(self, item) -> DesignPanel:
        entry = MODULE_BY_KEY[item.type_key]
        page = entry[2]()
        panel = DesignPanel(item.type_key, item.label, page, item.uid)
        panel.set_state(item.state)
        panel.apply_header_defaults(self.job.header)
        panel.set_label(item.label)
        panel.focus_requested.connect(self._on_focus_requested)
        panel.remove_requested.connect(self._on_remove_requested)
        panel.label_changed.connect(self._on_label_changed)
        panel.state_changed.connect(self._on_state_changed)
        if hasattr(page, "set_status_callback"):
            page.set_status_callback(self._emit_status)
        return panel

    def _restore_items(self):
        for item in self.job.items:
            if item.uid not in self._panels:
                self._panels[item.uid] = self._make_panel(item)

    def _sync_item_state(self, uid: str):
        item = self.job.item(uid)
        panel = self._panels.get(uid)
        if item is not None and panel is not None:
            item.label = panel.label
            item.state = panel.get_state()

    def _on_state_changed(self, panel: DesignPanel):
        self._sync_item_state(panel.uid)
        self.job_changed.emit()

    def _on_label_changed(self, panel: DesignPanel):
        self._sync_item_state(panel.uid)
        self.refresh_chips()
        self.job_changed.emit()

    def _on_focus_requested(self, panel: DesignPanel):
        if self._focused is panel:
            self.exit_focus()
        else:
            self.enter_focus(panel)

    def _on_remove_requested(self, panel: DesignPanel):
        reply = QMessageBox.question(
            self, "Remove Design",
            f'Remove "{panel.label}" from this job?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.job.remove_item(panel.uid)
        self._panels.pop(panel.uid, None)
        panel.deleteLater()
        if self._focused is panel:
            self._focused = None
        self.refresh_all()
        self.job_changed.emit()

    def add_item(self, type_key: str):
        item = self.job.add_item(type_key)
        self.job.active_type = type_key
        panel = self._make_panel(item)
        self._panels[item.uid] = panel
        # jump to the page that contains the new item
        idx = self.job.items.index(item)
        self._page = idx // PAGE_SIZE
        self._set_active_type(type_key)
        self.refresh_all()
        self.job_changed.emit()
        panel.label_edit.setFocus()
        panel.label_edit.selectAll()

    # ════════════════════════════════════════════════════════════════
    # Focus mode
    # ════════════════════════════════════════════════════════════════

    def enter_focus(self, panel: DesignPanel):
        if self._focused is panel:
            return
        self._focused = panel
        self._focus_panel_holder.setText(f"  {panel.module_name} · {panel.label}")
        # detach from grid, attach to focus container
        self._grid_view.set_panels([])
        panel.setParent(self._focus_container)
        panel.show()
        self._focus_container_layout.addWidget(panel)
        self._body.setCurrentWidget(self._focus_view)
        self._set_header_collapsed(True)
        self._refresh_focus_buttons()
        self._hover_timer.start()

    def exit_focus(self):
        if self._focused is None:
            return
        panel = self._focused
        self._focused = None
        self._focus_container_layout.removeWidget(panel)
        panel.setParent(None)
        self._body.setCurrentWidget(self._grid_page)
        self._set_header_collapsed(False)
        self._hover_timer.stop()
        self.refresh_all()
        self._refresh_focus_buttons()

    def _set_header_collapsed(self, collapsed: bool):
        """Collapse the job/type/mini nav rows in focus mode.

        When collapsed, only the slim hover strip remains at the top.
        Hovering the strip re-expands the header rows; moving the mouse
        away collapses them again so the focused panel keeps the full
        area. Polled via _poll_header_hover (120 ms) using underMouse(),
        which is True when the cursor is over the zone or any child.
        """
        if collapsed == (not self._header_expanded):
            return  # already in the requested state
        self._header_expanded = not collapsed
        self._hover_strip.setVisible(not collapsed)
        for row in self._header_rows:
            row.setVisible(not collapsed)

    def _poll_header_hover(self):
        if self._focused is None:
            return
        # underMouse() covers the zone and all its children, so the
        # headers stay up while the cursor is anywhere over them.
        self._set_header_collapsed(not self._header_zone.underMouse())

    # ════════════════════════════════════════════════════════════════
    # Refresh
    # ════════════════════════════════════════════════════════════════

    def _set_active_type(self, key: str):
        self.job.active_type = key
        for k, btn in self._type_buttons.items():
            btn.setChecked(k == key)
        self.refresh_chips()
        self.job_changed.emit()

    def refresh_type_tabs(self):
        for key, btn in self._type_buttons.items():
            n = len(self.job.items_of(key))
            btn.setText(f"  {MODULE_BY_KEY[key][3]}  {MODULE_BY_KEY[key][0]} ({n})")

    def refresh_chips(self):
        key = self.job.active_type
        entry = MODULE_BY_KEY[key]
        self._mini_section.setText(f"{entry[0].upper()}")
        # clear existing chips
        while self._chips_row.count():
            item = self._chips_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        items = self.job.items_of(key)
        for item in items:
            panel = self._panels.get(item.uid)
            active = self._focused is panel
            chip = QPushButton(item.label)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet(self._chip_style(active=active))
            chip.clicked.connect(lambda _=False, uid=item.uid: self._chip_clicked(uid))
            chip.setToolTip("Show this design")
            self._chips_row.addWidget(chip)
        self._add_btn.setText(f"+ New {entry[0].split()[0]}")
        self.refresh_type_tabs()

    def _chip_clicked(self, uid: str):
        # bring the item's page into view
        for i, item in enumerate(self.job.items):
            if item.uid == uid:
                self._page = i // PAGE_SIZE
                break
        self.refresh_grid()

    def refresh_grid(self):
        total = len(self.job.items)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        if self._page >= pages:
            self._page = pages - 1
        self._page = max(0, self._page)
        start = self._page * PAGE_SIZE
        visible = self.job.items[start:start + PAGE_SIZE]
        panels = [self._panels[it.uid] for it in visible if it.uid in self._panels]
        self._grid_view.set_panels(panels)
        self._empty_state.setVisible(total == 0)
        self._grid_view.setVisible(total > 0)
        self._page_lbl.setText(f"{self._page + 1} / {pages}")
        self._prev_btn.setEnabled(self._page > 0)
        self._next_btn.setEnabled(self._page < pages - 1)
        self._dots.setText("• " * pages if pages > 1 else "")
        self._count_lbl.setText(f"{total} design{'s' if total != 1 else ''}")

    def _goto_page(self, page: int):
        pages = max(1, (len(self.job.items) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page = max(0, min(page, pages - 1))
        self.refresh_grid()

    def refresh_all(self):
        self.refresh_type_tabs()
        self.refresh_chips()
        self.refresh_grid()
        self._refresh_job_summary()
        self._refresh_focus_buttons()

    def _refresh_job_summary(self):
        h = self.job.header
        parts = []
        if h.get("company"):
            parts.append(f"🏢 {h['company']}")
        if h.get("job_ref"):
            parts.append(f"JOB REF: {h['job_ref']}")
        if h.get("engineer"):
            parts.append(f"ENGINEER: {h['engineer']}")
        if h.get("date"):
            parts.append(f"DATE: {h['date']}")
        if not parts:
            parts = ["Untitled Job"]
        self._job_summary.setText("   ·   ".join(parts))

    def _refresh_focus_buttons(self):
        for panel in self._panels.values():
            pass  # visual state only - buttons already reflect via view

    def _export_all(self):
        """Write every *designed* item's report (with header block) to the
        output file.  Items that have never been run are skipped - an
        export with nothing designed is an error, not a silent save."""
        out = self.job.header.get("output_file", "").strip()
        if not out:
            self._emit_status("Set an Output File Name in Edit Job first.", True)
            return
        if not self.job.items:
            self._emit_status("Create a design first, then Export All.", True)
            return

        designed = []
        skipped = 0
        for item in self.job.items:
            panel = self._panels.get(item.uid)
            if panel is None:
                skipped += 1
                continue
            if panel.is_designed():
                designed.append(panel)
            else:
                skipped += 1

        if not designed:
            self._emit_status(
                "Nothing to save - run at least one design first "
                "(use the Design/Calculate button).", True
            )
            return

        sections = []
        for panel in designed:
            sections.append(panel.report_text(self.job.header))
            sections.append("\n" + "=" * 46 + "\n")
        try:
            with open(out, "w") as f:
                f.write("\n".join(sections))
            msg = (
                f"Reports written to {out} ({len(designed)} design"
                f"{'s' if len(designed) != 1 else ''})"
            )
            if skipped:
                msg += f" - {skipped} not designed, skipped."
            self._emit_status(msg, False)
        except Exception as exc:
            self._emit_status(f"Export failed: {exc}", True)

    def _emit_status(self, message: str, is_error: bool = False):
        self.status_message.emit(message, is_error)

    # ════════════════════════════════════════════════════════════════
    # Styles
    # ════════════════════════════════════════════════════════════════

    @staticmethod
    def _tab_style() -> str:
        return (
            f"QPushButton {{ background: transparent; color: {TEXT_SECONDARY};"
            f" border: 1px solid transparent; border-radius: {RADIUS_SM}px;"
            f" padding: 6px 12px; font-size: {FONT_SIZE['base']}px; }}"
            f"QPushButton:hover {{ color: {TEXT_PRIMARY}; background: {BG_LIGHT}; }}"
            f"QPushButton:checked {{ color: {ACCENT}; background: {ACCENT_SOFT};"
            f" border: 1px solid {ACCENT_SOFT_BORDER}; font-weight: 600; }}"
        )

    @staticmethod
    def _chip_style(active: bool = False) -> str:
        if active:
            return (
                f"QPushButton {{ background: {ACCENT_SOFT}; color: {ACCENT};"
                f" border: 1px solid {ACCENT_SOFT_BORDER}; border-radius: {RADIUS_SM}px;"
                f" padding: 5px 14px; font-weight: 600; }}"
            )
        return (
            f"QPushButton {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px;"
            f" padding: 5px 14px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
        )

    @staticmethod
    def _tool_btn_style() -> str:
        return (
            f"QToolButton {{ background: transparent; color: {TEXT_SECONDARY};"
            f" border: none; border-radius: {RADIUS_SM}px; padding: 5px 10px;"
            f" font-size: {FONT_SIZE['base']}px; }}"
            f"QToolButton:hover {{ color: {ACCENT}; background: {BG_LIGHT}; }}"
        )

    @staticmethod
    def _page_btn_style() -> str:
        return (
            f"QToolButton {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px;"
            f" padding: 4px 12px; font-size: {FONT_SIZE['md']}px; }}"
            f"QToolButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
            f"QToolButton:disabled {{ color: {TEXT_MUTED}; border-color: {BORDER}; }}"
        )
