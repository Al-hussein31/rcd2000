"""Design tokens for RCD2000 GUI - amber-on-dark engineering aesthetic.

Refined palette: avoids pure black (per Material dark-theme guidance),
uses a warm off-white for text, and keeps a single desaturated accent
so the eye always knows where to look. Spacing/typography are scales,
not magic numbers - reference SPACE/FONT_SIZE from calling code.
"""

# ── Colour palette ────────────────────────────────────────────────
# Base surfaces (blue-black tint, not true black - kinder on the eyes,
# avoids the "OLED void" look while still reading as dark mode)
BG_DARKEST = "#0E1013"
BG_DARK    = "#15171C"   # main canvas
BG_MID     = "#1B1E25"   # header / status bar / menus
BG_LIGHT   = "#242832"   # hover states, input fields
BG_CARD    = "#191C22"   # card surfaces (slightly lifted off canvas)
BG_CARD_ALT = "#1F222A"  # zebra striping / nested surfaces

SIDEBAR_BG = "#101216"   # sits a touch darker than canvas -> depth

# Single accent, used sparingly and consistently
ACCENT       = "#D48C28"
ACCENT_HOVER = "#E6A13F"
ACCENT_PRESS = "#B8751F"
ACCENT_MUTED = "#8A6320"
ACCENT_SOFT  = "rgba(212, 140, 40, 0.12)"   # tinted backgrounds
ACCENT_SOFT_BORDER = "rgba(212, 140, 40, 0.35)"

TEXT_PRIMARY   = "#ECECEE"   # warm off-white, not pure #fff
TEXT_SECONDARY = "#9CA0AA"
TEXT_MUTED     = "#666A73"

BORDER       = "#272B33"
BORDER_LIGHT = "#383D48"

SUCCESS    = "#4FAE6E"
SUCCESS_BG = "rgba(79, 174, 110, 0.12)"
ERROR      = "#E0554F"
ERROR_BG   = "rgba(224, 85, 79, 0.12)"
WARNING    = "#E0A23A"
WARNING_BG = "rgba(224, 162, 58, 0.12)"
INFO       = "#4C9BE0"
INFO_BG    = "rgba(76, 155, 224, 0.12)"

# ── Spacing scale (use these, not magic numbers) ───────────────────
SPACE = {0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 7: 32, 8: 40}

# ── Border radius ───────────────────────────────────────────────────
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

# ── Typography scale ─────────────────────────────────────────────────
FONT_FAMILY = "'Inter', 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
PAINTER_FONT = "SF Pro Display"
FONT_MONO = "'SF Mono', 'JetBrains Mono', 'Menlo', 'Consolas', monospace"

FONT_SIZE = {
    "xs": 11, "sm": 12, "base": 13, "md": 14,
    "lg": 16, "xl": 18, "xxl": 22, "display": 26,
}

# ── GroupBox (legacy - prefer Card) ─────────────────────────────────
GROUP_BOX_STYLE = (
    "QGroupBox {"
    f"  color: {ACCENT}; font-weight: 600; border: 1px solid {BORDER};"
    f"  border-radius: {RADIUS_MD}px; margin-top: 12px; padding: 16px 12px 12px;"
    "}"
    "QGroupBox::title {"
    "  subcontrol-origin: margin; left: 12px; padding: 0 6px;"
    "}"
)

# ── Card style ───────────────────────────────────────────────────────
# Flat + subtle border instead of a heavy top-accent bar on every card -
# reserves color for things that actually need attention.
CARD_STYLE = (
    f"background: {BG_CARD}; border: 1px solid {BORDER};"
    f" border-radius: {RADIUS_LG}px;"
)

# ── Format helpers ───────────────────────────────────────────────────
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
            f"background: {SUCCESS_BG}; color: {SUCCESS}; font-weight: 600;"
            f" border-radius: 10px; padding: 2px 10px; font-size: {FONT_SIZE['xs']}px;"
        )
    return (
        f"background: {ERROR_BG}; color: {ERROR}; font-weight: 600;"
        f" border-radius: 10px; padding: 2px 10px; font-size: {FONT_SIZE['xs']}px;"
    )


def util_style(ratio: float) -> str:
    if ratio < 0.5:
        return f"QProgressBar::chunk {{ background: {SUCCESS}; border-radius: 3px; }}"
    if ratio < 0.8:
        return f"QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}"
    return f"QProgressBar::chunk {{ background: {ERROR}; border-radius: 3px; }}"
