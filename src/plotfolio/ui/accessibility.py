"""Color-accessibility review and explicit optional pattern changes."""

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PySide6 import QtCore as C
from PySide6 import QtGui as G
from PySide6 import QtWidgets as W

from ..accessibility import color_findings, simulate
from ..rendering import build_figure
from .workflow_widgets import combo, hint


class AccessibilityDialog(W.QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self.setWindowTitle("Color accessibility")
        self.resize(1000, 800)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Approximate previews at full simulated severity. These are design aids, not a certification. The project and normal exports keep their original colors.",
        )
        self.mode = combo(["Original", "Grayscale", "Protan", "Deutan", "Tritan"])
        layout.addWidget(self.mode)
        self.image = W.QLabel()
        self.image.setAlignment(C.Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(300, 300)
        layout.addWidget(self.image, 1)
        self.report = W.QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMaximumHeight(110)
        layout.addWidget(self.report)
        row = W.QHBoxLayout()
        layout.addLayout(row)
        self.pattern = combo(["Different lines", "Different lines and markers"])
        row.addWidget(self.pattern)
        apply = W.QPushButton("Apply patterns to selected panel")
        apply.clicked.connect(self.apply)
        row.addWidget(apply)
        close = W.QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        if studio.current_panel() and studio.current_panel()["kind"] == "Scatter":
            self.pattern.setCurrentIndex(1)
            self.pattern.setEnabled(False)
        self.mode.currentTextChanged.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        fig, _, _ = build_figure(self.studio.doc)
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        rgba = np.asarray(canvas.buffer_rgba())
        rgb = simulate(rgba[..., :3] / 255, self.mode.currentText())
        pixels = np.ascontiguousarray(np.rint(rgb * 255).astype("uint8"))
        image = G.QImage(
            pixels.data,
            pixels.shape[1],
            pixels.shape[0],
            pixels.strides[0],
            G.QImage.Format.Format_RGB888,
        ).copy()
        self.pixmap = G.QPixmap.fromImage(image)
        self.image.setPixmap(
            self.pixmap.scaled(
                850,
                530,
                C.Qt.AspectRatioMode.KeepAspectRatio,
                C.Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.report.setPlainText(
            "\n".join(color_findings(self.studio.doc, self.mode.currentText()))
            or "No close series-color pairs detected by this heuristic. Inspect heatmaps/images and differences in lightness visually."
        )

    def apply(self):
        p = self.studio.current_panel()
        if not p or p["kind"] not in ["Line", "Scatter"]:
            self.report.setPlainText("Select a Line or Scatter panel for pattern changes.")
            return
        self.studio.checkpoint()
        lines = ["solid", "dashed", "dotted", "dashdot"]
        markers = ["o", "s", "^", "D", "v", "x"]
        for i, s in enumerate(p["series"]):
            s["linestyle"] = lines[i % len(lines)]
            if self.pattern.currentIndex() == 1:
                s["marker"] = markers[i % len(markers)]
        self.studio.refresh()
        self.studio.schedule()
        self.refresh()
