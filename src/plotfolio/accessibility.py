"""Approximate color previews in linear sRGB; never alter underlying data."""

import itertools

import numpy as np
from matplotlib.colors import to_rgb

from .rendering import color_for

# Machado, Oliveira & Fernandes (2009), severity 100 supplementary matrices.
# https://doi.org/10.1109/TVCG.2009.113
MATRICES = {
    "Protan": [
        [0.152286, 1.052583, -0.204868],
        [0.114503, 0.786281, 0.099216],
        [-0.003882, -0.048116, 1.051998],
    ],
    "Deutan": [
        [0.367322, 0.860646, -0.227968],
        [0.280085, 0.672501, 0.047413],
        [-0.011820, 0.042940, 0.968881],
    ],
    "Tritan": [
        [1.255528, -0.076749, -0.178779],
        [-0.078411, 0.930809, 0.147602],
        [0.004733, 0.691367, 0.303900],
    ],
}


def simulate(rgb, mode):
    rgb = np.asarray(rgb, dtype=float)
    if mode == "Original":
        return rgb.copy()
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    if mode == "Grayscale":
        luminance = linear @ np.array([0.2126, 0.7152, 0.0722])
        linear = np.repeat(luminance[..., None], 3, axis=-1)
    else:
        linear = linear @ np.asarray(MATRICES[mode]).T
    linear = np.clip(linear, 0, 1)
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)


def color_findings(doc, mode):
    findings = []
    for i, p in enumerate(doc["panels"]):
        if p["kind"] in ["Image", "Heatmap"]:
            continue
        series = [s for s in p["series"] if s.get("visible", True)]
        offset = int(p.get("palette_offset", 0))
        colors = [
            simulate(
                to_rgb(color_for(s, j + offset, len(series) + offset, doc["settings"]["colormap"])),
                mode,
            )
            for j, s in enumerate(series)
        ]
        for a, b in itertools.combinations(range(len(series)), 2):
            if np.linalg.norm(colors[a] - colors[b]) < 0.13:
                findings.append(
                    f"Panel {i + 1}: {series[a]['label']} / {series[b]['label']} may be hard to distinguish. Use different line styles or markers."
                )
    return findings
