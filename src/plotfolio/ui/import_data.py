"""Multi-file import with parsing preview and column assignments."""

import copy
from pathlib import Path

from PySide6 import QtCore as C
from PySide6 import QtWidgets as W

from ..ingestion import ROLES, read_tables, sheet_names
from .workflow_widgets import combo, form, hint, table


class ImportDialog(W.QDialog):
    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.result = []
        self.metadata = {}
        self.preview = None
        self.active = None
        self.setWindowTitle("Import data")
        self.resize(1000, 730)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Preview parsing before importing. These settings apply to the selected files; column roles and units are saved with the data.",
        )
        split = W.QSplitter()
        layout.addWidget(split, 1)
        self.files = W.QListWidget()
        self.files.addItems([Path(path).name for path in paths])
        split.addWidget(self.files)
        right = W.QWidget()
        body = W.QVBoxLayout(right)
        split.addWidget(right)
        split.setSizes([220, 780])
        f = form(body, "Parsing")
        self.delimiter = combo(["Auto", "Comma", "Semicolon", "Tab", "Space"])
        f.addRow("Delimiter", self.delimiter)
        self.start = W.QSpinBox()
        self.start.setRange(1, 100000)
        f.addRow("Header / first data row", self.start)
        self.has_header = W.QCheckBox("First selected row contains headers")
        self.has_header.setChecked(True)
        f.addRow(self.has_header)
        self.sheet = combo(["All sheets"])
        f.addRow("Excel sheet", self.sheet)
        self.tabs = W.QTabWidget()
        body.addWidget(self.tabs, 1)
        self.roles = W.QTableWidget()
        self.roles.setColumnCount(3)
        self.roles.setHorizontalHeaderLabels(["Column", "Role", "Unit"])
        self.status = hint(body, "")
        buttons = W.QDialogButtonBox(
            W.QDialogButtonBox.StandardButton.Ok | W.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(W.QDialogButtonBox.StandardButton.Ok).setText("Import all files")
        layout.addWidget(buttons)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        self.files.currentRowChanged.connect(self.select_file)
        self.delimiter.currentTextChanged.connect(self.refresh)
        self.start.valueChanged.connect(self.refresh)
        self.has_header.toggled.connect(self.refresh)
        self.sheet.currentTextChanged.connect(self.refresh)
        self.files.setCurrentRow(0)

    def capture_metadata(self):
        if self.preview is None:
            return
        for r, header in enumerate(self.preview["headers"]):
            role = self.roles.cellWidget(r, 1).currentText()
            unit = self.roles.item(r, 2).text()
            self.metadata[header] = dict(role=role, unit=unit, label=header)

    def select_file(self, index):
        self.capture_metadata()
        self.active = index
        path = self.paths[index]
        self.sheet.blockSignals(True)
        self.sheet.clear()
        self.sheet.addItem("All sheets")
        try:
            if Path(path).suffix.lower() == ".xlsx":
                self.sheet.addItems(sheet_names(path))
        except Exception as error:
            self.status.setText(str(error))
        self.sheet.setEnabled(Path(path).suffix.lower() == ".xlsx")
        self.sheet.blockSignals(False)
        self.refresh()

    def options(self):
        return dict(
            delimiter=self.delimiter.currentText(),
            header_row=self.start.value(),
            has_header=self.has_header.isChecked(),
            sheet=self.sheet.currentText(),
        )

    def refresh(self, *_):
        if self.active is None:
            return
        self.capture_metadata()
        self.tabs.clear()
        self.preview = None
        try:
            tables = read_tables(self.paths[self.active], **self.options())
            self.preview = tables[0]
            self.tabs.addTab(table(self.preview), "Data preview")
            self.roles.setRowCount(len(self.preview["headers"]))
            for r, header in enumerate(self.preview["headers"]):
                item = W.QTableWidgetItem(header)
                item.setFlags(item.flags() & ~C.Qt.ItemFlag.ItemIsEditable)
                self.roles.setItem(r, 0, item)
                info = self.metadata.get(header, {})
                role = combo(ROLES)
                role.setCurrentText(info.get("role", "Unassigned"))
                self.roles.setCellWidget(r, 1, role)
                self.roles.setItem(r, 2, W.QTableWidgetItem(info.get("unit", "")))
            self.tabs.addTab(self.roles, "Roles and units")
            self.roles.resizeColumnsToContents()
            self.status.setText(
                f"{len(tables)} table(s) · {len(self.preview['rows'])} rows in previewed table. Excel formulas use saved values; recalculate and save the workbook first if needed."
            )
        except Exception as error:
            self.status.setText(str(error))

    def apply(self):
        self.capture_metadata()
        try:
            loaded = []
            options = self.options()
            for path in self.paths:
                file_options = dict(options)
                if Path(path).suffix.lower() != ".xlsx":
                    file_options["sheet"] = "All sheets"
                for ds in read_tables(path, **file_options):
                    ds["column_metadata"].update(
                        {
                            header: copy.deepcopy(self.metadata[header])
                            for header in ds["headers"]
                            if header in self.metadata
                        }
                    )
                    loaded.append(
                        (
                            Path(path).stem
                            + (
                                f" · {ds['import_options']['sheet']}"
                                if ds["import_options"]["sheet"]
                                else ""
                            ),
                            ds,
                        )
                    )
            self.result = loaded
            self.accept()
        except Exception as error:
            self.status.setText(str(error))
