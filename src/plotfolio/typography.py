"""Optional panel typography; zero sizes inherit figure-wide defaults."""

from matplotlib.ticker import EngFormatter, ScalarFormatter


def defaults():
    return dict(
        font_family="",
        xlabel_size=0.0,
        ylabel_size=0.0,
        xtick_size=0.0,
        ytick_size=0.0,
        title_size=0.0,
        panel_label_size=0.0,
        xformat="Auto",
        yformat="Auto",
    )


def apply_typography(ax, p, g):
    family = p.get("font_family") or g["family"]
    font = float(g["font"])
    ax.xaxis.label.set_fontsize(p.get("xlabel_size") or font * 1.12)
    ax.yaxis.label.set_fontsize(p.get("ylabel_size") or font * 1.12)
    ax.title.set_fontsize(p.get("title_size") or font * g["title_scale"])
    for text in [ax.xaxis.label, ax.yaxis.label, ax.title]:
        text.set_fontfamily(family)
    for axis in ["x", "y"]:
        ax.tick_params(axis=axis, labelsize=p.get(axis + "tick_size") or font)
        obj = getattr(ax, axis + "axis")
        for text in obj.get_ticklabels():
            text.set_fontfamily(family)
        obj.offsetText.set_fontfamily(family)
        obj.offsetText.set_fontsize(p.get(axis + "tick_size") or font)
        mode = p.get(axis + "format", "Auto")
        categorical = (
            p["kind"] in ["Image", "Heatmap"]
            or axis == "x"
            and (
                p["kind"] in ["Bar", "Box", "Violin", "Strip", "Heatmap"] or p.get("categorical_x")
            )
        )
        if not categorical and mode != "Auto":
            if mode == "Engineering":
                formatter = EngFormatter(
                    places=int(p[axis + "decimals"]) if int(p[axis + "decimals"]) >= 0 else None
                )
            else:
                formatter = ScalarFormatter(useOffset=False, useMathText=True)
                formatter.set_scientific(mode == "Scientific")
                if mode == "Scientific":
                    formatter.set_powerlimits((0, 0))
            obj.set_major_formatter(formatter)
    legend = ax.get_legend()
    if legend:
        for text in [*legend.get_texts(), legend.get_title()]:
            text.set_fontfamily(family)
