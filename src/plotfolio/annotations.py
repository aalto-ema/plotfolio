"""Matplotlib annotation construction in data or axes coordinates."""

from matplotlib.patches import Ellipse, Rectangle


def add_annotation(ax, a):
    fraction = a["coords"] == "Axes fraction"
    transform = ax.transAxes if fraction else ax.transData
    common = dict(color=a["color"], alpha=float(a["alpha"]), zorder=int(a.get("zorder", 8)))
    x, y = float(a["x"]), float(a["y"])
    kind = a["kind"]
    if kind == "Text":
        ax.text(x, y, a["text"], transform=transform, fontsize=float(a["fontsize"]), **common)
    elif kind in ["Rectangle", "Ellipse"]:
        w, h = float(a["width"]), float(a["height"])
        if w <= 0 or h <= 0:
            raise ValueError("Annotation width and height must be positive.")
        patch = Rectangle((x, y), w, h) if kind == "Rectangle" else Ellipse((x, y), w, h)
        patch.set(
            transform=transform,
            facecolor=a["color"],
            edgecolor=a["color"],
            alpha=float(a["alpha"]),
            linewidth=float(a["linewidth"]),
            linestyle=a["linestyle"],
            zorder=int(a.get("zorder", 8)),
        )
        ax.add_patch(patch)
    elif kind == "Line":
        ax.plot(
            [x, float(a["x2"])],
            [y, float(a["y2"])],
            transform=transform,
            linewidth=float(a["linewidth"]),
            linestyle=a["linestyle"],
            **common,
        )
    else:
        ax.annotate(
            a["text"],
            xy=(float(a["x2"]), float(a["y2"])),
            xytext=(x, y),
            xycoords=transform,
            textcoords=transform,
            fontsize=float(a["fontsize"]),
            color=a["color"],
            alpha=float(a["alpha"]),
            zorder=int(a.get("zorder", 8)),
            arrowprops=dict(
                arrowstyle="->",
                color=a["color"],
                alpha=float(a["alpha"]),
                linewidth=float(a["linewidth"]),
                linestyle=a["linestyle"],
            ),
        )
