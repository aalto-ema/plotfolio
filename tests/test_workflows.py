"""Numerical, provenance, import and template workflow regressions."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from openpyxl import Workbook
from scipy.stats import t

from plotfolio.analysis import replay_operation, summarize, transform
from plotfolio.data import columns, numeric
from plotfolio.expressions import expression
from plotfolio.fitting import fit_curve
from plotfolio.ingestion import read_tables
from plotfolio.model import document, panel
from plotfolio.projects import load_project, save_project
from plotfolio.rendering import build_figure
from plotfolio.templates import (
    apply_template,
    batch_export,
    load_template,
    make_template,
    save_template,
)


class WorkflowTests(unittest.TestCase):
    def dataset(self):
        return dict(
            name="Synthetic",
            headers=["x", "y", "group"],
            rows=[["0", "1", "a"], ["1", "3", "a"], ["2", "5", "b"], ["3", "7", "b"]],
            source="Synthetic regression data",
        )

    def test_import_preview_options_excel_sheets_and_no_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text("preamble\nx;y\n1;2\n3;4\n")
            ds = read_tables(path, delimiter="Semicolon", header_row=2)[0]
            self.assertEqual(ds["headers"], ["x", "y"])
            self.assertEqual(ds["import_options"]["header_row"], 2)
            plain = Path(tmp) / "plain.tsv"
            plain.write_text("1\t2\n3\t4\n")
            self.assertEqual(read_tables(plain, has_header=False)[0]["rows"][0], ["1", "2"])
            book = Workbook()
            book.active.append(["x", "y"])
            book.active.append([1, 2])
            sheet = book.create_sheet("Second")
            sheet.append(["x", "y"])
            sheet.append([3, 4])
            excel = Path(tmp) / "data.xlsx"
            book.save(excel)
            self.assertEqual(len(read_tables(excel)), 2)
            self.assertEqual(read_tables(excel, sheet="Second")[0]["rows"], [["3", "4"]])

    def test_transform_raw_preservation_history_and_safe_expressions(self):
        ds = self.dataset()
        original = copy.deepcopy(ds)
        result = transform(ds, "y", "Scale", factor=1000)
        np.testing.assert_allclose(numeric(columns(result)["processed"]), [1000, 3000, 5000, 7000])
        self.assertEqual(ds, original)
        self.assertEqual(result["history"][0]["factor"], 1000)
        calculated = transform(
            result,
            "y",
            "Calculated column",
            output="j",
            expression_text='col("processed") / 1000 + x',
        )
        self.assertEqual(len(calculated["history"]), 2)
        replayed = replay_operation(result, calculated["history"][-1])
        self.assertEqual(replayed["rows"], calculated["rows"])
        np.testing.assert_allclose(numeric(columns(calculated)["j"]), [1, 4, 7, 10])
        filtered = transform(ds, "y", "Filter rows", filter_text="x >= 2")
        self.assertEqual(len(filtered["rows"]), 2)
        for unsafe in ['__import__("os")', "x.__class__", 'open("file")', "[x for x in y]"]:
            with self.assertRaises(ValueError):
                expression(unsafe, {"x": np.arange(3)})
        smooth = transform(ds, "y", "Moving average", window=3)
        np.testing.assert_allclose(numeric(columns(smooth)["processed"]), [5 / 3, 3, 5, 19 / 3])

    def test_explicit_replicate_uncertainty(self):
        ds = self.dataset()
        sd = summarize(ds, "group", "y", uncertainty="SD")
        self.assertAlmostEqual(float(sd["rows"][0][1]), 2)
        self.assertAlmostEqual(float(sd["rows"][0][2]), np.sqrt(2))
        sem = summarize(ds, "group", "y", uncertainty="SEM")
        self.assertAlmostEqual(float(sem["rows"][0][2]), 1)
        ci = summarize(ds, "group", "y", uncertainty="Confidence interval")
        self.assertAlmostEqual(float(ci["rows"][0][2]), t.ppf(0.975, 1))
        median = summarize(ds, "group", "y", center="Median", uncertainty="Confidence interval")
        self.assertEqual(
            median, summarize(ds, "group", "y", center="Median", uncertainty="Confidence interval")
        )
        with self.assertRaisesRegex(ValueError, "SEM"):
            summarize(ds, "group", "y", center="Median", uncertainty="SEM")

    def test_linear_fit_weighting_diagnostics_and_bands(self):
        x = np.linspace(0, 5, 30)
        noise = 0.03 * np.sin(x * 10)
        y = 2 * x + 1 + noise
        result = fit_curve(x, y)
        slope, intercept = np.polyfit(x, y, 1)
        self.assertAlmostEqual(result["parameters"]["a"]["value"], slope, places=7)
        self.assertAlmostEqual(result["parameters"]["b"]["value"], intercept, places=7)
        self.assertEqual(len(result["residuals"]), 30)
        self.assertIsNotNone(result["lower"])
        weighted = fit_curve(x, y, sigma=np.full(30, 0.03), absolute_sigma=True, xmin=1, xmax=4)
        self.assertTrue(weighted["absolute_sigma"])
        self.assertGreater(weighted["excluded"], 0)
        with self.assertRaisesRegex(ValueError, "positive"):
            fit_curve(x, y, sigma=np.zeros(30))
        nonlinear = fit_curve(x, 3 * np.exp(-x / 1.4) + 0.2, model="Exponential decay")
        self.assertAlmostEqual(nonlinear["parameters"]["tau"]["value"], 1.4, places=6)
        custom = fit_curve(
            x,
            y,
            model="Custom",
            formula="a*x+b",
            parameters=["a", "b"],
            initial=[1, 0],
            lower=[0, -10],
            upper=[5, 10],
        )
        self.assertAlmostEqual(custom["parameters"]["a"]["value"], slope, places=6)
        poly = fit_curve(x, y, model="Polynomial", degree=2)
        self.assertEqual(len(poly["parameters"]), 3)
        json.dumps(result, allow_nan=False)

    def test_asymmetric_errors_follow_negative_scaling_and_invalid_bands_reject(self):
        doc = document()
        doc["settings"].update(rows=1, cols=1)
        ds = dict(
            name="Synthetic",
            headers=["x", "y", "lo", "hi", "lower", "upper"],
            rows=[["0", "1", ".1", ".2", ".9", "1.2"], ["1", "2", ".1", ".2", "1.9", "2.2"]],
        )
        doc["datasets"]["data"] = ds
        p = panel("data", "x", ["y"])
        p["series"][0].update(
            yfactor=-2, error_low="lo", error_high="hi", band_lower="lower", band_upper="upper"
        )
        doc["panels"] = [p]
        fig, axes, _ = build_figure(doc)
        FigureCanvasAgg(fig).draw()
        segment = axes[0].containers[0].lines[2][0].get_segments()[0]
        np.testing.assert_allclose(segment[:, 1], [-2.4, -1.8])
        ds["rows"][0][4] = "9"
        with self.assertRaisesRegex(ValueError, "lower boundaries"):
            build_figure(doc)

    def test_template_mapping_batch_preflight_and_source_free_save(self):
        doc = document()
        doc["settings"].update(rows=1, cols=1)
        doc["datasets"]["one"] = self.dataset()
        doc["panels"] = [panel("one", "x", ["y"])]
        template = make_template(doc)
        self.assertNotIn("rows", template["sources"]["one"])
        ds = self.dataset()
        ds["headers"] = ["potential", "current", "group"]
        mapped = apply_template(
            template, {"new": ds}, {"one": "new"}, {"one": {"x": "potential", "y": "current"}}
        )
        self.assertEqual(mapped["panels"][0]["x"], "potential")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save_template(doc, folder / "template.json")
            self.assertEqual(load_template(folder / "template.json")["template_version"], 1)
            paths = batch_export(template, [("a", self.dataset()), ("b", self.dataset())], folder)
            self.assertTrue(all(Path(path).is_file() for path in paths))
            with self.assertRaisesRegex(ValueError, "already exists"):
                batch_export(template, [("a", self.dataset())], folder)
            bad = self.dataset()
            bad["headers"] = ["x", "wrong", "group"]
            with self.assertRaisesRegex(ValueError, "missing mapped"):
                batch_export(template, [("new", self.dataset()), ("bad", bad)], folder)
            self.assertFalse((folder / "new.pdf").exists())

    def test_insets_secondary_axes_asymmetric_errors_and_portability(self):
        doc = document()
        doc["settings"].update(rows=1, cols=1)
        ds = self.dataset()
        ds["headers"] += ["lo", "hi"]
        ds["rows"] = [[*row, ".1", ".2"] for row in ds["rows"]]
        doc["datasets"]["one"] = ds
        p = panel("one", "x", ["y"])
        p["series"][0].update(error_low="lo", error_high="hi")
        p["data_inset"] = dict(
            xmin=1, xmax=2, ymin=2, ymax=6, bounds=[0.55, 0.1, 0.35, 0.35], connectors=True, font=7
        )
        p["secondary_x"] = dict(factor=1000, offset=0, label="mV")
        doc["panels"] = [p]
        fig, axes, _ = build_figure(doc)
        FigureCanvasAgg(fig).draw()
        self.assertGreaterEqual(len(axes[0].child_axes), 2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            save_project(doc, path)
            self.assertEqual(load_project(path), doc)
        p["kind"] = "Bar"
        p["x"] = "group"
        p["data_inset"] = None
        p["secondary_x"] = None
        doc["datasets"]["one"] = summarize(ds, "group", "y")
        p["series"][0].update(y="estimate", error_low="error_low", error_high="error_high")
        fig, _, _ = build_figure(doc)
        FigureCanvasAgg(fig).draw()
