"""Panel alignment and non-printing placement guides in one focused dialog."""

from PySide6 import QtWidgets as W

from ..alignment import align_panels
from .workflow_widgets import combo, hint, number


class AlignmentDialog(W.QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self.setWindowTitle("Align panels and placement guides")
        self.resize(650, 570)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Select panels, then align their plotting areas or distribute equal gaps. The reference is the first selected panel. Changes are undoable; data and axis limits are preserved.",
        )
        self.list = W.QListWidget()
        self.list.setSelectionMode(W.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.addItems([p["name"] for p in studio.doc["panels"]])
        layout.addWidget(self.list, 1)
        self.operation = combo(
            [
                "Left",
                "Right",
                "Top",
                "Bottom",
                "Horizontal centers",
                "Vertical centers",
                "Distribute horizontally",
                "Distribute vertically",
            ]
        )
        layout.addWidget(self.operation)
        apply = W.QPushButton("Align selected panels")
        apply.clicked.connect(self.apply)
        layout.addWidget(apply)
        form = W.QFormLayout()
        layout.addLayout(form)
        self.snapping = W.QCheckBox("Snap annotation placement and panel labels")
        self.snapping.setChecked(studio.doc["settings"].get("snap", False))
        form.addRow(self.snapping)
        self.step = number(studio.doc["settings"].get("snap_step", 0.05) * 100, 1, 25, 1)
        form.addRow("Guide interval / % of panel", self.step)
        guides = W.QPushButton("Apply guide settings")
        guides.clicked.connect(self.guides)
        layout.addWidget(guides)
        self.status = hint(
            layout, "Guides appear during annotation placement and are never exported."
        )
        close = W.QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)

    def apply(self):
        try:
            indices = sorted(self.list.row(item) for item in self.list.selectedItems())
            result = align_panels(self.studio.doc, indices, self.operation.currentText())
            self.studio.checkpoint()
            self.studio.doc = result
            self.studio.refresh()
            self.studio.schedule()
            self.status.setText("Panels aligned. Undo restores the previous layout.")
        except Exception as error:
            self.status.setText(str(error))

    def guides(self):
        self.studio.checkpoint()
        g = self.studio.doc["settings"]
        g.update(snap=self.snapping.isChecked(), snap_step=self.step.value() / 100)
        self.studio.schedule()
        self.status.setText(
            "Guide settings applied. Use Marks → Place on preview, or edit panel label coordinates."
        )
