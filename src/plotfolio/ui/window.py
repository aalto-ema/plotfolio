"""PlotFolio main window and live editing state controller."""

import copy
import math
import time
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6 import QtCore as C
from PySide6 import QtGui as G
from PySide6 import QtWidgets as W

from ..engine import (
    SOURCES,
    TEMPLATES,
    annotation,
    build_figure,
    demo_document,
    image_payload,
    numeric_columns,
    panel,
    series,
)
from ..ingestion import axis_label
from .editors import EditorMixin
from .project_actions import ProjectActionsMixin
from .recovery import RecoveryMixin
from .theme import STYLE
from .widgets import ColorEdit, PreviewFrame, StudioToolbar
from .workflows import WorkflowMixin


class Studio(RecoveryMixin, WorkflowMixin, EditorMixin, ProjectActionsMixin, W.QMainWindow):
    def __init__(self):
        super().__init__()
        self.doc = demo_document()
        self.filename = None
        self.dirty = False
        self.guard = True
        self.history = []
        self.future = []
        self.last_edit = None
        self.last_edit_time = 0
        self.panel_index = 0
        self.series_index = 0
        self.mark_index = -1
        self.fields = {}
        self.field_rows = {}
        self.plot_axes = []
        self.canvas = None
        self.toolbar = None
        self.place_mode = False
        self.place_start = None
        self.resize(1500, 960)
        self.setMinimumSize(1060, 700)
        self.setStyleSheet(STYLE)
        self.timer = C.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(230)
        self.timer.timeout.connect(self.render)
        self.create_toolbar()
        self.create_layout()
        self.create_data_dock()
        self.guard = False
        self.refresh()
        self.render()
        self.setup_recovery()

    def create_toolbar(self):
        bar = self.addToolBar("Project")
        bar.setMovable(False)
        bar.addWidget(W.QLabel("PlotFolio  /  Studio"))
        self.actions = {}
        for text, shortcut, callback in [
            ("New", "Ctrl+N", self.new),
            ("Open", "Ctrl+O", self.open_project),
            ("Save", "Ctrl+S", self.save),
            ("Import data", "Ctrl+I", self.import_data),
            ("Undo", "Ctrl+Z", self.undo),
            ("Redo", "Ctrl+Shift+Z", self.redo),
        ]:
            action = G.QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            bar.addAction(action)
            self.actions[text] = action
        space = W.QWidget()
        space.setSizePolicy(W.QSizePolicy.Policy.Expanding, W.QSizePolicy.Policy.Preferred)
        bar.addWidget(space)
        self.live = W.QLabel("LIVE PREVIEW")
        self.live.setStyleSheet("font-size: 10px; color: #81DED0;")
        bar.addWidget(self.live)
        preview = W.QPushButton("Manuscript preview…")
        preview.clicked.connect(self.manuscript_preview)
        bar.addWidget(preview)
        export = W.QPushButton("Export figure…")
        export.setObjectName("primary")
        export.clicked.connect(self.export)
        bar.addWidget(export)
        file_menu = self.menuBar().addMenu("File")
        for name in ["New", "Open", "Save"]:
            file_menu.addAction(self.actions[name])
        save_as = G.QAction("Save as…", self)
        save_as.setShortcut("Ctrl+Shift+S")
        save_as.triggered.connect(self.save_as)
        file_menu.addAction(save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.actions["Import data"])
        file_menu.addAction("Export figure…", self.export)
        file_menu.addAction("Publication checks…", self.publication_checks)
        file_menu.addAction("Recover interrupted work…", self.recover_work)
        data_menu = self.menuBar().addMenu("Analyze")
        data_menu.addAction("Fit selected series…", self.fit_selected)
        data_menu.addAction("Transform dataset…", self.transform_dataset)
        data_menu.addAction("Summarize replicates…", self.summarize_replicates)
        data_menu.addSeparator()
        data_menu.addAction("Data provenance…", self.data_history)
        templates_menu = self.menuBar().addMenu("Templates")
        templates_menu.addAction("Save figure template…", self.save_figure_template)
        templates_menu.addAction("Apply figure template…", self.apply_figure_template)
        templates_menu.addAction("Batch plotting…", self.batch_plot)
        panel_menu = self.menuBar().addMenu("Panel tools")
        panel_menu.addAction("Align panels and guides…", self.align_and_snap)
        panel_menu.addAction("Zoom inset, linked axes & uncertainty…", self.panel_tools)
        menu = self.menuBar().addMenu("Help")
        menu.addAction("Quick guide", self.guide)
        menu.addAction("Load example", self.load_demo)

    def publication_checks(self):
        from .preflight import PreflightDialog

        PreflightDialog(self).exec()

    def align_and_snap(self):
        from .alignment import AlignmentDialog

        AlignmentDialog(self).exec()

    def create_layout(self):
        split = W.QSplitter()
        self.setCentralWidget(split)
        left = W.QWidget()
        lb = W.QVBoxLayout(left)
        lb.setContentsMargins(12, 16, 12, 12)
        title = W.QLabel("FIGURE PANELS")
        title.setObjectName("heading")
        lb.addWidget(title)
        hint = W.QLabel("Select a panel to edit it.\nClick a plot to select its panel.")
        hint.setObjectName("muted")
        lb.addWidget(hint)
        self.panels = W.QListWidget()
        self.panels.currentRowChanged.connect(self.select_panel)
        lb.addWidget(self.panels, 1)
        row = W.QHBoxLayout()
        for text, fn in [("+ Panel", self.add_panel), ("Duplicate", self.duplicate_panel)]:
            button = W.QPushButton(text)
            button.clicked.connect(fn)
            row.addWidget(button)
        lb.addLayout(row)
        row = W.QHBoxLayout()
        for text, fn in [
            ("↑", lambda: self.move_panel(-1)),
            ("↓", lambda: self.move_panel(1)),
            ("Remove", self.remove_panel),
        ]:
            button = W.QPushButton(text)
            button.clicked.connect(fn)
            row.addWidget(button)
        lb.addLayout(row)
        lb.addSpacing(16)
        lbl = W.QLabel("DATASETS")
        lbl.setObjectName("heading")
        lb.addWidget(lbl)
        self.datasets = W.QListWidget()
        self.datasets.setMaximumHeight(160)
        self.datasets.currentRowChanged.connect(self.dataset_selected)
        lb.addWidget(self.datasets)
        button = W.QPushButton("Preview data")
        button.clicked.connect(self.show_data)
        lb.addWidget(button)
        button = W.QPushButton("Import data…")
        button.clicked.connect(self.import_data)
        lb.addWidget(button)
        note = W.QLabel(
            "Data and images are embedded\nin saved projects. Source files\nare never modified."
        )
        note.setObjectName("muted")
        lb.addWidget(note)
        left.setMinimumWidth(210)
        left.setMaximumWidth(300)
        split.addWidget(left)
        center = W.QWidget()
        cb = W.QVBoxLayout(center)
        cb.setContentsMargins(12, 16, 12, 12)
        self.preview_title = W.QLabel("Figure preview")
        self.preview_title.setObjectName("heading")
        cb.addWidget(self.preview_title)
        self.message = W.QLabel("")
        self.message.setWordWrap(True)
        self.message.setMinimumHeight(30)
        cb.addWidget(self.message)
        self.plot_container = W.QWidget()
        self.plot_container.setStyleSheet("background: white; border-radius: 8px;")
        self.plot_layout = W.QVBoxLayout(self.plot_container)
        self.plot_layout.setContentsMargins(4, 4, 4, 4)
        cb.addWidget(self.plot_container, 1)
        self.summary = W.QLabel()
        self.summary.setObjectName("muted")
        cb.addWidget(self.summary)
        split.addWidget(center)
        self.tabs = W.QTabWidget()
        self.tabs.setMinimumWidth(380)
        self.tabs.setMaximumWidth(470)
        split.addWidget(self.tabs)
        self.build_figure_tab()
        self.build_panel_tab()
        self.build_series_tab()
        self.build_marks_tab()
        split.setSizes([225, 850, 400])
        self.statusBar().showMessage("Ready — edits update the figure automatically")

    def manuscript_preview(self):
        from .manuscript import ManuscriptDialog

        dialog = ManuscriptDialog(self.doc, self)
        dialog.exec()

    def create_data_dock(self):
        self.data_dock = W.QDockWidget("Data preview — original CSV values", self)
        self.data_dock.setAllowedAreas(C.Qt.DockWidgetArea.BottomDockWidgetArea)
        body = W.QWidget()
        layout = W.QVBoxLayout(body)
        row = W.QHBoxLayout()
        self.data_choice = W.QComboBox()
        self.data_choice.currentTextChanged.connect(self.update_data)
        row.addWidget(self.data_choice)
        self.data_info = W.QLabel()
        row.addWidget(self.data_info, 1)
        b = W.QPushButton("Export original CSV…")
        b.clicked.connect(self.export_data)
        row.addWidget(b)
        layout.addLayout(row)
        self.data_table = W.QTableView()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(False)
        layout.addWidget(self.data_table)
        self.data_dock.setWidget(body)
        self.addDockWidget(C.Qt.DockWidgetArea.BottomDockWidgetArea, self.data_dock)
        self.data_dock.hide()

    def current_panel(self):
        return (
            self.doc["panels"][self.panel_index]
            if 0 <= self.panel_index < len(self.doc["panels"])
            else None
        )

    def current_series(self):
        p = self.current_panel()
        return (
            p["series"][self.series_index]
            if p and 0 <= self.series_index < len(p["series"])
            else None
        )

    def current_mark(self):
        p = self.current_panel()
        return (
            p["annotations"][self.mark_index]
            if p and 0 <= self.mark_index < len(p["annotations"])
            else None
        )

    def target(self, scope):
        return {
            "g": lambda: self.doc["settings"],
            "p": self.current_panel,
            "s": self.current_series,
            "a": self.current_mark,
        }[scope]()

    def snapshot(self):
        # Source tables are immutable in this editor; share them across undo states.
        state = {k: copy.deepcopy(v) for k, v in self.doc.items() if k != "datasets"}
        state["datasets"] = dict(self.doc["datasets"])
        return state

    def checkpoint(self, key=None):
        now = time.monotonic()
        if key is None or key != self.last_edit or now - self.last_edit_time > 0.7:
            self.history.append(self.snapshot())
            self.history = self.history[-60:]
        self.last_edit = key
        self.last_edit_time = now
        self.future.clear()
        self.dirty = True

    def change(self, scope, key, value):
        if self.guard:
            return
        target = self.target(scope)
        if target is None:
            return
        if (
            scope == "p"
            and key in ["label_x", "label_y"]
            and self.doc["settings"].get("snap")
            and str(value).strip()
        ):
            from ..alignment import snap

            try:
                value = str(snap(float(value), self.doc["settings"].get("snap_step", 0.05)))
            except ValueError:
                pass
        if scope == "p" and key in ["row", "col"]:
            value = int(value) - 1
        if scope == "g" and key in ["wspace", "hspace"]:
            value = float(value) / 100
        if target.get(key) == value:
            return
        self.checkpoint((scope, self.panel_index, self.series_index, self.mark_index, key))
        target[key] = value
        if scope == "p" and key in ["dataset", "x"]:
            target["fits"] = []
            target["replicates"] = None
        if scope == "s" and key in ["y", "xfactor", "yfactor"] and self.current_panel():
            self.current_panel()["fits"] = []
            if key == "y":
                self.current_panel()["replicates"] = None
        if scope == "g" and key in ["template", "columns"]:
            single, double, font, dpi = TEMPLATES[self.doc["settings"]["template"]]
            self.doc["settings"].update(
                width=single if self.doc["settings"]["columns"] == "Single" else double
            )
            if key == "template" and value != "Custom":
                self.doc["settings"].update(font=font, dpi=dpi)
            self.fill_scope("g")
            self.template_description()
        if scope == "p" and key == "dataset":
            ds = self.doc["datasets"].get(value)
            if ds:
                nums = numeric_columns(ds)
                if target["x"] not in ds["headers"]:
                    target["x"] = ds["headers"][0]
                compatible = [s for s in target["series"] if s["y"] in nums]
                for s in compatible:
                    if s["error"] not in nums:
                        s["error"] = ""
                target["series"] = compatible or (
                    [series(next((v for v in nums if v != target["x"]), nums[0]))] if nums else []
                )
                self.series_index = 0
                self.refresh_editors()
        if scope == "p" and key in ["kind", "name", "row", "col", "rowspan", "colspan"]:
            self.refresh_panel_list()
            self.context_controls()
        if scope == "s" and key in ["label", "visible", "y"]:
            self.refresh_series_list()
        if scope == "a" and key in ["kind", "text"]:
            self.refresh_mark_list()
            self.context_controls()
        self.schedule()

    def set_value(self, widget, value):
        if isinstance(widget, ColorEdit):
            widget.set_value(value)
        elif isinstance(widget, W.QComboBox):
            value = str(value)
            if widget.findText(value) < 0:
                widget.addItem(value)
            widget.setCurrentText(value)
        elif isinstance(widget, W.QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, (W.QSpinBox, W.QDoubleSpinBox)):
            widget.setValue(float(value) if isinstance(widget, W.QDoubleSpinBox) else int(value))
        else:
            widget.setText(str(value))

    def fill_scope(self, scope):
        previous = self.guard
        self.guard = True
        target = self.target(scope)
        for (s, key), widget in self.fields.items():
            if s != scope:
                continue
            widget.setEnabled(target is not None)
            if target is not None:
                value = target[key]
                if scope == "p" and key in ["row", "col"]:
                    value += 1
                if scope == "g" and key in ["wspace", "hspace"]:
                    value *= 100
                self.set_value(widget, value)
        self.guard = previous

    def choices(self, scope, key, values):
        widget = self.fields[(scope, key)]
        widget.clear()
        widget.addItems(values)

    def refresh(self):
        self.guard = True
        ids = list(self.doc["datasets"])
        self.datasets.clear()
        for key in ids:
            ds = self.doc["datasets"][key]
            self.datasets.addItem(f"{key}\n{len(ds['rows']):,} rows · {len(ds['headers'])} columns")
        self.data_choice.clear()
        self.data_choice.addItems(ids)
        self.choices("p", "dataset", ids)
        self.panel_index = min(self.panel_index, len(self.doc["panels"]) - 1)
        self.refresh_panel_list()
        self.fill_scope("g")
        self.refresh_editors()
        self.template_description()
        self.guard = False
        self.update_data()
        self.update_title()

    def refresh_panel_list(self):
        prior = self.guard
        self.guard = True
        self.panels.clear()
        for i, p in enumerate(self.doc["panels"]):
            self.panels.addItem(
                f"{chr(65 + i) if i < 26 else i + 1}   {p['name']}\n     {p['kind']} · row {p['row'] + 1}, col {p['col'] + 1}"
            )
        self.panels.setCurrentRow(self.panel_index)
        self.guard = prior

    def refresh_editors(self):
        prior = self.guard
        self.guard = True
        p = self.current_panel()
        ds = self.doc["datasets"].get(p["dataset"]) if p else None
        headers = ds["headers"] if ds else []
        nums = numeric_columns(ds) if ds else []
        self.choices("p", "x", headers)
        self.choices("s", "y", nums)
        self.choices("s", "error", [""] + nums)
        self.add_column.clear()
        self.add_column.addItems(nums)
        self.fill_scope("p")
        self.refresh_series_list()
        self.refresh_mark_list()
        self.fill_scope("s")
        self.fill_scope("a")
        self.main_image_label.setText(p["image_name"] or "No main image" if p else "No panel")
        self.inset_label.setText(p["inset_name"] or "No inset" if p else "No panel")
        self.context_controls()
        self.guard = prior

    def refresh_series_list(self):
        prior = self.guard
        self.guard = True
        self.series_list.clear()
        p = self.current_panel()
        if p:
            for s in p["series"]:
                self.series_list.addItem(("● " if s["visible"] else "○ ") + s["label"])
            self.series_index = min(max(0, self.series_index), len(p["series"]) - 1)
        else:
            self.series_index = -1
        self.series_list.setCurrentRow(self.series_index)
        self.fill_scope("s")
        self.guard = prior

    def refresh_mark_list(self):
        prior = self.guard
        self.guard = True
        self.marks.clear()
        p = self.current_panel()
        if p:
            for a in p["annotations"]:
                self.marks.addItem(
                    a["kind"]
                    + " · "
                    + (a["text"][:25] if a["kind"] in ["Text", "Arrow"] else a["coords"])
                )
            self.mark_index = min(self.mark_index, len(p["annotations"]) - 1)
        else:
            self.mark_index = -1
        self.marks.setCurrentRow(self.mark_index)
        self.fill_scope("a")
        self.guard = prior

    def context_controls(self):
        p = self.current_panel()
        a = self.current_mark()
        s = self.current_series()
        image = bool(p and p["kind"] == "Image")
        self.fields[("p", "line_order")].setEnabled(bool(p and p["kind"] == "Line"))
        categorical = bool(
            p
            and (
                p["kind"] in ["Bar", "Box", "Violin", "Strip"]
                or (p["kind"] == "Scatter" and p.get("categorical_x", False))
            )
        )
        self.fields[("p", "category_colors")].setEnabled(
            bool(p and p["kind"] == "Bar" and len(p["series"]) == 1)
        )
        self.fields[("p", "palette_offset")].setEnabled(p is not None and not image)
        for key in [
            "dataset",
            "x",
            "xscale",
            "yscale",
            "xmin",
            "xmax",
            "ymin",
            "ymax",
            "xticks",
            "yticks",
            "xcount",
            "ycount",
            "xdecimals",
            "ydecimals",
            "rotation",
        ]:
            self.fields[("p", key)].setEnabled(
                p is not None
                and not image
                and not (key == "x" and p["kind"] == "Histogram")
                and not (categorical and key in ["xscale", "xticks", "xcount", "xdecimals"])
            )
        for key in ["linestyle", "marker", "xfactor", "error"]:
            allowed = bool(p and s)
            if key == "linestyle":
                allowed = allowed and p["kind"] == "Line"
            elif key == "marker":
                allowed = allowed and p["kind"] in ["Line", "Scatter", "Strip"]
            elif key == "xfactor":
                allowed = allowed and p["kind"] in ["Line", "Scatter"]
            else:
                allowed = allowed and p["kind"] in ["Line", "Scatter", "Bar"]
            self.fields[("s", key)].setEnabled(allowed)
        for key in ["text", "fontsize", "x2", "y2", "width", "height", "linewidth", "linestyle"]:
            form, widget = self.field_rows[("a", key)]
            visible = (
                not a
                or (key in ["text", "fontsize"] and a["kind"] in ["Text", "Arrow"])
                or (key in ["x2", "y2"] and a["kind"] in ["Line", "Arrow"])
                or (key in ["width", "height"] and a["kind"] in ["Rectangle", "Ellipse"])
                or (key in ["linewidth", "linestyle"] and a["kind"] != "Text")
            )
            form.setRowVisible(widget, visible)
        self.place_button.setEnabled(a is not None)

    def select_panel(self, index):
        if self.guard:
            return
        self.panel_index = index
        self.series_index = 0
        self.mark_index = -1
        self.place_button.setChecked(False)
        self.refresh_editors()
        self.update_summary()

    def select_series(self, index):
        if self.guard:
            return
        self.series_index = index
        self.fill_scope("s")
        self.context_controls()

    def select_mark(self, index):
        if self.guard:
            return
        self.mark_index = index
        self.fill_scope("a")
        self.context_controls()

    def dataset_selected(self, index):
        if self.guard or index < 0:
            return
        self.data_choice.setCurrentIndex(index)

    def schedule(self):
        self.timer.start()
        self.update_title()
        self.update_summary()

    def update_title(self):
        self.setWindowTitle(
            f"PlotFolio Studio — {Path(self.filename).name if self.filename else 'Untitled'}"
            + (" • unsaved" if self.dirty else "")
        )
        self.actions["Undo"].setEnabled(bool(self.history))
        self.actions["Redo"].setEnabled(bool(self.future))

    def update_summary(self):
        g = self.doc["settings"]
        p = self.current_panel()
        self.summary.setText(
            f"{g['width']:g} × {g['height']:g} mm  •  {len(self.doc['panels'])} panels  •  {g['dpi']} DPI raster export  •  Selected: {p['name'] if p else 'none'}"
        )

    def template_description(self):
        name = self.doc["settings"]["template"]
        url = SOURCES.get(name)
        self.template_link.setText(
            f'<a href="{url}">Publisher figure guidance ↗</a>' if url else ""
        )
        self.template_note.setText(
            "Editable starting point. RSC values are from CrystEngComm; Wiley is general guidance. Check your specific journal."
        )

    def render(self):
        try:
            fig, axes, notes = build_figure(self.doc)
            if self.place_mode and self.doc["settings"].get("snap"):
                import numpy as np

                for ax in axes[self.panel_index : self.panel_index + 1]:
                    for position in np.arange(
                        0, 1.001, self.doc["settings"].get("snap_step", 0.05)
                    ):
                        ax.plot(
                            [position, position],
                            [0, 1],
                            transform=ax.transAxes,
                            color="#008D8A",
                            alpha=0.2,
                            lw=0.4,
                            zorder=1.5,
                        )
                        ax.plot(
                            [0, 1],
                            [position, position],
                            transform=ax.transAxes,
                            color="#008D8A",
                            alpha=0.2,
                            lw=0.4,
                            zorder=1.5,
                        )
            canvas = FigureCanvasQTAgg(fig)
            canvas.draw()
            toolbar = StudioToolbar(canvas, self.plot_container, self.export, self.apply_view)
            canvas.mpl_connect("button_press_event", self.legend_press)
            canvas.mpl_connect("motion_notify_event", self.legend_motion)
            canvas.mpl_connect("button_release_event", self.legend_release)
            canvas.mpl_connect("button_press_event", self.plot_clicked)
            # Replace only after the new figure has rendered successfully.
            if self.canvas:
                self.plot_layout.removeWidget(self.plot_frame)
                self.plot_frame.deleteLater()
                self.plot_layout.removeWidget(self.toolbar)
                self.toolbar.deleteLater()
            self.canvas, self.toolbar, self.plot_axes = canvas, toolbar, axes
            self.rendered_panels = copy.deepcopy(self.doc["panels"])
            self.rendered_settings = copy.deepcopy(self.doc["settings"])
            self.plot_frame = PreviewFrame(
                canvas, float(self.doc["settings"]["width"]) / float(self.doc["settings"]["height"])
            )
            self.plot_layout.addWidget(toolbar)
            self.plot_layout.addWidget(self.plot_frame, 1)
            self.message.setStyleSheet("color: #65768C;")
            self.message.setText(
                " · ".join(notes[:3]) if notes else "Live preview · changes apply automatically"
            )
            self.live.setText("LIVE PREVIEW")
            self.update_summary()
            return True
        except Exception as e:
            self.message.setStyleSheet(
                "color: #B84B35; background: #FFF0EC; padding: 7px; border-radius: 5px;"
            )
            self.message.setText("Fix to update preview: " + str(e))
            self.live.setText("PREVIEW NEEDS UPDATE")
            return False

    def reset_legend_position(self, scope):
        target = self.target(scope)
        if target is None:
            return
        self.checkpoint()
        target.update(
            legend_placement="Outside below" if scope == "g" else "Inside", legend_x="", legend_y=""
        )
        if scope == "p":
            target["legend_loc"] = "best"
        self.fill_scope(scope)
        self.schedule()

    def legend_press(self, event):
        self.legend_drag = None
        if event.button != 1 or self.place_mode or self.toolbar.mode or self.timer.isActive():
            return
        if (
            getattr(self, "rendered_panels", []) != self.doc["panels"]
            or getattr(self, "rendered_settings", {}) != self.doc["settings"]
        ):
            return
        candidates = [
            (legend, "g", None, self.canvas.figure.transFigure)
            for legend in self.canvas.figure.legends
        ]
        candidates += [
            (ax.get_legend(), "p", i, ax.transAxes)
            for i, ax in enumerate(self.plot_axes)
            if ax.get_legend()
        ]
        for legend, scope, index, transform in candidates:
            if legend.contains(event)[0]:
                self.focus_plot_field(
                    index if index is not None else self.panel_index,
                    0 if scope == "g" else 1,
                    scope,
                    "legend_placement",
                )
                bounds = legend.get_window_extent(self.canvas.get_renderer())
                self.legend_drag = dict(
                    legend=legend,
                    scope=scope,
                    index=index,
                    transform=transform,
                    start=(event.x, event.y),
                    origin=(bounds.x0, bounds.y0),
                    moved=False,
                )
                return

    def legend_motion(self, event):
        drag = getattr(self, "legend_drag", None)
        if not drag or event.x is None or event.y is None:
            return
        dx, dy = event.x - drag["start"][0], event.y - drag["start"][1]
        if abs(dx) + abs(dy) < 3 and not drag["moved"]:
            return
        x, y = (
            drag["transform"].inverted().transform((drag["origin"][0] + dx, drag["origin"][1] + dy))
        )
        drag.update(position=(float(x), float(y)), moved=True)
        drag["legend"].set_loc("lower left")
        drag["legend"].borderaxespad = 0
        drag["legend"].set_bbox_to_anchor((x, y), transform=drag["transform"])
        self.canvas.draw_idle()

    def legend_release(self, event):
        drag = getattr(self, "legend_drag", None)
        self.legend_drag = None
        if not drag or not drag["moved"]:
            return
        self.checkpoint()
        target = self.doc["settings"] if drag["scope"] == "g" else self.doc["panels"][drag["index"]]
        target.update(
            legend_placement="Custom", legend_x=drag["position"][0], legend_y=drag["position"][1]
        )
        if drag["scope"] == "p":
            self.panels.setCurrentRow(drag["index"])
        self.fill_scope(drag["scope"])
        self.schedule()

    def focus_plot_field(self, panel_index, tab, scope, key):
        self.panels.setCurrentRow(panel_index)
        self.tabs.setCurrentIndex(tab)
        widget = self.fields[(scope, key)]
        self.tabs.currentWidget().ensureWidgetVisible(widget)
        widget.setFocus()

    def plot_clicked(self, event):
        if getattr(self, "legend_drag", None):
            return
        if event.button != 1 or self.toolbar.mode:
            return
        if (
            not self.place_mode
            and not self.timer.isActive()
            and getattr(self, "rendered_panels", []) == self.doc["panels"]
        ):
            from ..interaction import hit_target

            hit = hit_target(self.plot_axes, event)
            if hit:
                index, target = hit
                kind, key = target.split(":", 1)
                if kind == "panel":
                    self.focus_plot_field(index, 1, "p", key)
                    return
                self.panels.setCurrentRow(index)
                if kind == "series":
                    self.series_list.setCurrentRow(int(key))
                    self.tabs.setCurrentIndex(2)
                    return
                if kind == "annotation":
                    self.marks.setCurrentRow(int(key))
                    self.tabs.setCurrentIndex(3)
                    return
                if kind == "fit" and event.dblclick:
                    from .fit_style import FitStyleDialog

                    FitStyleDialog(self, self.doc["panels"][index]["fits"][int(key)]).exec()
                    return
                if kind == "fit":
                    self.statusBar().showMessage(
                        "Double-click this fitted curve to edit its appearance."
                    )
                    return
        if event.inaxes not in self.plot_axes:
            return
        # Do not place on a stale preview following an invalid edit.
        if getattr(self, "rendered_panels", []) != self.doc["panels"]:
            return
        index = self.plot_axes.index(event.inaxes)
        if not self.place_mode:
            self.panels.setCurrentRow(index)
            return
        if index != self.panel_index:
            self.statusBar().showMessage("Click inside the selected panel to place its annotation.")
            return
        a = self.current_mark()
        if not a:
            return
        if a["coords"] == "Axes fraction":
            x, y = event.inaxes.transAxes.inverted().transform((event.x, event.y))
        else:
            x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        if self.doc["settings"].get("snap"):
            from ..alignment import snap

            ax = event.inaxes
            fraction = ax.transAxes.inverted().transform((event.x, event.y))
            fraction = [snap(v, self.doc["settings"].get("snap_step", 0.05)) for v in fraction]
            x, y = (
                fraction
                if a["coords"] == "Axes fraction"
                else ax.transData.inverted().transform(ax.transAxes.transform(fraction))
            )
        self.checkpoint()
        if not self.place_start:
            a.update(x=float(x), y=float(y))
            if a["kind"] == "Text":
                self.place_button.setChecked(False)
            else:
                self.place_start = (float(x), float(y))
                self.statusBar().showMessage("Now click the second point.")
        else:
            x0, y0 = self.place_start
            if a["kind"] in ["Rectangle", "Ellipse"]:
                a.update(
                    x=min(x0, float(x)) if a["kind"] == "Rectangle" else (x0 + float(x)) / 2,
                    y=min(y0, float(y)) if a["kind"] == "Rectangle" else (y0 + float(y)) / 2,
                    width=max(abs(float(x) - x0), 1e-6),
                    height=max(abs(float(y) - y0), 1e-6),
                )
            else:
                a.update(x2=float(x), y2=float(y))
            self.place_button.setChecked(False)
        self.fill_scope("a")
        self.schedule()

    def apply_view(self):
        p = self.current_panel()
        if not p or p["kind"] in ["Image", "Heatmap"] or self.panel_index >= len(self.plot_axes):
            return
        ax = self.plot_axes[self.panel_index]
        self.checkpoint()
        p.update(
            xmin=f"{ax.get_xlim()[0]:.12g}",
            xmax=f"{ax.get_xlim()[1]:.12g}",
            ymin=f"{ax.get_ylim()[0]:.12g}",
            ymax=f"{ax.get_ylim()[1]:.12g}",
        )
        if self.doc["settings"]["sharex"] or self.doc["settings"]["sharey"]:
            for target in self.doc["panels"]:
                if target["kind"] in ["Image", "Heatmap"]:
                    continue
                for axis in ["x", "y"]:
                    if self.doc["settings"]["share" + axis]:
                        target[axis + "min"] = p[axis + "min"]
                        target[axis + "max"] = p[axis + "max"]
        self.fill_scope("p")
        self.schedule()

    def toggle_place(self, checked):
        self.place_mode = checked
        self.place_start = None
        if self.doc["settings"].get("snap"):
            self.schedule()
        if checked and self.toolbar and self.toolbar.mode:
            if "pan" in str(self.toolbar.mode).lower():
                self.toolbar.pan()
            elif "zoom" in str(self.toolbar.mode).lower():
                self.toolbar.zoom()
        self.place_button.setText("Click selected panel…" if checked else "Place on preview")
        self.statusBar().showMessage(
            "Click selected panel; two clicks for shapes/arrows/lines. Esc cancels."
            if checked
            else "Ready — edits update automatically"
        )

    def free_slot(self):
        g = self.doc["settings"]
        occupied = set()
        for p in self.doc["panels"]:
            occupied |= {
                (r, c)
                for r in range(p["row"], p["row"] + p["rowspan"])
                for c in range(p["col"], p["col"] + p["colspan"])
            }
        for r in range(int(g["rows"])):
            for c in range(int(g["cols"])):
                if (r, c) not in occupied:
                    return r, c
        if int(g["rows"]) >= 8:
            raise ValueError("Grid is full. Remove a panel or increase columns.")
        r = int(g["rows"])
        g["rows"] = r + 1
        g["height_ratios"] = ""
        return r, 0

    def reset_colors(self):
        self.checkpoint()
        for p in self.doc["panels"]:
            for s in p["series"]:
                s["color"] = ""
        self.fill_scope("s")
        self.schedule()

    def reset_panel_position(self):
        p = self.current_panel()
        if p is None or not (p.get("offset_x", 0) or p.get("offset_y", 0)):
            return
        self.checkpoint()
        p.update(offset_x=0.0, offset_y=0.0)
        self.fill_scope("p")
        self.schedule()

    def reset_geometry(self):
        self.checkpoint()
        g = self.doc["settings"]
        cols = max(1, int(g["cols"]))
        rows = max(1, math.ceil(len(self.doc["panels"]) / cols))
        single, double, _, _ = TEMPLATES[g["template"]]
        width = single if g["columns"] == "Single" else double
        g.update(
            width=width,
            height=max(30, min(500, width * rows / cols * 170 / 180)),
            rows=rows,
            width_ratios="",
            height_ratios="",
            wspace=0.08,
            hspace=0.08,
        )
        for i, p in enumerate(self.doc["panels"]):
            p.update(
                row=i // cols,
                col=i % cols,
                rowspan=1,
                colspan=1,
                box_aspect="",
                offset_x=0.0,
                offset_y=0.0,
            )
        self.refresh()
        self.schedule()
        self.statusBar().showMessage(
            "Size and spacing reset. Use Undo to restore the previous layout."
        )

    def reflow(self):
        self.checkpoint()
        g = self.doc["settings"]
        cols = int(g["cols"])
        required = max(1, math.ceil(len(self.doc["panels"]) / cols))
        if required > 8:
            self.error("Too many panels for this column count.")
            return
        g["rows"] = required
        g["height_ratios"] = ""
        for i, p in enumerate(self.doc["panels"]):
            p.update(row=i // cols, col=i % cols, rowspan=1, colspan=1)
        self.refresh()
        self.schedule()

    def add_panel(self):
        self.checkpoint()
        try:
            r, c = self.free_slot()
            ids = list(self.doc["datasets"])
            dsid = ids[max(0, self.datasets.currentRow())] if ids else ""
            ds = self.doc["datasets"].get(dsid)
            nums = numeric_columns(ds) if ds else []
            x = ds["headers"][0] if ds else ""
            ys = [next((v for v in nums if v != x), nums[0])] if nums else []
            if ds:
                metadata = ds.get("column_metadata", {})
                x = next((h for h, info in metadata.items() if info.get("role") == "X"), x)
                assigned = [
                    h for h, info in metadata.items() if info.get("role") == "Y" and h in nums
                ]
                if assigned:
                    ys = assigned
                else:
                    ys = [
                        h
                        for h in ys
                        if metadata.get(h, {}).get("role") not in ["Ignore", "Y error", "X error"]
                    ]

            p = panel(dsid, x, ys, r, c)
            if ds and ds.get("column_metadata"):
                p["xlabel"] = axis_label(ds, x)
                if len(ys) == 1:
                    p["ylabel"] = axis_label(ds, ys[0])
                errors = [
                    h for h, info in ds["column_metadata"].items() if info.get("role") == "Y error"
                ]
                if len(errors) == 1 and len(ys) == 1:
                    for s in p["series"]:
                        s["error"] = errors[0]
                xerrors = [
                    h for h, info in ds["column_metadata"].items() if info.get("role") == "X error"
                ]
                if len(xerrors) == 1:
                    for s in p["series"]:
                        s["error_x"] = xerrors[0]
            p["name"] = f"Panel {len(self.doc['panels']) + 1}"
            self.doc["panels"].append(p)
            self.panel_index = len(self.doc["panels"]) - 1
            self.series_index = 0
            self.mark_index = -1
            self.refresh()
            self.tabs.setCurrentIndex(1)
            self.schedule()
        except Exception as e:
            self.error(e)

    def duplicate_panel(self):
        p = self.current_panel()
        if not p:
            return
        self.checkpoint()
        try:
            r, c = self.free_slot()
            duplicate = copy.deepcopy(p)
            duplicate.update(name=p["name"] + " copy", row=r, col=c, rowspan=1, colspan=1)
            self.doc["panels"].append(duplicate)
            self.panel_index = len(self.doc["panels"]) - 1
            self.refresh()
            self.schedule()
        except Exception as e:
            self.error(e)

    def remove_panel(self):
        if not self.current_panel():
            return
        self.checkpoint()
        self.doc["panels"].pop(self.panel_index)
        self.refresh()
        self.schedule()

    def move_panel(self, delta):
        index = self.panel_index
        other = index + delta
        if not 0 <= other < len(self.doc["panels"]):
            return
        self.checkpoint()
        p, q = self.doc["panels"][index], self.doc["panels"][other]
        # Swap order and grid positions so visual order follows the list.
        for key in ["row", "col", "rowspan", "colspan"]:
            p[key], q[key] = q[key], p[key]
        self.doc["panels"][index], self.doc["panels"][other] = q, p
        self.panel_index = other
        self.refresh()
        self.schedule()

    def add_series(self):
        p = self.current_panel()
        column = self.add_column.currentText()
        if not p or not column:
            return
        self.checkpoint()
        p["series"].append(series(column, len(p["series"])))
        self.series_index = len(p["series"]) - 1
        self.refresh_series_list()
        self.context_controls()
        self.schedule()

    def remove_series(self):
        p = self.current_panel()
        if not self.current_series():
            return
        self.checkpoint()
        p["series"].pop(self.series_index)
        self.refresh_series_list()
        self.context_controls()
        self.schedule()

    def add_mark(self):
        p = self.current_panel()
        if not p:
            return
        self.checkpoint()
        p["annotations"].append(annotation(self.mark_kind.currentText()))
        self.mark_index = len(p["annotations"]) - 1
        self.refresh_mark_list()
        self.context_controls()
        self.schedule()

    def remove_mark(self):
        p = self.current_panel()
        if not self.current_mark():
            return
        self.checkpoint()
        p["annotations"].pop(self.mark_index)
        self.place_button.setChecked(False)
        self.refresh_mark_list()
        self.context_controls()
        self.schedule()

    def copy_axes(self):
        p = self.current_panel()
        if not p:
            return
        self.checkpoint()
        keys = [
            axis + suffix
            for axis in ["x", "y"]
            for suffix in ["scale", "min", "max", "ticks", "count", "decimals"]
        ]
        for target in self.doc["panels"]:
            if target["kind"] not in ["Image", "Heatmap"]:
                for key in keys:
                    target[key] = p[key]
        self.schedule()

    def choose_image(self, inset):
        p = self.current_panel()
        if not p:
            return
        path, _ = W.QFileDialog.getOpenFileName(
            self, "Choose panel image", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp)"
        )
        if not path:
            return
        try:
            payload = image_payload(path)
            self.checkpoint()
            key = "inset" if inset else "image"
            p[key] = payload
            p[key + "_name"] = Path(path).name
            if not inset:
                p["kind"] = "Image"
            self.refresh_editors()
            self.refresh_panel_list()
            self.schedule()
        except Exception as e:
            self.error(e)

    def clear_image(self, inset):
        p = self.current_panel()
        if not p:
            return
        self.checkpoint()
        key = "inset" if inset else "image"
        p[key] = ""
        p[key + "_name"] = ""
        self.refresh_editors()
        self.schedule()

    def undo(self):
        if not self.history:
            return
        self.future.append(self.snapshot())
        self.doc = self.history.pop()
        self.dirty = True
        self.last_edit = None
        self.refresh()
        self.schedule()

    def redo(self):
        if not self.future:
            return
        self.history.append(self.snapshot())
        self.doc = self.future.pop()
        self.dirty = True
        self.last_edit = None
        self.refresh()
        self.schedule()

    def error(self, error):
        W.QMessageBox.warning(self, "PlotFolio", str(error))

    def closeEvent(self, event):
        if self.confirm_discard():
            self.clear_recovery()
            event.accept()
        else:
            event.ignore()
