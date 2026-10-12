"""Project schema defaults. Data remain JSON-serializable and independent of Qt."""


def settings():
    return dict(
        width=180,
        height=120,
        font=10,
        family="Arial",
        title_scale=1.4,
        rows=1,
        cols=2,
        width_ratios="",
        height_ratios="",
        sharex=False,
        sharey=False,
        grid=True,
        legend=True,
        letters=True,
        label_case="lowercase",
        label_parentheses=False,
        label_x=-0.14,
        label_y=1.04,
        line_width=1.8,
        marker_size=5,
        tick_direction="in",
        colormap="Reference",
        dpi=600,
        template="Custom",
        columns="Double",
    )


def series(column, index=0):
    return dict(
        y=column,
        label=column,
        color="",
        marker="o",
        linestyle="solid",
        xfactor=1.0,
        yfactor=1.0,
        error="",
        visible=True,
        color_index=index,
    )


def panel(dataset="", x="", ys=(), row=0, col=0):
    return dict(
        name="Panel",
        dataset=dataset,
        x=x,
        kind="Line",
        title="",
        xlabel="",
        ylabel="",
        xscale="linear",
        yscale="linear",
        xmin="",
        xmax="",
        ymin="",
        ymax="",
        xticks="",
        yticks="",
        xcount=5,
        ycount=5,
        xdecimals=-1,
        ydecimals=-1,
        rotation=0,
        row=row,
        col=col,
        rowspan=1,
        colspan=1,
        series=[series(y, i) for i, y in enumerate(ys)],
        annotations=[],
        image="",
        image_name="",
        inset="",
        inset_name="",
        inset_bounds="0.58,0.58,0.38,0.38",
        label_x="",
        label_y="",
        box_aspect="",
        heatmap_label="",
        image_alpha=1.0,
        colorbar=True,
        category_colors=False,
        palette_offset=0,
        legend="Auto",
        legend_loc="best",
        line_order="Sort by X",
        aspect="auto",
    )


def document():
    return dict(version=2, settings=settings(), datasets={}, panels=[])


def annotation(kind="Text"):
    return dict(
        kind=kind,
        text=r"$n_{0}$",
        coords="Axes fraction",
        x=0.15,
        y=0.75,
        x2=0.4,
        y2=0.5,
        width=0.3,
        height=0.2,
        color="#E6AB02",
        alpha=0.25 if kind in ["Rectangle", "Ellipse"] else 1.0,
        linewidth=1.2,
        fontsize=10,
        linestyle="solid",
        zorder=8,
    )
