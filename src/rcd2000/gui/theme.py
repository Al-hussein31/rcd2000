"""Theme constants for the RCD2000 GUI."""

# ── Colours ──────────────────────────────────────────────────────
BG_DARK = "#1e1e1e"
BG_MID = "#252526"
BG_LIGHT = "#2d2d2d"
SIDEBAR_BG = "#1a1a1a"
ACCENT = "#d48c28"
ACCENT_HOVER = "#e8a030"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#999999"
BORDER = "#3a3a3a"
SUCCESS = "#4caf50"
ERROR = "#e53935"
TABLE_HEADER = "#333333"
TABLE_ALT = "#2a2a2a"

# ── Shared GroupBox stylesheet ───────────────────────────────────
GROUP_BOX_STYLE = (
    "QGroupBox {"
    f"  color: {ACCENT}; font-weight: bold;"
    "  border: 1px solid " + BORDER + "; border-radius: 6px;"
    "  margin-top: 12px; padding: 16px 12px 12px;"
    "}"
    "QGroupBox::title {"
    "  subcontrol-origin: margin; left: 12px; padding: 0 6px;"
    "}"
)

# ── Format helpers ───────────────────────────────────────────────
def fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:,.1f}"
    return str(v)

def fmt2(v) -> str:
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)
