# RCD2000 UI/UX redesign — drop-in notes

## Files
- `theme.py` → replaces `rcd2000/gui/theme.py`
- `widgets.py` → replaces `rcd2000/gui/widgets.py`
- `app.py` → replaces `rcd2000/gui/app.py`

Your 6 page files (`column_page.py`, `beam_page.py`, `slab_page.py`,
`stair_page.py`, `base_page.py`, `continuous_beam_page.py`) do **not**
need any changes — they call the same functions (`spinbox`, `combo`,
`Card`, `make_table`, etc.) with the same signatures. They just render
with the new look automatically.

## One new dependency

    pip install qtawesome

Real vector icons for the sidebar instead of unicode glyphs. If it's
not installed, the app still runs fine — everything falls back to the
old glyphs automatically (see `_qta_icon()` / `icon()` in the files).

## What changed
- **Palette**: warmer off-black surfaces (not true black), single
  desaturated amber accent used sparingly, off-white text — matches
  current dark-UI best practice for reduced eye strain and better
  contrast.
- **Spacing/typography**: `SPACE` and `FONT_SIZE` scales are now
  actually referenced instead of scattered magic numbers.
- **Results tables**: `make_table()` now builds a lightweight custom
  panel instead of `QTableWidget` — same call signature, lighter
  weight, easier to keep on-brand, no default Qt table chrome.
- **Sidebar**: collapsible via the toggle button (top of sidebar) or
  `Ctrl+B` — icon rail (64px) ↔ full width (220px). Toggle is instant,
  no animation, per your "no moving things" note.
- **History**: now a `CollapsibleSection` (click the header, or
  `Ctrl+H`) instead of always-open.
- **Cards**: flat surface + thin border instead of the amber top-bar
  on every single card — reserves color for things that need
  attention (badges, accent buttons) rather than decorating everything.
- **Discoverability**: an (i) info button in the header now shows all
  keyboard shortcuts on hover, since the menu bar is hidden.

## Not touched (by design, per your ask)
Draft autosave, crash recovery, history restoring actual input values,
and input validation wiring are logic/architecture changes, not visual
ones — happy to do those next if you want, but for now this is UI/UX
only so your IDE can slot it in cleanly.
