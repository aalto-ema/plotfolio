import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PIL import Image
from PySide6 import QtTest
from PySide6 import QtWidgets as W

from plotfolio.engine import *
from plotfolio.ui.window import Studio


def main():
    app = W.QApplication([])
    app.setStyle("Fusion")
    ui = Studio()
    ui.show()
    app.processEvents()
    ui.panels.setCurrentRow(2)
    ui.mark_kind.setCurrentText("Arrow")
    ui.add_mark()
    QtTest.QTest.qWait(350)
    ui.place_button.setChecked(True)

    def click(x, y):
        ax = ui.plot_axes[2]
        pixels = ax.transAxes.transform((x, y))
        coords = ax.transData.inverted().transform(pixels)
        event = SimpleNamespace(
            button=1, inaxes=ax, x=pixels[0], y=pixels[1], xdata=coords[0], ydata=coords[1]
        )
        ui.plot_clicked(event)
        QtTest.QTest.qWait(350)

    click(0.2, 0.8)
    assert ui.place_mode
    click(0.7, 0.3)
    assert not ui.place_mode
    mark = ui.current_mark()
    assert abs(mark["x"] - 0.2) < 1e-7 and abs(mark["x2"] - 0.7) < 1e-7
    ui.fields[("s", "xfactor")].setValue(1e-9)
    QtTest.QTest.qWait(350)
    assert abs(ui.current_series()["xfactor"] - 1e-9) < 1e-20
    ui.reset_colors()
    ui.fields[("g", "colormap")].setCurrentText("plasma")
    QtTest.QTest.qWait(350)
    assert ui.plot_axes[2].lines[0].get_color() != COLORS[0]
    ui.plot_axes[2].set_xlim(1e-9, 3e-9)
    ui.apply_view()
    QtTest.QTest.qWait(350)
    assert abs(float(ui.current_panel()["xmax"]) - 3e-9) < 1e-20
    ui.fields[("g", "cols")].setValue(3)
    ui.reflow()
    QtTest.QTest.qWait(350)
    assert ui.doc["panels"][3]["row"] == 1 and ui.doc["panels"][3]["col"] == 0
    assert "Fix to update" not in ui.message.text()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        image = root / "img.png"
        Image.new("RGB", (40, 80), "orange").save(image)
        with patch.object(W.QFileDialog, "getOpenFileName", return_value=(str(image), "")):
            ui.choose_image(True)
        QtTest.QTest.qWait(350)
        assert ui.current_panel()["inset"]
        with patch.object(W.QFileDialog, "getOpenFileName", return_value=(str(image), "")):
            ui.choose_image(False)
        QtTest.QTest.qWait(350)
        assert ui.current_panel()["kind"] == "Image"
        assert len(ui.plot_axes[ui.panel_index].images) == 1
        # Save+load remains valid after deleting imported images.
        ui.filename = str(root / "project.json")
        assert ui.save()
        image.unlink()
        restored = load_project(ui.filename)
        assert restored == ui.doc
        ui.resize(1120, 720)
        app.processEvents()
        with patch.object(
            W.QFileDialog,
            "getSaveFileName",
            return_value=(str(root / "figure.pdf"), "PDF vector (*.pdf)"),
        ):
            ui.export()
        media = re.search(
            rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]",
            (root / "figure.pdf").read_bytes(),
        )
        assert media and abs(float(media.group(1)) * 25.4 / 72 - ui.doc["settings"]["width"]) < 1e-6
    ui.dirty = False
    ui.close()
    print(
        "PASS: click-to-place arrows, small unit factors, live colormaps, view limits, reflow, image import/insets, portable image project, real UI export dimensions"
    )


if __name__ == "__main__":
    main()
