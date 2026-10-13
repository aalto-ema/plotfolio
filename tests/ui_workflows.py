"""Modal workflow integration and scientific result application."""

import copy
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from plotfolio.model import document, panel
from plotfolio.templates import make_template
from plotfolio.ui.analysis_dialogs import DatasetAnalysisDialog, FitDialog
from plotfolio.ui.import_data import ImportDialog
from plotfolio.ui.panel_tools import PanelToolsDialog
from plotfolio.ui.template_dialogs import BatchDialog, TemplateMappingDialog
from plotfolio.ui.window import Studio


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    studio = Studio()
    studio.show()
    QTest.qWait(400)
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        csv = folder / "input.csv"
        csv.write_text(
            "potential,current,sigma,group\n0,1,.1,A\n1,2.9,.1,A\n2,5.1,.1,B\n3,7,.1,B\n"
        )
        importer = ImportDialog([str(csv)], studio)
        assert importer.preview["headers"] == ["potential", "current", "sigma", "group"]
        importer.roles.cellWidget(0, 1).setCurrentText("X")
        importer.roles.cellWidget(1, 1).setCurrentText("Y")
        importer.roles.item(0, 2).setText("V")
        importer.apply()
        ds = importer.result[0][1]
        assert ds["column_metadata"]["potential"]["unit"] == "V"
        doc = document()
        doc["settings"].update(rows=1, cols=1, width=130, height=100)
        doc["datasets"]["data"] = ds
        doc["panels"] = [panel("data", "potential", ["current"])]
        studio.replace_document(doc)
        original = copy.deepcopy(ds)
        fit = FitDialog(studio)
        fit.compute()
        assert fit.result is not None, fit.status.text()
        fit.apply()
        QTest.qWait(400)
        assert studio.current_panel()["fits"]
        tools = PanelToolsDialog(studio)
        tools.zoom_enabled.setChecked(True)
        tools.limits["xmin"].setText(".5")
        tools.limits["xmax"].setText("2.5")
        tools.limits["ymin"].setText("1")
        tools.limits["ymax"].setText("6")
        enabled, factor, offset, label = tools.secondary["x"]
        enabled.setChecked(True)
        factor.setValue(1000)
        label.setText("Potential / mV")
        tools.apply()
        assert studio.current_panel()["data_inset"]
        assert studio.render()
        derived = DatasetAnalysisDialog(studio)
        derived.column.setCurrentText("current")
        derived.factor.setValue(1000)
        derived.output.setText("milli")
        derived.unit.setText("mA")
        derived.apply()
        QTest.qWait(400)
        assert studio.doc["datasets"]["data"] == original
        assert studio.current_panel()["series"][0]["y"] == "milli"
        assert not studio.current_panel()["fits"]
        studio.undo()
        assert studio.current_panel()["fits"]
        summary = DatasetAnalysisDialog(studio, True)
        summary.column.setCurrentText("current")
        summary.group.setCurrentText("group")
        summary.apply()
        QTest.qWait(400)
        assert studio.current_panel()["kind"] == "Bar"
        assert studio.render()
        assert studio.current_panel()["replicates"]
        studio.undo()
        summary2 = DatasetAnalysisDialog(studio, True)
        summary2.column.setCurrentText("current")
        summary2.group.setCurrentText("group")
        summary2.plot.setCurrentText("Scatter + error bars")
        summary2.apply()
        QTest.qWait(400)
        assert studio.render(), studio.message.text()
        studio.undo()
        template = make_template(studio.doc)
        mapping = TemplateMappingDialog(template, studio.doc["datasets"], studio)
        mapping.apply()
        assert mapping.result is not None, mapping.status.text()
        batch = BatchDialog(template, {"one": ds, "two": ds}, studio)
        batch.folder.setText(str(folder))
        batch.run_batch()
        deadline = time.monotonic() + 20
        while batch.worker.isRunning() and time.monotonic() < deadline:
            time.sleep(0.02)
            app.processEvents()
        assert not batch.worker.isRunning(), "Batch worker did not finish"
        app.processEvents()
        assert (folder / "one.pdf").exists(), batch.status.text()
        assert (folder / "two.pdf").exists()
        if len(sys.argv) > 1:
            studio.grab().save(str(Path(sys.argv[1]) / "plotfolio-workflows-main.png"))
        fit2 = FitDialog(studio)
        fit2.compute()
        fit2.show()
        QTest.qWait(300)
        if len(sys.argv) > 1:
            fit2.grab().save(str(Path(sys.argv[1]) / "plotfolio-workflows-fit.png"))
        fit2.close()
    studio.dirty = False
    studio.close()
    print(
        "PASS: import roles/units, fitting, linked inset, immutable transforms, summaries, undo, template mapping and batch worker"
    )


if __name__ == "__main__":
    main()
