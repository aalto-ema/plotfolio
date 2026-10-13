"""Consistent panel and figure legends, including exportable custom anchors."""

import math
from collections import Counter

from matplotlib.colors import to_rgba


def legend_defaults(shared=False):
    return dict(
        legend_placement="Outside below" if shared else "Inside",
        legend_font=0.0,
        legend_columns=1,
        legend_labelspacing=0.4,
        legend_columnspacing=1.0,
        legend_handlelength=1.8,
        legend_borderpad=0.4,
        legend_markerscale=1.0,
        legend_frame=True,
        legend_opacity=1.0,
        legend_title="",
        legend_x="",
        legend_y="",
    )


def options(settings, base_font):
    return dict(
        fontsize=float(settings.get("legend_font", 0)) or base_font * 0.95,
        ncols=int(settings.get("legend_columns", 1)),
        labelspacing=float(settings.get("legend_labelspacing", 0.4)),
        columnspacing=float(settings.get("legend_columnspacing", 1)),
        handlelength=float(settings.get("legend_handlelength", 1.8)),
        borderpad=float(settings.get("legend_borderpad", 0.4)),
        markerscale=float(settings.get("legend_markerscale", 1)),
        frameon=settings.get("legend_frame", True),
        framealpha=float(settings.get("legend_opacity", 1)),
        title=settings.get("legend_title", ""),
        title_fontsize=float(settings.get("legend_font", 0)) or base_font * 0.95,
        fancybox=False,
        edgecolor="black",
    )


def draw_legend(owner, handles, labels, settings, font, shared=False):
    placement = settings.get("legend_placement", "Inside")
    if placement == "Hidden" or not handles:
        return None
    opts = options(settings, font)
    if placement == "Custom":
        try:
            x, y = float(settings["legend_x"]), float(settings["legend_y"])
        except (ValueError, KeyError):
            raise ValueError("Custom legend position needs numeric X and Y coordinates.") from None
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("Legend coordinates must be finite.")
        opts.update(
            loc="lower left",
            bbox_to_anchor=(x, y),
            bbox_transform=owner.transFigure if shared else owner.transAxes,
            borderaxespad=0,
        )
    elif shared:
        opts["loc"] = {
            "Outside right": "outside right center",
            "Outside below": "outside lower center",
            "Inside": "upper right",
        }.get(placement, "outside lower center")
    elif placement == "Outside right":
        opts.update(loc="upper left", bbox_to_anchor=(1.02, 1))
    elif placement == "Outside below":
        opts.update(loc="upper center", bbox_to_anchor=(0.5, -0.16))
    else:
        opts["loc"] = settings.get("legend_loc", "best")
    return owner.legend(handles, labels, **opts)


def handle_style(handle):
    if hasattr(handle, "lines"):
        handle = handle.lines[0]
    elif hasattr(handle, "patches") and handle.patches:
        handle = handle.patches[0]
    style = []
    for method in (
        "get_color",
        "get_facecolor",
        "get_marker",
        "get_linestyle",
        "get_linewidth",
        "get_markersize",
        "get_alpha",
    ):
        if hasattr(handle, method):
            value = getattr(handle, method)()
            if method in ("get_color", "get_facecolor"):
                try:
                    value = to_rgba(value)
                except (ValueError, TypeError):
                    value = str(value)
            style.append(str(value))
    return type(handle).__name__, tuple(style)


def shared_entries(entries):
    """Merge matching labels/styles; qualify equal labels with different styles."""
    unique = {}
    for handles, labels, name in entries:
        for handle, label in zip(handles, labels):
            unique.setdefault((label, handle_style(handle)), (handle, label, name))
    counts = Counter(label for _, label, _ in unique.values())
    handles = []
    labels = []
    for handle, label, name in unique.values():
        handles.append(handle)
        labels.append(f"{label} — {name}" if counts[label] > 1 else label)
    return handles, labels
