"""Inspector forms; field changes are delegated to the window state controller."""

from PySide6 import QtGui as G
from PySide6 import QtWidgets as W

from ..constants import CMAPS, KINDS, TEMPLATES
from .widgets import ColorEdit, NumberBox


class EditorMixin:
    def page(self, name):
        scroll = W.QScrollArea()
        scroll.setWidgetResizable(True)
        body = W.QWidget()
        body.setObjectName("inspectorBody")
        layout = W.QVBoxLayout(body)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        scroll.setWidget(body)
        self.tabs.addTab(scroll, name)
        return layout

    def group(self, parent, title):
        group = W.QGroupBox(title)
        form = W.QFormLayout(group)
        form.setRowWrapPolicy(W.QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setSpacing(8)
        form.setFieldGrowthPolicy(W.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        parent.addWidget(group)
        return form

    def hint(self, parent, text):
        label = W.QLabel(text)
        label.setWordWrap(True)
        label.setObjectName("muted")
        parent.addWidget(label)
        return label

    def field(
        self,
        form,
        scope,
        key,
        label,
        kind="text",
        choices=None,
        minimum=0,
        maximum=100,
        step=0.1,
        tip="",
    ):
        if kind == "combo":
            widget = W.QComboBox()
            widget.addItems(choices or [])
            widget.currentTextChanged.connect(lambda value: self.change(scope, key, value))
        elif kind == "bool":
            widget = W.QCheckBox()
            widget.toggled.connect(lambda value: self.change(scope, key, value))
        elif kind in ["int", "float", "factor", "dimension"]:
            widget = W.QSpinBox() if kind == "int" else NumberBox()
            widget.setRange(minimum, maximum)
            if kind in ["float", "factor", "dimension"]:
                widget.setDecimals(16 if kind == "factor" else 6)
                widget.setSingleStep(step)
            if kind == "dimension":
                widget.setStyleSheet("QDoubleSpinBox { padding-right: 22px; }")
                widget.setDecimals(2)
            widget.setKeyboardTracking(False)
            widget.valueChanged.connect(lambda value: self.change(scope, key, value))
        elif kind == "color":
            widget = ColorEdit()
            widget.changed.connect(lambda value: self.change(scope, key, value))
        else:
            widget = W.QLineEdit()
            widget.setPlaceholderText("Auto" if key.endswith(("min", "max", "ticks")) else "")
            widget.textEdited.connect(lambda value: self.change(scope, key, value))
        if tip:
            widget.setToolTip(tip)
        form.addRow(label, widget)
        self.fields[(scope, key)] = widget
        self.field_rows[(scope, key)] = (form, widget)
        return widget

    def build_figure_tab(self):
        box = self.page("Figure")
        form = self.group(box, "Publication size")
        self.field(form, "g", "template", "Publisher template", "combo", list(TEMPLATES))
        self.field(form, "g", "columns", "Column format", "combo", ["Single", "Double"])
        self.field(form, "g", "width", "Width / mm", "dimension", minimum=30, maximum=500, step=1)
        self.field(form, "g", "height", "Height / mm", "dimension", minimum=30, maximum=500, step=1)
        self.field(form, "g", "dpi", "Raster export DPI", "int", minimum=72, maximum=2400)
        self.hint(
            box, "Type width and height in millimetres; press Enter or leave the field to apply."
        )
        self.template_note = self.hint(
            box, "Templates are starting points; verify the target journal’s instructions."
        )
        self.template_link = W.QLabel()
        self.template_link.setOpenExternalLinks(True)
        box.addWidget(self.template_link)
        form = self.group(box, "Layout & relative panel sizes")
        self.field(form, "g", "rows", "Rows", "int", minimum=1, maximum=8)
        self.field(form, "g", "cols", "Columns", "int", minimum=1, maximum=8)
        self.field(
            form,
            "g",
            "width_ratios",
            "Column ratios",
            tip="One positive number per column; e.g. 20:50:30. Blank = equal.",
        )
        self.field(
            form,
            "g",
            "height_ratios",
            "Row ratios",
            tip="One positive number per row; e.g. 2:1. Blank = equal.",
        )
        self.field(
            form, "g", "wspace", "Horizontal gap / %", "float", minimum=0, maximum=100, step=1
        )
        self.field(form, "g", "hspace", "Vertical gap / %", "float", minimum=0, maximum=100, step=1)
        self.hint(
            box,
            "Gaps are a percentage of the subplot grid dimension. Automatic layout also reserves space for labels and colorbars.",
        )
        reset = W.QPushButton("Reset size & spacing")
        reset.setToolTip(
            "Restore template width, balanced height, equal panel sizes and automatic spacing. Undo restores your previous layout."
        )
        reset.clicked.connect(self.reset_geometry)
        form.addRow("", reset)
        button = W.QPushButton("Arrange panels in this grid")
        button.clicked.connect(self.reflow)
        form.addRow("", button)
        self.hint(
            box,
            "Ratios control grid tracks. Use panel spans in the Panel tab to create larger individual panels.",
        )
        self.field(form, "g", "sharex", "Share X axes", "bool")
        self.field(form, "g", "sharey", "Share Y axes", "bool")
        form = self.group(box, "Typography & appearance")
        self.field(
            form,
            "g",
            "family",
            "Font family",
            "combo",
            ["Arial", "DejaVu Sans", "Helvetica", "DejaVu Serif", "STIXGeneral"],
        )
        self.field(form, "g", "font", "Base font / pt", "float", minimum=5, maximum=30, step=0.5)
        self.field(
            form, "g", "title_scale", "Title size multiplier", "float", minimum=0.5, maximum=3
        )
        self.field(form, "g", "line_width", "Line width / pt", "float", minimum=0.2, maximum=6)
        self.field(form, "g", "marker_size", "Marker size / pt", "float", minimum=1, maximum=15)
        self.field(form, "g", "tick_direction", "Tick direction", "combo", ["in", "out", "inout"])
        self.field(form, "g", "colormap", "Palette / colormap", "combo", CMAPS)
        self.field(form, "g", "grid", "Light grid", "bool")
        self.field(form, "g", "legend", "Show legends", "bool")
        self.field(form, "g", "letters", "Panel labels", "bool")
        self.field(form, "g", "label_case", "Label case", "combo", ["lowercase", "uppercase"])
        self.field(form, "g", "label_parentheses", "Parentheses", "bool")
        self.field(form, "g", "label_x", "Label X / axes fraction", "float", minimum=-1, maximum=2)
        self.field(form, "g", "label_y", "Label Y / axes fraction", "float", minimum=-1, maximum=2)
        button = W.QPushButton("Reset all series to automatic palette")
        button.clicked.connect(self.reset_colors)
        box.addWidget(button)
        self.hint(
            box,
            "Auto-colored series follow the palette. Explicit series colors override it. The same colormap controls heatmaps.",
        )
        box.addStretch()

    def build_panel_tab(self):
        box = self.page("Panel")
        form = self.group(box, "Selected panel")
        self.field(form, "p", "name", "Panel name")
        self.field(form, "p", "dataset", "Dataset", "combo")
        self.field(form, "p", "kind", "Plot type", "combo", KINDS)
        self.field(
            form,
            "p",
            "line_order",
            "Line connection order",
            "combo",
            ["Sort by X", "CSV row order"],
            tip="Use CSV row order for cyclic voltammetry and other paths that reverse direction.",
        )
        self.field(
            form,
            "p",
            "aspect",
            "Axis unit aspect",
            "combo",
            ["auto", "equal"],
            tip="Equal keeps one X unit the same physical length as one Y unit, useful for Nyquist plots.",
        )
        self.field(form, "p", "x", "X / category column", "combo")
        self.field(form, "p", "category_colors", "Color bars by category", "bool")
        self.field(
            form, "p", "palette_offset", "Palette starting offset", "int", minimum=0, maximum=10
        )
        self.field(form, "p", "legend", "Legend visibility", "combo", ["Auto", "Show", "Hide"])
        self.field(
            form,
            "p",
            "legend_loc",
            "Legend position",
            "combo",
            [
                "best",
                "upper right",
                "upper left",
                "lower left",
                "lower right",
                "center",
                "center left",
                "center right",
                "upper center",
                "lower center",
            ],
        )
        self.field(form, "p", "title", "Title")
        self.field(form, "p", "xlabel", "X label")
        self.field(form, "p", "ylabel", "Y label")
        self.hint(
            box,
            r"Math labels: $H_{2}O$, $10^{-3}$, $\alpha$. Put math between dollar signs. Applies to titles, axes, legends and text annotations.",
        )
        form = self.group(box, "Panel label & shape")
        self.field(
            form,
            "p",
            "label_x",
            "Label X override",
            tip="Blank follows Figure settings. Coordinates are fractions of the axes.",
        )
        self.field(form, "p", "label_y", "Label Y override")
        self.field(
            form,
            "p",
            "box_aspect",
            "Height / width ratio",
            tip="Blank = automatic; 1 gives a square plotting area.",
        )
        self.field(form, "p", "heatmap_label", "Colorbar label")
        form = self.group(box, "Grid position")
        self.field(form, "p", "row", "Row (starts at 1)", "int", minimum=1, maximum=8)
        self.field(form, "p", "col", "Column (starts at 1)", "int", minimum=1, maximum=8)
        self.field(form, "p", "rowspan", "Row span", "int", minimum=1, maximum=8)
        self.field(form, "p", "colspan", "Column span", "int", minimum=1, maximum=8)
        self.field(
            form,
            "p",
            "offset_x",
            "X offset / mm",
            "float",
            minimum=-20,
            maximum=20,
            step=0.25,
            tip="Fine adjustment from the automatic grid position. Positive moves right; zero restores the grid position.",
        )
        self.field(
            form,
            "p",
            "offset_y",
            "Y offset / mm",
            "float",
            minimum=-20,
            maximum=20,
            step=0.25,
            tip="Positive moves up. Labels, annotations and image insets move with the panel.",
        )
        reset_position = W.QPushButton("Reset panel position")
        reset_position.clicked.connect(self.reset_panel_position)
        form.addRow("", reset_position)
        form = self.group(box, "Axes, limits & ticks")
        for axis in ["x", "y"]:
            self.field(
                form, "p", axis + "scale", axis.upper() + " scale", "combo", ["linear", "log"]
            )
            self.field(form, "p", axis + "min", axis.upper() + " minimum")
            self.field(form, "p", axis + "max", axis.upper() + " maximum")
            self.field(
                form,
                "p",
                axis + "count",
                axis.upper() + " target tick count",
                "int",
                minimum=2,
                maximum=20,
                tip="Approximate count; Matplotlib chooses readable steps.",
            )
            self.field(
                form,
                "p",
                axis + "ticks",
                axis.upper() + " explicit ticks",
                tip="Comma-separated positions, e.g. 0, 0.5, 1. Overrides automatic ticks.",
            )
            self.field(
                form,
                "p",
                axis + "decimals",
                axis.upper() + " decimals (-1 auto)",
                "int",
                minimum=-1,
                maximum=8,
            )
        self.field(
            form, "p", "rotation", "X label rotation / °", "float", minimum=-90, maximum=90, step=5
        )
        button = W.QPushButton("Copy axes to all plot panels")
        button.clicked.connect(self.copy_axes)
        box.addWidget(button)
        self.hint(
            box,
            "Shared axes require matching scales, limits and tick settings. Copy axes first, then enable sharing in Figure.",
        )
        form = self.group(box, "Main image & inset")
        self.main_image_label = W.QLabel("No main image")
        form.addRow("Main image", self.main_image_label)
        row = W.QWidget()
        layout = W.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        for text, fn in [
            ("Choose…", lambda: self.choose_image(False)),
            ("Clear", lambda: self.clear_image(False)),
        ]:
            b = W.QPushButton(text)
            b.clicked.connect(fn)
            layout.addWidget(b)
        form.addRow("", row)
        self.inset_label = W.QLabel("No inset")
        form.addRow("Inset image", self.inset_label)
        row = W.QWidget()
        layout = W.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        for text, fn in [
            ("Choose…", lambda: self.choose_image(True)),
            ("Clear", lambda: self.clear_image(True)),
        ]:
            b = W.QPushButton(text)
            b.clicked.connect(fn)
            layout.addWidget(b)
        form.addRow("", row)
        self.field(
            form,
            "p",
            "inset_bounds",
            "Inset x,y,w,h",
            tip="Axes fractions, e.g. 0.58,0.58,0.38,0.38",
        )
        self.field(form, "p", "image_alpha", "Image opacity", "float", minimum=0, maximum=1)
        self.field(form, "p", "colorbar", "Heatmap colorbar", "bool")
        self.hint(
            box,
            "Choosing a main image switches the panel to Image. Inset bounds are fractions of the selected panel; images keep their original aspect ratio.",
        )
        box.addStretch()

    def build_series_tab(self):
        box = self.page("Series")
        self.hint(
            box,
            "Each series can have its own label, line, marker, color, scaling and uncertainty column. Changes apply immediately.",
        )
        self.series_list = W.QListWidget()
        self.series_list.setMaximumHeight(160)
        self.series_list.currentRowChanged.connect(self.select_series)
        box.addWidget(self.series_list)
        row = W.QHBoxLayout()
        self.add_column = W.QComboBox()
        row.addWidget(self.add_column, 1)
        b = W.QPushButton("+ Series")
        b.clicked.connect(self.add_series)
        row.addWidget(b)
        box.addLayout(row)
        b = W.QPushButton("Remove selected series")
        b.clicked.connect(self.remove_series)
        box.addWidget(b)
        form = self.group(box, "Series styling")
        self.field(form, "s", "visible", "Visible", "bool")
        self.field(form, "s", "y", "Y / value column", "combo")
        self.field(form, "s", "label", "Legend label")
        self.field(form, "s", "color", "Color (blank = auto)", "color")
        self.field(
            form,
            "s",
            "marker",
            "Marker",
            "combo",
            ["o", "s", "^", "v", "D", "P", "X", "+", "x", "*", "None"],
        )
        self.field(
            form,
            "s",
            "linestyle",
            "Line style",
            "combo",
            ["solid", "dashed", "dotted", "dashdot", "none"],
        )
        self.field(form, "s", "error", "Y uncertainty column", "combo")
        form = self.group(box, "Unit conversion / scaling")
        self.field(
            form, "s", "xfactor", "Multiply X by", "factor", minimum=-1e12, maximum=1e12, step=1
        )
        self.field(
            form, "s", "yfactor", "Multiply Y by", "factor", minimum=-1e12, maximum=1e12, step=1
        )
        self.hint(
            box,
            "Scaling affects plotted values only. Uncertainties scale by |Y factor|. X factors apply to numeric Line/Scatter plots; categorical labels are preserved.",
        )
        self.hint(
            box,
            "Bar charts need one summary row per category. Box, Violin and Strip show replicate distributions without silently averaging them.",
        )
        box.addStretch()

    def build_marks_tab(self):
        box = self.page("Marks")
        self.hint(
            box,
            "Add text, highlights or callouts to the selected panel. Use data units or panel fractions (0–1).",
        )
        self.marks = W.QListWidget()
        self.marks.setMaximumHeight(150)
        self.marks.currentRowChanged.connect(self.select_mark)
        box.addWidget(self.marks)
        row = W.QHBoxLayout()
        self.mark_kind = W.QComboBox()
        self.mark_kind.addItems(["Text", "Rectangle", "Ellipse", "Line", "Arrow"])
        row.addWidget(self.mark_kind, 1)
        b = W.QPushButton("+ Add")
        b.clicked.connect(self.add_mark)
        row.addWidget(b)
        box.addLayout(row)
        b = W.QPushButton("Remove selected annotation")
        b.clicked.connect(self.remove_mark)
        box.addWidget(b)
        self.place_button = W.QPushButton("Place on preview")
        self.place_button.setCheckable(True)
        self.place_button.toggled.connect(self.toggle_place)
        box.addWidget(self.place_button)
        self.hint(
            box,
            "Text: click once. Shapes, lines and arrows: click a start and an end point. Press Esc to cancel placement.",
        )
        form = self.group(box, "Annotation properties")
        self.field(
            form, "a", "kind", "Type", "combo", ["Text", "Rectangle", "Ellipse", "Line", "Arrow"]
        )
        self.field(form, "a", "text", "Text / math label")
        self.field(form, "a", "coords", "Coordinates", "combo", ["Axes fraction", "Data"])
        for key, label in [
            ("x", "X / start X"),
            ("y", "Y / start Y"),
            ("x2", "End X"),
            ("y2", "End Y"),
            ("width", "Width"),
            ("height", "Height"),
        ]:
            self.field(form, "a", key, label, "float", minimum=-1e12, maximum=1e12, step=0.05)
        self.field(form, "a", "color", "Color", "color")
        self.field(form, "a", "alpha", "Opacity", "float", minimum=0, maximum=1)
        self.field(form, "a", "linewidth", "Line width / pt", "float", minimum=0.1, maximum=8)
        self.field(form, "a", "fontsize", "Text size / pt", "float", minimum=4, maximum=40)
        self.field(
            form, "a", "linestyle", "Line style", "combo", ["solid", "dashed", "dotted", "dashdot"]
        )
        self.field(form, "a", "zorder", "Layer (higher = front)", "int", minimum=0, maximum=30)
        box.addStretch()
        escape = G.QShortcut(G.QKeySequence("Escape"), self)
        escape.activated.connect(lambda: self.place_button.setChecked(False))
