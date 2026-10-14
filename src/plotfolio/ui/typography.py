"""Typography overrides near panel labels, with an explicit reset to inheritance."""

from PySide6 import QtGui as G
from PySide6 import QtWidgets as W

from ..typography import defaults
from .workflow_widgets import combo, hint, number


class TypographyDialog(W.QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self.panel = studio.current_panel()
        if not self.panel:
            raise ValueError("Select a panel first.")
        self.setWindowTitle("Panel typography")
        self.resize(570, 580)
        layout = W.QVBoxLayout(self)
        hint(
            layout,
            "Zero sizes inherit figure-wide settings. Changes affect appearance only, and are saved for export.",
        )
        form = W.QFormLayout()
        layout.addLayout(form)
        self.inherit = W.QCheckBox("Use figure font family")
        self.inherit.setChecked(not self.panel.get("font_family"))
        form.addRow(self.inherit)
        self.family = W.QFontComboBox()
        self.family.setCurrentFont(
            G.QFont(self.panel.get("font_family") or studio.doc["settings"]["family"])
        )
        form.addRow("Font family", self.family)
        self.family.setEnabled(not self.inherit.isChecked())
        self.inherit.toggled.connect(lambda checked: self.family.setEnabled(not checked))
        self.sizes = {}
        for key, label in [
            ("xlabel_size", "X label"),
            ("ylabel_size", "Y label"),
            ("xtick_size", "X ticks"),
            ("ytick_size", "Y ticks"),
            ("title_size", "Title"),
            ("panel_label_size", "Panel letter"),
        ]:
            widget = number(self.panel.get(key, 0), 0, 40, 0.5)
            self.sizes[key] = widget
            form.addRow(label + " / pt (0 = auto)", widget)
        self.formats = {}
        for axis in ["x", "y"]:
            widget = combo(["Auto", "Plain", "Scientific", "Engineering"])
            widget.setCurrentText(self.panel.get(axis + "format", "Auto"))
            self.formats[axis] = widget
            form.addRow(axis.upper() + " number format", widget)
        hint(
            layout,
            "Categorical labels keep their text. Engineering notation uses SI-prefix shorthand; scientific notation uses a power-of-ten multiplier. Axis data and limits remain unchanged.",
        )
        row = W.QHBoxLayout()
        layout.addLayout(row)
        apply = W.QPushButton("Apply")
        apply.clicked.connect(self.apply)
        row.addWidget(apply)
        reset = W.QPushButton("Reset to figure defaults")
        reset.clicked.connect(self.reset)
        row.addWidget(reset)
        close = W.QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)

    def apply(self):
        self.studio.checkpoint()
        self.panel.update(
            font_family="" if self.inherit.isChecked() else self.family.currentFont().family(),
            **{key: widget.value() for key, widget in self.sizes.items()},
            **{axis + "format": widget.currentText() for axis, widget in self.formats.items()},
        )
        self.studio.schedule()

    def reset(self):
        self.studio.checkpoint()
        self.panel.update(defaults())
        self.inherit.setChecked(True)
        for widget in self.sizes.values():
            widget.setValue(0)
        for widget in self.formats.values():
            widget.setCurrentText("Auto")
        self.studio.schedule()
