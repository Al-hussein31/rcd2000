"""History page - a full page (not a modal) listing saved jobs.

Real-time search, per-row actions (open / edit / delete), checkboxes
for multi-delete, columns (name, reference, last opened, time worked,
note), pagination, and a verification modal before deletion.
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QToolButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QMessageBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal

from rcd2000.gui.theme import (
    BG_DARK, BG_MID, BG_CARD, BG_LIGHT, ACCENT, ACCENT_SOFT, ACCENT_SOFT_BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, FONT_SIZE, SPACE,
    RADIUS_SM, RADIUS_MD,
)
from rcd2000.gui.job import JobStore

PAGE_SIZE = 8


class HistoryPage(QWidget):
    """Searchable, paged history of jobs."""

    open_job_requested = Signal(str)          # slug
    back_requested = Signal()
    status_message = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs = []          # currently listed (post-search)
        self._page = 0
        self._row_slugs: list = []
        self._row_checkboxes: list = []
        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE[5], SPACE[4], SPACE[5], SPACE[4])
        outer.setSpacing(SPACE[3])

        # Header row
        top = QHBoxLayout()
        title = QLabel("YOUR JOBS")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 700; background: transparent;"
        )
        back = QPushButton("‹ Home")
        back.setCursor(Qt.PointingHandCursor)
        back.setStyleSheet(self._ghost_style())
        back.clicked.connect(self.back_requested.emit)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(back)
        outer.addLayout(top)

        # Search bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search jobs by name, reference, or note…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        self.search_edit.setStyleSheet(
            f"QLineEdit {{ background: {BG_CARD}; color: {TEXT_PRIMARY};"
            f" border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px;"
            f" padding: 10px 14px; font-size: {FONT_SIZE['base']}px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )
        outer.addWidget(self.search_edit)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["", "Job / Reference", "Opened", "Time worked", "Note", "Actions"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
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
            f"QTableWidget::item {{ color: {TEXT_PRIMARY}; padding: 10px 8px;"
            f" border-bottom: 1px solid {BG_LIGHT}; }}"
        )
        outer.addWidget(self.table, 1)

        # Pagination
        page_row = QHBoxLayout()
        self.prev_btn = QToolButton()
        self.prev_btn.setText("‹")
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(lambda: self._goto(self._page - 1))
        self.page_lbl = QLabel("1 / 1")
        self.page_lbl.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE['sm']}px; background: transparent;"
        )
        self.next_btn = QToolButton()
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

    # ── data ────────────────────────────────────────────────────────

    def refresh(self):
        self._jobs = list(sorted(JobStore.list_jobs(), key=lambda j: j.updated, reverse=True))
        self._apply_filter()

    def _apply_filter(self):
        q = self.search_edit.text().strip().lower() if self.search_edit else ""
        if q:
            def match(job):
                hay = " ".join([
                    job.name, job.note,
                    job.header.get("job_ref", ""),
                    job.header.get("company", ""),
                ]).lower()
                return q in hay
            self._jobs = [j for j in JobStore.list_jobs() if match(j)]
        else:
            self._jobs = sorted(JobStore.list_jobs(), key=lambda j: j.updated, reverse=True)
        self._page = 0
        self._render_page()

    def _render_page(self):
        total = len(self._jobs)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page = max(0, min(self._page, pages - 1))
        start = self._page * PAGE_SIZE
        slice_ = self._jobs[start:start + PAGE_SIZE]

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

            # name / ref
            name_item = QTableWidgetItem(f"{job.name}")
            name_item.setData(Qt.UserRole + 1, job.slug)
            ref = job.header.get("job_ref", "") or "-"
            sub = f"\nJOB REF: {ref}" if ref != "-" else ""
            name_item.setText(job.name + sub)
            name_item.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 1, name_item)

            # opened
            when = datetime.fromtimestamp(job.last_opened or job.updated).strftime("%d %b %y  %H:%M")
            opened_item = QTableWidgetItem(when)
            opened_item.setForeground(Qt.GlobalColor.lightGray)
            self.table.setItem(row, 2, opened_item)

            # types + time
            types = ", ".join(sorted({it.type_key for it in job.items})) or "no designs"
            types_item = QTableWidgetItem(f"{types}\nworked {job.duration_text()}")
            types_item.setForeground(Qt.GlobalColor.lightGray)
            self.table.setItem(row, 3, types_item)

            # note
            note_item = QTableWidgetItem(job.note or "")
            note_item.setForeground(Qt.GlobalColor.lightGray)
            self.table.setItem(row, 4, note_item)

            # action buttons
            act = QWidget()
            ah = QHBoxLayout(act)
            ah.setContentsMargins(4, 4, 4, 4)
            ah.setSpacing(6)
            open_b = QToolButton()
            open_b.setText("Open")
            open_b.setCursor(Qt.PointingHandCursor)
            open_b.clicked.connect(lambda _=False, s=job.slug: self.open_job_requested.emit(s))
            edit_b = QToolButton()
            edit_b.setText("Edit")
            edit_b.setCursor(Qt.PointingHandCursor)
            edit_b.clicked.connect(lambda _=False, s=job.slug: self._edit_note(s))
            del_b = QToolButton()
            del_b.setText("Delete")
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
            self.table.setCellWidget(row, 5, act)

        self.table.setColumnWidth(0, 44)
        self.table.setColumnWidth(3, 190)
        self.table.setColumnWidth(5, 210)
        self.page_lbl.setText(f"{self._page + 1} / {pages}")
        self.prev_btn.setEnabled(self._page > 0)
        self.next_btn.setEnabled(self._page < pages - 1)
        self.sel_lbl.setText(f"{self._selected_count()} selected")

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
            self._delete_confirm(slugs)

    def _delete_confirm(self, slugs: list):
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
        self._delete_confirm([slug])

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