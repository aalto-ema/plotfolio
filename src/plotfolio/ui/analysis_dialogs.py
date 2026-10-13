"""On-demand analysis workflows with preview before committing derived results."""

import copy
import json

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6 import QtWidgets as W

from ..analysis import summarize, transform
from ..data import columns, numeric, numeric_columns
from ..fit_styles import draw_fit
from ..fitting import MODELS, fit_curve
from ..model import series
from .fit_style import FitStyleDialog, FitStyleEditor
from .workflow_widgets import advanced, combo, form, hint, line, number, table, unique_key


class FitDialog(W.QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self.result = None
        self.panel = studio.current_panel()
        self.selected = studio.current_series()
        if not self.panel or not self.selected or self.panel["kind"] not in ["Line", "Scatter"]:
            raise ValueError("Select a Line or Scatter series to fit.")
        self.setWindowTitle("Fit selected series")
        self.resize(1050, 800)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Fit the selected series in its plotted units. Source data remain unchanged. Review residuals and diagnostics before adding a curve.",
        )
        split = W.QSplitter()
        layout.addWidget(split, 1)
        left = W.QWidget()
        controls = W.QVBoxLayout(left)
        scroll = W.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left)
        split.addWidget(scroll)
        f = form(controls, "Model")
        self.model_form = f
        self.model = combo(MODELS)
        f.addRow("Model", self.model)
        self.degree = W.QSpinBox()
        self.degree.setRange(1, 8)
        self.degree.setValue(2)
        f.addRow("Polynomial degree", self.degree)
        self.formula = line("a*x+b")
        f.addRow("Custom formula", self.formula)
        self.parameters = line("a,b")
        f.addRow("Parameter names", self.parameters)
        self.fit_label = line(self.selected["label"] + " fit")
        f.addRow("Legend label", self.fit_label)
        appearance = advanced(controls, "Curve appearance")
        self.style_editor = FitStyleEditor(dict(color=self.selected.get("color") or "#333333"))
        appearance.addRow(self.style_editor)
        self.show_band = self.style_editor.show_band
        more = advanced(controls, "Fit range, weights and bounds")
        self.xmin = line()
        self.xmax = line()
        more.addRow("Minimum X (blank auto)", self.xmin)
        more.addRow("Maximum X", self.xmax)
        self.sigma = combo(
            ["Unweighted", *numeric_columns(studio.doc["datasets"][self.panel["dataset"]])]
        )
        more.addRow("Y uncertainty column", self.sigma)
        self.absolute = W.QCheckBox("Uncertainties are absolute measurement SD")
        more.addRow(self.absolute)
        self.confidence = number(95, 50, 99.9, 1)
        more.addRow("Confidence / %", self.confidence)
        self.initial = line()
        self.lower = line()
        self.upper = line()
        more.addRow("Initial values (comma list)", self.initial)
        more.addRow("Lower bounds (use -inf)", self.lower)
        more.addRow("Upper bounds (use inf)", self.upper)
        hint(
            controls,
            "Blank initial values use model guesses. Custom functions support arithmetic, exp, log, sqrt, sin/cos and other listed math functions; no Python code is executed.",
        )
        run = W.QPushButton("Preview fit")
        run.setObjectName("primary")
        run.clicked.connect(self.compute)
        controls.addWidget(run)
        self.remove = combo(
            [
                f"{i + 1}: {fit.get('label', fit['model'])}"
                for i, fit in enumerate(self.panel.get("fits", []))
            ]
        )
        controls.addWidget(self.remove)
        edit_style = W.QPushButton("Edit selected fit appearance…")
        edit_style.clicked.connect(self.edit_existing_style)
        controls.addWidget(edit_style)
        remove = W.QPushButton("Remove selected existing fit")
        remove.clicked.connect(self.remove_fit)
        controls.addWidget(remove)
        controls.addStretch()
        self.tabs = W.QTabWidget()
        split.addWidget(self.tabs)
        split.setSizes([360, 690])
        self.report = W.QPlainTextEdit()
        self.report.setReadOnly(True)
        self.tabs.addTab(self.report, "Report")
        self.status = hint(layout, "")
        row = W.QHBoxLayout()
        layout.addLayout(row)
        export = W.QPushButton("Export parameters and residuals…")
        export.clicked.connect(self.export_result)
        row.addWidget(export)
        self.add = W.QPushButton("Add fit to panel")
        self.add.setObjectName("primary")
        self.add.setEnabled(False)
        self.add.clicked.connect(self.apply)
        row.addWidget(self.add)
        close = W.QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addWidget(close)
        self.model.currentTextChanged.connect(self.context)
        self.context()
        for widget in [self.model, self.sigma]:
            widget.currentTextChanged.connect(self.invalidate)
        for widget in [self.degree, self.confidence]:
            widget.valueChanged.connect(self.invalidate)
        for widget in [
            self.formula,
            self.parameters,
            self.xmin,
            self.xmax,
            self.initial,
            self.lower,
            self.upper,
        ]:
            widget.textChanged.connect(self.invalidate)
        self.absolute.toggled.connect(self.invalidate)
        self.style_editor.changed.connect(self.preview_style)
        self.fit_label.textChanged.connect(self.preview_style)

    def context(self, *_):
        kind = self.model.currentText()
        self.degree.setEnabled(kind == "Polynomial")
        self.model_form.setRowVisible(self.degree, kind == "Polynomial")
        self.model_form.setRowVisible(self.formula, kind == "Custom")
        self.model_form.setRowVisible(self.parameters, kind == "Custom")
        self.formula.setEnabled(kind == "Custom")
        self.parameters.setEnabled(kind == "Custom")

    def invalidate(self, *_):
        self.result = None
        self.add.setEnabled(False)
        self.status.setText("Settings changed. Preview the fit again to apply.")

    def compute(self):
        try:
            ds = self.studio.doc["datasets"][self.panel["dataset"]]
            data = columns(ds)
            s = self.selected
            x = numeric(data[self.panel["x"]]) * float(s["xfactor"])
            y = numeric(data[s["y"]]) * float(s["yfactor"])

            def values(field):
                return (
                    [float(v.strip()) for v in field.text().split(",")]
                    if field.text().strip()
                    else None
                )

            sigma = (
                None
                if self.sigma.currentText() == "Unweighted"
                else numeric(data[self.sigma.currentText()]) * abs(float(s["yfactor"]))
            )
            self.result = fit_curve(
                x,
                y,
                model=self.model.currentText(),
                degree=self.degree.value(),
                formula=self.formula.text(),
                parameters=[v.strip() for v in self.parameters.text().split(",")],
                initial=values(self.initial),
                lower=values(self.lower),
                upper=values(self.upper),
                sigma=sigma,
                xmin=float(self.xmin.text()) if self.xmin.text().strip() else None,
                xmax=float(self.xmax.text()) if self.xmax.text().strip() else None,
                confidence=self.confidence.value() / 100,
                absolute_sigma=self.absolute.isChecked(),
            )
            self.result["source"] = dict(
                dataset=self.panel["dataset"],
                x=self.panel["x"],
                y=s["y"],
                xfactor=s["xfactor"],
                yfactor=s["yfactor"],
                sigma_column=self.sigma.currentText(),
            )
            r = self.result
            lines = [
                f"{r['model']}: {r['formula']}",
                f"Observations: {r['n']}; excluded/outside range: {r['excluded']}; residual df: {r['df']}",
                f"Unweighted residual RMSE: {r['rmse']:.6g}; R²: {r['r_squared']}",
                f"Weighted χ²: {r['chi_square']}; reduced χ²: {r['reduced_chi_square']}",
                f"Weighted: {r['weighted']}; absolute sigma: {r['absolute_sigma']}",
                "​",
            ]
            for name, param in r["parameters"].items():
                lines.append(f"{name} = {param['value']:.8g}; standard error = {param['stderr']}")
            lines.extend(["", r["band_method"], *r["messages"]])
            self.report.setPlainText("\n".join(lines))
            while self.tabs.count() > 1:
                widget = self.tabs.widget(1)
                self.tabs.removeTab(1)
                widget.deleteLater()
            figure = Figure(figsize=(5, 4), layout="constrained")
            ax = figure.add_subplot()
            ax.scatter(r["data_x"], r["data_y"], s=12, color="#009EFA", label="Observations")
            styled = dict(r, **self.style_editor.values(), label=self.fit_label.text())
            draw_fit(ax, styled)
            ax.set_xlabel(self.panel["xlabel"] or self.panel["x"])
            ax.set_ylabel(self.panel["ylabel"] or s["label"])
            ax.legend()
            canvas = FigureCanvasQTAgg(figure)
            canvas.draw()
            self.tabs.addTab(canvas, "Curve and band")
            self.preview_canvas = canvas
            residual = Figure(figsize=(5, 4), layout="constrained")
            ra = residual.add_subplot()
            ra.scatter(r["data_x"], r["residuals"], s=12)
            ra.axhline(0, color="#65768C", lw=0.8)
            ra.set_xlabel(self.panel["xlabel"] or self.panel["x"])
            ra.set_ylabel("Residual (observed − fitted)")
            rcanvas = FigureCanvasQTAgg(residual)
            rcanvas.draw()
            self.tabs.addTab(rcanvas, "Residuals")
            self.tabs.setCurrentIndex(1)
            self.add.setEnabled(True)
            self.status.setText("Fit ready. " + " ".join(r["messages"]))
        except Exception as error:
            self.result = None
            self.add.setEnabled(False)
            self.status.setText(str(error))

    def apply(self):
        if self.result is None:
            return
        try:
            style = self.style_editor.values()
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.studio.checkpoint()
        result = copy.deepcopy(self.result)
        result.update(
            label=self.fit_label.text().strip() or self.selected["label"] + " fit",
            **style,
        )
        self.panel.setdefault("fits", []).append(result)
        self.studio.schedule()
        self.accept()

    def edit_existing_style(self):
        index = self.remove.currentIndex()
        if index < 0:
            self.status.setText("Choose an existing fitted curve first.")
            return
        FitStyleDialog(self.studio, self.panel["fits"][index]).exec()
        for i, fit in enumerate(self.panel["fits"]):
            self.remove.setItemText(i, f"{i + 1}: {fit.get('label', fit['model'])}")

    def preview_style(self, *_):
        if self.result is None or not hasattr(self, "preview_canvas"):
            return
        try:
            figure = self.preview_canvas.figure
            figure.clear()
            ax = figure.add_subplot()
            ax.scatter(
                self.result["data_x"],
                self.result["data_y"],
                s=12,
                color="#009EFA",
                label="Observations",
            )
            draw_fit(
                ax, dict(self.result, **self.style_editor.values(), label=self.fit_label.text())
            )
            ax.set_xlabel(self.panel["xlabel"] or self.panel["x"])
            ax.set_ylabel(self.panel["ylabel"] or self.selected["label"])
            ax.legend()
            self.preview_canvas.draw()
        except Exception as error:
            self.status.setText(str(error))

    def remove_fit(self):
        index = self.remove.currentIndex()
        if index < 0:
            return
        self.studio.checkpoint()
        self.panel["fits"].pop(index)
        self.remove.removeItem(index)
        self.studio.schedule()

    def export_result(self):
        if self.result is None:
            self.status.setText("Preview a fit first.")
            return
        path, _ = W.QFileDialog.getSaveFileName(
            self, "Export full fit report", "fit-report.json", "JSON (*.json)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as stream:
                    json.dump(self.result, stream, indent=2, allow_nan=False)
                self.status.setText(
                    "Report exported with parameters, covariance, residuals and provenance."
                )
            except Exception as error:
                self.status.setText(str(error))


class DatasetAnalysisDialog(W.QDialog):
    def __init__(self, studio, summary=False):
        super().__init__(studio)
        self.studio = studio
        if not studio.doc["datasets"]:
            raise ValueError("Import a dataset before opening analysis tools.")
        self.summary = summary
        self.result = None
        self.preview_widget = None
        self.setWindowTitle("Summarize replicates" if summary else "Transform dataset")
        self.resize(880, 730)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Preview a derived dataset before applying. Originals remain embedded and unchanged; operation parameters are recorded in the new dataset history.",
        )
        f = form(layout, "Summary" if summary else "Transformation")
        self.dataset = combo(studio.doc["datasets"])
        f.addRow("Dataset", self.dataset)
        p = studio.current_panel()
        if p:
            self.dataset.setCurrentText(p["dataset"])
        self.column = combo([])
        f.addRow("Value column", self.column)
        if summary:
            self.group = combo([])
            f.addRow("Group / X column", self.group)
            self.center = combo(["Mean", "Median"])
            f.addRow("Center", self.center)
            self.uncertainty = combo(["SD", "SEM", "Confidence interval", "None"])
            f.addRow("Uncertainty", self.uncertainty)
            self.confidence = number(95, 50, 99.9, 1)
            f.addRow("Confidence / %", self.confidence)
            self.plot = combo(
                ["Bar + individual points", "Line + uncertainty band", "Scatter + error bars"]
            )
            f.addRow("Plot result", self.plot)
        else:
            self.kind = combo(
                [
                    "Scale",
                    "Calculated column",
                    "Normalize maximum",
                    "Normalize range",
                    "Subtract baseline",
                    "Moving average",
                    "Savitzky–Golay",
                    "Filter rows",
                ]
            )
            f.addRow("Operation", self.kind)
            self.output = line("processed")
            f.addRow("New column name", self.output)
            self.unit = line()
            f.addRow("Output unit", self.unit)
            self.formula = line('col("column") * 1000')
            f.addRow("Expression / filter", self.formula)
            self.factor = number(1)
            f.addRow("Scale factor", self.factor)
            self.baseline = number(0)
            f.addRow("Baseline constant", self.baseline)
            more = advanced(layout, "Smoothing options")
            self.window = W.QSpinBox()
            self.window.setRange(3, 10001)
            self.window.setSingleStep(2)
            self.window.setValue(5)
            more.addRow("Window (odd points)", self.window)
            self.degree = W.QSpinBox()
            self.degree.setRange(0, 8)
            self.degree.setValue(2)
            more.addRow("Polynomial degree", self.degree)
            hint(
                layout,
                'Expressions use column identifiers or col("name"), arithmetic, comparisons, and sin/cos/exp/log/sqrt/abs/minimum/maximum/where. Filtering needs a boolean expression. Smoothing acts in row order and assumes equally spaced samples.',
            )
            self.kind.currentTextChanged.connect(self.context)
        self.preview_layout = W.QVBoxLayout()
        layout.addLayout(self.preview_layout, 1)
        self.status = hint(layout, "")
        row = W.QHBoxLayout()
        layout.addLayout(row)
        preview = W.QPushButton("Preview result")
        preview.clicked.connect(self.compute)
        row.addWidget(preview)
        self.apply_button = W.QPushButton("Create derived dataset")
        self.apply_button.setObjectName("primary")
        self.apply_button.clicked.connect(self.apply)
        row.addWidget(self.apply_button)
        close = W.QPushButton("Cancel")
        close.clicked.connect(self.reject)
        row.addWidget(close)
        self.dataset.currentTextChanged.connect(self.populate)
        self.populate()
        if not summary:
            self.context()

    def populate(self, *_):
        ds = self.studio.doc["datasets"][self.dataset.currentText()]
        self.column.clear()
        self.column.addItems(numeric_columns(ds))
        selected = self.studio.current_series()
        if selected and selected["y"] in numeric_columns(ds):
            self.column.setCurrentText(selected["y"])
        if self.summary:
            self.group.clear()
            self.group.addItems(ds["headers"])
            groups = [
                h
                for h, info in ds.get("column_metadata", {}).items()
                if info.get("role") == "Group"
            ]
            if groups:
                self.group.setCurrentText(groups[0])
        else:
            self.formula.setText("col(" + json.dumps(self.column.currentText()) + ") * 1000")
            self.unit.setText(
                ds.get("column_metadata", {}).get(self.column.currentText(), {}).get("unit", "")
            )

    def context(self, *_):
        kind = self.kind.currentText()
        self.factor.setEnabled(kind == "Scale")
        self.baseline.setEnabled(kind == "Subtract baseline")
        self.formula.setEnabled(kind in ["Calculated column", "Filter rows"])
        self.output.setEnabled(kind != "Filter rows")

    def compute(self):
        try:
            ds = self.studio.doc["datasets"][self.dataset.currentText()]
            if self.summary:
                result = summarize(
                    ds,
                    self.group.currentText(),
                    self.column.currentText(),
                    self.center.currentText(),
                    self.uncertainty.currentText(),
                    self.confidence.value() / 100,
                )
            else:
                result = transform(
                    ds,
                    self.column.currentText(),
                    self.kind.currentText(),
                    output=self.output.text(),
                    expression_text=self.formula.text(),
                    factor=self.factor.value(),
                    baseline=self.baseline.value(),
                    window=self.window.value(),
                    degree=self.degree.value(),
                    filter_text=self.formula.text(),
                )
            if self.summary and self.plot.currentText().startswith("Line"):
                groups = numeric([row[0] for row in result["rows"]])
                if not np.isfinite(groups).all():
                    raise ValueError(
                        "Line summaries need numeric group/X values. Choose Bar for named categories."
                    )
            if not self.summary and self.kind.currentText() != "Filter rows":
                result["column_metadata"][self.output.text()]["unit"] = self.unit.text()
                result["history"][-1]["output_unit"] = self.unit.text()
            self.result = result
            if self.preview_widget:
                self.preview_layout.removeWidget(self.preview_widget)
                self.preview_widget.deleteLater()
            self.preview_widget = table(result)
            self.preview_layout.addWidget(self.preview_widget)
            self.status.setText(
                f"{len(result['rows'])} result rows; preview shows up to 100. "
                + json.dumps(result["history"][-1], ensure_ascii=False)
            )
            return True
        except Exception as error:
            self.result = None
            self.status.setText(str(error))
            return False

    def apply(self):
        # Recompute from the current controls, so a stale preview can never be committed.
        if not self.compute():
            return
        self.studio.checkpoint()
        key = unique_key(
            self.studio.doc["datasets"],
            self.dataset.currentText()
            + " · "
            + ("summary" if self.summary else self.kind.currentText()),
        )
        self.result["derived_from"] = self.dataset.currentText()
        self.studio.doc["datasets"][key] = self.result
        p = self.studio.current_panel()
        if p and self.summary:
            kind = self.plot.currentText()
            p.update(
                dataset=key,
                x=self.group.currentText(),
                series=[series("estimate")],
                fits=[],
                kind="Bar"
                if kind.startswith("Bar")
                else ("Line" if kind.startswith("Line") else "Scatter"),
                title="",
                legend="Hide",
                xmin="",
                xmax="",
                ymin="",
                ymax="",
                xticks="",
                yticks="",
                xscale="linear",
                yscale="linear",
                data_inset=None,
                secondary_x=None,
                secondary_y=None,
                replicates=None,
                categorical_x=kind.startswith("Scatter")
                and not np.isfinite(numeric([row[0] for row in self.result["rows"]])).all(),
            )
            p["xlabel"] = self.group.currentText()
            p["ylabel"] = self.column.currentText()
            p["series"][0].update(
                label=self.column.currentText(), error_low="error_low", error_high="error_high"
            )
            if kind.startswith("Line"):
                p["series"][0].update(band_lower="lower", band_upper="upper")
            if kind.startswith("Bar"):
                p["replicates"] = dict(
                    dataset=self.dataset.currentText(),
                    group=self.group.currentText(),
                    value=self.column.currentText(),
                )
        elif p and p["dataset"] == self.dataset.currentText():
            p["dataset"] = key
            p["fits"] = []
            p["replicates"] = None
            s = self.studio.current_series()
            if s and self.kind.currentText() != "Filter rows":
                s.update(
                    y=self.output.text(),
                    label=self.output.text(),
                    yfactor=1,
                    error="",
                    error_low="",
                    error_high="",
                    band_lower="",
                    band_upper="",
                )
        self.studio.refresh()
        self.studio.schedule()
        self.accept()
