import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg

from plotfolio.examples import demo_document
from plotfolio.projects import load_project, save_project
from plotfolio.rendering import build_figure


class PanelPositionTests(unittest.TestCase):
    def test_physical_offsets_are_local_and_do_not_accumulate(self):
        doc = demo_document()
        base, base_axes, _ = build_figure(doc)
        FigureCanvasAgg(base).draw()
        moved = copy.deepcopy(doc)
        moved["panels"][0].update(offset_x=1.5, offset_y=-2)
        fig, axes, _ = build_figure(moved)
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        expected = base_axes[0].get_position().bounds
        actual = axes[0].get_position().bounds
        np.testing.assert_allclose(
            np.array(actual) - expected, [1.5 / 180, -2 / 170, 0, 0], atol=1e-7
        )
        np.testing.assert_allclose(
            axes[1].get_position().bounds, base_axes[1].get_position().bounds, atol=1e-7
        )
        canvas.draw()
        base.canvas.draw()
        np.testing.assert_allclose(
            np.array(axes[0].get_position().bounds) - base_axes[0].get_position().bounds,
            [1.5 / 180, -2 / 170, 0, 0],
            atol=1e-7,
        )
        actual = axes[0].get_position().bounds
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.plotfolio.json"
            save_project(moved, path)
            self.assertEqual(load_project(path), moved)
            fig.savefig(Path(tmp) / "figure.pdf")
            base.savefig(Path(tmp) / "base.pdf")
            np.testing.assert_allclose(
                np.array(axes[0].get_position().bounds) - base_axes[0].get_position().bounds,
                [1.5 / 180, -2 / 170, 0, 0],
                atol=1e-7,
            )

    def test_invalid_offsets(self):
        doc = demo_document()
        doc["panels"][0]["offset_x"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            build_figure(doc)
