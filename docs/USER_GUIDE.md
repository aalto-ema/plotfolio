# PlotFolio user guide

A live Qt desktop editor for publication figures. Built with **PySide6 (Qt's official Python bindings)** and Matplotlib. Select an existing panel and edit it directly: changes update the preview automatically. There is no re-add or rebuild step.

## Start

Requires Python 3.10+ and a desktop environment.

Install with `python -m pip install -e .`, then run `plotfolio` or `python -m plotfolio`.

Manual setup on macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m plotfolio
```

On Windows use `py -3 -m venv .venv`, `.venv\Scripts\activate`, then the same pip and app commands. No Tkinter is required.

The app opens a four-panel electrochemistry example so you can immediately explore the controls. Choose **New** for an empty project. You can also run `python -m plotfolio examples/example.plotfolio.json`. Default datasets are schematic cyclic voltammetry (`example_cv.csv`) and ideal RC impedance (`example_eis.csv`). Additional sample CSVs for kinetics, categorical summaries and replicate distributions are retained.

## Workspace

- **Left:** select, add, duplicate, reorder or remove panels; choose a dataset to preview.
- **Center:** a live figure preview that keeps the specified aspect ratio. Click a plot to select its panel. The toolbar supports inspection with pan/zoom; **Use view as limits** stores the selected panel's view for export.
- **Right:** four focused tabs: **Figure**, **Panel**, **Series**, and **Marks**. Scroll within a tab to reach additional settings.
- **Bottom:** an optional read-only CSV preview. All rows are available through a virtual table model; scaling never changes source values.

Text edits update after a short pause. Numeric controls accept a value with Enter or when you leave the field. Undo and redo preserve changes to plots, images, annotations, data and layout. If a setting is temporarily invalid, an inline message explains the problem and the last valid preview stays visible. Exports require valid settings.

Shortcuts: New `Ctrl+N`, Open `Ctrl+O`, Save `Ctrl+S`, Save As `Ctrl+Shift+S`, Import `Ctrl+I`, Undo `Ctrl+Z`, Redo `Ctrl+Shift+Z`. Qt uses the corresponding Command shortcuts on macOS. Escape cancels annotation placement.

## Data and plot types

CSV/TSV import retains numeric and text columns. Use a header row with unique, nonempty names. Comma, semicolon and tab delimiters are detected, and UTF-8 BOM files are supported. Decimal points and scientific notation are accepted. Malformed row lengths are reported with their line number. Import multiple CSV files to combine datasets in a figure.

In **Panel**, choose the dataset, X/category column and plot type. In **Series**, add one or more numeric value columns. Changing to a dataset with matching column names preserves compatible series styles.

| Type | Meaning |
|---|---|
| Line | Numeric X/Y pairs; choose sorted X or original CSV order; optional symmetric Y error bars |
| Scatter | Numeric X/Y pairs; optional symmetric Y error bars |
| Bar | Text or numeric categories; grouped bars for multiple value columns |
| Box | Replicate distributions for each category and series |
| Violin | Replicate density distributions; each group needs at least two distinct values |
| Strip | Individual observations by category, with deterministic small horizontal offsets |
| Histogram | Value distribution; automatic bin selection |
| Heatmap | CSV rows × selected numeric series; optional colorbar |
| Image | An imported image as the panel's main content |

Bar plots require one summary row per category. The app deliberately does not average replicates or infer error statistics: use Box, Violin or Strip for raw replicates, or prepare explicit summary rows for bars. Category ordering follows the CSV. Category X axes retain category labels; numeric X tick controls are disabled for those plots. Heatmap row numbers follow CSV order.

Missing, nonnumeric and infinite plotted values are excluded with a visible count. Nonpositive values are excluded on logarithmic axes. Negative uncertainties are rejected. SD, SEM and confidence intervals must be defined by you and explained in the figure caption.

## Series styling, palettes and units

Each series has an editable legend label, visibility, color, marker, solid/dashed/dotted/dash-dot line style, X/Y multiplier and optional Y uncertainty column. Clear a color field to use the figure's selected palette. Color swatches open a color picker.

Available palettes/colormaps include the reference colors, tab10, Set2, Dark2, viridis, plasma, inferno, magma, cividis, coolwarm, Spectral and Greys. Auto colors follow the selected palette; explicit series colors override it. **Reset all series to automatic palette** clears overrides with undo available. A panel's palette starting offset lets adjacent panels use different parts of the same palette. Single-series bar plots can optionally color bars by category.

Line width, marker size, font family/base size, title size multiplier, grid and tick direction are controlled in **Figure**. Legends can be shown/hidden and positioned independently in **Panel**.

Scale factors accept scientific notation, such as `1e-3` or `1e-9`. Numeric X scaling applies to Line and Scatter; Y scaling applies to plotted values for all data plot types. Uncertainties scale by the absolute Y factor. Original CSV values remain unchanged. Data-coordinate annotations refer to the scaled plotted units.

## Axes and mathematical labels

Each panel has explicit minimum/maximum limits, linear/log scales, a target tick count, explicit comma-separated numeric tick positions, decimal precision and X-label rotation. Blank limits use automatic limits; `-1` decimal precision uses automatic formatting. The target count is approximate so ticks can use readable steps. Explicit ticks override automatic locations. Tick direction can be inward, outward or both.

Use Matplotlib math text for subscripts, superscripts and symbols in titles, axis labels, legend labels and text annotations:

- `H$_2$O`
- `$n(t)/n(0)$`
- `$x_i^{2}$`
- `$\tau = 1.42 \pm 0.05$ ps`

This supports mathematical labels without a local LaTeX installation; full LaTeX document syntax is not supported. If a requested font is unavailable, Matplotlib substitutes an installed font.

Shared X/Y axes link all compatible data plot panels. Images and heatmaps are excluded. Shared scales, limits and tick settings must match, and shared categorical X axes need identical category order. **Copy axes to all plot panels** prepares common settings before you enable sharing. Sharing all axes is figure-wide; separate sharing groups are not currently implemented.

## Unequal panels and layout

Set grid rows and columns in **Figure**. Enter **column ratios**, for example `20:50:30`, for a three-column grid, or **row ratios**, such as `2:1`, for a tall upper row. Ratios control the relative drawing space of grid tracks; labels and margins add space around the axes.

In **Panel**, set the row/column (numbered from 1) and row/column spans. A panel can span multiple tracks to make it individually larger. Overlaps and positions outside the grid are reported instead of silently drawing one panel over another. **Arrange panels in this grid** reflows all panels in list order, resets spans and adjusts the row count. Adding or duplicating a panel uses a free slot and adds a row if necessary.

## Annotations and images

**Marks** supports Text, Rectangle, Ellipse, Line and Arrow. Each has a color, opacity, coordinate system and layer order; shape/line thickness, line pattern and text size are editable where applicable.

- **Axes fraction:** X/Y range from 0 to 1 across the selected panel. Useful for labels that should stay in the same relative place.
- **Data:** coordinates use the plotted axis units, including any scaling.
- **Place on preview:** text uses one click; rectangles, ellipses, lines and arrows use two clicks. Select the panel first, then click inside it. Pan/zoom mode is disabled when you enter placement mode. Escape cancels.

A rectangle uses its lower-left X/Y corner plus width/height; an ellipse uses its center plus width/height. Lines and arrows use start/end coordinates. Set a rectangle to a low opacity (e.g. 0.2) to highlight a region. Layers above 2 cover ordinary data marks; lower layers sit beneath them.

In **Panel**, choose a main image to switch the panel to Image, or add an inset to an existing plot. Supported imports: PNG, JPEG, TIFF, BMP and WebP. Inset bounds use `x,y,width,height` fractions, for example `0.58,0.58,0.38,0.38`. Both main and inset images preserve aspect ratio. Images are embedded as PNG pixel data in projects; no external links are needed to reopen them. Import uses the first frame/page of animated or multipage images.

## Journal templates and export

Templates set a starting width, font size and export DPI. Height stays editable. These are publisher-guidance presets, **not a guarantee of acceptance by every journal**:

| Template | Single / double width | Basis |
|---|---|---|
| ACS — general graphics | 84.7 / 177.8 mm | General graphics dimensions in the linked ACS author guidelines |
| RSC — CrystEngComm | 83 / 171 mm | CrystEngComm's specified column widths |
| Wiley — general artwork | 80 / 180 mm | Endpoints of Wiley's general 80–180 mm width guidance |

The 9 pt font and 600 DPI settings are app defaults for these presets, not publisher-wide mandates. Follow your target journal's current instructions for size, font, file type and resolution. Source links are available in the app:

- [ACS author guidelines](https://researcher-resources.acs.org/publish/author_guidelines?coden=mamobx)
- [RSC CrystEngComm guidelines](https://www.rsc.org/publishing/publish-with-us/publish-a-journal-article/crystengcomm)
- [Wiley figure preparation](https://authors.wiley.com/author-resources/Journal-Authors/Prepare/manuscript-preparation-guidelines.html/figure-preparation.html)

Export PDF/SVG for vector lines and text, or PNG/TIFF with selectable DPI. Imported images retain raster pixels inside vector output; selecting a high DPI does not create missing image detail. The export canvas preserves the specified millimetre dimensions, independently of the preview window size. No tight-bounding-box crop changes the output size. The toolbar save button uses the same export workflow.

Pan/zoom changes the inspection view. Press **Use view as limits** if you want that view to become the figure's saved/exported limits. Export otherwise uses the explicit model settings. Inspect exported figures at their final size for readability and clipping.

## Portable projects

Save `.plotfolio.json` projects to embed the CSV contents, plot settings and image pixels. Source files are never modified. Open/Save As lets you create figure variants. Existing version-1 PlotFolio JSON projects can be opened and migrated; their original linked CSV must be available for that first migration. Once saved in this version, the data are embedded.

Projects do not automatically reload external CSV files. Import updated data and choose the new dataset in the desired panels. This keeps a saved figure reproducible from its captured data.

## Verification

```sh
python -m unittest discover -s tests -p 'test_engine.py'
QT_QPA_PLATFORM=offscreen python tests/ui_smoke.py
QT_QPA_PLATFORM=offscreen python tests/ui_interactions.py
```

On Windows set `QT_QPA_PLATFORM=offscreen` as an environment variable before the UI scripts. Checks cover the plot types, category labels, uncertainty scaling, missing/log data, ratios/spans, shared axes, annotations, images, legacy migration, physical export dimensions, live editing, undo/redo, unit factors, click placement and portable projects.

## Default electrochemistry examples

The startup figure contains CV at 25, 50 and 100 mV/s, an EIS Nyquist plot, a categorical activity bar chart, and a normalized response heatmap. **All data are synthetic.** The CV is schematic: Gaussian oxidation/reduction peaks with a capacitive background, not a diffusion simulation or fitted experiment. EIS is calculated from `Z = Rs + Rct / (1 + j·2πf·Rct·Cdl)` with Rs = 12 Ω, Rct = 180 Ω and Cdl = 40 µF; there is no Warburg element.

The CV uses **CSV row order**, which preserves the turning point and reverse sweep. Use this setting for imported voltammograms too; sorting potential destroys the acquisition path. Nyquist uses equal axis units so its ideal semicircle is not distorted. Both controls are in the Panel tab.

Technique references: [Pine Research CV](https://pineresearch.com/support-article/cyclic-voltammetry-cv/) and [Gamry EIS](https://www.gamry.com/application-notes/eis/basics-of-electrochemical-impedance-spectroscopy).

## PlotFolio 0.3 additions

Use Figure → Panel labels to choose case, parentheses and axes-fraction positions. Panel → Panel label & shape gives per-panel overrides; leave these blank to follow global settings. Height/width ratio 1 makes a square plotting area.

Choose Manuscript preview from the toolbar to see the figure on A4 or Letter paper. Two-column mode verifies single-column fit and never shrinks the figure. Open manuscript PDF to place the figure on a selected existing page using millimetre offsets from the left and top. Save preview PDF creates a copy. Screen zoom affects only viewing, and 100% depends on display DPI.

## Direct dimensions and layout reset

In Figure → Publication size, type numeric width and height in millimetres, then press Enter or leave the field. Horizontal and vertical gap controls set minimum spacing as percentages of the subplot grid; automatic layout can add room for axis labels and colorbars. Reset size & spacing restores the selected template width, a balanced height, equal grid tracks, automatic gaps and panel shapes, and removes panel spans. It retains your column count, data and styling. Undo restores the previous layout.

## Fine panel positioning

Select a panel, then use Panel → Grid position → X offset / mm and Y offset / mm. Zero follows the automatic grid; positive X moves right and positive Y moves up. Use 0.25 mm steps or type an exact value. The panel, labels, annotations, inset and colorbar move together; data values and axis limits stay unchanged. Offsets also apply to exported figures and manuscript previews. Reset panel position clears only the selected panel's offsets; Undo restores them. Reset size & spacing clears all panel offsets. Large shifts can overlap adjacent panels or clip labels, so inspect the preview.
