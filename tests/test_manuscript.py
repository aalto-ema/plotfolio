import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

from plotfolio.examples import demo_document
from plotfolio.manuscript import MM, manuscript_pdf
from plotfolio.rendering import build_figure


class ManuscriptTests(unittest.TestCase):
    def test_exact_placement_and_source_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.pdf"
            dest = Path(tmp) / "copy.pdf"
            doc = demo_document()
            manuscript_pdf(doc, source)
            original = source.read_bytes()
            with self.assertRaisesRegex(ValueError, "preserve the original"):
                manuscript_pdf(doc, source, source=source)
            self.assertEqual(source.read_bytes(), original)
            doc["settings"].update(width=60, height=60)
            manuscript_pdf(doc, dest, source=source, top=10)
            self.assertEqual(source.read_bytes(), original)
            page = PdfReader(dest).pages[0]
            self.assertAlmostEqual(float(page.mediabox.width) / MM, 210, places=4)
            transforms = [args for args, op in page.get_contents().operations if op == b"cm"]
            self.assertTrue(
                any(
                    abs(float(v[4]) - 15 * MM) < 0.01
                    and abs(float(v[5]) - (297 - 70) * MM) < 0.01
                    and list(v[:4]) == [1, 0, 0, 1]
                    for v in transforms
                )
            )
            with self.assertRaisesRegex(ValueError, "never shrunk"):
                manuscript_pdf(demo_document(), dest, columns=2)

    def test_label_format_and_position(self):
        doc = demo_document()
        doc["settings"].update(label_parentheses=True)
        doc["panels"][0].update(label_x=".1", label_y=".9")
        _, axes, _ = build_figure(doc)
        label = axes[0].texts[-1]
        self.assertEqual(label.get_text(), "(a)")
        self.assertEqual(label.get_position(), (0.1, 0.9))
