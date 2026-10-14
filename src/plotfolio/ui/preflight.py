"""A review report, not an approval barrier to export."""

from PySide6 import QtWidgets as W

from ..preflight import check_figure
from .workflow_widgets import hint


class PreflightDialog(W.QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self.setWindowTitle("Publication checks")
        self.resize(750, 500)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Checks use the exported physical size. Findings are review prompts, not journal acceptance guarantees. Small-font threshold: 7 pt; image threshold: 300 DPI.",
        )
        self.list = W.QListWidget()
        layout.addWidget(self.list, 1)
        self.issues = []
        row = W.QHBoxLayout()
        layout.addLayout(row)
        refresh = W.QPushButton("Run checks")
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        select = W.QPushButton("Select affected panel")
        select.clicked.connect(self.select)
        row.addWidget(select)
        close = W.QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        self.refresh()

    def refresh(self):
        self.issues = check_figure(self.studio.doc)
        self.list.clear()
        self.list.addItems(
            [f"{item['severity']}: {item['message']}" for item in self.issues]
            or ["No issues detected by these checks. Inspect the exported figure visually."]
        )

    def select(self):
        index = self.list.currentRow()
        if 0 <= index < len(self.issues) and self.issues[index]["panel"] is not None:
            self.studio.panels.setCurrentRow(self.issues[index]["panel"])
            self.studio.tabs.setCurrentIndex(1)
            self.accept()
