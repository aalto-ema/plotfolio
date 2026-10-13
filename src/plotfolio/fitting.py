"""Least-squares fits with residuals, covariance diagnostics and approximate bands."""

import warnings

import numpy as np
from scipy.optimize import OptimizeWarning, curve_fit
from scipy.stats import norm, t

from .expressions import expression

MODELS = {
    "Linear": ("a*x+b", ["a", "b"]),
    "Polynomial": ("", ["c0", "c1", "c2"]),
    "Exponential decay": ("a*exp(-x/tau)+c", ["a", "tau", "c"]),
    "Custom": ("a*x+b", ["a", "b"]),
}


def fit_curve(
    x,
    y,
    model="Linear",
    degree=2,
    formula="a*x+b",
    parameters=None,
    initial=None,
    lower=None,
    upper=None,
    sigma=None,
    xmin=None,
    xmax=None,
    confidence=0.95,
    absolute_sigma=False,
):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("Fit needs matching one-dimensional X and Y arrays.")
    if not 0 < confidence < 1:
        raise ValueError("Confidence level must be between 0 and 1.")
    finite = np.isfinite(x) & np.isfinite(y)
    if xmin is not None:
        finite &= x >= float(xmin)
    if xmax is not None:
        finite &= x <= float(xmax)
    if xmin is not None and xmax is not None and float(xmin) >= float(xmax):
        raise ValueError("Fit range minimum must be smaller than maximum.")
    if sigma is not None:
        sigma = np.asarray(sigma, dtype=float)
        if sigma.shape != y.shape:
            raise ValueError("Uncertainty column must match the data length.")
        # Invalid or zero uncertainty is an input error, not a silently dropped observation.
        if np.any(~np.isfinite(sigma[finite])) or np.any(sigma[finite] <= 0):
            raise ValueError("All uncertainties in the fit range must be finite and positive.")
        sigma = sigma[finite]
    x, y = x[finite], y[finite]
    if model == "Polynomial":
        if not 1 <= degree <= 8:
            raise ValueError("Polynomial degree must be 1–8.")
        parameters = [f"c{i}" for i in range(degree + 1)]
        formula = "+".join(f"c{i}*x**{i}" for i in range(degree + 1))
    elif model != "Custom":
        if model not in MODELS:
            raise ValueError("Unknown fit model.")
        formula, parameters = MODELS[model]
    else:
        parameters = parameters or ["a", "b"]
    if (
        not parameters
        or len(parameters) > 12
        or len(set(parameters)) != len(parameters)
        or any(not p.isidentifier() or p in ["x", "pi", "e"] for p in parameters)
    ):
        raise ValueError("Use 1–12 distinct parameter identifiers, excluding x, pi and e.")
    if len(x) <= len(parameters) or np.ptp(x) == 0:
        raise ValueError(
            "Fit needs more finite observations than parameters and distinct X values."
        )
    count = len(parameters)

    def function(xx, *params):
        output = expression(formula, dict(x=xx, **dict(zip(parameters, params))))
        return np.broadcast_to(np.asarray(output, dtype=float), np.asarray(xx).shape)

    if initial is None:
        if model == "Linear":
            initial = np.polyfit(x, y, 1).tolist()
        elif model == "Polynomial":
            initial = np.polynomial.polynomial.polyfit(x, y, degree).tolist()
        elif model == "Exponential decay":
            initial = [float(y.max() - y.min()), float(np.ptp(x) / 2), float(y.min())]
        else:
            initial = [1.0] * count
    lower = list(lower) if lower is not None else [-np.inf] * count
    upper = list(upper) if upper is not None else [np.inf] * count
    if model == "Exponential decay" and lower[1] == -np.inf:
        lower[1] = np.finfo(float).tiny
    if len(initial) != count or len(lower) != count or len(upper) != count:
        raise ValueError("Initial values and bounds must match the number of parameters.")
    if (
        not np.isfinite(initial).all()
        or any(a >= b for a, b in zip(lower, upper))
        or any(not a <= v <= b for v, a, b in zip(initial, lower, upper))
    ):
        raise ValueError("Initial values must be finite and inside valid lower/upper bounds.")
    if not np.isfinite(function(x, *initial)).all():
        raise ValueError("Model is not finite at the initial parameter values.")
    messages = []
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", OptimizeWarning)
        popt, pcov = curve_fit(
            function,
            x,
            y,
            p0=initial,
            bounds=(lower, upper),
            sigma=sigma,
            absolute_sigma=bool(absolute_sigma and sigma is not None),
            maxfev=20000,
        )
        messages.extend(str(w.message) for w in captured)
    predicted = function(x, *popt)
    residual = y - predicted
    if not np.isfinite(predicted).all():
        raise ValueError("Fitted model contains nonfinite predictions.")
    grid = np.linspace(float(x.min()), float(x.max()), 300)
    curve = function(grid, *popt)
    df = len(x) - count
    sse = float(residual @ residual)
    sst = float(np.sum((y - y.mean()) ** 2))
    stable = bool(np.isfinite(pcov).all() and (not np.any(pcov) or np.linalg.cond(pcov) < 1e12))
    if not stable:
        messages.append(
            "Parameter covariance is poorly determined; uncertainties and bands are unavailable."
        )
    if any(np.isclose(v, a) or np.isclose(v, b) for v, a, b in zip(popt, lower, upper)):
        messages.append("A parameter is at a bound; covariance-based intervals may be unreliable.")
    stderr = np.sqrt(np.maximum(np.diag(pcov), 0)) if stable else np.full(count, np.nan)
    band_low = band_high = None
    if stable:
        jac = []
        for i, value in enumerate(popt):
            step = 1e-5 * max(abs(value), 1)
            plus = popt.copy()
            minus = popt.copy()
            plus[i] += step
            minus[i] -= step
            jac.append((function(grid, *plus) - function(grid, *minus)) / (2 * step))
        jac = np.array(jac).T
        variance = np.einsum("ij,jk,ik->i", jac, pcov, jac)
        critical = (
            norm.ppf((1 + confidence) / 2)
            if sigma is not None and absolute_sigma
            else t.ppf((1 + confidence) / 2, df)
        )
        delta = critical * np.sqrt(np.maximum(variance, 0))
        if np.isfinite(delta).all():
            band_low = (curve - delta).tolist()
            band_high = (curve + delta).tolist()
    critical = (
        norm.ppf((1 + confidence) / 2)
        if sigma is not None and absolute_sigma
        else t.ppf((1 + confidence) / 2, df)
    )
    result = dict(
        model=model,
        formula=formula,
        parameters={
            name: dict(value=float(value), stderr=float(error) if np.isfinite(error) else None)
            for name, value, error in zip(parameters, popt, stderr)
        },
        covariance=pcov.tolist() if stable else None,
        n=len(x),
        excluded=int(len(finite) - finite.sum()),
        df=df,
        rmse=float(np.sqrt(sse / len(x))),
        r_squared=1 - sse / sst if sst > 0 else None,
        chi_square=float(np.sum((residual / sigma) ** 2)) if sigma is not None else None,
        reduced_chi_square=float(np.sum((residual / sigma) ** 2) / df)
        if sigma is not None
        else None,
        weighted=sigma is not None,
        absolute_sigma=bool(absolute_sigma and sigma is not None),
        confidence=confidence,
        band_method="Approximate mean-response interval from parameter covariance (delta method); not a prediction interval.",
        x=grid.tolist(),
        y=curve.tolist(),
        lower=band_low,
        upper=band_high,
        data_x=x.tolist(),
        data_y=y.tolist(),
        residuals=residual.tolist(),
        messages=messages,
        recipe=dict(
            model=model,
            degree=degree,
            formula=formula,
            parameters=parameters,
            initial=[float(v) for v in initial],
            lower=[float(v) if np.isfinite(v) else None for v in lower],
            upper=[float(v) if np.isfinite(v) else None for v in upper],
            xmin=xmin,
            xmax=xmax,
            confidence=confidence,
        ),
    )
    return result
