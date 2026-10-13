"""Reusable figure designs and preflighted batch exports; no source data in templates."""

import copy
import json
import os
import re
import tempfile
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg

from .model import document, panel, settings
from .rendering import build_figure


def requirements(template):
    required = {slot: set() for slot in template["sources"]}
    for p in template["panels"]:
        if p["kind"] == "Image":
            continue
        needed = required[p["dataset"]]
        if p.get("x"):
            needed.add(p["x"])
        for s in p["series"]:
            for key in [
                "y",
                "error",
                "error_x",
                "error_low",
                "error_high",
                "band_lower",
                "band_upper",
            ]:
                if s.get(key):
                    needed.add(s[key])
    return {slot: sorted(cols) for slot, cols in required.items()}


def make_template(doc):
    sources = {p["dataset"]: {} for p in doc["panels"] if p["kind"] != "Image"}
    for key in sources:
        ds = doc["datasets"].get(key)
        if ds is None:
            raise ValueError("Every non-image panel must have a dataset before saving a template.")
        sources[key] = dict(
            name=ds["name"],
            headers=list(ds["headers"]),
            column_metadata=copy.deepcopy(ds.get("column_metadata", {})),
        )
    panels = copy.deepcopy(doc["panels"])
    for p in panels:
        p["fits"] = []
        p["replicates"] = None
        if p.get("data_inset"):
            p["data_inset"]["connectors"] = bool(p["data_inset"].get("connectors", True))
    return dict(
        template_version=1, settings=copy.deepcopy(doc["settings"]), panels=panels, sources=sources
    )


def save_template(doc, path):
    Path(path).write_text(
        json.dumps(make_template(doc), indent=2, allow_nan=False), encoding="utf-8"
    )


def load_template(path):
    template = json.loads(Path(path).read_text(encoding="utf-8"))
    if template.get("template_version") != 1 or not isinstance(template.get("sources"), dict):
        raise ValueError("Unsupported figure template.")
    template["settings"] = {**settings(), **template["settings"]}
    template["panels"] = [{**panel(), **p} for p in template["panels"]]
    return template


def apply_template(template, datasets, source_map, column_map=None):
    doc = document()
    doc["settings"] = copy.deepcopy(template["settings"])
    doc["panels"] = copy.deepcopy(template["panels"])
    doc["datasets"] = dict(datasets)
    column_map = column_map or {}
    for slot, needed in requirements(template).items():
        target = source_map.get(slot)
        if target not in datasets:
            raise ValueError(f"Choose a dataset for template source {slot}.")
        for header in needed:
            mapped = column_map.get(slot, {}).get(header, header)
            if mapped not in datasets[target]["headers"]:
                raise ValueError(f"{datasets[target]['name']}: missing mapped column {mapped!r}.")
    for p in doc["panels"]:
        if p["kind"] == "Image":
            continue
        slot = p["dataset"]
        p["dataset"] = source_map[slot]
        mapping = column_map.get(slot, {})
        p["x"] = mapping.get(p["x"], p["x"])
        for s in p["series"]:
            for key in [
                "y",
                "error",
                "error_x",
                "error_low",
                "error_high",
                "band_lower",
                "band_upper",
            ]:
                if s.get(key):
                    s[key] = mapping.get(s[key], s[key])
        p["fits"] = []
        p["replicates"] = None
    fig, _, _ = build_figure(doc)
    FigureCanvasAgg(fig).draw()
    return doc


def batch_export(template, items, folder, format="pdf", column_map=None, progress=None):
    """One template source, many tables. Preflight all outputs before writing any."""
    if len(template["sources"]) != 1:
        raise ValueError(
            "Batch plotting needs a template with one dataset source. Use Apply template to map multiple sources explicitly."
        )
    if format not in ["pdf", "svg", "png", "tiff"]:
        raise ValueError("Choose PDF, SVG, PNG or TIFF.")
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("Choose an existing export folder.")
    slot = next(iter(template["sources"]))
    prepared = []
    names = set()
    for index, (name, dataset) in enumerate(items, 1):
        if progress:
            progress(f"Checking {index}/{len(items)}: {name}")
        stem = re.sub(r"[^\w.-]+", "_", name).strip("._") or "figure"
        path = folder / f"{stem}.{format}"
        if path.exists() or path.name in names:
            raise ValueError(
                f"Output {path.name} already exists or has a duplicate name. Choose a new folder or distinct input names."
            )
        names.add(path.name)
        doc = apply_template(template, {"data": dataset}, {slot: "data"}, column_map)
        fig, _, _ = build_figure(doc)
        FigureCanvasAgg(fig).draw()
        prepared.append((path, fig, doc["settings"]["dpi"]))
    if not prepared:
        raise ValueError("Select at least one dataset for batch plotting.")
    with tempfile.TemporaryDirectory(prefix=".plotfolio-batch-", dir=folder) as temporary:
        for index, (path, fig, dpi) in enumerate(prepared, 1):
            if progress:
                progress(f"Rendering {index}/{len(prepared)}: {path.name}")
            fig.savefig(Path(temporary) / path.name, dpi=int(dpi), facecolor="white")
        for path, _, _ in prepared:
            os.link(Path(temporary, path.name), path)
    return [str(path) for path, _, _ in prepared]
