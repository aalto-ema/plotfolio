"""Optional export archive settings, separate from the ordinary figure export."""

from PySide6 import QtWidgets as W

from ..bundles import export_bundle
from .workflow_widgets import hint


class BundleDialog(W.QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self.setWindowTitle("Export publication bundle")
        self.resize(530, 330)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Includes figures, embedded source/derived CSVs, rendered curve coordinates, fit reports and a portable project/provenance record. Review source-path metadata before sharing.",
        )
        self.formats = {}
        for format in ["pdf", "svg", "png", "tiff"]:
            box = W.QCheckBox(format.upper())
            box.setChecked(format in ["pdf", "svg"])
            self.formats[format] = box
            layout.addWidget(box)
        self.status = hint(layout, "")
        button = W.QPushButton("Export ZIP…")
        button.setObjectName("primary")
        button.clicked.connect(self.export)
        layout.addWidget(button)
        close = W.QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)

    def export(self):
        path, _ = W.QFileDialog.getSaveFileName(
            self, "Export publication bundle", "figure-bundle.zip", "ZIP (*.zip)"
        )
        if not path:
            return
        try:
            if not path.lower().endswith(".zip"):
                path += ".zip"
            export_bundle(
                self.studio.doc, path, [key for key, box in self.formats.items() if box.isChecked()]
            )
            self.status.setText("Publication bundle exported.")
        except Exception as error:
            self.status.setText(str(error))
