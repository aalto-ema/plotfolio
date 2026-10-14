"""Stable editor targets attached to rendered artists; no numerical behavior."""


def descendants(value):
    if hasattr(value, "set_gid"):
        yield value
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from descendants(child)


def tag_targets(axes, panels):
    for ax, p in zip(axes, panels):
        ax.xaxis.label.set_gid("panel:xlabel")
        ax.yaxis.label.set_gid("panel:ylabel")
        ax.title.set_gid("panel:title")
        for text in ax.get_xticklabels():
            text.set_gid("panel:xticks")
        for text in ax.get_yticklabels():
            text.set_gid("panel:yticks")
        for container in ax.containers:
            label = container.get_label()
            index = next(
                (
                    i
                    for i, s in enumerate(p["series"])
                    if s.get("visible", True) and s["label"] == label
                ),
                None,
            )
            if index is not None:
                for artist in descendants(container):
                    if not artist.get_gid():
                        artist.set_gid(f"series:{index}")
        for artist in ax.lines:
            if not artist.get_gid():
                index = next(
                    (
                        i
                        for i, s in enumerate(p["series"])
                        if s.get("visible", True) and s["label"] == artist.get_label()
                    ),
                    None,
                )
                if index is not None:
                    if not artist.get_gid():
                        artist.set_gid(f"series:{index}")


def hit_target(axes, event):
    for index, ax in enumerate(axes):
        artists = [
            ax.xaxis.label,
            ax.yaxis.label,
            ax.title,
            *ax.texts,
            *ax.get_xticklabels(),
            *ax.get_yticklabels(),
            *ax.patches,
            *ax.lines,
            *ax.collections,
        ]
        for artist in artists:
            if artist in [*ax.lines, *ax.patches, *ax.collections] and event.inaxes is not ax:
                continue
            if artist.get_gid() and artist.get_visible() and artist.contains(event)[0]:
                return index, artist.get_gid()
    return None
