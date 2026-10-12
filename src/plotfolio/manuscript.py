"""Place a vector figure at its exact physical dimensions on a manuscript page."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

from .rendering import build_figure

MM = 72 / 25.4


def manuscript_pdf(doc, destination, page_size="A4", columns=1, source=None, page=0, x=15, top=80):
    if source and Path(source).resolve() == Path(destination).resolve():
        raise ValueError(
            "Save the preview to a different file to preserve the original manuscript."
        )
    figure, _, _ = build_figure(doc)
    buffer = BytesIO()
    figure.savefig(buffer, format="pdf")
    buffer.seek(0)
    figure_page = PdfReader(buffer).pages[0]
    width, height = (float(doc["settings"][key]) for key in ("width", "height"))
    if source:
        reader = PdfReader(source)
        if not 0 <= page < len(reader.pages):
            raise ValueError("Selected manuscript page does not exist.")
        writer = PdfWriter(clone_from=reader)
        target = writer.pages[page]
        target.transfer_rotation_to_content()
        pw, ph = float(target.cropbox.width), float(target.cropbox.height)
    else:
        pw, ph = A4 if page_size == "A4" else letter
        slot = (pw / MM - 30 - (6 if columns == 2 else 0)) / columns
        if width > slot + 0.01:
            raise ValueError(
                f"Figure is {width:g} mm wide; this column is {slot:.1f} mm. Change figure width or choose one column. Figures are never shrunk."
            )
        background = BytesIO()
        c = canvas.Canvas(background, pagesize=(pw, ph))
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, pw, ph, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-Bold", 16)
        c.drawString(15 * MM, ph - 23 * MM, "Scientific figures in manuscript context")
        c.setFont("Times-Roman", 10)
        text = "This sample page provides a reference for assessing figure typography and line weights."
        c.drawString(15 * MM, ph - 35 * MM, text)
        for col in range(columns):
            for line in range(6):
                c.drawString(
                    (15 + col * (slot + 6)) * MM,
                    ph - (43 + line * 4) * MM,
                    "Sample manuscript text for readability.",
                )
        c.setFont("Times-Roman", 9)
        c.drawString(
            x * MM,
            ph - (top + height + 7) * MM,
            "Figure 1. Preview figure placed at its original physical size.",
        )
        c.setFont("Helvetica", 8)
        c.drawString(
            15 * MM,
            12 * MM,
            f"PlotFolio size preview | {width:g} × {height:g} mm | no figure scaling",
        )
        c.save()
        background.seek(0)
        reader = PdfReader(background)
        writer = PdfWriter(clone_from=reader)
        target = writer.pages[0]
    if x < 0 or top < 0 or (x + width) * MM > pw + 0.01 or (top + height) * MM > ph + 0.01:
        raise ValueError(
            "The figure extends beyond the manuscript page. Adjust position or figure dimensions."
        )
    tx = float(target.cropbox.left) + x * MM
    ty = float(target.cropbox.top) - (top + height) * MM
    target.merge_transformed_page(figure_page, Transformation().translate(tx, ty))
    writer.add_metadata(
        {
            "/Creator": "PlotFolio",
            "/Subject": f"Exact-size figure preview: {width:g} × {height:g} mm",
        }
    )
    with Path(destination).open("wb") as output:
        writer.write(output)
    return width, height
