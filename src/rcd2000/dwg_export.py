"""DWG export for RCD2000 (Batch 11).

Converts RCD2000 DXF output into native AutoCAD DWG (AC1032 / R2018 —
the format every AutoCAD 2018–2026 uses natively).

Two interchangeable backends:
- **local** (default): ezdxf's ``odafc`` add-on shells out to the free
  ODA File Converter. Offline, free, instant, no tokens. Requires the
  user to install ODA File Converter once
  (https://www.opendesign.com/guestfiles/oda_file_converter).
- **aps** (opt-in): Autodesk Platform Services Automation API v3 runs
  AccoreConsole in the cloud (open DXF, SaveAs DWG). 300 free AutoCAD
  minutes/month, then ~$3 per 12 minutes. Requires APS credentials.

Pure Python, no Qt. Headless-testable: all checks degrade gracefully
when the converter/credentials are absent.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from ezdxf.addons import odafc

# Env override so users can point at an ODA converter not on PATH
ODAFC_ENV = "RCD2000_ODAFC_PATH"

# DWG version to emit. AC1032 (R2018) is the native format of AutoCAD
# 2018 through 2026, so this IS what clients mean by "native DWG".
DWG_VERSION = "R2018"


class DwgExportError(RuntimeError):
    """Raised when a DWG conversion cannot be performed."""


def find_converter() -> Optional[Path]:
    """Locate ODAFileConverter: env override -> ezdxf config -> PATH."""
    env = os.environ.get(ODAFC_ENV)
    if env and Path(env).is_file():
        return Path(env)

    # ezdxf's own lookup (config keys then shutil.which)
    if odafc.is_installed():
        # Trust odafc's own detection; it handles platform paths.
        return None  # signal: use odafc defaults

    return None


def is_available() -> bool:
    """True if the local ODA backend is usable."""
    return bool(find_converter() or odafc.is_installed())


def dxf_to_dwg(
    dxf_path: str | Path,
    out_path: str | Path | None = None,
    version: str = DWG_VERSION,
    replace: bool = True,
) -> Path:
    """Convert a DXF file to native DWG using ODA File Converter.

    Raises DwgExportError with install instructions if the converter
    is not found.
    """
    src = Path(dxf_path)
    if not src.exists():
        raise DwgExportError(f"DXF not found: {src}")

    dst = Path(out_path) if out_path else src.with_suffix(".dwg")

    if not is_available():
        raise DwgExportError(
            "ODA File Converter not found. Install the free converter from "
            "https://www.opendesign.com/guestfiles/oda_file_converter "
            f"or set {ODAFC_ENV} to its executable path."
        )

    try:
        odafc.convert(str(src), str(dst), version=version, audit=True,
                      replace=replace)
    except odafc.ODAFCNotInstalledError as exc:  # type: ignore[attr-defined]
        raise DwgExportError(
            "ODA File Converter not installed: "
            "https://www.opendesign.com/guestfiles/oda_file_converter"
        ) from exc
    except odafc.ODAFCError as exc:  # type: ignore[attr-defined]
        raise DwgExportError(f"ODA File Converter failed: {exc}") from exc

    if not dst.exists():
        raise DwgExportError(
            f"Conversion produced no output file (expected {dst})"
        )
    return dst


def export_doc_to_dwg(
    doc,
    out_path: str | Path,
    version: str = DWG_VERSION,
    replace: bool = True,
) -> Path:
    """Convert an in-memory ezdxf Drawing straight to DWG (no temp DXF).

    Convenient when the caller already holds the exporter's ``doc``.
    """
    dst = Path(out_path)
    if not is_available():
        raise DwgExportError(
            "ODA File Converter not found. Install from "
            "https://www.opendesign.com/guestfiles/oda_file_converter "
            f"or set {ODAFC_ENV}."
        )
    try:
        odafc.export_dwg(doc, str(dst), version=version, audit=True,
                         replace=replace)
    except odafc.ODAFCError as exc:  # type: ignore[attr-defined]
        raise DwgExportError(f"ODA File Converter failed: {exc}") from exc
    if not dst.exists():
        raise DwgExportError(f"Conversion produced no output file ({dst})")
    return dst


def install_hint() -> str:
    """Human-readable instructions for enabling the local DWG backend."""
    return (
        "To enable .dwg export:\n"
        "  1. Download ODA File Converter (free):\n"
        "     https://www.opendesign.com/guestfiles/oda_file_converter\n"
        "  2. Install it, or set the environment variable "
        f"{ODAFC_ENV} to its executable path.\n"
        "  The converter runs fully offline; no Autodesk account needed."
    )
