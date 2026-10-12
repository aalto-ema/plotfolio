"""Deterministic figure rendering, independent of the desktop interface."""

import math

import matplotlib as mpl
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter, LogLocator, MaxNLocator

from .annotations import add_annotation
from .constants import COLORS
from .data import columns, image_array, numeric, ratios


def color_for(s, index, total, cmap):
    if s.get("color"):
        return s["color"]
    if cmap == "Reference":
        return COLORS[index % len(COLORS)]
    mapping = mpl.colormaps[cmap]
    if cmap in ["tab10", "Set2", "Dark2"]:
        return mapping(index % mapping.N)
    return mapping(0.15 + 0.7 * index / max(1, total - 1))


def build_figure(doc):
    g = doc["settings"]
    panels = doc["panels"]
    notes = []
    width, height = float(g["width"]), float(g["height"])
    if not (30 <= width <= 500 and 30 <= height <= 500):
        raise ValueError("Figure dimensions must be 30–500 mm.")
    nr, nc = int(g["rows"]), int(g["cols"])
    if not (1 <= nr <= 8 and 1 <= nc <= 8):
        raise ValueError("Grid rows and columns must be 1–8.")
    font = float(g["font"])
    rc = {
        "font.family": g["family"],
        "font.size": font,
        "mathtext.fontset": "cm",
        "axes.labelsize": font * 1.12,
        "axes.titlesize": font * float(g["title_scale"]),
        "axes.titlepad": 10,
        "axes.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.direction": g["tick_direction"],
        "ytick.direction": g["tick_direction"],
        "xtick.major.width": 1.0,
        "ytick.major.width": 1.0,
        "legend.fontsize": font * 0.95,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
    with mpl.rc_context(rc):
        fig = Figure(figsize=(width / 25.4, height / 25.4), dpi=110, layout="constrained")
        if not panels:
            fig.text(
                0.5,
                0.5,
                "Add a panel to start your figure",
                ha="center",
                va="center",
                color="#6A778C",
            )
            return fig, [], notes
        gs = fig.add_gridspec(
            nr,
            nc,
            width_ratios=ratios(g["width_ratios"], nc),
            height_ratios=ratios(g["height_ratios"], nr),
        )
        occupied = set()
        axes = []
        shared = None
        signatures = {"x": None, "y": None}
        shared_options = {"x": None, "y": None}
        for i, p in enumerate(panels):
            r, c, rs, cs = (int(p[k]) for k in ["row", "col", "rowspan", "colspan"])
            cells = {(rr, cc) for rr in range(r, r + rs) for cc in range(c, c + cs)}
            if r < 0 or c < 0 or rs < 1 or cs < 1 or r + rs > nr or c + cs > nc:
                raise ValueError(f"Panel {i + 1} falls outside the grid.")
            if cells & occupied:
                raise ValueError(
                    f"Panel {i + 1} overlaps another panel. Change its row/column or span."
                )
            occupied |= cells
            shareable = p["kind"] not in ["Image", "Heatmap"]
            ax = fig.add_subplot(
                gs[r : r + rs, c : c + cs],
                sharex=shared if shareable and g["sharex"] else None,
                sharey=shared if shareable and g["sharey"] else None,
            )
            axes.append(ax)
            if shareable and shared is None:
                shared = ax
            ax.set_title(p["title"])
            if p["kind"] != "Image":
                ax.set_xscale(p["xscale"])
                ax.set_yscale(p["yscale"])
            categorical = p["kind"] in ["Bar", "Box", "Violin", "Strip"]
            categories = []
            ss = [s for s in p["series"] if s.get("visible", True)]
            if p["kind"] == "Image":
                if not p["image"]:
                    raise ValueError(f"Panel {i + 1}: choose a main image in the Panel tab.")
                ax.imshow(image_array(p["image"]), alpha=float(p["image_alpha"]))
                ax.set_axis_off()
            else:
                if p["dataset"] not in doc["datasets"]:
                    raise ValueError(f"Panel {i + 1}: select a dataset.")
                data = columns(doc["datasets"][p["dataset"]])
                if not ss:
                    raise ValueError(f"Panel {i + 1}: add at least one visible series.")
                if p["kind"] == "Heatmap":
                    matrix = np.column_stack(
                        [numeric(data[s["y"]]) * float(s["yfactor"]) for s in ss]
                    )
                    if not np.isfinite(matrix).any():
                        raise ValueError("Heatmap contains no numeric data.")
                    cmap = g["colormap"] if g["colormap"] != "Reference" else "viridis"
                    im = ax.imshow(np.ma.masked_invalid(matrix), aspect="auto", cmap=cmap)
                    ax.set_xticks(range(len(ss)), [s["label"] for s in ss])
                    if p["colorbar"]:
                        cax = ax.inset_axes([1.04, 0, 0.045, 1])
                        fig.colorbar(im, cax=cax, label=p.get("heatmap_label", ""))
                    if p["x"] in data:
                        positions = np.linspace(0, len(matrix) - 1, min(5, len(matrix))).astype(int)
                        ax.set_yticks(positions, [data[p["x"]][k] for k in positions])
                else:
                    if p["kind"] != "Histogram" and p["x"] not in data:
                        raise ValueError("Select an X column.")
                    if categorical:
                        categories = list(dict.fromkeys(v for v in data[p["x"]] if v.strip()))
                        if not categories:
                            raise ValueError("No nonempty categories.")
                        if p["xscale"] == "log":
                            raise ValueError("Categorical X axes cannot use a log scale.")
                    for j, s in enumerate(ss):
                        if s["y"] not in data:
                            raise ValueError(f"Missing column {s['y']}.")
                        xf, yf = float(s["xfactor"]), float(s["yfactor"])
                        if not math.isfinite(xf) or not math.isfinite(yf):
                            raise ValueError("Scale factors must be finite.")
                        y = numeric(data[s["y"]]) * yf
                        err = (
                            numeric(data[s["error"]]) * abs(yf)
                            if s["error"] and p["kind"] in ["Line", "Scatter", "Bar"]
                            else None
                        )
                        if err is not None and np.any(err[np.isfinite(err)] < 0):
                            raise ValueError("Uncertainties must be nonnegative.")
                        valid = np.isfinite(y)
                        if p["kind"] == "Histogram" and p["xscale"] == "log":
                            valid &= y > 0
                        if p["yscale"] == "log" and p["kind"] != "Histogram":
                            valid &= y > 0
                        if err is not None:
                            valid &= np.isfinite(err)
                        offset = int(p.get("palette_offset", 0))
                        color = color_for(s, j + offset, len(ss) + offset, g["colormap"])
                        label = s["label"]
                        marker = s["marker"] if s["marker"] != "None" else None
                        line = s["linestyle"]
                        lw = float(g["line_width"])
                        ms = float(g["marker_size"])
                        if categorical:
                            xraw = data[p["x"]]
                            valid &= np.array([bool(v.strip()) for v in xraw])
                            groups = [
                                y[valid & np.array([v == cat for v in xraw])] for cat in categories
                            ]
                            pos = np.arange(len(categories)) + (j - (len(ss) - 1) / 2) * (
                                0.75 / max(1, len(ss))
                            )
                            if p["kind"] == "Bar":
                                values = []
                                errors = []
                                for cat, group in zip(categories, groups):
                                    if len(group) > 1:
                                        raise ValueError(
                                            f"Bar category {cat!r} has replicates. Use Box/Violin/Strip or provide explicit summary rows."
                                        )
                                    values.append(group[0] if len(group) else np.nan)
                                    mask = valid & np.array([v == cat for v in xraw])
                                    errors.append(
                                        err[mask][0] if err is not None and mask.any() else np.nan
                                    )
                                ax.bar(
                                    pos,
                                    values,
                                    width=0.7 / max(1, len(ss)),
                                    yerr=errors if err is not None else None,
                                    color=[
                                        color_for(
                                            {"color": ""},
                                            k + int(p.get("palette_offset", 0)),
                                            len(categories) + int(p.get("palette_offset", 0)),
                                            g["colormap"],
                                        )
                                        for k in range(len(categories))
                                    ]
                                    if p.get("category_colors", False) and len(ss) == 1
                                    else color,
                                    edgecolor="black",
                                    linewidth=0.8,
                                    label=label,
                                    capsize=3,
                                )
                            elif p["kind"] == "Strip":
                                for at, group in zip(pos, groups):
                                    jitter = (
                                        np.linspace(-0.08, 0.08, len(group))
                                        if len(group) > 1
                                        else np.zeros(len(group))
                                    )
                                    ax.scatter(
                                        at + jitter,
                                        group,
                                        color=color,
                                        s=ms**2,
                                        marker=marker or "o",
                                        edgecolor="black",
                                        linewidth=0.6,
                                    )
                                ax.scatter([], [], color=color, s=ms**2, label=label)
                            else:
                                pairs = [
                                    (at, group) for at, group in zip(pos, groups) if len(group)
                                ]
                                if not pairs:
                                    raise ValueError(f"No valid values for {label}.")
                                positions = [at for at, _ in pairs]
                                groups = [group for _, group in pairs]
                                if p["kind"] == "Box":
                                    box = ax.boxplot(
                                        groups,
                                        positions=positions,
                                        widths=0.55 / max(1, len(ss)),
                                        patch_artist=True,
                                        manage_ticks=False,
                                    )
                                    for patch in box["boxes"]:
                                        patch.set_facecolor(color)
                                        patch.set_alpha(0.7)
                                else:
                                    if any(len(v) < 2 or np.ptp(v) == 0 for v in groups):
                                        raise ValueError(
                                            "Violin groups need at least two distinct numeric values."
                                        )
                                    parts = ax.violinplot(
                                        groups,
                                        positions=positions,
                                        widths=0.65 / max(1, len(ss)),
                                        showmedians=True,
                                    )
                                    for body in parts["bodies"]:
                                        body.set_facecolor(color)
                                        body.set_alpha(0.7)
                                ax.plot([], [], color=color, linewidth=4, label=label)
                            ax.set_xticks(range(len(categories)), categories)
                        elif p["kind"] == "Histogram":
                            if not valid.any():
                                raise ValueError(f"No valid values for {label}.")
                            ax.hist(
                                y[valid],
                                bins="auto",
                                color=color,
                                alpha=0.65,
                                label=label,
                                edgecolor="white",
                            )
                        else:
                            x = numeric(data[p["x"]]) * xf
                            valid &= np.isfinite(x)
                            if p["xscale"] == "log":
                                valid &= x > 0
                            if not valid.any():
                                raise ValueError(f"No valid points for {label}.")
                            xx, yy = x[valid], y[valid]
                            ee = err[valid] if err is not None else None
                            if (
                                p["kind"] == "Line"
                                and p.get("line_order", "Sort by X") == "Sort by X"
                            ):
                                order = np.argsort(xx, kind="stable")
                                xx, yy = xx[order], yy[order]
                                if ee is not None:
                                    ee = ee[order]
                            ax.errorbar(
                                xx,
                                yy,
                                yerr=ee,
                                color=color,
                                label=label,
                                marker=marker,
                                linestyle=line if p["kind"] == "Line" else "none",
                                linewidth=lw,
                                markersize=ms,
                                markeredgecolor="black",
                                markeredgewidth=0.75,
                                capsize=3,
                                elinewidth=0.9,
                            )
                        omitted = len(y) - int(valid.sum())
                        if omitted:
                            notes.append(f"{p['name']} / {label}: excluded {omitted} invalid rows.")
                        if s["error"] and p["kind"] in ["Box", "Violin", "Strip", "Histogram"]:
                            notes.append(
                                f"{p['name']}: uncertainty column is only displayed for Line, Scatter and Bar."
                            )
            if p["kind"] != "Image":
                ax.set_xlabel(
                    p["xlabel"] or (p["x"] if p["kind"] != "Histogram" else ss[0]["label"])
                )
                ax.set_ylabel(
                    p["ylabel"]
                    or (
                        "Count"
                        if p["kind"] == "Histogram"
                        else (ss[0]["label"] if len(ss) == 1 else "")
                    )
                )
                for axis in ["x", "y"]:
                    low, high = p[axis + "min"], p[axis + "max"]
                    lo = float(low) if str(low).strip() else None
                    hi = float(high) if str(high).strip() else None
                    if (lo is not None and not math.isfinite(lo)) or (
                        hi is not None and not math.isfinite(hi)
                    ):
                        raise ValueError("Axis limits must be finite.")
                    if lo is not None and hi is not None and lo >= hi:
                        raise ValueError("Axis minimum must be less than maximum.")
                    if p[axis + "scale"] == "log" and any(
                        v is not None and v <= 0 for v in [lo, hi]
                    ):
                        raise ValueError("Log-axis limits must be positive.")
                    ticks = p[axis + "ticks"].strip()
                    if shareable and g["share" + axis]:
                        sig = (p[axis + "scale"], tuple(categories) if axis == "x" else ())
                        opts = (
                            str(low),
                            str(high),
                            ticks,
                            int(p[axis + "count"]),
                            int(p[axis + "decimals"]),
                        )
                        if signatures[axis] is not None and signatures[axis] != sig:
                            raise ValueError(
                                f"Shared {axis.upper()} axes require matching scales and categories."
                            )
                        if shared_options[axis] is not None and shared_options[axis] != opts:
                            raise ValueError(
                                f"Shared {axis.upper()} axes require matching limits/ticks. Use “Copy axes to all”."
                            )
                        signatures[axis] = sig
                        shared_options[axis] = opts
                    obj = getattr(ax, axis + "axis")
                    if ticks:
                        values = [float(v) for v in ticks.split(",")]
                        if not all(math.isfinite(v) for v in values):
                            raise ValueError("Tick values must be finite.")
                        if p[axis + "scale"] == "log" and any(v <= 0 for v in values):
                            raise ValueError("Log ticks must be positive.")
                        getattr(ax, "set_" + axis + "ticks")(values)
                    elif not (p["kind"] == "Heatmap" or (axis == "x" and categorical)):
                        obj.set_major_locator(
                            LogLocator(numticks=int(p[axis + "count"]))
                            if p[axis + "scale"] == "log"
                            else MaxNLocator(nbins=max(1, int(p[axis + "count"]) - 1))
                        )
                    if int(p[axis + "decimals"]) >= 0 and not (axis == "x" and categorical):
                        obj.set_major_formatter(
                            FormatStrFormatter("%." + str(int(p[axis + "decimals"])) + "f")
                        )
                    if lo is not None or hi is not None:
                        getattr(ax, "set_" + axis + "lim")(lo, hi)
                ax.tick_params(axis="x", labelrotation=float(p["rotation"]))
                if g["grid"]:
                    ax.grid(color="#D9D9D9", alpha=0.7, linewidth=0.55)
                    ax.set_axisbelow(True)
                handles, labels = ax.get_legend_handles_labels()
                legend = p.get("legend", "Auto")
                show_legend = g["legend"] if legend == "Auto" else legend == "Show"
                if legend == "Auto" and p.get("category_colors") and len(ss) == 1:
                    show_legend = False
                if show_legend and handles:
                    ax.legend(
                        frameon=True,
                        fancybox=False,
                        framealpha=1,
                        edgecolor="black",
                        loc=p.get("legend_loc", "best"),
                    )
            if p.get("box_aspect", "") != "":
                ax.set_box_aspect(float(p["box_aspect"]))
            if p.get("aspect", "auto") == "equal":
                ax.set_aspect("equal", adjustable="box")
            if p["inset"]:
                bounds = [float(v) for v in p["inset_bounds"].split(",")]
                if (
                    len(bounds) != 4
                    or bounds[2] <= 0
                    or bounds[3] <= 0
                    or bounds[0] < 0
                    or bounds[1] < 0
                    or bounds[0] + bounds[2] > 1
                    or bounds[1] + bounds[3] > 1
                ):
                    raise ValueError("Inset bounds need x,y,width,height inside 0–1.")
                inset = ax.inset_axes(bounds)
                inset.imshow(image_array(p["inset"]), alpha=float(p["image_alpha"]))
                inset.set_axis_off()
            for a in p["annotations"]:
                add_annotation(ax, a)
            if g["letters"] and len(panels) > 1:
                label = chr(65 + i) if i < 26 else str(i + 1)
                if g.get("label_case") == "lowercase":
                    label = label.lower()
                if g.get("label_parentheses", False):
                    label = f"({label})"
                x = p.get("label_x", "")
                y = p.get("label_y", "")
                ax.text(
                    float(x) if str(x).strip() else g.get("label_x", -0.14),
                    float(y) if str(y).strip() else g.get("label_y", 1.04),
                    label,
                    transform=ax.transAxes,
                    fontsize=font * 1.3,
                    va="bottom",
                    fontweight="bold",
                )
        return fig, axes, notes
