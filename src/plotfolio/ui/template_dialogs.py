"""Reusable templates, explicit column mapping and background batch exports."""

from pathlib import Path

from PySide6 import QtCore as C
from PySide6 import QtWidgets as W

from ..templates import apply_template, batch_export, requirements
from .workflow_widgets import combo, hint


class TemplateMappingDialog(W.QDialog):
    def __init__(self, template, datasets, parent=None):
        super().__init__(parent)
        self.template = template
        self.datasets = datasets
        self.result = None
        self.source_controls = {}
        self.column_controls = {}
        self.setWindowTitle("Apply figure template")
        self.resize(680, 650)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Match each template source and column to imported data. This changes layout and styling; Undo restores the current figure. Source tables remain untouched.",
        )
        scroll = W.QScrollArea()
        scroll.setWidgetResizable(True)
        body = W.QWidget()
        forms = W.QVBoxLayout(body)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        for slot, headers in requirements(template).items():
            group = W.QGroupBox(template["sources"][slot]["name"])
            form = W.QFormLayout(group)
            forms.addWidget(group)
            source = combo(datasets)
            form.addRow("Dataset", source)
            self.source_controls[slot] = source
            self.column_controls[slot] = {}
            for header in headers:
                widget = combo([])
                self.column_controls[slot][header] = widget
                form.addRow(header, widget)
            source.currentTextChanged.connect(lambda _, key=slot: self.populate(key))
            self.populate(slot)
        self.status = hint(layout, "")
        buttons = W.QDialogButtonBox(
            W.QDialogButtonBox.StandardButton.Ok | W.QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)

    def populate(self, slot):
        ds = self.datasets.get(self.source_controls[slot].currentText())
        for header, widget in self.column_controls[slot].items():
            widget.clear()
            widget.addItems(ds["headers"] if ds else [])
            if ds and header in ds["headers"]:
                widget.setCurrentText(header)
            else:
                widget.setCurrentIndex(-1)

    def maps(self):
        return (
            {slot: widget.currentText() for slot, widget in self.source_controls.items()},
            {
                slot: {header: widget.currentText() for header, widget in controls.items()}
                for slot, controls in self.column_controls.items()
            },
        )

    def apply(self):
        try:
            source_map, column_map = self.maps()
            self.result = apply_template(self.template, self.datasets, source_map, column_map)
            self.accept()
        except Exception as error:
            self.status.setText(str(error))


class BatchWorker(C.QThread):
    completed = C.Signal(object)
    failed = C.Signal(str)
    progress = C.Signal(str)

    def __init__(self, template, items, folder, format, column_map):
        super().__init__()
        self.args = (template, items, folder, format, column_map)

    def run(self):
        try:
            self.completed.emit(batch_export(*self.args, progress=self.progress.emit))
        except Exception as error:
            self.failed.emit(str(error))


class BatchDialog(W.QDialog):
    def __init__(self, template, datasets, parent=None):
        super().__init__(parent)
        self.template = template
        self.datasets = dict(datasets)
        self.worker = None
        if len(template["sources"]) != 1:
            raise ValueError(
                "Batch plotting uses a one-source template. Apply template supports multiple source mappings."
            )
        self.setWindowTitle("Batch plotting")
        self.resize(680, 650)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Select imported datasets with the same structure. Missing columns and existing output names are checked before any exports are written. Outputs use the template’s final size and DPI.",
        )
        self.list = W.QListWidget()
        layout.addWidget(self.list, 1)
        for key in datasets:
            item = W.QListWidgetItem(key)
            item.setFlags(item.flags() | C.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(C.Qt.CheckState.Checked)
            self.list.addItem(item)
        imports = W.QHBoxLayout()
        layout.addLayout(imports)
        add_files = W.QPushButton("Add files…")
        add_files.clicked.connect(self.add_files)
        imports.addWidget(add_files)
        add_folder = W.QPushButton("Import folder…")
        add_folder.clicked.connect(self.add_folder)
        imports.addWidget(add_folder)
        controls = W.QFormLayout()
        layout.addLayout(controls)
        self.format = combo(["pdf", "svg", "png", "tiff"])
        controls.addRow("Output format", self.format)
        folder_row = W.QWidget()
        fr = W.QHBoxLayout(folder_row)
        fr.setContentsMargins(0, 0, 0, 0)
        self.folder = W.QLineEdit()
        fr.addWidget(self.folder)
        choose = W.QPushButton("Choose…")
        choose.clicked.connect(self.choose_folder)
        fr.addWidget(choose)
        controls.addRow("Export folder", folder_row)
        self.mapping = {}
        slot = next(iter(template["sources"]))
        hint(
            layout,
            "Column mappings apply to every selected dataset. Leave names unchanged when headers already match.",
        )
        for header in requirements(template)[slot]:
            widget = W.QLineEdit(header)
            self.mapping[header] = widget
            controls.addRow(header, widget)
        self.status = hint(layout, "")
        self.progress = W.QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        self.run_button = W.QPushButton("Export selected datasets")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.run_batch)
        layout.addWidget(self.run_button)
        self.close_button = W.QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)

    def add_inputs(self, paths):
        if not paths:
            return
        from .import_data import ImportDialog
        from .workflow_widgets import unique_key

        dialog = ImportDialog(paths, self)
        if dialog.exec() != W.QDialog.DialogCode.Accepted:
            return
        for name, ds in dialog.result:
            key = unique_key(self.datasets, name)
            self.datasets[key] = ds
            item = W.QListWidgetItem(key)
            item.setFlags(item.flags() | C.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(C.Qt.CheckState.Checked)
            self.list.addItem(item)

    def add_files(self):
        if self.worker and self.worker.isRunning():
            return
        paths, _ = W.QFileDialog.getOpenFileNames(
            self, "Add batch inputs", "", "Data (*.csv *.tsv *.txt *.xlsx)"
        )
        self.add_inputs(paths)

    def add_folder(self):
        if self.worker and self.worker.isRunning():
            return
        folder = W.QFileDialog.getExistingDirectory(self, "Import batch input folder")
        if folder:
            self.add_inputs(
                [
                    str(path)
                    for path in sorted(Path(folder).iterdir())
                    if path.suffix.lower() in [".csv", ".tsv", ".txt", ".xlsx"]
                ]
            )

    def choose_folder(self):
        folder = W.QFileDialog.getExistingDirectory(self, "Choose export folder")
        if folder:
            self.folder.setText(folder)

    def run_batch(self):
        items = [
            (self.list.item(i).text(), self.datasets[self.list.item(i).text()])
            for i in range(self.list.count())
            if self.list.item(i).checkState() == C.Qt.CheckState.Checked
        ]
        slot = next(iter(self.template["sources"]))
        mapping = {slot: {header: widget.text() for header, widget in self.mapping.items()}}
        self.run_button.setEnabled(False)
        self.close_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.show()
        self.status.setText("Preflighting and exporting…")
        self.worker = BatchWorker(
            self.template, items, self.folder.text(), self.format.currentText(), mapping
        )
        self.worker.progress.connect(self.status.setText)
        self.worker.completed.connect(self.success)
        self.worker.failed.connect(self.failure)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def success(self, paths):
        self.status.setText(f"Exported {len(paths)} figures to {Path(paths[0]).parent}.")

    def failure(self, message):
        self.status.setText(message)

    def worker_finished(self):
        self.progress.hide()
        self.run_button.setEnabled(True)
        self.close_button.setEnabled(True)

    def reject(self):
        if self.worker and self.worker.isRunning():
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)
