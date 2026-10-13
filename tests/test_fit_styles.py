import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba

from plotfolio.fit_styles import fit_style
from plotfolio.fitting import fit_curve
from plotfolio.model import document, panel
from plotfolio.projects import load_project, save_project
from plotfolio.rendering import build_figure


class FitStyleTests(unittest.TestCase):
    def test_fit_appearance_exports_and_preserves_numerical_results(self):
        doc = document()
        doc["settings"].update(rows=1, cols=1)
        x = np.linspace(0, 4, 20)
        y = 2 * x + 1 + 0.02 * np.sin(7 * x)
        doc["datasets"]["d"] = dict(
            name="Synthetic", headers=["x", "y"], rows=[[str(a), str(b)] for a, b in zip(x, y)]
        )
        p = panel("d", "x", ["y"])
        doc["panels"] = [p]
        fit = fit_curve(x, y)
        original = copy.deepcopy(fit)
        fit.update(
            label="Styled fit",
            color="#BF6CD0",
            linestyle="dotted",
            linewidth=2.4,
            marker="s",
            markersize=6,
            alpha=0.7,
            band_color="#009EFA",
            band_alpha=0.25,
        )
        p["fits"] = [fit]
        fig, axes, _ = build_figure(doc)
        FigureCanvasAgg(fig).draw()
        curve = next(line for line in axes[0].lines if line.get_label() == "Styled fit")
        self.assertEqual(curve.get_linestyle(), ":")
        self.assertEqual(curve.get_linewidth(), 2.4)
        self.assertEqual(curve.get_marker(), "s")
        self.assertEqual(curve.get_alpha(), 0.7)
        np.testing.assert_allclose(
            axes[0].collections[-1].get_facecolor()[0], to_rgba("#009EFA", 0.25)
        )
        for key in original:
            self.assertEqual(fit[key], original[key])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "styled.json"
            save_project(doc, path)
            self.assertEqual(load_project(path), doc)
            fig.savefig(Path(tmp) / "styled.pdf")
        fit["visible"] = False
        fig, axes, _ = build_figure(doc)
        FigureCanvasAgg(fig).draw()
        self.assertFalse(any(line.get_label() == "Styled fit" for line in axes[0].lines))

    def test_legacy_defaults_and_invalid_color(self):
        style = fit_style({})
        self.assertEqual(style["linestyle"], "dashed")
        self.assertEqual(style["linewidth"], 1.3)
        with self.assertRaisesRegex(ValueError, "colors"):
            fit_style({"color": "invalid color"})
