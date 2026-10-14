"""Explicit uncertainty definitions and approximate fit prediction bands."""

import numpy as np
from scipy.stats import norm, t

DEFINITIONS = [
    "Unspecified",
    "Measurement SD",
    "Sample SD",
    "SEM",
    "Confidence interval",
    "Prediction interval",
    "Other",
]


def prediction_band(fit, noise_sd=None):
    if fit.get("lower") is None or fit.get("upper") is None:
        raise ValueError("Prediction bands need an identifiable parameter covariance.")
    if noise_sd is None:
        if fit.get("weighted"):
            raise ValueError(
                "Weighted fits need an explicit new-observation SD in plotted Y units."
            )
        noise_sd = float(np.sqrt(np.sum(np.square(fit["residuals"])) / fit["df"]))
    if not np.isfinite(noise_sd) or noise_sd < 0:
        raise ValueError("New-observation SD must be finite and nonnegative.")
    critical = (
        norm.ppf((1 + fit["confidence"]) / 2)
        if fit.get("absolute_sigma")
        else t.ppf((1 + fit["confidence"]) / 2, fit["df"])
    )
    mean_variance = ((np.asarray(fit["upper"]) - fit["lower"]) / (2 * critical)) ** 2
    delta = critical * np.sqrt(mean_variance + noise_sd**2)
    y = np.asarray(fit["y"])
    return dict(
        prediction_lower=(y - delta).tolist(),
        prediction_upper=(y + delta).tolist(),
        prediction_sd=noise_sd,
        prediction_method="Approximate delta-method interval for a new independent observation; Gaussian additive noise assumed.",
    )


def band_appearance(definition, color, alpha):
    if definition == "Prediction interval":
        return dict(color=color, alpha=alpha, hatch="//", edgecolor=color, linewidth=0.4)
    return dict(color=color, alpha=alpha, linewidth=0)
