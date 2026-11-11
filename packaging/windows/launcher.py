"""Entry point for the frozen Windows application."""

import sys
import tempfile
import traceback
from importlib.resources import files
from pathlib import Path


def smoke_test(result):
    """Check the native Qt plugin, packaged resources, and PDF stack."""
    try:
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtWidgets import QApplication

        from plotfolio.manuscript import manuscript_pdf
        from plotfolio.rendering import build_figure
        from plotfolio.ui.window import Studio

        app = QApplication([])
        app.setApplicationName("PlotFolio Installer Test")
        studio = Studio()
        studio.show()
        app.processEvents()
        assert studio.isVisible() and len(studio.plot_axes) >= 4
        assert files("plotfolio.ui").joinpath("icons/chevron.svg").is_file()
        figure, _, _ = build_figure(studio.doc)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for extension in ("pdf", "svg", "png", "tiff"):
                export = folder / f"figure.{extension}"
                figure.savefig(export, dpi=100)
                assert export.stat().st_size > 0
            pdf = folder / "manuscript.pdf"
            manuscript_pdf(studio.doc, pdf)
            document = QPdfDocument()
            try:
                assert document.load(str(pdf)) == QPdfDocument.Error.None_
                assert document.pageCount() == 1
            finally:
                document.close()
        studio.close()
    except Exception:
        result.write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    result.write_text("PASS", encoding="utf-8")
    return 0


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--installer-smoke-test":
        return smoke_test(Path(sys.argv[2]))
    from plotfolio.app import main as run_app

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
