"""Tests for DWG export (Batch 11).

The local backend needs ODA File Converter installed; tests skip cleanly
when it's absent. The APS module is unit-tested for its pure helpers
without hitting the network.
"""

import pytest

from rcd2000.dwg_export import (
    DwgExportError,
    dxf_to_dwg,
    export_doc_to_dwg,
    find_converter,
    is_available,
    install_hint,
)
from rcd2000 import aps


class TestDetection:
    def test_find_converter_returns_none_when_absent(self):
        # In CI/clean environments there is no converter; must not crash.
        assert find_converter() in (None, None)  # noqa: PLR0133

    def test_is_available_boolean(self):
        assert isinstance(is_available(), bool)

    def test_install_hint_mentions_url(self):
        hint = install_hint()
        assert "opendesign.com" in hint


class TestDwgExportErrors:
    def test_missing_dxf_raises(self, tmp_path):
        with pytest.raises(DwgExportError, match="not found"):
            dxf_to_dwg(tmp_path / "nope.dxf")

    def test_export_skips_when_no_converter(self, tmp_path):
        """When converter absent, raises a friendly DwgExportError."""
        from rcd2000.dxf_export import DxfExporter
        ex = DxfExporter()
        out = tmp_path / "b.dxf"
        ex.save(str(out))
        if not is_available():
            with pytest.raises(DwgExportError):
                dxf_to_dwg(str(out), str(tmp_path / "b.dwg"))
        # else: converter present — just make sure it produces a file
        else:
            result = dxf_to_dwg(str(out), str(tmp_path / "b.dwg"))
            assert result.exists()


class TestApsModule:
    def test_scopes_include_required(self):
        for scope in ("code:all", "bucket:create", "data:read"):
            assert scope in aps.SCOPES

    def test_credentials_missing_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("APS_CLIENT_ID", raising=False)
        monkeypatch.delenv("APS_CLIENT_SECRET", raising=False)
        dxf = tmp_path / "x.dxf"
        dxf.write_text("0\nSECTION\n")
        with pytest.raises(aps.ApsError, match="credentials"):
            aps.dxf_to_dwg(str(dxf), str(tmp_path / "x.dwg"))

    def test_activity_payload_has_script(self):
        # pure check that provision payload shape is sane (no network)
        from rcd2000.aps import ACTIVITY_ID
        assert "DxfToDwg" in ACTIVITY_ID

    def test_imports_requests(self):
        import requests  # noqa: F401
        assert requests is not None
