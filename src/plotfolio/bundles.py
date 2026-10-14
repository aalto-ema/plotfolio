"""Atomic publication bundles with figures, embedded sources and rendered curve data."""

import csv
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
from matplotlib.backends.backend_agg import FigureCanvasAgg

from .rendering import build_figure


def csv_text(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue()


def export_bundle(doc, destination, formats=("pdf", "svg", "png")):
    destination = Path(destination)
    if destination.suffix.lower() != ".zip":
        raise ValueError("Export bundles use a .zip filename.")
    if any(format not in ["pdf", "svg", "png", "tiff"] for format in formats) or not formats:
        raise ValueError("Select supported figure formats.")
    for dataset in doc["datasets"].values():
        if dataset.get("source") and Path(dataset["source"]).resolve() == destination.resolve():
            raise ValueError("Choose an output separate from the source data.")
    fig, axes, notes = build_figure(doc)
    FigureCanvasAgg(fig).draw()
    descriptor, temporary = tempfile.mkstemp(
        prefix=".plotfolio-bundle-", suffix=".zip", dir=destination.parent
    )
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            with mpl.rc_context({"pdf.fonttype": 42, "svg.fonttype": "none"}):
                for format in formats:
                    stream = io.BytesIO()
                    fig.savefig(
                        stream, format=format, dpi=int(doc["settings"]["dpi"]), facecolor="white"
                    )
                    archive.writestr("figure." + format, stream.getvalue())
            archive.writestr("project.plotfolio.json", json.dumps(doc, indent=2, allow_nan=False))
            manifest = dict(
                bundle_version=1,
                created_utc=datetime.now(timezone.utc).isoformat(),
                dimensions_mm=[doc["settings"]["width"], doc["settings"]["height"]],
                datasets=[],
                plotted_curves=[],
                fits=[],
                render_notes=notes,
            )
            for i, (key, ds) in enumerate(doc["datasets"].items(), 1):
                path = f"sources/{i:03d}.csv"
                archive.writestr(path, csv_text(ds["headers"], ds["rows"]))
                manifest["datasets"].append(
                    dict(
                        key=key,
                        name=ds["name"],
                        file=path,
                        source=ds.get("source", ""),
                        history=ds.get("history", []),
                        column_metadata=ds.get("column_metadata", {}),
                    )
                )
            for i, (p, ax) in enumerate(zip(doc["panels"], axes), 1):
                for j, s in enumerate(p["series"]):
                    artist = next(
                        (line for line in ax.lines if line.get_gid() == f"series:{j}"), None
                    )
                    if artist is not None:
                        path = f"plotted/panel-{i:02d}-series-{j + 1:02d}.csv"
                        archive.writestr(
                            path,
                            csv_text(
                                ["X plotted units", "Y plotted units"],
                                zip(artist.get_xdata(), artist.get_ydata()),
                            ),
                        )
                        manifest["plotted_curves"].append(
                            dict(
                                panel=i,
                                series=j + 1,
                                label=s["label"],
                                file=path,
                                uncertainty_definition=s.get("error_definition", "Unspecified"),
                                band_definition=s.get("band_definition", "Unspecified"),
                            )
                        )
                for j, fit in enumerate(p.get("fits", []), 1):
                    path = f"fits/panel-{i:02d}-fit-{j:02d}.json"
                    archive.writestr(path, json.dumps(fit, indent=2, allow_nan=False))
                    manifest["fits"].append(dict(panel=i, file=path))
            archive.writestr("provenance.json", json.dumps(manifest, indent=2, allow_nan=False))
            archive.writestr(
                "README.txt",
                "PlotFolio publication bundle\nFigures use the saved physical size. Source CSVs contain embedded raw/derived tables. Plotted CSVs contain rendered line/scatter coordinates in plotted units; categorical/image/distribution data are preserved in source tables and the project. Fit JSON reports include parameters, residuals and intervals. Uncertainty definitions and styles are retained in the portable project. Source paths may be present in provenance; review them before sharing.\n",
            )
        os.replace(temporary, destination)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination
