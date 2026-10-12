"""Reusable Qt widgets and read-only CSV table model."""

import math

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6 import QtCore as C
from PySide6 import QtGui as G
from PySide6 import QtWidgets as W


class DataModel(C.QAbstractTableModel):
    def __init__(self, dataset=None):
        super().__init__()
        self.dataset = dataset or dict(headers=[], rows=[])

    def rowCount(self, parent=C.QModelIndex()):
        return 0 if parent.isValid() else len(self.dataset["rows"])

    def columnCount(self, parent=C.QModelIndex()):
        return 0 if parent.isValid() else len(self.dataset["headers"])

    def data(self, index, role=C.Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role == C.Qt.ItemDataRole.DisplayRole:
            return str(self.dataset["rows"][index.row()][index.column()])

    def headerData(self, section, orientation, role=C.Qt.ItemDataRole.DisplayRole):
        if role == C.Qt.ItemDataRole.DisplayRole:
            return (
                self.dataset["headers"][section]
                if orientation == C.Qt.Orientation.Horizontal
                else str(section + 1)
            )


class ColorEdit(W.QWidget):
    changed = C.Signal(str)

    def __init__(self):
        super().__init__()
        box = W.QHBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        self.edit = W.QLineEdit()
        self.edit.setPlaceholderText("Auto palette")
        self.button = W.QPushButton("●")
        self.button.setFixedWidth(36)
        box.addWidget(self.edit)
        box.addWidget(self.button)
        self.edit.editingFinished.connect(self.finish)
        self.button.clicked.connect(self.pick)

    def finish(self):
        self.paint()
        self.changed.emit(self.edit.text())

    def pick(self):
        color = W.QColorDialog.getColor(
            G.QColor(self.edit.text() or "#009EFA"), self, "Series / annotation color"
        )
        if color.isValid():
            self.set_value(color.name())
            self.changed.emit(color.name())

    def set_value(self, value):
        self.edit.setText(str(value))
        self.paint()

    def value(self):
        return self.edit.text()

    def paint(self):
        value = self.edit.text()
        color = G.QColor(value)
        self.button.setStyleSheet(
            f"color: {color.name()}; font-size: 18px;" if color.isValid() else ""
        )


class NumberBox(W.QDoubleSpinBox):
    """Compact numbers and scientific notation for very small scale factors."""

    def textFromValue(self, value):
        return f"{value:.10g}"

    def valueFromText(self, text):
        try:
            return float(text)
        except ValueError:
            return self.value()

    def validate(self, text, pos):
        try:
            value = float(text)
            state = (
                G.QValidator.State.Acceptable
                if math.isfinite(value) and self.minimum() <= value <= self.maximum()
                else G.QValidator.State.Invalid
            )
        except ValueError:
            state = (
                G.QValidator.State.Intermediate
                if text in ["", "-", "+", ".", "-."] or text.lower().endswith(("e", "e-", "e+"))
                else G.QValidator.State.Invalid
            )
        return state, text, pos


class PreviewFrame(W.QWidget):
    """Fit a figure to the viewport without changing its visual aspect ratio."""

    def __init__(self, canvas, ratio):
        super().__init__()
        self.canvas = canvas
        self.ratio = ratio
        canvas.setParent(self)
        self.setMinimumSize(200, 180)
        self.setStyleSheet("background: #E9EEF5;")

    def resizeEvent(self, event):
        width = max(1, self.width() - 24)
        height = max(1, self.height() - 24)
        if width / height > self.ratio:
            width = int(height * self.ratio)
        else:
            height = int(width / self.ratio)
        self.canvas.setGeometry(
            (self.width() - width) // 2, (self.height() - height) // 2, width, height
        )
        super().resizeEvent(event)


class StudioToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent, on_export, on_apply):
        self.on_export = on_export
        super().__init__(canvas, parent)
        self.setStyleSheet(
            "QToolBar { background: white; border: none; padding: 3px; } QToolButton { color: #263448; background: white; border: none; padding: 6px; } QToolButton:hover { background: #E8F2F7; }"
        )
        self.addSeparator()
        action = self.addAction("Use view as limits")
        action.setToolTip("Save the selected panel’s current pan/zoom view as its axis limits.")
        action.triggered.connect(on_apply)

    def save_figure(self, *args):
        self.on_export()
