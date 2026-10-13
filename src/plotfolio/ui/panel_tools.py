"""Advanced axes, numeric zoom inset and uncertainty columns kept out of the inspector."""

import copy

from PySide6 import QtWidgets as W

from ..data import numeric_columns
from .workflow_widgets import combo, form, hint, line, number


class PanelToolsDialog(W.QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self.panel = studio.current_panel()
        if not self.panel:
            raise ValueError("Select a panel first.")
        self.setWindowTitle("Advanced panel tools")
        self.resize(640, 680)
        layout = W.QVBoxLayout(self)
        self.tabs = W.QTabWidget()
        layout.addWidget(self.tabs)
        zoom_page = W.QWidget()
        zoom_layout = W.QVBoxLayout(zoom_page)
        self.tabs.addTab(zoom_page, "Data zoom inset")
        f = form(zoom_layout, "Magnified data region")
        self.zoom_enabled = W.QCheckBox("Show data zoom inset")
        self.zoom_enabled.setChecked(bool(self.panel.get("data_inset")))
        f.addRow(self.zoom_enabled)
        available = self.panel["kind"] in ["Line", "Scatter"] and not self.panel.get(
            "categorical_x", False
        )
        self.zoom_enabled.setEnabled(available)
        ax = (
            studio.plot_axes[studio.panel_index]
            if studio.panel_index < len(studio.plot_axes)
            else None
        )
        xlim = ax.get_xlim() if ax else (0, 1)
        ylim = ax.get_ylim() if ax else (0, 1)
        spec = self.panel.get("data_inset") or dict(
            xmin=min(xlim),
            xmax=max(xlim),
            ymin=min(ylim),
            ymax=max(ylim),
            bounds=[0.55, 0.52, 0.4, 0.4],
            connectors=True,
            font=7,
        )
        self.limits = {}
        for key, label in [
            ("xmin", "Minimum X"),
            ("xmax", "Maximum X"),
            ("ymin", "Minimum Y"),
            ("ymax", "Maximum Y"),
        ]:
            widget = line(spec[key])
            self.limits[key] = widget
            f.addRow(label, widget)
        self.bounds = line(",".join(str(v) for v in spec["bounds"]))
        f.addRow("Inset x,y,width,height", self.bounds)
        self.connectors = W.QCheckBox("Show zoom rectangle and connectors")
        self.connectors.setChecked(spec.get("connectors", True))
        f.addRow(self.connectors)
        self.inset_font = number(spec.get("font", 7), 4, 20, 0.5)
        f.addRow("Inset tick font / pt", self.inset_font)
        hint(
            zoom_layout,
            "Pan/zoom the main plot before opening this dialog to use the current view as the initial region. Limits use plotted units; inset bounds use panel fractions. Main axis limits are unchanged. Available for Line and Scatter.",
        )
        zoom_layout.addStretch()
        units_page = W.QWidget()
        units_layout = W.QVBoxLayout(units_page)
        self.tabs.addTab(units_page, "Linked unit axes")
        hint(
            units_layout,
            "Secondary = primary × factor + offset. These axes follow the main limits; they do not add another dataset. Examples: V → mV: 1000, 0; °C → K: 1, 273.15.",
        )
        self.secondary = {}
        for axis in ["x", "y"]:
            f = form(units_layout, "Top X axis" if axis == "x" else "Right Y axis")
            spec = self.panel.get("secondary_" + axis) or dict(factor=1, offset=0, label="")
            enabled = W.QCheckBox("Show linked axis")
            enabled.setChecked(bool(self.panel.get("secondary_" + axis)))
            f.addRow(enabled)
            factor = number(spec["factor"])
            offset = number(spec["offset"])
            label = line(spec["label"])
            f.addRow("Conversion factor", factor)
            f.addRow("Offset", offset)
            f.addRow("Axis label", label)
            numeric_axis = self.panel["kind"] in [
                "Line",
                "Scatter",
                "Histogram",
            ] and not self.panel.get("categorical_x", False)
            for widget in [enabled, factor, offset, label]:
                widget.setEnabled(numeric_axis)
            self.secondary[axis] = (enabled, factor, offset, label)
        units_layout.addStretch()
        band_page = W.QWidget()
        band_layout = W.QVBoxLayout(band_page)
        self.tabs.addTab(band_page, "Series uncertainty")
        hint(
            band_layout,
            "Configure the selected series. Error columns contain nonnegative deviations; band columns contain absolute lower/upper boundaries in source Y units. Scaling is applied consistently.",
        )
        f = form(band_layout, "Selected series")
        self.selected = studio.current_series()
        ds = studio.doc["datasets"].get(self.panel["dataset"], {})
        names = ["", *numeric_columns(ds)] if ds else [""]
        self.band_fields = {}
        for key, label in [
            ("error_x", "X error column"),
            ("error_low", "Lower error column"),
            ("error_high", "Upper error column"),
            ("band_lower", "Band lower boundary"),
            ("band_upper", "Band upper boundary"),
        ]:
            widget = combo(names)
            widget.setCurrentText((self.selected or {}).get(key, ""))
            widget.setEnabled(self.selected is not None)
            self.band_fields[key] = widget
            f.addRow(label, widget)
        self.alpha = number((self.selected or {}).get("band_alpha", 0.18), 0, 1, 0.05)
        f.addRow("Band opacity", self.alpha)
        band_layout.addStretch()
        self.status = hint(layout, "")
        buttons = W.QDialogButtonBox(
            W.QDialogButtonBox.StandardButton.Apply | W.QDialogButtonBox.StandardButton.Close
        )
        layout.addWidget(buttons)
        buttons.button(W.QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject)

    def apply(self):
        try:
            p = copy.deepcopy(self.panel)
            p["data_inset"] = (
                dict(
                    **{key: float(widget.text()) for key, widget in self.limits.items()},
                    bounds=[float(value) for value in self.bounds.text().split(",")],
                    connectors=self.connectors.isChecked(),
                    font=self.inset_font.value(),
                )
                if self.zoom_enabled.isChecked()
                else None
            )
            for axis, (enabled, factor, offset, label) in self.secondary.items():
                p["secondary_" + axis] = (
                    dict(factor=factor.value(), offset=offset.value(), label=label.text())
                    if enabled.isChecked()
                    else None
                )
            if self.selected:
                index = self.studio.series_index
                p["series"][index].update(
                    {key: widget.currentText() for key, widget in self.band_fields.items()}
                )
                p["series"][index]["band_alpha"] = self.alpha.value()
            from matplotlib.backends.backend_agg import FigureCanvasAgg

            from ..rendering import build_figure

            candidate = copy.deepcopy(self.studio.doc)
            candidate["panels"][self.studio.panel_index] = p
            fig, _, _ = build_figure(candidate)
            FigureCanvasAgg(fig).draw()
            self.studio.checkpoint()
            self.panel.clear()
            self.panel.update(p)
            self.selected = self.studio.current_series()
            self.studio.refresh()
            self.studio.schedule()
            self.status.setText("Panel tools applied. Undo restores previous settings.")
        except Exception as error:
            self.status.setText(str(error))
