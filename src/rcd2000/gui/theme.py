"""Design tokens for RCD2000 GUI — amber-on-dark engineering aesthetic."""

# ── Colour palette ────────────────────────────────────────────────
BG_DARKEST = "#0D0D0D"
BG_DARK = "#1A1A1A"
BG_MID = "#252525"
BG_LIGHT = "#2E2E2E"
BG_CARD = "#1A1A1A"

SIDEBAR_BG = "#111111"

ACCENT = "#d48c28"
ACCENT_HOVER = "#e8a030"
ACCENT_MUTED = "#b8860b"
ACCENT_GLOW = "rgba(212, 140, 40, 0.15)"

TEXT_PRIMARY = "#E0E0E0"
TEXT_SECONDARY = "#999999"
TEXT_MUTED = "#666666"

BORDER = "#3A3A3A"
BORDER_LIGHT = "#4A4A4A"

SUCCESS = "#4CAF50"
SUCCESS_BG = "rgba(76, 175, 80, 0.15)"
ERROR = "#E53935"
ERROR_BG = "rgba(229, 57, 53, 0.15)"
WARNING = "#FF9800"
WARNING_BG = "rgba(255, 152, 0, 0.15)"
INFO = "#2196F3"
INFO_BG = "rgba(33, 150, 243, 0.15)"

# ── Spacing ───────────────────────────────────────────────────────
SPACE = {0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 7: 32, 8: 40}

# ── Border radius ─────────────────────────────────────────────────
RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 12

# ── Typography ────────────────────────────────────────────────────
FONT_FAMILY = "'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
FONT_MONO = "'SF Mono', 'Menlo', 'Consolas', monospace"

# ── GroupBox (kept for compatibility, prefer Card) ─────────────────
GROUP_BOX_STYLE = (
    "QGroupBox {"
    f"  color: {ACCENT}; font-weight: bold; border: 1px solid {BORDER};"
    f"  border-radius: {RADIUS_MD}px; margin-top: 12px; padding: 16px 12px 12px;"
    "}"
    "QGroupBox::title {"
    "  subcontrol-origin: margin; left: 12px; padding: 0 6px;"
    "}"
)

# ── Card style ────────────────────────────────────────────────────
CARD_STYLE = (
    f"background: {BG_CARD}; border: 1px solid {BORDER};"
    f" border-radius: {RADIUS_LG}px;"
    f" border-top: 3px solid {ACCENT};"
)

# ── Format helpers ────────────────────────────────────────────────
def fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:,.1f}"
    return str(v)

def fmt2(v) -> str:
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def status_style(ok: bool) -> str:
    if ok:
        return (
            f"background: {SUCCESS_BG}; color: {SUCCESS}; font-weight: bold;"
            f" border-radius: 10px; padding: 2px 10px; font-size: 11px;"
        )
    return (
        f"background: {ERROR_BG}; color: {ERROR}; font-weight: bold;"
        f" border-radius: 10px; padding: 2px 10px; font-size: 11px;"
    )


def util_style(ratio: float) -> str:
    if ratio < 0.5:
        return f"QProgressBar::chunk {{ background: {SUCCESS}; border-radius: 3px; }}"
    if ratio < 0.8:
        return f"QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}"
    return f"QProgressBar::chunk {{ background: {ERROR}; border-radius: 3px; }}"
