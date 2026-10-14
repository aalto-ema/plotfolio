import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from plotfolio.bundles import export_bundle
from plotfolio.examples import demo_document


class BundleTests(unittest.TestCase):
    def test_archive_contains_sources_figures_and_scaled_rendered_curves(self):
        doc = demo_document()
        doc["panels"][0]["series"][0]["yfactor"] = 2
        with tempfile.TemporaryDirectory() as folder:
            path = export_bundle(doc, Path(folder) / "bundle.zip", formats=["pdf"])
            with zipfile.ZipFile(path) as archive:
                self.assertIn("figure.pdf", archive.namelist())
                self.assertIn("project.plotfolio.json", archive.namelist())
                manifest = json.loads(archive.read("provenance.json"))
                self.assertEqual(len(manifest["datasets"]), 4)
                self.assertTrue(manifest["plotted_curves"])
                self.assertEqual(json.loads(archive.read("project.plotfolio.json")), doc)
