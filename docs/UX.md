# UX decisions

The left sidebar selects panels and data; the right inspector edits the selected object; the central preview gives immediate feedback. Four inspector tabs separate figure-wide, panel, series and annotation controls. Edits preserve panel identity and refresh automatically. Invalid intermediate input leaves an inline message rather than opening a dialog on every keystroke.

Both sidebars use the same surface colors, white controls, accent selection and rounded borders. Forms wrap long rows to remain usable at narrower widths. Combo popups and scrollbars share the theme. Global panel-label positions have optional per-panel overrides, so common adjustments require one change.

The canvas preview fits the workspace. Manuscript preview is a separate PDF context: it places vector artwork without scaling, checks page bounds and column fit, and lets the user choose placement on an existing manuscript copy. Display zoom does not change exported dimensions. Fonts should be judged at intended print size; screen DPI can differ from physical size.
