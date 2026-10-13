"""Analysis overlays, data zoom insets and explicit linked-unit secondary axes."""

import math

import numpy as np
from matplotlib.collections import PolyCollection

from .fit_styles import draw_fit


def overlays(ax, panel, doc=None):
    for fit in panel.get("fits", []):
        draw_fit(ax, fit)
    raw = panel.get("replicates")
    if raw and doc and panel["kind"] == "Bar":
        from .data import columns, numeric

        data = columns(doc["datasets"][raw["dataset"]])
        summary = columns(doc["datasets"][panel["dataset"]])
        categories = list(dict.fromkeys(summary[panel["x"]]))
        for i, category in enumerate(categories):
            values = numeric(
                [v for group, v in zip(data[raw["group"]], data[raw["value"]]) if group == category]
            )
            values = values[np.isfinite(values)] * float(panel["series"][0]["yfactor"])
            jitter = (
                np.linspace(-0.12, 0.12, len(values)) if len(values) > 1 else np.zeros(len(values))
            )
            ax.scatter(i + jitter, values, s=14, c="#263448", alpha=0.65, zorder=5)
    zoom = panel.get("data_inset")
    if zoom:
        if panel["kind"] not in ["Line", "Scatter"] or panel.get("categorical_x", False):
            raise ValueError("Data zoom insets are available for Line and Scatter panels.")
        bounds = [float(value) for value in zoom["bounds"]]
        if (
            len(bounds) != 4
            or bounds[2] <= 0
            or bounds[3] <= 0
            or min(bounds[:2]) < 0
            or bounds[0] + bounds[2] > 1
            or bounds[1] + bounds[3] > 1
        ):
            raise ValueError("Inset bounds must fit inside the panel (fractions 0–1).")
        limits = [float(zoom[key]) for key in ["xmin", "xmax", "ymin", "ymax"]]
        if (
            not all(math.isfinite(value) for value in limits)
            or limits[0] >= limits[1]
            or limits[2] >= limits[3]
        ):
            raise ValueError("Inset limits must be finite and increasing.")
        inset = ax.inset_axes(bounds)
        for line in ax.lines:
            inset.plot(
                *line.get_data(),
                color=line.get_color(),
                marker=line.get_marker(),
                linestyle=line.get_linestyle(),
                linewidth=line.get_linewidth(),
                markersize=line.get_markersize() * 0.8,
                markeredgecolor=line.get_markeredgecolor(),
                markeredgewidth=line.get_markeredgewidth(),
                markerfacecolor=line.get_markerfacecolor(),
                alpha=line.get_alpha(),
                markevery=line.get_markevery(),
            )
        if (
            ax.get_xscale() == "log"
            and min(limits[:2]) <= 0
            or ax.get_yscale() == "log"
            and min(limits[2:]) <= 0
        ):
            raise ValueError("Log inset limits must be positive.")
        for collection in ax.collections:
            if isinstance(collection, PolyCollection) and len(collection.get_facecolor()):
                for path in collection.get_paths():
                    vertices = path.vertices
                    inset.fill(
                        vertices[:, 0],
                        vertices[:, 1],
                        color=collection.get_facecolor()[0],
                        alpha=collection.get_alpha(),
                        linewidth=0,
                    )
        inset.set_xscale(ax.get_xscale())
        inset.set_yscale(ax.get_yscale())
        inset.set_xlim(*limits[:2])
        inset.set_ylim(*limits[2:])
        inset.tick_params(labelsize=zoom.get("font", 7))
        inset.grid(alpha=0.15)
        if zoom.get("connectors", True):
            ax.indicate_inset_zoom(inset, edgecolor="#65768C", alpha=0.6)
    for axis in ["x", "y"]:
        spec = panel.get("secondary_" + axis)
        if not spec:
            continue
        if panel["kind"] in ["Image", "Bar", "Box", "Violin", "Strip", "Heatmap"] or panel.get(
            "categorical_x", False
        ):
            raise ValueError("Linked unit axes need a numeric axis.")
        factor, offset = float(spec["factor"]), float(spec["offset"])
        if not math.isfinite(factor) or factor == 0 or not math.isfinite(offset):
            raise ValueError(
                "Secondary conversion needs a finite nonzero factor and finite offset."
            )
        location = "top" if axis == "x" else "right"
        method = getattr(ax, "secondary_" + axis + "axis")
        linked = method(
            location,
            functions=(
                lambda value, f=factor, o=offset: value * f + o,
                lambda value, f=factor, o=offset: (value - o) / f,
            ),
        )
        getattr(linked, "set_" + axis + "label")(spec.get("label", ""))
