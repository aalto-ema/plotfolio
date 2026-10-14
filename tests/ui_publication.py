"""Focused UI coverage for direct editing and publication/recovery tools."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from matplotlib.backend_bases import MouseEvent
from PySide6 import QtTest
from PySide6.QtWidgets import QApplication

from plotfolio.recovery import write_snapshot
from plotfolio.ui.accessibility import AccessibilityDialog
from plotfolio.ui.alignment import AlignmentDialog
from plotfolio.ui.bundles import BundleDialog
from plotfolio.ui.preflight import PreflightDialog
from plotfolio.ui.typography import TypographyDialog
from plotfolio.ui.window import Studio


def main():
    app = QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        os.environ["PLOTFOLIO_AUTOSAVE_DIR"] = folder
        w = Studio()
        w.show()
        QtTest.QTest.qWait(350)
        label = w.plot_axes[0].xaxis.label
        box = label.get_window_extent(w.canvas.get_renderer())
        w.plot_clicked(
            MouseEvent("button_press_event", w.canvas, *box.get_points().mean(axis=0), button=1)
        )
        assert w.tabs.currentIndex() == 1
        w.dirty = True
        w.autosave()
        assert w.recovery_path.exists()
        w.clear_recovery()
        w.doc["settings"]["snap"] = True
        w.mark_kind.setCurrentText("Text")
        w.add_mark()
        w.place_button.setChecked(True)
        QtTest.QTest.qWait(350)
        point = w.plot_axes[0].transAxes.transform((0.123, 0.234))
        w.plot_clicked(MouseEvent("button_press_event", w.canvas, *point, button=1))
        assert abs(w.current_mark()["x"] - 0.1) < 1e-9
        assert abs(w.current_mark()["y"] - 0.25) < 1e-9
        w.doc["panels"][1]["offset_y"] = -1
        alignment = AlignmentDialog(w)
        alignment.list.item(0).setSelected(True)
        alignment.list.item(1).setSelected(True)
        alignment.operation.setCurrentText("Top")
        alignment.apply()
        assert "aligned" in alignment.status.text()
        typography = TypographyDialog(w)
        typography.sizes["xlabel_size"].setValue(12)
        typography.apply()
        assert w.current_panel()["xlabel_size"] == 12
        typography.reset()
        assert w.current_panel()["xlabel_size"] == 0
        checks = PreflightDialog(w)
        assert checks.list.count() > 0
        colors = AccessibilityDialog(w)
        colors.mode.setCurrentText("Grayscale")
        assert colors.pixmap is not None
        bundle = BundleDialog(w)
        with patch(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=(str(Path(folder) / "bundle.zip"), ""),
        ):
            bundle.export()
        assert (Path(folder) / "bundle.zip").exists(), bundle.status.text()
        # A simulated terminated session can be restored without overwriting a project.
        w.dirty = False
        path = write_snapshot(folder, "interrupted", w.doc)
        content = json.loads(path.read_text())
        content["pid"] = 99999999
        path.write_text(json.dumps(content))
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QPushButton

        def restore():
            dialog = app.activeModalWidget()
            next(
                button for button in dialog.findChildren(QPushButton) if button.text() == "Restore"
            ).click()

        QTimer.singleShot(100, restore)
        w.recover_work()
        assert w.dirty and not path.exists()
        w.dirty = False
        w.close()
    print(
        "PASS: direct editing, autosave/recovery, snapped placement, alignment, typography, checks, color preview and bundle export"
    )


if __name__ == "__main__":
    main()
