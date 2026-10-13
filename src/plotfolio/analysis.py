"""Recorded transformations and explicit replicate summaries; raw tables stay immutable."""

import copy

import numpy as np
from scipy.signal import savgol_filter
from scipy.stats import t

from .data import columns, numeric
from .expressions import expression


def strings(values):
    return [str(float(value)) if np.isfinite(value) else "" for value in values]


def derived(dataset, headers, rows, operation):
    result = copy.deepcopy(dataset)
    result.update(name=dataset["name"] + " · " + operation["kind"], headers=headers, rows=rows)
    result["history"] = [*dataset.get("history", []), operation]
    result["source"] = dataset.get("source", "")
    result["column_metadata"] = {
        header: copy.deepcopy(
            dataset.get("column_metadata", {}).get(
                header, {"role": "Unassigned", "unit": "", "label": header}
            )
        )
        for header in headers
    }
    return result


def transform(
    dataset,
    column,
    kind,
    output="processed",
    expression_text="",
    factor=1,
    baseline=0,
    window=5,
    degree=2,
    filter_text="",
):
    data = columns(dataset)
    if column not in data:
        raise ValueError("Choose a source column.")
    y = numeric(data[column])
    if kind == "Filter rows":
        mask = np.asarray(
            expression(
                filter_text,
                {key: numeric(value) for key, value in data.items() if key.isidentifier()},
                lambda key: numeric(data[key]),
            )
        )
        if mask.shape != y.shape or mask.dtype.kind != "b":
            raise ValueError('Filter must return one boolean per row, e.g. col("potential") > 0.')
        if not mask.any():
            raise ValueError("Filter would remove all rows.")
        return derived(
            dataset,
            list(dataset["headers"]),
            [row.copy() for row, keep in zip(dataset["rows"], mask) if keep],
            dict(kind=kind, expression=filter_text, removed=int((~mask).sum())),
        )
    if not output.strip() or output in data:
        raise ValueError("Choose a new, nonempty output column name.")
    if kind == "Calculated column":
        values = expression(
            expression_text,
            {key: numeric(value) for key, value in data.items() if key.isidentifier()},
            lambda key: numeric(data[key]),
        )
        values = np.broadcast_to(np.asarray(values, dtype=float), y.shape)
    elif kind == "Scale":
        if not np.isfinite(factor):
            raise ValueError("Scale factor must be finite.")
        values = y * factor
    elif kind == "Normalize maximum":
        maximum = np.nanmax(np.abs(y))
        if not np.isfinite(maximum) or maximum == 0:
            raise ValueError("Normalization needs a finite nonzero maximum magnitude.")
        values = y / maximum
    elif kind == "Normalize range":
        span = np.nanmax(y) - np.nanmin(y)
        if not np.isfinite(span) or span == 0:
            raise ValueError("Range normalization needs distinct finite values.")
        values = (y - np.nanmin(y)) / span
    elif kind == "Subtract baseline":
        if not np.isfinite(baseline):
            raise ValueError("Baseline must be finite.")
        values = y - baseline
    elif kind in ["Moving average", "Savitzky–Golay"]:
        if window < 3 or window % 2 == 0 or window > len(y):
            raise ValueError(
                "Smoothing window must be odd, at least 3, and no longer than the data."
            )
        if not np.isfinite(y).all():
            raise ValueError("Smoothing needs finite input; explicitly filter invalid rows first.")
        if kind == "Moving average":
            values = np.convolve(
                np.pad(y, window // 2, mode="edge"), np.ones(window) / window, mode="valid"
            )
        else:
            if not 0 <= degree < window:
                raise ValueError("Polynomial degree must be smaller than the smoothing window.")
            values = savgol_filter(y, window, degree)
    else:
        raise ValueError("Unknown transformation.")
    rows = [[*row, value] for row, value in zip(dataset["rows"], strings(values))]
    result = derived(
        dataset,
        [*dataset["headers"], output],
        rows,
        dict(
            kind=kind,
            column=column,
            output=output,
            expression=expression_text,
            factor=float(factor),
            baseline=float(baseline),
            window=int(window),
            degree=int(degree),
        ),
    )
    result["history"][-1]["nonfinite_output_rows"] = int((~np.isfinite(values)).sum())
    result["column_metadata"][output] = dict(
        role="Y",
        unit=""
        if kind.startswith("Normalize")
        else dataset.get("column_metadata", {}).get(column, {}).get("unit", ""),
        label=output,
    )
    return result


def summarize(dataset, group, value, center="Mean", uncertainty="SD", confidence=0.95):
    if center not in ["Mean", "Median"] or uncertainty not in [
        "None",
        "SD",
        "SEM",
        "Confidence interval",
    ]:
        raise ValueError("Choose a supported center and uncertainty definition.")
    if not 0 < confidence < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    if center == "Median" and uncertainty == "SEM":
        raise ValueError(
            "SEM here is defined for the mean. Use a bootstrap confidence interval for a median."
        )
    data = columns(dataset)
    groups = list(dict.fromkeys(data[group]))
    rows = []
    counts = {}
    rng = np.random.default_rng(0)
    for category in groups:
        if not category.strip():
            continue
        values = numeric([v for g, v in zip(data[group], data[value]) if g == category])
        values = values[np.isfinite(values)]
        if len(values) == 0:
            continue
        estimate = float(np.mean(values) if center == "Mean" else np.median(values))
        low = high = estimate
        if uncertainty != "None":
            if len(values) < 2:
                raise ValueError(
                    f"Group {category!r} needs at least two finite replicates for uncertainty."
                )
            sd = float(np.std(values, ddof=1))
            sem = sd / np.sqrt(len(values))
            if uncertainty in ["SD", "SEM"]:
                delta = sd if uncertainty == "SD" else sem
                low, high = estimate - delta, estimate + delta
            elif center == "Mean":
                delta = float(t.ppf((1 + confidence) / 2, len(values) - 1)) * sem
                low, high = estimate - delta, estimate + delta
            else:
                # Deterministic percentile bootstrap, bounded working memory.
                samples = np.concatenate(
                    [
                        np.median(rng.choice(values, (min(100, 2000 - start), len(values))), axis=1)
                        for start in range(0, 2000, 100)
                    ]
                )
                low, high = np.quantile(samples, [(1 - confidence) / 2, (1 + confidence) / 2])
        rows.append(
            [
                category,
                str(estimate),
                str(estimate - low),
                str(high - estimate),
                str(low),
                str(high),
                str(len(values)),
            ]
        )
        counts[category] = len(values)
    if not rows:
        raise ValueError("No groups with finite measurements.")
    headers = [group, "estimate", "error_low", "error_high", "lower", "upper", "n"]
    result = derived(
        dataset,
        headers,
        rows,
        dict(
            kind="Replicate summary",
            group=group,
            value=value,
            center=center,
            uncertainty=uncertainty,
            confidence=confidence,
            method="Student t interval for mean; 2000 percentile bootstrap samples (seed 0) for median",
            counts=counts,
            excluded_rows=len(dataset["rows"]) - sum(counts.values()),
        ),
    )

    result["column_metadata"]["estimate"] = dict(
        role="Y",
        unit=dataset.get("column_metadata", {}).get(value, {}).get("unit", ""),
        label=value,
    )
    return result


def replay_operation(dataset, operation):
    """Recompute one recorded operation against its explicitly selected parent table."""
    if operation["kind"] == "Replicate summary":
        return summarize(
            dataset,
            operation["group"],
            operation["value"],
            operation["center"],
            operation["uncertainty"],
            operation["confidence"],
        )
    if operation["kind"] == "Filter rows":
        # Filtering does not depend on the chosen value column.
        return transform(
            dataset, dataset["headers"][0], "Filter rows", filter_text=operation["expression"]
        )
    result = transform(
        dataset,
        operation["column"],
        operation["kind"],
        output=operation["output"],
        expression_text=operation.get("expression", ""),
        factor=operation.get("factor", 1),
        baseline=operation.get("baseline", 0),
        window=operation.get("window", 5),
        degree=operation.get("degree", 2),
    )
    if "output_unit" in operation:
        result["column_metadata"][operation["output"]]["unit"] = operation["output_unit"]
        result["history"][-1]["output_unit"] = operation["output_unit"]
    return result
