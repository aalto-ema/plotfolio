"""Physical panel alignment and normalized-coordinate snapping."""

import copy

from matplotlib.backends.backend_agg import FigureCanvasAgg

from .rendering import build_figure


def snap(value, step):
    if step <= 0:
        raise ValueError("Snap interval must be positive.")
    return round(value / step) * step


def align_panels(doc, indices, operation, reference=None):
    if len(indices) < 2:
        raise ValueError("Select at least two panels.")
    fig, axes, _ = build_figure(doc)
    FigureCanvasAgg(fig).draw()
    w, h = doc["settings"]["width"], doc["settings"]["height"]
    bounds = {i: axes[i].get_position() for i in indices}
    reference = reference if reference in indices else indices[0]
    result = copy.deepcopy(doc)
    delta = {i: [0.0, 0.0] for i in indices}
    if operation.startswith("Distribute"):
        if len(indices) < 3:
            raise ValueError("Distribution needs at least three panels.")
        horizontal = "horizontally" in operation
        axis = 0 if horizontal else 1
        dimension = w if horizontal else h

        def start(b):
            return b.x0 if horizontal else b.y0

        def end(b):
            return b.x1 if horizontal else b.y1

        def size(b):
            return b.width if horizontal else b.height

        ordered = sorted(indices, key=lambda i: start(bounds[i]))
        lo = start(bounds[ordered[0]])
        hi = end(bounds[ordered[-1]])
        gap = (hi - lo - sum(size(bounds[i]) for i in ordered)) / (len(ordered) - 1)
        if gap < 0:
            raise ValueError("The selected span is too small for nonoverlapping, equal gaps.")
        cursor = lo
        for i in ordered:
            delta[i][axis] = (cursor - start(bounds[i])) * dimension
            cursor += size(bounds[i]) + gap
    else:
        funcs = {
            "Left": lambda b: b.x0,
            "Right": lambda b: b.x1,
            "Horizontal centers": lambda b: (b.x0 + b.x1) / 2,
            "Bottom": lambda b: b.y0,
            "Top": lambda b: b.y1,
            "Vertical centers": lambda b: (b.y0 + b.y1) / 2,
        }
        horizontal = operation in ["Left", "Right", "Horizontal centers"]
        axis = 0 if horizontal else 1
        dimension = w if horizontal else h
        if operation not in funcs:
            raise ValueError("Choose an alignment operation.")
        target = funcs[operation](bounds[reference])
        for i in indices:
            delta[i][axis] = (target - funcs[operation](bounds[i])) * dimension
    for i, (dx, dy) in delta.items():
        p = result["panels"][i]
        p["offset_x"] = float(p.get("offset_x", 0)) + dx
        p["offset_y"] = float(p.get("offset_y", 0)) + dy
    test, _, _ = build_figure(result)
    FigureCanvasAgg(test).draw()
    return result
