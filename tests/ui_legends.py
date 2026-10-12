"""Drag panel/shared legends and verify undoable, persisted model anchors."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from matplotlib.backend_bases import MouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from plotfolio.ui.window import Studio


def drag(window, legend):
    box = legend.get_window_extent(window.canvas.get_renderer())
    x, y = box.x0 + 10, box.y0 + 10
    for name, xx, yy in [
        ("button_press_event", x, y),
        ("motion_notify_event", x + 20, y - 10),
        ("button_release_event", x + 20, y - 10),
    ]:
        window.canvas.callbacks.process(name, MouseEvent(name, window.canvas, xx, yy, button=1))
    QTest.qWait(400)


def main():
    app = QApplication([])
    window = Studio()
    window.show()
    QTest.qWait(400)
    drag(window, window.plot_axes[0].get_legend())
    assert window.doc["panels"][0]["legend_placement"] == "Custom"
    before = copy.deepcopy(window.doc)
    window.reset_legend_position("p")
    assert window.doc["panels"][0]["legend_placement"] == "Inside"
    window.undo()
    assert window.doc == before
    window.fields[("g", "legend_mode")].setCurrentText("Shared figure")
    QTest.qWait(400)
    assert len(window.canvas.figure.legends) == 1
    drag(window, window.canvas.figure.legends[0])
    assert window.doc["settings"]["legend_placement"] == "Custom"
    window.reset_legend_position("g")
    assert window.doc["settings"]["legend_placement"] == "Outside below"
    window.dirty = False
    window.close()
    app.processEvents()
    print("PASS: panel/shared legend dragging, custom anchors, reset and undo")


if __name__ == "__main__":
    main()
