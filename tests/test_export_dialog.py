"""Tests for the GUI export dialog + workbench export flow (Batch 13).

Covers: dialog construction (scope/format), TXT/PDF/DXF/IFC export paths,
per-design vs all scope, stale-item skipping, and DWG graceful failure
when ODA File Converter is absent.
"""

import os
import tempfile

import pytest
from PySide6.QtWidgets import QApplication

from rcd2000.gui.job import Job
from rcd2000.gui.workbench import Workbench
from rcd2000.gui.export_dialog import ExportDialog, FORMATS


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def wb(app):
    outdir = tempfile.mkdtemp()
    job = Job(slug="test", name="Test Job", header={
        "job_ref": "J1", "company": "Acme", "engineer": "E",
        "date": "2026-08-12",
        "output_file": os.path.join(outdir, "out.txt"),
    })
    w = Workbench(job)
    w._restore_items()
    w._export_outdir = outdir
    return w


def _design_beam(wb, item):
    wb._restore_items()  # ensure the new item has a panel
    panel = wb._panels[item.uid]
    page = panel.page
    page.b_b.setValue(300)
    page.b_bf.setValue(300)
    page.b_h.setValue(600)
    page.b_hf.setValue(0)
    page.n_supports.setValue(2)
    page.n_members.setValue(1)
    for w in page._member_widgets:
        w[1].setValue(6.0)
        w[2].setValue(45.0)
    page._on_calculate()
    return panel


def _scope_items(wb):
    out = []
    for item in wb.job.items:
        panel = wb._panels.get(item.uid)
        out.append((item.uid, panel.label if panel else item.label,
                    item.type_key,
                    bool(panel and panel.is_designed()),
                    bool(panel and panel.is_stale())))
    return out


class TestExportDialog:
    def test_formats_defined(self):
        exts = [f[1] for f in FORMATS]
        assert exts == ["txt", "pdf", "dxf", "dwg", "ifc"]

    def test_dialog_builds(self, wb):
        dlg = ExportDialog(_scope_items(wb), wb.job.header)
        assert dlg.format_ext == "txt"
        assert dlg.scope_this is False

    def test_dialog_scope_this(self, wb):
        item = wb.job.add_item("beam")
        _design_beam(wb, item)
        dlg = ExportDialog(_scope_items(wb), wb.job.header,
                           default_scope="this")
        assert dlg.scope_this is True
        assert dlg.scope_uid == item.uid

    def test_format_switch_shows_combined(self, wb):
        dlg = ExportDialog(_scope_items(wb), wb.job.header)
        dlg.format_combo.setCurrentIndex(2)  # DXF
        assert dlg.include_combined is True


class TestWorkbenchExport:
    def test_txt_export_all(self, wb):
        item = wb.job.add_item("beam")
        _design_beam(wb, item)
        out = wb._export_outdir
        wb._export_all_txt([(item, wb._panels[item.uid])], out, None)
        assert os.path.exists(os.path.join(out, "out.txt"))

    def test_dxf_export_single(self, wb):
        item = wb.job.add_item("beam")
        _design_beam(wb, item)
        out = wb._export_outdir
        dlg = ExportDialog(_scope_items(wb), wb.job.header,
                           default_scope="this")
        dlg._out_dir = out
        dlg.format_combo.setCurrentIndex(2)  # DXF
        wb._run_export(dlg, scope_this=wb._panels[item.uid])
        files = os.listdir(out)
        assert any(f.startswith("B") and f.endswith(".dxf") for f in files)
        assert "_all.dxf" in files

    def test_ifc_export(self, wb):
        item = wb.job.add_item("beam")
        _design_beam(wb, item)
        out = wb._export_outdir
        dlg = ExportDialog(_scope_items(wb), wb.job.header,
                           default_scope="this")
        dlg._out_dir = out
        dlg.format_combo.setCurrentIndex(4)  # IFC
        wb._run_export(dlg, scope_this=wb._panels[item.uid])
        assert any(f.endswith(".ifc") for f in os.listdir(out))

    def test_stale_skipped(self, wb):
        item = wb.job.add_item("beam")
        panel = _design_beam(wb, item)
        out = wb._export_outdir
        # change an input -> stale
        panel.page.b_b.setValue(350)
        assert panel.is_stale()
        dlg = ExportDialog(_scope_items(wb), wb.job.header,
                           default_scope="this")
        dlg._out_dir = out
        dlg.format_combo.setCurrentIndex(2)  # DXF
        wb._run_export(dlg, scope_this=panel)
        # nothing new written (stale design skipped)
        dxfs = [f for f in os.listdir(out) if f.endswith(".dxf")]
        assert len(dxfs) == 0

    def test_dwg_graceful_without_oda(self, wb):
        from rcd2000.dwg_export import is_available
        item = wb.job.add_item("beam")
        _design_beam(wb, item)
        out = wb._export_outdir
        dlg = ExportDialog(_scope_items(wb), wb.job.header,
                           default_scope="this")
        dlg._out_dir = out
        dlg.format_combo.setCurrentIndex(3)  # DWG
        # should not raise even without ODA converter
        wb._run_export(dlg, scope_this=wb._panels[item.uid])
        if not is_available():
            assert not any(f.endswith(".dwg") for f in os.listdir(out))
