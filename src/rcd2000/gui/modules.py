"""Design-type registry shared by the workbench, panels, and the app.

Each entry describes one RCD2000 design module:
  (name, type_key, page_class, glyph, qtawesome_icon)

``type_key`` is the stable id used in persisted jobs.  ``page_class``
is the form page (a ``DesignFormPage`` subclass) instantiated once per
design item.  ``glyph`` is a unicode fallback when qtawesome is missing.
"""

from rcd2000.gui.pages import (
    ColumnPage,
    BeamPage,
    SlabPage,
    StairPage,
    BasePage,
    ContinuousBeamPage,
)

#: (display name, type key, page class, glyph, qta icon name)
MODULES = [
    ("Column Design", "column", ColumnPage, "\u25ae", "fa5s.ruler-vertical"),
    ("Beam Design", "beam", BeamPage, "\u2501", "fa5s.ruler-horizontal"),
    ("Slab Design", "slab", SlabPage, "\u25a6", "fa5s.th-large"),
    ("Stair Design", "stair", StairPage, "\u2571", "fa5s.grip-lines"),
    ("Foundation Design", "base", BasePage, "\u25a4", "fa5s.university"),
    ("Continuous Beam", "cont_beam", ContinuousBeamPage, "\u2261", "fa5s.link"),
]

#: Map type_key -> module entry for fast lookup
MODULE_BY_KEY = {entry[1]: entry for entry in MODULES}

#: Short prefixes used for auto-generated item labels (C1, B1, S1 …)
LABEL_PREFIX = {
    "column": "C",
    "beam": "B",
    "slab": "S",
    "stair": "ST",
    "base": "F",
    "cont_beam": "CB",
}

#: Heading used at the top of every output page, per module
HEADING = {
    "column": "COLUMN ANALYSIS AND DESIGN TO BS - 8110",
    "beam": "BEAM ANALYSIS AND DESIGN BS - 8110",
    "slab": "SLAB ANALYSIS AND DESIGN BS 8110",
    "stair": "STAIR ANALYSIS AND DESIGN BS 8110",
    "base": "BASE ANALYSIS AND DESIGN BS - 8110",
    "cont_beam": "CONTINUOUS BEAM ANALYSIS AND DESIGN BS - 8110",
}
