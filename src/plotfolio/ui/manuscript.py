"""PDF manuscript context with exact-size vector placement and zoom controls."""

import shutil
import tempfile
from pathlib import Path

from PySide6 import QtCore as C
from PySide6 import QtWidgets as W
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView

from ..manuscript import manuscript_pdf


class ManuscriptDialog(W.QDialog):
    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.source = None
        self.temp = tempfile.TemporaryDirectory(prefix="plotfolio-")
        self.path = Path(self.temp.name) / "preview.pdf"
        self.setWindowTitle("PlotFolio · Manuscript preview")
        self.resize(1050, 850)
        layout = W.QVBoxLayout(self)
        note = W.QLabel(
            "Figures keep their exported millimetre dimensions. Fit page changes only the screen zoom."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        row = W.QHBoxLayout()
        self.paper = W.QComboBox()
        self.paper.addItems(["A4", "Letter"])
        self.columns = W.QComboBox()
        self.columns.addItems(["One column / full width", "Two columns / single-column figure"])
        row.addWidget(self.paper)
        row.addWidget(self.columns)
        load = W.QPushButton("Open manuscript PDF…")
        load.clicked.connect(self.load_source)
        row.addWidget(load)
        sample = W.QPushButton("Sample page")
        sample.clicked.connect(self.sample)
        row.addWidget(sample)
        layout.addLayout(row)
        row = W.QHBoxLayout()
        self.page = W.QSpinBox()
        self.page.setRange(1, 999)
        self.page.setValue(1)
        self.x = W.QDoubleSpinBox()
        self.x.setRange(0, 500)
        self.x.setValue(15)
        self.x.setSuffix(" mm")
        self.top = W.QDoubleSpinBox()
        self.top.setRange(0, 500)
        self.top.setValue(80)
        self.top.setSuffix(" mm")
        for label, widget in [("Page", self.page), ("Left", self.x), ("From top", self.top)]:
            row.addWidget(W.QLabel(label))
            row.addWidget(widget)
        refresh = W.QPushButton("Update placement")
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        fit = W.QPushButton("Fit page")
        fit.clicked.connect(self.fit)
        row.addWidget(fit)
        self.zoom = W.QSpinBox()
        self.zoom.setRange(25, 300)
        self.zoom.setValue(100)
        self.zoom.setSuffix("%")
        self.zoom.valueChanged.connect(self.set_zoom)
        row.addWidget(self.zoom)
        layout.addLayout(row)
        self.status = W.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.pdf = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.pdf)
        layout.addWidget(self.view, 1)
        save = W.QPushButton("Save preview PDF…")
        save.clicked.connect(self.save)
        layout.addWidget(save)
        self.paper.currentTextChanged.connect(self.refresh)
        self.columns.currentIndexChanged.connect(self.refresh)
        self.refresh()
        self.fit()

    def refresh(self, *_):
        self.pdf.close()
        try:
            manuscript_pdf(
                self.doc,
                self.path,
                self.paper.currentText(),
                self.columns.currentIndex() + 1,
                self.source,
                self.page.value() - 1,
                self.x.value(),
                self.top.value(),
            )
            self.pdf.load(str(self.path))
            self.view.pageNavigator().jump(self.page.value() - 1, C.QPointF())
            self.status.setText(
                f"{self.source or 'Sample manuscript'} · Vector figure at original size. Screen 100% uses display DPI and may differ from a physical ruler."
            )
        except Exception as error:
            self.status.setText(str(error))

    def fit(self):
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)

    def set_zoom(self, value):
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(value / 100)

    def load_source(self):
        path, _ = W.QFileDialog.getOpenFileName(self, "Open manuscript PDF", "", "PDF (*.pdf)")
        if path:
            self.source = path
            self.refresh()

    def sample(self):
        self.source = None
        self.page.setValue(1)
        self.refresh()

    def save(self):
        if self.pdf.pageCount() == 0:
            return
        path, _ = W.QFileDialog.getSaveFileName(
            self, "Save preview copy", "manuscript-preview.pdf", "PDF (*.pdf)"
        )
        if path:
            if self.source and Path(path).resolve() == Path(self.source).resolve():
                self.status.setText(
                    "Choose a different filename to preserve the original manuscript."
                )
                return
            shutil.copyfile(self.path, path)
