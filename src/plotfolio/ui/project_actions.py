"""User-facing file operations, export, and data-preview actions."""

from pathlib import Path

import matplotlib as mpl
from PySide6 import QtWidgets as W

from ..engine import build_figure, demo_document, document, load_project, read_csv, save_project
from .widgets import DataModel


class ProjectActionsMixin:
    def show_data(self):
        self.data_dock.show()
        self.update_data()

    def update_data(self, *args):
        if self.guard:
            return
        ds = self.doc["datasets"].get(self.data_choice.currentText())
        self.data_model = DataModel(ds)
        self.data_table.setModel(self.data_model)
        self.data_table.horizontalHeader().setSectionResizeMode(
            W.QHeaderView.ResizeMode.Interactive
        )
        if ds:
            self.data_info.setText(
                f"{len(ds['rows']):,} rows · {len(ds['headers'])} columns · read-only original data"
            )
        else:
            self.data_info.setText("Import CSV to preview data")

    def export_data(self):
        ds = self.doc["datasets"].get(self.data_choice.currentText())
        if not ds:
            return
        path, _ = W.QFileDialog.getSaveFileName(
            self, "Export original data", ds["name"] + ".csv", "CSV (*.csv)"
        )
        if path:
            try:
                import csv

                with open(path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(ds["headers"])
                    writer.writerows(ds["rows"])
            except Exception as e:
                self.error(e)

    def import_csv(self):
        paths, _ = W.QFileDialog.getOpenFileNames(
            self, "Import CSV datasets", "", "CSV / TSV (*.csv *.tsv);;All files (*)"
        )
        if not paths:
            return
        try:
            loaded = [(Path(path).stem, read_csv(path)) for path in paths]
            self.checkpoint()
            for name, ds in loaded:
                key = name
                n = 2
                while key in self.doc["datasets"]:
                    key = f"{name} {n}"
                    n += 1
                self.doc["datasets"][key] = ds
            self.refresh()
            self.datasets.setCurrentRow(len(self.doc["datasets"]) - 1)
            self.show_data()
            self.statusBar().showMessage(
                "CSV imported. Add a panel or change the selected panel’s dataset."
            )
            self.schedule()
        except Exception as e:
            self.error(e)

    def confirm_discard(self):
        if not self.dirty:
            return True
        result = W.QMessageBox.question(
            self,
            "Unsaved changes",
            "Save your project before continuing?",
            W.QMessageBox.StandardButton.Save
            | W.QMessageBox.StandardButton.Discard
            | W.QMessageBox.StandardButton.Cancel,
        )
        if result == W.QMessageBox.StandardButton.Save:
            return self.save()
        return result == W.QMessageBox.StandardButton.Discard

    def replace_document(self, doc, filename=None):
        self.timer.stop()
        self.clear_recovery()
        self.doc = doc
        self.filename = filename
        self.dirty = False
        self.history = []
        self.future = []
        self.panel_index = 0
        self.series_index = 0
        self.mark_index = -1
        self.last_edit = None
        self.place_button.setChecked(False)
        self.refresh()
        self.render()

    def new(self):
        if self.confirm_discard():
            self.replace_document(document())

    def load_demo(self):
        if self.confirm_discard():
            self.replace_document(demo_document())

    def open_project(self):
        if not self.confirm_discard():
            return
        path, _ = W.QFileDialog.getOpenFileName(
            self, "Open PlotFolio project", "", "PlotFolio projects (*.plotfolio.json *.json)"
        )
        if path:
            try:
                self.replace_document(load_project(path), path)
            except Exception as e:
                self.error(e)

    def save_as(self):
        previous = self.filename
        self.filename = None
        if not self.save():
            self.filename = previous
            self.update_title()

    def save(self):
        path = self.filename
        if not path:
            path, _ = W.QFileDialog.getSaveFileName(
                self,
                "Save portable project",
                "Figure.plotfolio.json",
                "PlotFolio project (*.plotfolio.json)",
            )
        if not path:
            return False
        try:
            save_project(self.doc, path)
            self.filename = path
            self.dirty = False
            self.clear_recovery()
            self.update_title()
            self.statusBar().showMessage("Saved project with embedded data and images.")
            return True
        except Exception as e:
            self.error(e)
            return False

    def export(self):
        self.timer.stop()
        if not self.render():
            self.error("Resolve the preview error before exporting.")
            return
        path, filter_ = W.QFileDialog.getSaveFileName(
            self,
            "Export at final publication size",
            "Figure.pdf",
            "PDF vector (*.pdf);;SVG vector (*.svg);;PNG (*.png);;TIFF (*.tiff)",
        )
        if not path:
            return
        try:
            extension = {
                "PDF": ".pdf",
                "SVG": ".svg",
                "PNG": ".png",
                "TIFF": ".tiff",
                "EPS": ".eps",
            }[(filter_ or "PDF").split()[0]]
            if not Path(path).suffix:
                path += extension
            if Path(path).suffix.lower() not in [".pdf", ".svg", ".png", ".tiff", ".tif"]:
                raise ValueError("Choose PDF, SVG, PNG or TIFF.")
            with mpl.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"}):
                export_figure, _, _ = build_figure(self.doc)
                export_figure.savefig(path, dpi=int(self.doc["settings"]["dpi"]), facecolor="white")
            from ..preflight import check_figure

            issues = check_figure(self.doc)
            self.statusBar().showMessage(
                "Exported "
                + path
                + (
                    f" — {len(issues)} publication checks to review (File → Publication checks)."
                    if issues
                    else ""
                )
            )
        except Exception as e:
            self.error(e)

    def guide(self):
        W.QMessageBox.information(
            self,
            "PlotFolio quick guide",
            "1. Import data; preview parsing, roles and units.\n2. Add a panel, or select an existing one.\n3. Panel: choose dataset, type, labels, axes and images.\n4. Series: edit each curve’s label, style, scale and errors.\n5. Marks: add text, shapes or arrows; place by clicking the preview.\n6. Figure: set dimensions, ratios, typography and journal template.\n7. Save the portable project; export at final physical size.\n\nUse Analyze for fits, transformations and replicate summaries; Templates for reusable designs and batch plotting; Panel tools for data zoom insets and linked units.\n\nAll edits update automatically. Undo/redo is available.\nMath: $x_{i}$ for subscripts, $x^{2}$ for superscripts.\nRatios: 20:50:30 for three grid columns.\nPan/zoom is for inspection; set explicit limits in Panel for export.",
        )
