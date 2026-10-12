"""Scientific behavior, portable project and export regression checks."""

import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PIL import Image

from plotfolio.engine import *


class EngineTests(unittest.TestCase):
    def one(self, kind="Line", replicates=False):
        d = document()
        d["settings"].update(rows=1, cols=1, width=85, height=70)
        rows = [["a", "1", "2", ".1"], ["b", "3", "4", ".2"]]
        if replicates:
            rows += [["a", "1.4", "2.5", ".1"], ["b", "3.7", "4.3", ".2"]]
        if kind not in ["Bar", "Box", "Violin", "Strip"]:
            rows = [["0", "1", "2", ".1"], ["1", "3", "4", ".2"], ["2", "4", "6", ".3"]]
        d["datasets"]["data"] = dict(
            name="data", headers=["x", "y", "z", "error"], rows=rows, source="test"
        )
        p = panel("data", "x", ["y", "z"])
        p["kind"] = kind
        d["panels"] = [p]
        return d

    def draw(self, d):
        fig, axes, notes = build_figure(d)
        FigureCanvasAgg(fig).draw()
        return fig, axes, notes

    def test_csv_headers_categories_and_separator(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.csv"
            p.write_text("\ufeffgroup;y\na;2\nb;3\n")
            ds = read_csv(p)
            self.assertEqual(ds["headers"], ["group", "y"])
            self.assertEqual(numeric_columns(ds), ["y"])
            p.write_text("x,y\n1,2,3\n")
            with self.assertRaises(ValueError):
                read_csv(p)

    def test_all_plot_types(self):
        for kind in KINDS[:-1]:
            with self.subTest(kind=kind):
                self.draw(self.one(kind, kind in ["Box", "Violin", "Strip"]))

    def test_category_tick_labels(self):
        for kind in ["Bar", "Box", "Violin", "Strip"]:
            _, axes, _ = self.draw(self.one(kind, kind != "Bar"))
            self.assertEqual([t.get_text() for t in axes[0].get_xticklabels()], ["a", "b"])

    def test_scaling_and_uncertainty(self):
        d = self.one()
        s = d["panels"][0]["series"][0]
        s.update(xfactor=1000, yfactor=2, error="error")
        _, axes, _ = self.draw(d)
        curve = axes[0].lines[0]
        np.testing.assert_allclose(curve.get_xdata(), [0, 1000, 2000])
        np.testing.assert_allclose(curve.get_ydata(), [2, 6, 8])
        errors = axes[0].containers[0].lines[2][0].get_segments()
        np.testing.assert_allclose(errors[0][:, 1], [1.8, 2.2])

    def test_negative_scale_uncertainty_absolute(self):
        d = self.one()
        d["panels"][0]["series"][0].update(yfactor=-2, error="error")
        _, axes, _ = self.draw(d)
        segments = axes[0].containers[0].lines[2][0].get_segments()
        np.testing.assert_allclose(segments[0][:, 1], [-2.2, -1.8])

    def test_invalid_rows_and_log(self):
        d = self.one()
        d["datasets"]["data"]["rows"][0][1] = "missing"
        _, _, notes = self.draw(d)
        self.assertTrue(any("excluded 1" in n for n in notes))
        d["panels"][0]["xscale"] = "log"
        self.draw(d)
        d["panels"][0]["xmin"] = "0"
        with self.assertRaisesRegex(ValueError, "positive"):
            self.draw(d)

    def test_negative_error(self):
        d = self.one()
        d["panels"][0]["series"][0]["error"] = "error"
        d["datasets"]["data"]["rows"][0][3] = "-.1"
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            self.draw(d)

    def test_bar_replicates_not_implicitly_averaged(self):
        with self.assertRaisesRegex(ValueError, "replicates"):
            self.draw(self.one("Bar", True))

    def test_axis_limits_and_ticks(self):
        d = self.one()
        d["panels"][0].update(xmin="-1", xmax="5", xticks="0,1,2", xdecimals=2)
        _, ax, _ = self.draw(d)
        np.testing.assert_allclose(ax[0].get_xlim(), [-1, 5])
        np.testing.assert_allclose(ax[0].get_xticks(), [0, 1, 2])
        self.assertEqual(ax[0].get_xticklabels()[0].get_text(), "0.00")

    def test_ratios_spans_and_overlap(self):
        d = self.one()
        d["settings"].update(cols=3, width_ratios="20:50:30", width=180)
        for i in [1, 2]:
            d["panels"].append(panel("data", "x", ["y"], 0, i))
        f, ax, _ = self.draw(d)
        np.testing.assert_allclose(
            f.axes[0].get_subplotspec().get_gridspec().get_width_ratios(), [20, 50, 30]
        )
        d["panels"][0]["colspan"] = 2
        with self.assertRaisesRegex(ValueError, "overlaps"):
            self.draw(d)
        d["panels"].pop(1)
        self.draw(d)
        with self.assertRaises(ValueError):
            ratios("1:0", 2)

    def test_shared_axes_and_conflicts(self):
        d = self.one()
        d["settings"].update(cols=2, sharex=True, sharey=True)
        d["panels"].append(panel("data", "x", ["z"], 0, 1))
        _, ax, _ = self.draw(d)
        self.assertTrue(ax[0].get_shared_x_axes().joined(ax[0], ax[1]))
        d["panels"][1]["xmin"] = "1"
        with self.assertRaisesRegex(ValueError, "matching limits"):
            self.draw(d)

    def test_annotations(self):
        d = self.one()
        for kind in ["Text", "Rectangle", "Ellipse", "Line", "Arrow"]:
            d["panels"][0]["annotations"].append(annotation(kind))
        _, ax, _ = self.draw(d)
        self.assertEqual(len(ax[0].patches), 2)
        self.assertEqual(len(ax[0].texts), 2)
        d["panels"][0]["annotations"][0].update(coords="Data", text=r"$x_i^{2}$")
        self.draw(d)

    def test_images_and_portable_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "image.png"
            Image.new("RGB", (80, 40), "red").save(image)
            payload = image_payload(image)
            image.unlink()
            d = self.one()
            d["panels"][0].update(kind="Image", image=payload, inset=payload)
            _, ax, _ = self.draw(d)
            self.assertEqual(len(ax[0].images), 1)
            self.assertEqual(len(ax[0].child_axes), 1)
            project = Path(tmp) / "project.json"
            save_project(d, project)
            restored = load_project(project)
            self.assertEqual(d, restored)
            self.draw(restored)

    def test_export_physical_size(self):
        d = self.one()
        fig, _, _ = self.draw(d)
        np.testing.assert_allclose(fig.get_size_inches() * 25.4, [85, 70])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "f.pdf"
            fig.savefig(p)
            match = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", p.read_bytes())
            self.assertIsNotNone(match)
            np.testing.assert_allclose(
                [float(v) * 25.4 / 72 for v in match.groups()], [85, 70], atol=1e-7
            )
            for ext in ["svg", "png", "tiff"]:
                fig.savefig(Path(tmp) / ("f." + ext), dpi=150)
            with Image.open(Path(tmp) / "f.png") as im:
                self.assertEqual(im.width, int(85 / 25.4 * 150))

    def test_palette_and_series_styles(self):
        d = self.one()
        d["settings"]["colormap"] = "plasma"
        d["panels"][0]["series"][0].update(
            color="#abcdef", marker="s", linestyle="dashed", label=r"$H_2O$"
        )
        _, ax, _ = self.draw(d)
        self.assertEqual(ax[0].lines[0].get_color(), "#abcdef")
        self.assertEqual(ax[0].lines[0].get_linestyle(), "--")
        self.assertEqual(ax[0].lines[0].get_marker(), "s")
        d["panels"][0]["series"][0]["visible"] = False
        self.draw(d)

    def test_legacy_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "data.csv").write_text("x,y\n0,1\n1,2\n")
            legacy = dict(
                version=1,
                csv="data.csv",
                settings=dict(
                    width="85",
                    height="65",
                    rows="1",
                    cols="1",
                    font="8",
                    grid=True,
                    legend=True,
                    dpi="600",
                ),
                panels=[
                    dict(
                        x="x",
                        ys=["y"],
                        error="",
                        kind="Line",
                        title="",
                        xlabel="",
                        ylabel="",
                        xscale="linear",
                        yscale="linear",
                    )
                ],
            )
            save_project(legacy, p / "legacy.json")
            d = load_project(p / "legacy.json")
            self.assertEqual(d["version"], 2)
            self.assertIsInstance(d["settings"]["width"], int)
            self.draw(d)

    def test_electrochemistry_demo(self):
        d = demo_document()
        _, axes, _ = self.draw(d)
        cv = axes[0].lines[0].get_xdata()
        self.assertTrue(np.any(np.diff(cv) < 0))
        self.assertTrue(np.any(np.diff(cv) > 0))
        self.assertEqual(axes[1].get_aspect(), 1.0)
        ds = columns(d["datasets"]["eis"])
        real = numeric(ds["Zreal_ohm"])
        imag = numeric(ds["minus_Zimag_ohm"])
        np.testing.assert_allclose((real - 102) ** 2 + imag**2, 90**2, rtol=1e-12)
        self.assertEqual(d["panels"][2]["kind"], "Bar")
        self.assertEqual(d["panels"][3]["kind"], "Heatmap")
        self.assertTrue(all(ax.get_title() == "" for ax in axes))

    def test_line_connection_order(self):
        d = self.one()
        d["datasets"]["data"]["rows"][2][0] = "0"
        d["panels"][0]["line_order"] = "CSV row order"
        _, axes, _ = self.draw(d)
        np.testing.assert_allclose(axes[0].lines[0].get_xdata(), [0, 1, 0])
        d["panels"][0]["line_order"] = "Sort by X"
        _, axes, _ = self.draw(d)
        np.testing.assert_allclose(axes[0].lines[0].get_xdata(), [0, 0, 1])


if __name__ == "__main__":
    unittest.main()
