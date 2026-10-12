import copy
import tempfile
import unittest
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg

from plotfolio.examples import demo_document
from plotfolio.projects import load_project, save_project
from plotfolio.rendering import build_figure


class LegendTests(unittest.TestCase):
    def draw(self, doc):
        fig, axes, _ = build_figure(doc)
        FigureCanvasAgg(fig).draw()
        return fig, axes

    def test_placements_and_options(self):
        for placement in ["Inside", "Outside right", "Outside below", "Custom", "Hidden"]:
            with self.subTest(placement=placement):
                doc = demo_document()
                doc["panels"][0].update(
                    legend_placement=placement,
                    legend_font=7,
                    legend_columns=3,
                    legend_frame=False,
                    legend_title="Scan rates",
                    legend_x=0.2,
                    legend_y=0.3,
                )
                fig, axes = self.draw(doc)
                legend = axes[0].get_legend()
                if placement == "Hidden":
                    self.assertIsNone(legend)
                else:
                    self.assertEqual(legend.get_texts()[0].get_fontsize(), 7)
                    self.assertFalse(legend.get_frame_on())
                    self.assertEqual(legend.get_title().get_text(), "Scan rates")
                    box = legend.get_window_extent(fig.canvas.get_renderer())
                    self.assertGreaterEqual(box.x0, -1)
                    self.assertLessEqual(box.x1, fig.bbox.width + 1)
                    self.assertGreaterEqual(box.y0, -1)

    def test_shared_merges_matching_styles_and_qualifies_conflicts(self):
        doc = demo_document()
        second = copy.deepcopy(doc["panels"][0])
        second.update(row=0, col=1, name="Another CV")
        doc["panels"][1] = second
        doc["settings"].update(legend_mode="Shared figure", legend_columns=3)
        fig, axes = self.draw(doc)
        self.assertEqual(len(fig.legends[0].get_texts()), 3)
        self.assertTrue(all(ax.get_legend() is None for ax in axes))
        second["series"][0]["color"] = "#000000"
        fig, _ = self.draw(doc)
        labels = [text.get_text() for text in fig.legends[0].get_texts()]
        self.assertEqual(len(labels), 4)
        self.assertTrue(any("Another CV" in label for label in labels))
        doc["panels"][1]["legend"] = "Hide"
        fig, _ = self.draw(doc)
        self.assertEqual(len(fig.legends[0].get_texts()), 3)

    def test_custom_positions_survive_save_and_pdf_export(self):
        doc = demo_document()
        doc["panels"][0].update(legend_placement="Custom", legend_x=0.15, legend_y=0.7)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legend.plotfolio.json"
            save_project(doc, path)
            restored = load_project(path)
            self.assertEqual(restored, doc)
            fig, axes = self.draw(restored)
            fig.savefig(Path(tmp) / "figure.pdf")
            anchor = (
                axes[0].transAxes.inverted().transform(axes[0].get_legend().get_bbox_to_anchor().p0)
            )
            self.assertAlmostEqual(anchor[0], 0.15)
            self.assertAlmostEqual(anchor[1], 0.7)
