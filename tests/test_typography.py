import unittest

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.ticker import ScalarFormatter

from plotfolio.examples import demo_document
from plotfolio.rendering import build_figure


class TypographyTests(unittest.TestCase):
    def test_overrides_are_local_and_data_are_unchanged(self):
        doc = demo_document()
        doc["panels"][0].update(
            xlabel_size=14, xtick_size=8, panel_label_size=17, xformat="Scientific"
        )
        fig, axes, _ = build_figure(doc)
        FigureCanvasAgg(fig).draw()
        self.assertEqual(axes[0].xaxis.label.get_fontsize(), 14)
        self.assertNotEqual(axes[1].xaxis.label.get_fontsize(), 14)
        self.assertEqual(axes[0].texts[-1].get_fontsize(), 17)
        self.assertIsInstance(axes[0].xaxis.get_major_formatter(), ScalarFormatter)
        self.assertEqual(doc["panels"][0]["xmin"], "-0.3")
