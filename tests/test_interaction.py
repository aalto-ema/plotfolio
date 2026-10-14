import unittest

from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg

from plotfolio.examples import demo_document
from plotfolio.interaction import hit_target
from plotfolio.rendering import build_figure


class InteractionTests(unittest.TestCase):
    def test_duplicate_series_labels_keep_distinct_targets_and_margin_labels_click(self):
        doc = demo_document()
        doc["panels"][0]["series"][1]["label"] = doc["panels"][0]["series"][0]["label"]
        fig, axes, _ = build_figure(doc)
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        self.assertEqual(axes[0].lines[1].get_gid(), "series:1")
        label = axes[0].xaxis.label
        b = label.get_window_extent(canvas.get_renderer())
        event = MouseEvent("button_press_event", canvas, *b.get_points().mean(axis=0), button=1)
        self.assertEqual(hit_target(axes, event), (0, "panel:xlabel"))
