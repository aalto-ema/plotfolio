import tempfile
import unittest
from pathlib import Path

from plotfolio.model import document
from plotfolio.recovery import read_snapshot, write_snapshot


class RecoveryTests(unittest.TestCase):
    def test_atomic_snapshot_preserves_embedded_document_and_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.json"
            source.write_text("original")
            doc = document()
            path = write_snapshot(folder, "session", doc, str(source))
            self.assertEqual(read_snapshot(path)["document"], doc)
            doc["settings"]["font"] = 12
            write_snapshot(folder, "session", doc, str(source))
            self.assertEqual(read_snapshot(path)["document"]["settings"]["font"], 12)
            self.assertEqual(source.read_text(), "original")
            self.assertFalse(list(Path(folder).glob("*.tmp")))
