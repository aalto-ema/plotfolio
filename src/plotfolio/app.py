"""Console entry point and Qt lifecycle."""

import sys

from PySide6 import QtWidgets as W

from .projects import load_project
from .ui.window import Studio


def main():
    app = W.QApplication(sys.argv)
    app.setApplicationName("PlotFolio")
    app.setStyle("Fusion")
    studio = Studio()
    if len(sys.argv) > 1:
        try:
            studio.replace_document(load_project(sys.argv[1]), sys.argv[1])
        except Exception as error:
            studio.error(error)
    studio.show()
    return app.exec()
