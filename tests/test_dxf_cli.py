"""Tests for the CAD DXF CLI (Batch 9).

Runs the actual CLI parser end-to-end for beam/column/slab/base and
asserts the output DXF exists with 0 audit errors and the right layout.
"""

import json
import subprocess
import sys

import pytest
import ezdxf


def run_cli(args):
    """Run rcd2000 CLI in a subprocess, return (code, stdout)."""
    proc = subprocess.run(
        [sys.executable, "-m", "rcd2000", *args],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture
def beam_json(tmp_path):
    p = tmp_path / "beam.json"
    p.write_text(json.dumps({
        "beam_id": "B1", "n_supports": 2, "n_members": 1,
        "b": 300, "bf": 300, "h": 600, "hf": 0,
        "fcu": 25, "fy": 460, "fyv": 460,
        "member_lengths": [6.0], "member_udl": [45.0],
        "ty1": 0, "ty2": 0,
    }))
    return p


@pytest.fixture
def col_json(tmp_path):
    p = tmp_path / "col.json"
    p.write_text(json.dumps({
        "column_id": "C1", "col_type": 1, "shape": 1, "load": 1500,
        "bx": 400, "by": 400, "depth": 400, "length": 3.2,
        "le": 3.2, "lex": 3.2, "ley": 3.2, "fcu": 25, "fy": 460,
    }))
    return p


class TestDxfCli:
    def test_beam_export(self, tmp_path, beam_json):
        out = tmp_path / "beam.dxf"
        code, stdout, stderr = run_cli([
            "dxf", "beam", str(beam_json), "-o", str(out),
        ])
        assert code == 0, stderr
        assert out.exists() and out.stat().st_size > 1000
        doc = ezdxf.readfile(str(out))
        assert len(doc.audit().errors) == 0

    def test_column_export(self, tmp_path, col_json):
        out = tmp_path / "col.dxf"
        code, _, stderr = run_cli([
            "dxf", "column", str(col_json), "-o", str(out),
        ])
        assert code == 0, stderr
        doc = ezdxf.readfile(str(out))
        assert len(doc.audit().errors) == 0

    def test_scale_flag(self, tmp_path, beam_json):
        out = tmp_path / "beam_100.dxf"
        code, _, stderr = run_cli([
            "dxf", "beam", str(beam_json), "-o", str(out), "--scale", "100",
        ])
        assert code == 0, stderr
        doc = ezdxf.readfile(str(out))
        # STRUCT_100 dimstyle must exist for 1:100 output
        assert "STRUCT_100" in doc.dimstyles

    def test_sheet_layout_created(self, tmp_path, beam_json):
        out = tmp_path / "beam_sheet.dxf"
        code, _, stderr = run_cli([
            "dxf", "beam", str(beam_json), "-o", str(out),
        ])
        assert code == 0, stderr
        doc = ezdxf.readfile(str(out))
        assert any(l.name.startswith("SHEET_") for l in doc.layouts)

    def test_invalid_element(self, tmp_path, beam_json):
        code, _, _ = run_cli(["dxf", "stair", str(beam_json)])
        assert code != 0
