# RCD2000 TUI — round 2 fixes (verified by actually running the app)

This time I built a stub of the `rcd2000` engine package and ran your
actual `app.py` + `styles.tcss` through Textual's real test harness
(`App.run_test()`), instead of just reading the code — so these fixes
are confirmed working, not guessed.

## Why the form looked empty / broken
`SectionBox` (the bordered box wrapping each group of fields) was
measuring **0 height** on every single instance, despite its children
having correct sizes. That's why you saw scattered fragments of text
floating in a sea of blank space, with the buttons pushed way down —
the boxes weren't sizing themselves to fit their contents at all.
Fixed by explicitly declaring `height: auto` on `.section-box` in
`styles.tcss` (relying on the implicit default wasn't working). Verified:
zero collapsed boxes across all 6 tabs now.

## Why "I can't write on the form"
Two compounding causes, both fixed:

1. On launch (and after switching tabs), focus was landing on a
   `RadioSet` — a widget that only responds to arrow keys + Enter/Space,
   **not typed characters**. So typing numbers did nothing, with no
   visual explanation why.
2. **The F1-F4 keyboard shortcuts never worked at all**, even before
   any of this. Textual auto-adds an `action_` prefix when resolving a
   binding's target method - so `Binding("f2", "action_calculate", ...)`
   was telling Textual to look for a method called
   `action_action_calculate`, which doesn't exist. It silently failed
   every time. Only the on-screen buttons (mouse clicks) ever actually
   worked, because those call the Python methods directly. Fixed by
   removing the redundant `action_` prefix from every binding. Verified
   F1/F2/F3/F4 all now actually fire via keypress.

## The DOS-style redesign (your suggestion, and it was the right one)
You're right that this should work like the original DOS tool: every
field is just a text box you type into and Tab past. I removed
`RadioSet` and `Select` entirely and replaced them with plain `Input`
fields where the valid choices are spelled out right in the label, e.g.:

    Column Type (1=Axial 2=Uniaxial 3=Biaxial): [_]
    Shape (1=Rectangular 2=Circular): [_]
    End 1 Type (0=Pinned 1=Fixed): [_]

This fixes the dropdown-visibility complaint too - there's no dropdown
overlay anymore to lose track of. Every field in the entire app now
behaves identically: type a value, Tab or Enter to the next one. No
special interaction mode to learn for some fields but not others.

## What I verified end-to-end (via the test harness, not just reading code)
- First field is focused on launch, and it's a real text `Input`
- Typing immediately lands in that field
- Tab moves to the next field, which also accepts typing right away
- Switching tabs refocuses the new tab's first field correctly
- F2 (Calculate), F3 (Clear), F4 (Report), F1 (Help) all fire via keypress
- No zero-height/collapsed boxes on any of the 6 tabs

## Files
Same as before - drop `app.py` and `styles.tcss` into `rcd2000/tui/`,
overwriting the old ones. No other files need to change.
