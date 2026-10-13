"""Reusable fit appearance controls and a non-destructive existing-fit editor."""

import copy

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6 import QtCore as C
from PySide6 import QtWidgets as W

from ..fit_styles import draw_fit, fit_style
from .widgets import ColorEdit
from .workflow_widgets import combo, hint, line, number


class FitStyleEditor(W.QWidget):
    changed = C.Signal()

    def __init__(self, fit, parent=None):
        super().__init__(parent)
        style = fit_style(fit)
        form = W.QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        self.color = ColorEdit()
        self.color.set_value(style["color"])
        form.addRow("Curve color", self.color)
        self.linestyle = combo(["solid", "dashed", "dotted", "dashdot", "none"])
        self.linestyle.setCurrentText(style["linestyle"])
        form.addRow("Line style", self.linestyle)
        self.width = number(style["linewidth"], 0.1, 10, 0.1)
        form.addRow("Line width / pt", self.width)
        self.marker = combo(["None", "o", "s", "^", "v", "D", "+", "x", "."])
        self.marker.setCurrentText(style["marker"])
        form.addRow("Marker", self.marker)
        self.marker_size = number(style["markersize"], 1, 20, 0.5)
        form.addRow("Marker size / pt", self.marker_size)
        self.alpha = number(style["alpha"], 0, 1, 0.05)
        form.addRow("Curve opacity", self.alpha)
        self.visible = W.QCheckBox("Show fit overlay")
        self.visible.setChecked(style["visible"])
        form.addRow(self.visible)
        self.show_band = W.QCheckBox("Show confidence band when available")
        self.show_band.setChecked(style["show_band"])
        form.addRow(self.show_band)
        self.band_color = ColorEdit()
        self.band_color.edit.setPlaceholderText("Same as curve")
        self.band_color.set_value(style["band_color"])
        form.addRow("Band color", self.band_color)
        self.band_alpha = number(style["band_alpha"], 0, 1, 0.05)
        form.addRow("Band opacity", self.band_alpha)
        for widget in [self.color, self.band_color]:
            widget.changed.connect(self.changed)
        for widget in [self.linestyle, self.marker]:
            widget.currentTextChanged.connect(self.changed)
        for widget in [self.width, self.marker_size, self.alpha, self.band_alpha]:
            widget.valueChanged.connect(self.changed)
        for widget in [self.visible, self.show_band]:
            widget.toggled.connect(self.changed)

    def values(self):
        return fit_style(
            dict(
                color=self.color.value(),
                linestyle=self.linestyle.currentText(),
                linewidth=self.width.value(),
                marker=self.marker.currentText(),
                markersize=self.marker_size.value(),
                alpha=self.alpha.value(),
                visible=self.visible.isChecked(),
                show_band=self.show_band.isChecked(),
                band_color=self.band_color.value(),
                band_alpha=self.band_alpha.value(),
            )
        )


class FitStyleDialog(W.QDialog):
    def __init__(self, studio, fit):
        super().__init__(studio)
        self.studio = studio
        self.fit = fit
        self.setWindowTitle("Fitted curve appearance")
        self.resize(900, 680)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Change appearance without recalculating the fit. Parameters, residuals and confidence intervals are preserved.",
        )
        split = W.QSplitter()
        layout.addWidget(split, 1)
        left = W.QWidget()
        left.setObjectName("inspectorBody")
        controls = W.QVBoxLayout(left)
        self.label = line(fit.get("label", fit["model"] + " fit"))
        controls.addWidget(W.QLabel("Legend label"))
        controls.addWidget(self.label)
        self.editor = FitStyleEditor(fit)
        controls.addWidget(self.editor)
        controls.addStretch()
        scroll = W.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left)
        split.addWidget(scroll)
        self.figure = Figure(figsize=(5, 4), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        split.addWidget(self.canvas)
        split.setSizes([330, 570])
        self.status = hint(layout, "")
        buttons = W.QDialogButtonBox(
            W.QDialogButtonBox.StandardButton.Apply | W.QDialogButtonBox.StandardButton.Close
        )
        layout.addWidget(buttons)
        buttons.button(W.QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject)
        self.editor.changed.connect(self.preview)
        self.label.textChanged.connect(self.preview)
        self.preview()

    def candidate(self):
        candidate = copy.deepcopy(self.fit)
        candidate.update(self.editor.values())
        candidate["label"] = self.label.text().strip() or self.fit["model"] + " fit"
        return candidate

    def preview(self, *_):
        try:
            candidate = self.candidate()
            self.figure.clear()
            ax = self.figure.add_subplot()
            if candidate.get("data_x"):
                ax.scatter(
                    candidate["data_x"],
                    candidate["data_y"],
                    s=12,
                    color="#009EFA",
                    label="Observations",
                )
            draw_fit(ax, candidate)
            ax.set_xlabel("X / plotted units")
            ax.set_ylabel("Y / plotted units")
            ax.legend()
            self.canvas.draw()
            self.status.setText("Preview only — Apply saves the appearance.")
            return True
        except Exception as error:
            self.status.setText(str(error))
            return False

    def apply(self):
        if not self.preview():
            return
        try:
            candidate = self.candidate()
            self.studio.checkpoint()
            self.fit.update({key: candidate[key] for key in [*self.editor.values(), "label"]})
            self.studio.schedule()
            self.status.setText("Appearance applied. Undo restores the previous style.")
        except Exception as error:
            self.status.setText(str(error))
