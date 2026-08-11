"""GUI tests for the import preview dialog + New Job popup (M2)."""

import os
import tempfile

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from rcd2000.gui import importer as I
from rcd2000.gui.import_dialog import (
    ImportPreviewDialog, MAX_BATCH, NewJobPopup, _ModuleRow, _OptionRow,
)
from rcd2000.gui.modules import MODULES


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


# ── helpers ─────────────────────────────────────────────────────────────

def _write(tmp_path, name, content):
    p = os.path.join(str(tmp_path), name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


def _beam_csv(tmp_path, rows=None):
    rows = rows or [
        "B1,30,460,300,500,6.0,20",
        "B2,35,460,300,550,7.5,25",
    ]
    return _write(
        tmp_path, "my_beam.csv",
        "Beam ID,FCU [N/mm2],FY [N/mm2],B [mm],H [mm],L1 [m],UDL1 [kN/m]\n"
        + "\n".join(rows) + "\n")


def _dialog(qapp, tmp_path, content=None, name="job.csv"):
    p = _write(tmp_path, name, content) if isinstance(content, str) \
        else _beam_csv(tmp_path)
    parsed = I.parse_file(p)
    return ImportPreviewDialog(parsed)


def _cell_text(dlg, row, header):
    cols = [dlg._table.horizontalHeaderItem(c).text() for c in range(dlg._table.columnCount())]
    return dlg._table.item(row, cols.index(header)).text()


def _set_cell(dlg, row, header, text):
    cols = [dlg._table.horizontalHeaderItem(c).text() for c in range(dlg._table.columnCount())]
    dlg._table.item(row, cols.index(header)).setText(text)


# ── table build ─────────────────────────────────────────────────────────

def test_beam_table_columns_and_values(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path)
    cols = [dlg._table.horizontalHeaderItem(c).text() for c in range(dlg._table.columnCount())]
    assert cols[0] == "Label"
    assert "FCU [N/mm2]" in cols and "B [mm]" in cols and "H [mm]" in cols
    assert "L1 [m]" in cols and "UDL1 [kN/m]" in cols
    assert dlg._table.rowCount() == 2
    assert _cell_text(dlg, 0, "Label") == "B1"
    assert _cell_text(dlg, 0, "B [mm]") == "300"
    assert _cell_text(dlg, 0, "L1 [m]") == "6"
    assert _cell_text(dlg, 0, "UDL1 [kN/m]") == "20"


def test_derived_count_columns_hidden(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path, content=(
        "Panel No,TYPE,DEPTH [mm],SPAN [m]\n"
        "S1,Continuous,200,3.0\n"))
    cols = [dlg._table.horizontalHeaderItem(c).text() for c in range(dlg._table.columnCount())]
    assert "PANEL_NPL" not in cols and "CONT_NSPAN" not in cols
    assert "N MEMBERS" not in cols and "N SUPPORTS" not in cols


def test_ambiguous_file_starts_without_mapping(qapp, tmp_path):
    # weak-only markers (FCU/FY/B/H appear in several modules) → ambiguous
    p = _write(tmp_path, "odd.csv", "FCU [N/mm2],FY [N/mm2],B [mm],H [mm]\n30,460,300,500\n")
    parsed = I.parse_file(p)
    assert parsed.module_key is None
    dlg = ImportPreviewDialog(parsed)
    assert dlg._states == []
    assert dlg._table.rowCount() == 0
    assert dlg._create_btn.isEnabled() is False
    # picking a module maps the rows
    dlg._module_combo.setCurrentIndex(dlg._module_combo.findData("column"))
    assert dlg._table.rowCount() == 1
    assert dlg._states[0]["col_fcu"] == 30
    assert dlg._create_btn.isEnabled() is True


def test_module_change_remaps(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path)
    assert dlg._states[0].get("beam_fy") == 460
    dlg._module_combo.setCurrentIndex(dlg._module_combo.findData("column"))
    assert dlg._states[0].get("beam_fy") is None
    # switching back restores values
    dlg._module_combo.setCurrentIndex(dlg._module_combo.findData("beam"))
    assert dlg._states[0].get("beam_fy") == 460


# ── editing ─────────────────────────────────────────────────────────────

def test_edit_scalar_cell_updates_state(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path)
    assert dlg._states[0].get("beam_fy") == 460
    _set_cell(dlg, 0, "FY [N/mm2]", "500")
    assert dlg._states[0].get("beam_fy") == 500


def test_edit_clears_cell(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path)
    _set_cell(dlg, 0, "FY [N/mm2]", "   ")
    assert dlg._states[0].get("beam_fy") is None


def test_edit_invalid_cell_marks_red_with_tooltip(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path)
    _set_cell(dlg, 0, "H [mm]", "abc")
    item = dlg._table.item(0, [dlg._table.horizontalHeaderItem(c).text()
                               for c in range(dlg._table.columnCount())].index("H [mm]"))
    assert item.background().color().alpha() > 0
    assert "abc" in item.toolTip()
    # fixing the cell clears the flag
    _set_cell(dlg, 0, "H [mm]", "600")
    assert dlg._states[0].get("b_h") == 600
    assert item.background().color().alpha() == 0


def test_edit_member_cell(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path)
    _set_cell(dlg, 0, "L1 [m]", "8.5")
    assert dlg._states[0]["members"][0]["length"] == 8.5


def test_slab_continuous_routes_pl_to_cont_spans(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path, content=(
        "Panel No,TYPE,DEPTH [mm],SPAN [m],SPAN LENGTH 1 [m],UDL1 [kN/m],PL1 [kN]\n"
        "S1,Continuous,200,3.0,3.0,10,15\n"))
    assert dlg._states[0]["slab_type"] == 2
    assert dlg._states[0]["cont_spans"][0]["pl"] == 15
    assert _cell_text(dlg, 0, "PL1 [kN]") == "15"
    _set_cell(dlg, 0, "PL1 [kN]", "22")
    assert dlg._states[0]["cont_spans"][0]["pl"] == 22


# ── warnings ────────────────────────────────────────────────────────────

def test_warnings_panel_lists_problems(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path, content=(
        "Beam ID,B [mm],H [mm],L1 [m]\n"
        "B1,300,500,abc\n"))
    texts = [dlg._warnings.item(i).text() for i in range(dlg._warnings.count())]
    # unparseable span surfaced
    assert any("l1" in t and "Unrecognised" in t for t in texts)
    # missing required fields listed, non-blocking
    assert any("missing beam_fcu" in t for t in texts)
    assert any("missing beam_fy" in t for t in texts)
    # b_b / b_h were provided — not flagged
    assert not any("missing b_b" in t for t in texts)


def test_clean_import_says_clean(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path)
    assert dlg._warnings.item(0).text() == "No warnings — clean import."


# ── create job ──────────────────────────────────────────────────────────

def test_create_job_from_dialog(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path)
    dlg._create_job()
    job = dlg.job
    assert job is not None
    assert job.name == "My Beam"
    assert [it.type_key for it in job.items] == ["beam", "beam"]
    assert [it.label for it in job.items] == ["B1", "B2"]
    assert job.header["fcu"] == 30
    assert job.header["fy"] == 460
    assert job.header["output_file"].endswith("My Beam.txt")


def test_create_job_materials_consensus(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path, content=(
        "Beam ID,FCU [N/mm2],B [mm],H [mm],L1 [m]\n"
        "B1,35,300,500,6.0\n"
        "B2,35,300,500,7.0\n"
        "B3,35,300,500,8.0\n"))
    dlg._create_job()
    assert dlg.job.header["fcu"] == 35  # unanimous → promoted to header


def test_create_job_materials_non_consensus_stays_default(qapp, tmp_path):
    dlg = _dialog(qapp, tmp_path, content=(
        "Beam ID,FCU [N/mm2],B [mm],H [mm],L1 [m]\n"
        "B1,35,300,500,6.0\n"
        "B2,40,300,500,7.0\n"))
    dlg._create_job()
    assert dlg.job.header["fcu"] == 30  # split → header default


def test_create_job_rcd2000_uses_job_ref(qapp, tmp_path):
    p = _write(tmp_path, "job.txt", (
        "JOB REF: FG-123\n"
        "Beam Id: B1\nSection Size = 300 x 500\nSpan Length = 6.0\nUDL = 20.0\n"))
    parsed = I.parse_file(p)
    assert parsed.job_ref == "FG-123"
    dlg = ImportPreviewDialog(parsed)
    assert _cell_text(dlg, 0, "Label") == "B1"
    assert _cell_text(dlg, 0, "B [mm]") == "300"
    dlg._create_job()
    assert dlg.job.header["job_ref"] == "FG-123"
    assert dlg.job.header["output_file"].endswith("Job.txt")


def test_create_job_nothing_mapped_shows_warning(qapp, tmp_path, monkeypatch):
    dlg = _dialog(qapp, tmp_path, content="A,B,C\n1,2,3\n")
    dlg._module_combo.setCurrentIndex(0)  # column — no recognisable fields
    warned = {}
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warned.setdefault("ok", True)))
    dlg._create_job()
    assert dlg.job is None
    assert warned.get("ok")


# ── batch cap ───────────────────────────────────────────────────────────

def test_ask_confirms_before_large_import(qapp, tmp_path, monkeypatch):
    rows = "\n".join(
        f"B{i},30,460,300,500,6.0,20" for i in range(MAX_BATCH + 1))
    p = _beam_csv(tmp_path, rows=[r.split(",")[0] + ",30,460,300,500,6.0,20"
                                 for r in rows.split("\n")])
    parsed = I.parse_file(p)
    assert len(parsed.table.rows) > MAX_BATCH
    answers = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: answers.append("asked") or QMessageBox.No))
    monkeypatch.setattr(ImportPreviewDialog, "exec", lambda self: QMessageBox.Rejected)
    assert ImportPreviewDialog.ask(None, parsed) is None
    assert answers == ["asked"]


def test_ask_small_import_no_confirm(qapp, tmp_path, monkeypatch):
    p = _beam_csv(tmp_path)
    parsed = I.parse_file(p)
    answers = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: answers.append("asked") or QMessageBox.No))
    monkeypatch.setattr(ImportPreviewDialog, "exec", lambda self: QMessageBox.Rejected)
    ImportPreviewDialog.ask(None, parsed)
    assert answers == []


# ── New Job popup ───────────────────────────────────────────────────────

class _FakeParent(QWidget):
    def _new_blank_job(self):
        pass

    def _import_file(self):
        pass

    def _download_template(self, key):
        pass


def test_new_job_popup_structure(qapp):
    popup = NewJobPopup()
    assert [r._action for r in popup._rows] == ["blank", "import", None]
    assert all(isinstance(r, _OptionRow) for r in popup._rows)
    assert len(popup._module_rows) == len(MODULES)
    assert all(isinstance(m, _ModuleRow) for m in popup._module_rows)
    assert [m._key for m in popup._module_rows] == [m[1] for m in MODULES]
    assert popup._template_box.isHidden()   # collapsed by default
    popup.deleteLater()


def test_new_job_popup_toggles_template_section(qapp):
    popup = NewJobPopup()
    popup._toggle_template()
    assert not popup._template_box.isHidden()
    popup._toggle_template()
    assert popup._template_box.isHidden()
    popup.deleteLater()


def test_new_job_popup_blank_click_returns_blank(qapp):
    popup = NewJobPopup()
    popup.show()
    QTest.mouseClick(popup._rows[0], Qt.LeftButton)
    assert popup._result == "blank"
    popup.close()


def test_new_job_popup_import_click_returns_import(qapp):
    popup = NewJobPopup()
    popup.show()
    QTest.mouseClick(popup._rows[1], Qt.LeftButton)
    assert popup._result == "import"
    popup.close()


def test_new_job_popup_expander_click_stays_open(qapp):
    popup = NewJobPopup()
    popup.show()
    QTest.mouseClick(popup._rows[2], Qt.LeftButton)   # Download Template…
    assert popup._result is None
    assert not popup._template_box.isHidden()
    popup.close()


def test_new_job_popup_module_click_returns_template_key(qapp):
    popup = NewJobPopup()
    popup.show()
    QTest.mouseClick(popup._module_rows[1], Qt.LeftButton)   # Beam
    assert popup._result == "template:beam"
    popup.close()


def test_new_job_popup_escape_dismisses(qapp):
    popup = NewJobPopup()
    popup.show()
    QTest.keyClick(popup, Qt.Key_Escape)
    assert popup._result is None
    assert popup.result() != 1   # rejected, not accepted
    popup.close()


# ── app regression ──────────────────────────────────────────────────────

def test_app_handlers_no_nameerror(qapp, tmp_path, monkeypatch):
    """Regression: QFileDialog/QMessageBox were missing from app.py
    imports, so 'Import from File…' / 'Download Template…' silently
    NameError'd in the slot and did nothing."""
    from rcd2000.gui import app as appmod
    # Skip the network update check when constructing MainWindow.
    monkeypatch.setattr(appmod.MainWindow, "_start_update_check",
                        lambda self: None)
    win = appmod.MainWindow()
    # Cancel path of both handlers must complete without raising.
    monkeypatch.setattr(appmod.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: ("", "")))
    win._import_file()
    monkeypatch.setattr(appmod.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: ("", "")))
    win._download_template("beam")
    # Dispatch path: import of a real CSV should reach the preview dialog.
    p = _beam_csv(tmp_path)
    answers = []
    monkeypatch.setattr(appmod.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (p, "")))
    monkeypatch.setattr(ImportPreviewDialog, "exec",
                        lambda self: QMessageBox.Rejected)
    win._import_file()   # reaches ImportPreviewDialog.ask → exec patched
    assert answers == []
    win.deleteLater()
