"""Small shared building blocks for modal scientific workflows."""

from PySide6 import QtWidgets as W

from .widgets import NumberBox


def combo(items):
    widget = W.QComboBox()
    widget.addItems([str(item) for item in items])
    return widget


def number(value, minimum=-1e9, maximum=1e9, step=0.1):
    widget = NumberBox()
    widget.setDecimals(12)
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    widget.setSingleStep(step)
    widget.setKeyboardTracking(False)
    return widget


def line(text=""):
    return W.QLineEdit(str(text))


def form(parent, title):
    group = W.QGroupBox(title)
    layout = W.QFormLayout(group)
    layout.setFieldGrowthPolicy(W.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    layout.setRowWrapPolicy(W.QFormLayout.RowWrapPolicy.WrapLongRows)
    parent.addWidget(group)
    return layout


def advanced(parent, title="More options"):
    toggle = W.QPushButton(title)
    toggle.setCheckable(True)
    parent.addWidget(toggle)
    body = W.QWidget()
    layout = W.QFormLayout(body)
    parent.addWidget(body)
    body.hide()
    toggle.toggled.connect(body.setVisible)
    return layout


def table(dataset, limit=100):
    widget = W.QTableWidget(min(len(dataset["rows"]), limit), len(dataset["headers"]))
    widget.setHorizontalHeaderLabels(dataset["headers"])
    widget.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
    for r, row in enumerate(dataset["rows"][:limit]):
        for c, value in enumerate(row):
            widget.setItem(r, c, W.QTableWidgetItem(str(value)))
    widget.resizeColumnsToContents()
    return widget


def hint(parent, text):
    label = W.QLabel(text)
    label.setWordWrap(True)
    label.setObjectName("muted")
    parent.addWidget(label)
    return label


def unique_key(datasets, proposed):
    key = proposed
    index = 2
    while key in datasets:
        key = f"{proposed} {index}"
        index += 1
    return key
