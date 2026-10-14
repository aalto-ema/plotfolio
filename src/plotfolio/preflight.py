"""Heuristic publication checks using fresh, final-size rendering."""

import itertools
import warnings

import numpy as np
from matplotlib import font_manager
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.text import Text

from .data import image_array
from .rendering import build_figure


def check_figure(doc):
    issues = []

    def add(code, message, panel=None, severity="Review"):
        issues.append(dict(code=code, message=message, panel=panel, severity=severity))

    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fig, axes, notes = build_figure(doc)
            canvas = FigureCanvasAgg(fig)
            canvas.draw()
        for warning in captured:
            if "constrained_layout" in str(warning.message):
                add(
                    "layout",
                    "Automatic layout could not fit all decorations. Increase figure size or reduce spacing.",
                )
    except Exception as error:
        add("render", str(error), severity="Error")
        return issues
    for note in notes:
        add("data", note)
    try:
        font_manager.findfont(doc["settings"]["family"], fallback_to_default=False)
    except ValueError:
        add(
            "font",
            f"Font {doc['settings']['family']} is unavailable; an installed font is substituted.",
        )
    for i, p in enumerate(doc["panels"]):
        if p.get("font_family"):
            try:
                font_manager.findfont(p["font_family"], fallback_to_default=False)
            except ValueError:
                add("font", f"Panel {i + 1}: font {p['font_family']} is unavailable.", i)
    renderer = canvas.get_renderer()
    page = fig.bbox
    for i, ax in enumerate(axes):
        excluded_ticks = set()
        for axis, limits in [(ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())]:
            lo, hi = sorted(limits)
            for tick in [*axis.get_major_ticks(), *axis.get_minor_ticks()]:
                if not lo <= tick.get_loc() <= hi:
                    excluded_ticks.update([tick.label1, tick.label2])
        text_items = [
            artist
            for artist in ax.findobj(Text)
            if artist.get_visible() and artist.get_text() and artist not in excluded_ticks
        ]
        for text in text_items:
            bbox = text.get_window_extent(renderer)
            if (
                bbox.width
                and bbox.height
                and (
                    bbox.x0 < -1
                    or bbox.y0 < -1
                    or bbox.x1 > page.width + 1
                    or bbox.y1 > page.height + 1
                )
            ):
                add(
                    "clipped",
                    f"Panel {i + 1}: text extends outside the page: {text.get_text()[:60]}",
                    i,
                )
            if text.get_fontsize() < 7:
                add("small_font", f"Panel {i + 1}: text below 7 pt: {text.get_text()[:40]}", i)
        p = doc["panels"][i]
        for key, fraction in [("image", 1), ("inset", None)]:
            if p.get(key):
                if fraction is None:
                    bounds = [float(v) for v in p["inset_bounds"].split(",")]
                    fraction = bounds[2]
                pixels = image_array(p[key]).shape[1]
                inches = ax.get_window_extent(renderer).width / fig.dpi * fraction
                if inches > 0 and pixels / inches < 300:
                    add(
                        "image_resolution",
                        f"Panel {i + 1}: {key} image is about {pixels / inches:.0f} DPI at final size (review against journal requirements).",
                        i,
                    )
        legend = ax.get_legend()
        if legend:
            box = legend.get_window_extent(renderer)
            if box.x0 < 0 or box.y0 < 0 or box.x1 > page.width or box.y1 > page.height:
                add("legend_clipped", f"Panel {i + 1}: legend extends beyond the page.", i)
            for line in ax.lines:
                xy = line.get_xydata()
                points = ax.transData.transform(xy[np.isfinite(xy).all(axis=1)])
                if any(box.contains(*point) for point in points):
                    add(
                        "legend_data",
                        f"Panel {i + 1}: legend may cover plotted data. Consider outside placement.",
                        i,
                    )
                    break
    for a, b in itertools.combinations(range(len(axes)), 2):
        if axes[a].get_window_extent(renderer).overlaps(axes[b].get_window_extent(renderer)):
            add(
                "panel_overlap",
                f"Panels {a + 1} and {b + 1} have overlapping plotting areas. Review offsets.",
                a,
            )
    for legend in fig.legends:
        box = legend.get_window_extent(renderer)
        if box.x0 < 0 or box.y0 < 0 or box.x1 > page.width or box.y1 > page.height:
            add("legend_clipped", "Shared legend extends beyond the page.")
        for text in legend.get_texts():
            if text.get_fontsize() < 7:
                add("small_font", "Shared legend contains text below 7 pt.")
    # Repeated tick warnings are grouped, rather than flooding the report.
    unique = {}
    for issue in issues:
        key = (issue["code"], issue["panel"])
        unique.setdefault(key, issue)
    return list(unique.values())
