import unittest

from plotfolio.examples import demo_document
from plotfolio.preflight import check_figure


class PublicationCheckTests(unittest.TestCase):
    def test_reports_small_fonts_and_off_page_legends(self):
        doc = demo_document()
        doc["settings"]["font"] = 5
        self.assertIn("small_font", [item["code"] for item in check_figure(doc)])
        doc["panels"][0].update(legend_placement="Custom", legend_x=5, legend_y=5)
        self.assertIn("legend_clipped", [item["code"] for item in check_figure(doc)])

    def test_invalid_layout_is_an_error_report(self):
        doc = demo_document()
        doc["panels"][1]["col"] = 0
        issues = check_figure(doc)
        self.assertEqual(issues[0]["severity"], "Error")

    def test_locator_ticks_outside_limits_are_not_clipping_findings(self):
        self.assertNotIn("clipped", [item["code"] for item in check_figure(demo_document())])
