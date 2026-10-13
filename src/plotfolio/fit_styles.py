"""Fit appearance defaults and drawing, independent of numerical fit results."""

import math

from matplotlib.colors import is_color_like


def fit_style(fit):
    style = dict(
        color=fit.get("color") or "#333333",
        linestyle=fit.get("linestyle", "dashed"),
        linewidth=float(fit.get("linewidth", 1.3)),
        marker=fit.get("marker", "None"),
        markersize=float(fit.get("markersize", 4)),
        alpha=float(fit.get("alpha", 1)),
        band_color=fit.get("band_color", ""),
        band_alpha=float(fit.get("band_alpha", 0.18)),
        show_band=fit.get("show_band", True),
        visible=fit.get("visible", True),
    )
    if (
        not is_color_like(style["color"])
        or style["band_color"]
        and not is_color_like(style["band_color"])
    ):
        raise ValueError("Choose valid curve and confidence-band colors.")
    for key in ["linewidth", "markersize"]:
        if not math.isfinite(style[key]) or style[key] <= 0:
            raise ValueError("Line width and marker size must be positive finite numbers.")
    for key in ["alpha", "band_alpha"]:
        if not math.isfinite(style[key]) or not 0 <= style[key] <= 1:
            raise ValueError("Opacity must be between 0 and 1.")
    return style


def draw_fit(ax, fit):
    style = fit_style(fit)
    if not style["visible"]:
        return
    ax.plot(
        fit["x"],
        fit["y"],
        color=style["color"],
        linestyle=style["linestyle"],
        linewidth=style["linewidth"],
        marker=None if style["marker"] == "None" else style["marker"],
        markersize=style["markersize"],
        markevery=max(1, len(fit["x"]) // 20),
        alpha=style["alpha"],
        label=fit.get("label", fit["model"] + " fit"),
    )
    if style["show_band"] and fit.get("lower") is not None:
        ax.fill_between(
            fit["x"],
            fit["lower"],
            fit["upper"],
            color=style["band_color"] or style["color"],
            alpha=style["band_alpha"],
            linewidth=0,
        )
