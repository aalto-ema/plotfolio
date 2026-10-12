import copy
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from PySide6 import QtCore, QtTest
from PySide6 import QtWidgets as W

from plotfolio.engine import build_figure, load_project, save_project
from plotfolio.ui.window import Studio


def main():
    app = W.QApplication([])
    app.setStyle("Fusion")
    ui = Studio()
    ui.show()
    app.processEvents()
    # Start with a representative complete workspace screenshot.
    ui.data_dock.show()
    ui.update_data()
    app.processEvents()
    ui.resize(1500, 1080)
    app.processEvents()
    if "--screenshot" in sys.argv:
        ui.grab().save(str(Path(__file__).resolve().parents[1] / "plotfolio_ui.png"))
    ui.data_dock.hide()
    # Dimensions must accept intermediate digits below the allowed final minimum.
    width = ui.fields[("g", "width")]
    width.setFocus()
    width.selectAll()
    QtTest.QTest.keyClicks(width, "162.5")
    QtTest.QTest.keyClick(width, QtCore.Qt.Key.Key_Return)
    QtTest.QTest.qWait(350)
    assert ui.doc["settings"]["width"] == 162.5
    ui.fields[("g", "wspace")].setValue(25)
    previous = copy.deepcopy(ui.doc)
    ui.reset_geometry()
    assert ui.doc["settings"]["wspace"] == 0.08
    assert ui.doc["datasets"] == previous["datasets"]
    ui.undo()
    assert ui.doc == previous
    ui.panels.setCurrentRow(0)
    app.processEvents()
    n = len(ui.doc["panels"])
    label = ui.fields[("p", "title")]
    label.setFocus()
    label.selectAll()
    QtTest.QTest.keyClicks(label, "Updated live")
    QtTest.QTest.qWait(400)
    assert ui.doc["panels"][0]["title"] == "Updated live" and len(ui.doc["panels"]) == n
    assert ui.plot_axes[0].get_title() == "Updated live"
    ui.fields[("s", "linestyle")].setCurrentText("dashed")
    QtTest.QTest.qWait(400)
    assert ui.plot_axes[0].lines[0].get_linestyle() == "--"
    ui.fields[("s", "yfactor")].setValue(2)
    QtTest.QTest.qWait(400)
    np.testing.assert_allclose(
        ui.plot_axes[0].lines[0].get_ydata()[0], float(ui.doc["datasets"]["cv"]["rows"][0][1]) * 2
    )
    ui.undo()
    QtTest.QTest.qWait(350)
    assert ui.doc["panels"][0]["series"][0]["yfactor"] == 1
    ui.redo()
    QtTest.QTest.qWait(350)
    assert ui.doc["panels"][0]["series"][0]["yfactor"] == 2
    ui.fields[("g", "template")].setCurrentText("RSC — CrystEngComm")
    QtTest.QTest.qWait(350)
    assert ui.doc["settings"]["width"] == 171
    ui.fields[("g", "columns")].setCurrentText("Single")
    QtTest.QTest.qWait(350)
    assert ui.doc["settings"]["width"] == 83
    ui.fields[("g", "columns")].setCurrentText("Double")
    QtTest.QTest.qWait(350)
    saved_panels = copy.deepcopy(ui.doc["panels"])
    ui.copy_axes()
    ui.doc["panels"][0]["xscale"] = "linear"
    ui.fields[("g", "sharex")].setChecked(True)
    QtTest.QTest.qWait(350)
    # Mixed categorical and numeric shared X axes must produce an inline error, not an invalid export.
    assert "matching scales and categories" in ui.message.text()
    ui.fields[("g", "sharex")].setChecked(False)
    ui.doc["panels"] = saved_panels
    ui.refresh()
    ui.schedule()
    QtTest.QTest.qWait(350)
    ui.mark_kind.setCurrentText("Rectangle")
    ui.add_mark()
    QtTest.QTest.qWait(350)
    assert len(ui.doc["panels"][0]["annotations"]) == 1
    ui.fields[("a", "alpha")].setValue(0.2)
    QtTest.QTest.qWait(350)
    assert abs(ui.plot_axes[0].patches[-1].get_alpha() - 0.2) < 1e-8
    ui.show_data()
    app.processEvents()
    assert ui.data_model.rowCount() == 301
    ui.data_choice.setCurrentText("eis")
    assert ui.data_model.rowCount() == 81
    # Fresh export geometry is independent of a resized Qt canvas.
    ui.resize(1100, 760)
    app.processEvents()
    f, _, _ = build_figure(ui.doc)
    np.testing.assert_allclose(f.get_size_inches() * 25.4, [171, 170])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.plotfolio.json"
        save_project(ui.doc, path)
        restored = load_project(path)
        assert restored == ui.doc
    ui.replace_document(__import__("plotfolio.engine", fromlist=["document"]).document())
    assert not ui.doc["panels"]
    ui.add_panel()
    QtTest.QTest.qWait(350)
    assert "select a dataset" in ui.message.text()
    ui.dirty = False
    ui.close()
    print(
        "PASS: Qt live edits, no extra panels, styling/scaling, undo/redo, journal sizing, inline validation, annotations, data table, export size, portable save, empty state"
    )


if __name__ == "__main__":
    main()
