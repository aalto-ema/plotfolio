import unittest

from matplotlib.backends.backend_agg import FigureCanvasAgg

from plotfolio.alignment import align_panels, snap
from plotfolio.examples import demo_document
from plotfolio.rendering import build_figure


class AlignmentTests(unittest.TestCase):
    def test_alignment_preserves_data_and_aligns_physical_edges(self):
        doc = demo_document()
        doc["panels"][1]["offset_y"] = -2
        result = align_panels(doc, [0, 1], "Top")
        fig, axes, _ = build_figure(result)
        FigureCanvasAgg(fig).draw()
        self.assertAlmostEqual(axes[0].get_position().y1, axes[1].get_position().y1, places=6)
        self.assertEqual(result["datasets"], doc["datasets"])
        self.assertAlmostEqual(snap(0.123, 0.05), 0.1)
        with self.assertRaisesRegex(ValueError, "three"):
            align_panels(doc, [0, 1], "Distribute horizontally")
