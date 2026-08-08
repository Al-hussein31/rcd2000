"""History page - a full page (not a modal) listing saved jobs.

Designed to be genuinely useful:

  · Stats bar: how many jobs, designs and hours are tracked
  · Live search across name, reference, company and note
  · Click ANY row to open that job (double-click too)
  · Type chips show which designs each job contains
  · Checkbox multi-select + verified multi-delete
  · Per-row Open / Edit note / Delete actions
  · Pagination so the list never gets overwhelming
  · Friendly empty state that guides you to create a job
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QToolButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QMessageBox, QCheckBox, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from rcd2000.gui.theme import (
    BG_MID, BG_CARD, BG_LIGHT, ACCENT, ACCENT_SOFT, ACCENT_SOFT_BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_SIZE, SPACE,
    RADIUS_SM, RADIUS_MD,
)
from rcd2000.gui.modules import MODULE_BY_KEY
from rcd2000.gui.job import Job, JobStore
from rcd2000.gui.widgets import icon as get_icon

PAGE_SIZE = 8


class TypeChip(QLabel):
    """Small colored chip showing one design type (e.g. "Beam")."""

    _COLORS = {
        "column": (ACCENT, ACCENT_SOFT, ACCENT_SOFT_BORDER),
        "beam": ("#4FC3F7", "#0E2A3A", "#1E5577"),
        "slab": ("#81C784", "#12351F", "#256B3A"),
        "stair": ("#FFB74D", "#3A2A10", "#6B4A1E"),
        "base": ("#E57373", "#3A1212", "#6B2222"),
        "cont_beam": ("#BA68C8", "#2A1235", "#4E2160"),
    }

    def __init__(self, type_key: str, parent=None):
        super().__init__(parent)
        entry = MODULE_BY_KEY.get(type_key)
        name = entry[0].title() if entry else type_key.replace("_", " ").title()
        glyph = entry[3] if entry else ""
        fg, bg, bd = self._COLORS.get(type_key, (TEXT_SECONDARY, BG_LIGHT, BORDER))
        self.setText(f"{glyph}  {name}" if glyph else name)
        self.setStyleSheet(
            f"color: {fg}; background: {bg}; border: 1px solid {bd};"
            f" border-radius: 9px; padding: 2px 10px; font-size: {FONT_SIZE['xs']}px;"
            f" font-weight: 600;"
        )


class HistoryPage(QWidget):
    """Searchable, paged history of jobs."""

    open_job_requested = Signal(str)          # slug
    back_requested = Signal()
    new_job_requested = Signal()
    status_message = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_jobs: list[Job] = []   # full unfiltered list
        self._jobs: list[Job] = []       # currently listed (post-search)
        self._page = 0
        self._row_slugs: list = []
        self._row_checkboxes: list = []
        self._build_ui()
        self.refresh()

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE[5], SPACE[4], SPACE[5], SPACE[4])
        outer.setSpacing(SPACE[3])

        # Header row
        top = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(1)
        title = QLabel("YOUR JOBS")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 24px; font-weight: 700; background: transparent;"
        )
        self._subtitle = QLabel("")
        self._subtitle.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['sm']}px; background: transparent;"
        )
        title_block.addWidget(title)
        title_block.addWidget(self._subtitle)
        top.addLayout(title_block)
        top.addStretch()
        back = QPushButton(" Home")
        back.setCursor(Qt.PointingHandCursor)
        back.setStyleSheet(self._ghost_style())
        _bi = get_icon("fa5s.arrow-left", TEXT_PRIMARY, 14)
        if _bi is not None:
            back.setIcon(_bi)
        back.clicked.connect(self.back_requested.emit)
        top.addWidget(back)
        outer.addLayout(top)

        # Stats bar
        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(SPACE[2])
        outer.addLayout(self._stats_row)

        # Search bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search jobs by name, reference, company or note…")
        self.search_edit.setClearButtonEnabled(True)
        _si = get_icon("fa5s.search", TEXT_MUTED, 15)
        if _si is not None:
            self.search_edit.addAction(_si, QLineEdit.LeadingPosition)
        self.search_edit.textChanged.connect(self._apply_filter)
        self.search_edit.setStyleSheet(
            f"QLineEdit {{ background: {BG_CARD}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;"
            f" padding: 11px 14px; font-size: {FONT_SIZE['base']}px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )
        outer.addWidget(self.search_edit)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["", "Job", "Designs", "Last opened", "Time", "Note", "Actions"]
        )
        self.table.verticalHeader().setVisible(False)
        # Row height must come from the section size, NOT from item padding:
        # Qt insets cell-widget geometry by the item's padding, crushing
        # widget-bearing cells (checkbox / chips / action buttons) to ~8px.
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setMouseTracking(True)
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        header = self.table.horizontalHeader()
        header.setStyleSheet(
            f"QHeaderView::section {{ background: {BG_MID}; color: {TEXT_MUTED};"
            f" border: none; padding: 8px; font-size: {FONT_SIZE['xs']}px;"
            f" font-weight: 700; border-bottom: 1px solid {BORDER}; }}"
        )
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-radius: {RADIUS_MD}px; font-size: {FONT_SIZE['base']}px;"
            f" gridline-color: transparent; }}"
            f"QTableWidget::item {{ color: {TEXT_PRIMARY};"
            f" border-bottom: 1px solid {BG_LIGHT}; }}"
            f"QTableWidget::item:selected {{ background: {ACCENT_SOFT}; color: {TEXT_PRIMARY}; }}"
            f"QTableWidget::item:hover {{ background: {BG_LIGHT}; }}"
        )
        # Row clicks open the job (columns 0 and 6 hold widgets, so those
        # clicks are handled by the widgets themselves)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        outer.addWidget(self.table, 1)

        # Empty state (stacked over the table area)
        self._empty_state = QFrame()
        self._empty_state.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-radius: {RADIUS_MD}px;"
        )
        es = QVBoxLayout(self._empty_state)
        es.setContentsMargins(SPACE[5], SPACE[6], SPACE[5], SPACE[6])
        es.setSpacing(SPACE[3])
        es.addStretch(1)
        ghost = QLabel()
        ghost.setAlignment(Qt.AlignCenter)
        ghost.setFixedSize(64, 64)
        _g = get_icon("fa5s.clipboard-list", TEXT_MUTED, 42)
        if _g is not None:
            ghost.setPixmap(_g.pixmap(48, 48))
        else:
            ghost.setText("\u25C8")
            ghost.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 42px; background: transparent;"
            )
        es.addWidget(ghost, 0, Qt.AlignCenter)
        empty_title = QLabel("No jobs yet")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700; background: transparent;"
        )
        es.addWidget(empty_title)
        empty_sub = QLabel(
            "Every concrete design project you start will appear here.\n"
            "Create your first job to get going."
        )
        empty_sub.setAlignment(Qt.AlignCenter)
        empty_sub.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['base']}px; background: transparent;"
        )
        es.addWidget(empty_sub)
        empty_btn = QPushButton("  NEW JOB")
        empty_btn.setCursor(Qt.PointingHandCursor)
        empty_btn.setMinimumHeight(44)
        _pi = get_icon("fa5s.plus", "#17140F", 14)
        if _pi is not None:
            empty_btn.setIcon(_pi)
        empty_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #17140F; font-weight: 700;"
            f" border: none; border-radius: {RADIUS_MD}px; padding: 10px 28px; }}"
            f"QPushButton:hover {{ background: #E6A13F; }}"
        )
        empty_btn.clicked.connect(self.new_job_requested.emit)
        es.addWidget(empty_btn, 0, Qt.AlignCenter)
        es.addStretch(2)
        outer.addWidget(self._empty_state, 1)

        # Pagination
        page_row = QHBoxLayout()
        self.prev_btn = QToolButton()
        _pli = get_icon("fa5s.chevron-left", TEXT_PRIMARY, 14)
        if _pli is not None:
            self.prev_btn.setIcon(_pli)
        else:
            self.prev_btn.setText("‹")
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(lambda: self._goto(self._page - 1))
        self.page_lbl = QLabel("1 / 1")
        self.page_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['sm']}px; background: transparent;"
        )
        self.next_btn = QToolButton()
        _ni = get_icon("fa5s.chevron-right", TEXT_PRIMARY, 14)
        if _ni is not None:
            self.next_btn.setIcon(_ni)
        else:
            self.next_btn.setText("›")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(lambda: self._goto(self._page + 1))
        for b in (self.prev_btn, self.next_btn):
            b.setStyleSheet(
                f"QToolButton {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
                f" border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px;"
                f" padding: 4px 12px; font-size: {FONT_SIZE['md']}px; }}"
                f"QToolButton:disabled {{ color: {TEXT_MUTED}; }}"
                f"QToolButton:hover {{ color: {ACCENT}; border-color: {ACCENT}; }}"
            )
        page_row.addStretch()
        page_row.addWidget(self.prev_btn)
        page_row.addWidget(self.page_lbl)
        page_row.addWidget(self.next_btn)
        page_row.addStretch()
        outer.addLayout(page_row)

        # Actions row
        actions = QHBoxLayout()
        self.sel_lbl = QLabel("0 selected")
        self.sel_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['sm']}px; background: transparent;"
        )
        open_btn = QPushButton("Open Selected")
        del_sel_btn = QPushButton("Delete Selected")
        for b in (open_btn, del_sel_btn):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(self._ghost_style())
        _oi2 = get_icon("fa5s.folder-open", TEXT_PRIMARY, 13)
        if _oi2 is not None:
            open_btn.setIcon(_oi2)
        _di2 = get_icon("fa5s.trash-alt", TEXT_PRIMARY, 13)
        if _di2 is not None:
            del_sel_btn.setIcon(_di2)
        open_btn.clicked.connect(self._open_selected)
        del_sel_btn.clicked.connect(self._delete_selected)
        actions.addWidget(self.sel_lbl)
        actions.addStretch()
        actions.addWidget(open_btn)
        actions.addWidget(del_sel_btn)
        outer.addLayout(actions)

    @staticmethod
    def _ghost_style() -> str:
        return (
            f"QPushButton {{ background: transparent; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;"
            f" padding: 8px 18px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
        )

    @staticmethod
    def _stat_chip(value: str, unit: str, icon_name: str = "") -> QWidget:
        chip = QWidget()
        chip.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-radius: {RADIUS_MD}px;"
        )
        h = QHBoxLayout(chip)
        h.setContentsMargins(12, 6, 14, 6)
        h.setSpacing(7)
        if icon_name:
            _ic = get_icon(icon_name, TEXT_MUTED, 14)
            if _ic is not None:
                ic_lbl = QLabel()
                ic_lbl.setPixmap(_ic.pixmap(14, 14))
                ic_lbl.setStyleSheet("background: transparent;")
                h.addWidget(ic_lbl)
        txt = QLabel(f"{value} {unit}")
        txt.setStyleSheet(
            f"background: transparent; color: {TEXT_SECONDARY};"
            f" font-size: {FONT_SIZE['sm']}px;"
        )
        h.addWidget(txt)
        return chip

    # ── data ────────────────────────────────────────────────────────

    def refresh(self):
        self._all_jobs = sorted(JobStore.list_jobs(), key=lambda j: j.updated, reverse=True)
        self._render_stats()
        self._apply_filter()

    def _render_stats(self):
        # Clear previous stat chips
        while self._stats_row.count():
            item = self._stats_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        jobs = self._all_jobs
        n_designs = sum(len(j.items) for j in jobs)
        n_secs = sum(j.time_spent for j in jobs)
        h, rem = divmod(int(n_secs), 3600)
        m = rem // 60
        time_txt = f"{h}h {m}m" if h else f"{m}m"
        self._stats_row.addWidget(self._stat_chip(str(len(jobs)), "job" if len(jobs) == 1 else "jobs", "fa5s.folder-open"))
        self._stats_row.addWidget(self._stat_chip(str(n_designs), "design" if n_designs == 1 else "designs", "fa5s.drafting-compass"))
        self._stats_row.addWidget(self._stat_chip(time_txt if n_secs else "0m", "tracked", "fa5s.clock"))
        self._stats_row.addStretch()
        self._subtitle.setText(
            f"{len(jobs)} project{'s' if len(jobs) != 1 else ''} · "
            f"{n_designs} design{'s' if n_designs != 1 else ''} · "
            f"{time_txt} tracked"
        )

    def _apply_filter(self):
        q = self.search_edit.text().strip().lower() if self.search_edit else ""
        if q:
            def match(job):
                hay = " ".join([
                    job.name, job.note,
                    job.header.get("job_ref", ""),
                    job.header.get("company", ""),
                    job.header.get("engineer", ""),
                ]).lower()
                return q in hay
            self._jobs = [j for j in self._all_jobs if match(j)]
        else:
            self._jobs = list(self._all_jobs)
        self._page = 0
        self._render_page()

    def _render_page(self):
        total = len(self._jobs)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page = max(0, min(self._page, pages - 1))
        start = self._page * PAGE_SIZE
        slice_ = self._jobs[start:start + PAGE_SIZE]

        has_jobs = bool(self._all_jobs)
        self.table.setVisible(has_jobs)
        self._empty_state.setVisible(not has_jobs)

        self.table.setRowCount(0)
        self.table.setRowCount(len(slice_))
        self._row_slugs = [j.slug for j in slice_]
        self._row_checkboxes = []

        for row, job in enumerate(slice_):
            # checkbox
            cb = QWidget()
            cbh = QHBoxLayout(cb)
            cbh.setContentsMargins(10, 0, 0, 0)
            cb_box = QCheckBox()
            cb_box.setCursor(Qt.PointingHandCursor)
            cb_box.toggled.connect(lambda on, r=row: self._update_sel())
            cb_box.setStyleSheet(
                f"QCheckBox {{ color: {TEXT_PRIMARY}; }}"
                f"QCheckBox::indicator {{ width: 16px; height: 16px;"
                f" border: 1px solid {BORDER}; border-radius: 4px; }}"
                f"QCheckBox::indicator:checked {{ background: {ACCENT};"
                f" border-color: {ACCENT}; }}"
            )
            cbh.addWidget(cb_box)
            self._row_checkboxes.append(cb_box)
            self.table.setCellWidget(row, 0, cb)

            # job: name + ref/company subline
            name_item = QTableWidgetItem()
            ref = job.header.get("job_ref", "") or ""
            co = job.header.get("company", "") or ""
            sub_parts = [p for p in (ref, co) if p]
            sub = f"  {sub_parts[0]}" if sub_parts else ""
            if len(sub_parts) > 1:
                sub += f"  ·  {sub_parts[1]}"
            name_item.setText(job.name + sub)
            name_item.setForeground(QColor(TEXT_PRIMARY))
            name_item.setData(Qt.UserRole + 1, job.slug)
            if sub:
                name_item.setToolTip(sub.strip())
            self.table.setItem(row, 1, name_item)

            # designs: type chips
            chips_w = QWidget()
            chips_l = QHBoxLayout(chips_w)
            chips_l.setContentsMargins(8, 8, 8, 8)
            chips_l.setSpacing(4)
            types = sorted({it.type_key for it in job.items})
            if types:
                for t in types[:3]:
                    chips_l.addWidget(TypeChip(t))
                if len(types) > 3:
                    more = QLabel(f"+{len(types) - 3}")
                    more.setStyleSheet(
                        f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;"
                    )
                    chips_l.addWidget(more)
            else:
                none_lbl = QLabel("no designs yet")
                none_lbl.setStyleSheet(
                    f"color: {TEXT_MUTED}; font-size: {FONT_SIZE['xs']}px; background: transparent;"
                )
                chips_l.addWidget(none_lbl)
            chips_l.addStretch()
            self.table.setCellWidget(row, 2, chips_w)

            # last opened
            when = datetime.fromtimestamp(job.last_opened or job.updated).strftime("%d %b %y  %H:%M")
            opened_item = QTableWidgetItem(when)
            opened_item.setForeground(QColor(TEXT_SECONDARY))
            self.table.setItem(row, 3, opened_item)

            # time worked
            time_item = QTableWidgetItem(job.duration_text() or "0m")
            time_item.setForeground(QColor(TEXT_SECONDARY))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, time_item)

            # note
            note_item = QTableWidgetItem(job.note or "")
            note_item.setForeground(QColor(TEXT_SECONDARY))
            self.table.setItem(row, 5, note_item)

            # action buttons
            act = QWidget()
            ah = QHBoxLayout(act)
            ah.setContentsMargins(4, 4, 4, 4)
            ah.setSpacing(6)
            open_b = QToolButton()
            open_b.setText("Open")
            _oi = get_icon("fa5s.folder-open", TEXT_SECONDARY, 13)
            if _oi is not None:
                open_b.setIcon(_oi)
            open_b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            open_b.setCursor(Qt.PointingHandCursor)
            open_b.clicked.connect(lambda _=False, s=job.slug: self.open_job_requested.emit(s))
            edit_b = QToolButton()
            edit_b.setText("Edit")
            _ei = get_icon("fa5s.edit", TEXT_SECONDARY, 13)
            if _ei is not None:
                edit_b.setIcon(_ei)
            edit_b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            edit_b.setCursor(Qt.PointingHandCursor)
            edit_b.clicked.connect(lambda _=False, s=job.slug: self._edit_note(s))
            del_b = QToolButton()
            del_b.setText("Delete")
            _di = get_icon("fa5s.trash-alt", TEXT_SECONDARY, 13)
            if _di is not None:
                del_b.setIcon(_di)
            del_b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            del_b.setCursor(Qt.PointingHandCursor)
            del_b.clicked.connect(lambda _=False, s=job.slug: self._confirm_delete([s]))
            for b in (open_b, edit_b, del_b):
                b.setStyleSheet(
                    f"QToolButton {{ background: transparent; color: {TEXT_SECONDARY};"
                    f" border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px;"
                    f" padding: 4px 10px; font-size: {FONT_SIZE['xs']}px; }}"
                    f"QToolButton:hover {{ color: {ACCENT}; border-color: {ACCENT}; }}"
                )
            ah.addWidget(open_b)
            ah.addWidget(edit_b)
            ah.addWidget(del_b)
            ah.addStretch()
            self.table.setCellWidget(row, 6, act)

        self.table.setColumnWidth(0, 44)
        self.table.setColumnWidth(2, 220)
        self.table.setColumnWidth(3, 140)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(6, 200)
        self.page_lbl.setText(f"{self._page + 1} / {pages}")
        self.prev_btn.setEnabled(self._page > 0)
        self.next_btn.setEnabled(self._page < pages - 1)
        self.sel_lbl.setText(f"{self._selected_count()} selected")

    # ── row clicks → open job ───────────────────────────────────────

    def _on_cell_clicked(self, row: int, col: int):
        """Single click on a data column opens the job."""
        if col in (1, 2, 3, 4, 5):
            self._open_row(row)

    def _on_cell_double_clicked(self, row: int, col: int):
        self._open_row(row)

    def _open_row(self, row: int):
        if 0 <= row < len(self._row_slugs):
            self.open_job_requested.emit(self._row_slugs[row])

    # ── helpers ────────────────────────────────────────────────────

    def _selected_count(self) -> int:
        return sum(1 for c in getattr(self, "_row_checkboxes", []) if c.isChecked())

    def _selected_slugs(self) -> list:
        slugs = []
        for row, cb in enumerate(getattr(self, "_row_checkboxes", [])):
            if cb.isChecked() and row < len(self._row_slugs):
                slugs.append(self._row_slugs[row])
        return slugs

    def _update_sel(self):
        self.sel_lbl.setText(f"{self._selected_count()} selected")

    def _open_selected(self):
        slugs = self._selected_slugs()
        if not slugs:
            self.status_message.emit("Select at least one job first.", True)
            return
        self.open_job_requested.emit(slugs[0])

    def _delete_selected(self):
        slugs = self._selected_slugs()
        if slugs:
            self._confirm_delete(slugs)

    def _confirm_delete(self, slugs: list):
        n = len(slugs)
        box = QMessageBox(self)
        box.setWindowTitle("Delete jobs")
        box.setText(
            f"Delete {n} job{'s' if n != 1 else ''}?"
        )
        box.setInformativeText(
            "This removes the job files from your computer. "
            "This action cannot be undone."
        )
        box.setIcon(QMessageBox.Warning)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        reply = box.exec()
        if reply == QMessageBox.Yes:
            for s in slugs:
                JobStore.delete(s)
            self.status_message.emit(f"Deleted {n} job{'s' if n != 1 else ''}.", False)
            self.refresh()

    def delete_slug(self, slug: str):
        self._confirm_delete([slug])

    def _edit_note(self, slug: str):
        job = JobStore.load(slug)
        if job is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit job")
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        lbl = QLabel("Job note (optional):")
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        note_edit = QLineEdit(job.note)
        note_edit.setPlaceholderText("e.g. Block A - ground floor columns")
        note_edit.setStyleSheet(
            f"QLineEdit {{ background: {BG_LIGHT}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_SM}px; padding: 8px 10px; }}"
        )
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #17140F; font-weight: 700;"
            f" border: none; border-radius: {RADIUS_SM}px; padding: 8px 20px; }}"
        )
        save_btn.clicked.connect(dlg.accept)
        lay.addWidget(lbl)
        lay.addWidget(note_edit)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(save_btn)
        lay.addLayout(row)
        if dlg.exec() == QDialog.Accepted:
            job.note = note_edit.text().strip()
            JobStore.save(job)
            self.status_message.emit("Note updated.", False)
            self.refresh()

    def _goto(self, page: int):
        pages = max(1, (len(self._jobs) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page = max(0, min(page, pages - 1))
        self._render_page()
