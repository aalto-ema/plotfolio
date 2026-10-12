"""Portable project persistence and legacy migrations."""

import json
from pathlib import Path

from .constants import COLORS
from .data import read_csv
from .legends import legend_defaults
from .model import document, panel, settings
from .rendering import build_figure


def save_project(doc, path):
    Path(path).write_text(json.dumps(doc, indent=2, allow_nan=False), encoding="utf-8")


def load_project(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("version") == 1:
        csvpath = Path(doc["csv"])
        if not csvpath.is_absolute():
            csvpath = Path(path).parent / csvpath
        ds = read_csv(csvpath)
        fresh = document()
        fresh["datasets"]["data"] = ds
        for k, v in doc["settings"].items():
            if k in fresh["settings"]:
                default = fresh["settings"][k]
                fresh["settings"][k] = bool(v) if isinstance(default, bool) else type(default)(v)
        for i, old in enumerate(doc["panels"]):
            p = panel(
                "data",
                old["x"],
                old["ys"],
                i // int(fresh["settings"]["cols"]),
                i % int(fresh["settings"]["cols"]),
            )
            for k in ["title", "xlabel", "ylabel", "kind", "xscale", "yscale"]:
                p[k] = old[k]
            p["name"] = f"Panel {i + 1}"
            for j, s in enumerate(p["series"]):
                s["error"] = old.get("error", "")
                s["color"] = COLORS[
                    (j + (2 if old.get("palette") == "Green / purple" else 0)) % len(COLORS)
                ]
            fresh["panels"].append(p)
        doc = fresh
    if doc.get("version") != 2:
        raise ValueError("Unsupported project version.")
    defaults = settings()
    if "label_case" not in doc["settings"]:
        defaults["label_case"] = "uppercase"
    doc["settings"] = {**defaults, **doc["settings"]}
    for index, p in enumerate(doc["panels"]):
        doc["panels"][index] = {**panel(), **p}
    for p in doc["panels"]:
        p.update({key: value for key, value in legend_defaults().items() if key not in p})
    build_figure(doc)
    return doc
