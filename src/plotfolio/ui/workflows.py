"""Menu-level entry points; advanced workflows stay out of the main inspector."""

import json

from PySide6 import QtWidgets as W

from ..templates import load_template, save_template
from .workflow_widgets import unique_key


class WorkflowMixin:
    def workflow(self, dialog_class, *args):
        self.timer.stop()
        try:
            dialog = dialog_class(*args)
            dialog.exec()
        except Exception as error:
            self.error(error)
        finally:
            self.schedule()

    def import_data(self):
        from .import_data import ImportDialog

        paths, _ = W.QFileDialog.getOpenFileNames(
            self, "Import datasets", "", "Data (*.csv *.tsv *.txt *.xlsx);;All files (*)"
        )
        if not paths:
            return
        dialog = ImportDialog(paths, self)
        if dialog.exec() != W.QDialog.DialogCode.Accepted:
            return
        self.checkpoint()
        for proposed, ds in dialog.result:
            key = unique_key(self.doc["datasets"], proposed)
            self.doc["datasets"][key] = ds
        self.refresh()
        self.datasets.setCurrentRow(len(self.doc["datasets"]) - 1)
        self.show_data()
        self.schedule()

    def fit_selected(self):
        from .analysis_dialogs import FitDialog

        self.workflow(FitDialog, self)

    def transform_dataset(self):
        from .analysis_dialogs import DatasetAnalysisDialog

        self.workflow(DatasetAnalysisDialog, self, False)

    def summarize_replicates(self):
        from .analysis_dialogs import DatasetAnalysisDialog

        self.workflow(DatasetAnalysisDialog, self, True)

    def panel_tools(self):
        from .panel_tools import PanelToolsDialog

        self.workflow(PanelToolsDialog, self)

    def save_figure_template(self):
        path, _ = W.QFileDialog.getSaveFileName(
            self,
            "Save reusable figure template",
            "figure.plotfolio-template.json",
            "Figure template (*.plotfolio-template.json)",
        )
        if path:
            try:
                save_template(self.doc, path)
                self.statusBar().showMessage(
                    "Template saved without source data or fitted results."
                )
            except Exception as error:
                self.error(error)

    def apply_figure_template(self):
        from .template_dialogs import TemplateMappingDialog

        path, _ = W.QFileDialog.getOpenFileName(
            self, "Open figure template", "", "Figure template (*.plotfolio-template.json *.json)"
        )
        if not path:
            return
        self.timer.stop()
        try:
            dialog = TemplateMappingDialog(load_template(path), self.doc["datasets"], self)
            if dialog.exec() == W.QDialog.DialogCode.Accepted:
                self.checkpoint()
                self.doc = dialog.result
                self.panel_index = 0
                self.series_index = 0
                self.mark_index = -1
                self.refresh()
                self.schedule()
        except Exception as error:
            self.error(error)

    def batch_plot(self):
        from .template_dialogs import BatchDialog

        path, _ = W.QFileDialog.getOpenFileName(
            self,
            "Choose batch figure template",
            "",
            "Figure template (*.plotfolio-template.json *.json)",
        )
        if path:
            try:
                self.workflow(BatchDialog, load_template(path), self.doc["datasets"], self)
            except Exception as error:
                self.error(error)

    def data_history(self):
        if not self.doc["datasets"]:
            self.error("Import a dataset first.")
            return
        dialog = W.QDialog(self)
        dialog.setWindowTitle("Data provenance")
        dialog.resize(680, 560)
        layout = W.QVBoxLayout(dialog)
        select = W.QComboBox()
        select.addItems(self.doc["datasets"])
        layout.addWidget(select)
        if self.current_panel():
            select.setCurrentText(self.current_panel()["dataset"])
        text = W.QPlainTextEdit()
        text.setReadOnly(True)
        layout.addWidget(text)
        status = W.QLabel()
        status.setWordWrap(True)
        layout.addWidget(status)
        replay = W.QPushButton("Recompute from recorded parent")
        layout.addWidget(replay)

        def update(*_):
            ds = self.doc["datasets"][select.currentText()]
            text.setPlainText(
                json.dumps(
                    {
                        name: ds.get(name)
                        for name in [
                            "name",
                            "source",
                            "derived_from",
                            "import_options",
                            "column_metadata",
                            "history",
                        ]
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            replay.setEnabled(
                bool(ds.get("history") and ds.get("derived_from") in self.doc["datasets"])
            )

        def recompute():
            try:
                from ..analysis import replay_operation

                ds = self.doc["datasets"][select.currentText()]
                parent = ds["derived_from"]
                result = replay_operation(self.doc["datasets"][parent], ds["history"][-1])
                result["derived_from"] = parent
                key = unique_key(self.doc["datasets"], select.currentText() + " · recomputed")
                self.checkpoint()
                self.doc["datasets"][key] = result
                self.refresh()
                self.schedule()
                select.addItem(key)
                select.setCurrentText(key)
                status.setText("Created a recomputed dataset. The original result is preserved.")
            except Exception as error:
                status.setText(str(error))

        select.currentTextChanged.connect(update)
        replay.clicked.connect(recompute)
        update()
        close = W.QPushButton("Close")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()
