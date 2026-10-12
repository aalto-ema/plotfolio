"""Documented synthetic examples; never present synthetic data as measurements."""

import numpy as np

from .model import annotation, document, panel


def demo_document():
    """Illustrative CV and exact ideal-RC impedance; never measured sample data."""
    doc = document()
    doc["settings"].update(rows=2, cols=2, height=170, font=9, line_width=1.4)
    forward = np.linspace(-0.3, 0.7, 151)
    potential = np.concatenate([forward, forward[-2::-1]])
    sweep = np.concatenate([np.ones(len(forward)), -np.ones(len(forward) - 1)])
    currents = []
    for rate in [25, 50, 100]:
        peak = np.where(
            sweep > 0,
            70 * np.exp(-(((potential - 0.28) / 0.12) ** 2)),
            -65 * np.exp(-(((potential - 0.12) / 0.12) ** 2)),
        )
        capacitive = 8 * (rate / 50) * sweep * np.sin(np.pi * (potential + 0.3))
        currents.append(peak * np.sqrt(rate / 50) + capacitive)
    doc["datasets"]["cv"] = dict(
        name="Cyclic voltammetry · synthetic",
        headers=["potential_V", "current_25_uA_cm2", "current_50_uA_cm2", "current_100_uA_cm2"],
        rows=[
            [str(e), *(str(current[k]) for current in currents)] for k, e in enumerate(potential)
        ],
        source="Synthetic schematic CV: Gaussian oxidation/reduction peaks plus a capacitive background. Not a diffusion simulation or experimental measurement.",
    )
    frequency = np.logspace(5, -1, 81)
    rs, rct, cdl = 12.0, 180.0, 40e-6
    z = rs + rct / (1 + 1j * 2 * np.pi * frequency * rct * cdl)
    doc["datasets"]["eis"] = dict(
        name="Impedance · ideal RC model",
        headers=["frequency_Hz", "Zreal_ohm", "minus_Zimag_ohm", "Zmag_ohm", "phase_deg"],
        rows=[
            [str(f), str(zz.real), str(-zz.imag), str(abs(zz)), str(np.angle(zz, deg=True))]
            for f, zz in zip(frequency, z)
        ],
        source="Synthetic ideal circuit Z = Rs + Rct/(1 + j*2*pi*f*Rct*Cdl); Rs=12 ohm, Rct=180 ohm, Cdl=40 microfarad. No diffusion/Warburg element.",
    )
    cv = panel("cv", "potential_V", doc["datasets"]["cv"]["headers"][1:], 0, 0)
    cv.update(
        name="Cyclic voltammetry",
        title="Cyclic voltammetry",
        xlabel="Potential / V vs reference",
        ylabel=r"$j$ / $\mu$A cm$^{-2}$",
        line_order="CSV row order",
        xmin="-0.3",
        xmax="0.7",
        ymin="-120",
        ymax="130",
        xdecimals=1,
    )
    for ss, rate in zip(cv["series"], [25, 50, 100]):
        ss.update(label=f"{rate} mV/s", marker="None")
    a = annotation()
    a.update(text="Synthetic CV", x=0.05, y=0.07, color="#65768C", fontsize=7)
    cv["annotations"] = [a]
    nyquist = panel("eis", "Zreal_ohm", ["minus_Zimag_ohm"], 0, 1)
    nyquist.update(
        name="EIS · Nyquist",
        title="Nyquist",
        xlabel=r"$Z^{\prime}$ / $\Omega$",
        ylabel=r"$-Z^{\prime\prime}$ / $\Omega$",
        xmin="0",
        xmax="210",
        ymin="0",
        ymax="105",
        aspect="equal",
        legend="Hide",
        palette_offset=1,
        line_order="CSV row order",
    )
    nyquist["series"][0].update(label="Ideal RC model", marker="None")
    a = annotation()
    a.update(text=r"$R_s + (R_{ct} \parallel C_{dl})$", x=0.25, y=0.2, color="#65768C", fontsize=7)
    nyquist["annotations"] = [a]
    doc["datasets"]["activity"] = dict(
        name="Activity · synthetic",
        headers=["electrode", "current", "sem"],
        rows=[["Bare", "2.4", "0.2"], ["Coated", "5.8", "0.4"], ["Porous", "8.1", "0.5"]],
        source="Illustrative synthetic summary values; error bars represent illustrative SEM, not measured uncertainty.",
    )
    bars = panel("activity", "electrode", ["current"], 1, 0)
    bars.update(
        name="Electrode activity",
        kind="Bar",
        xlabel="Electrode",
        ylabel=r"$j$ / mA cm$^{-2}$",
        ymin="0",
        ymax="10",
        category_colors=True,
        legend="Hide",
    )
    bars["series"][0].update(error="sem", label="Current density")
    potentials = np.linspace(-0.2, 0.6, 17)
    rates = [10, 25, 50, 100, 200]
    doc["datasets"]["map"] = dict(
        name="Response map · synthetic",
        headers=["potential", *[str(v) for v in rates]],
        rows=[
            [
                f"{v:.2f}",
                *[str(np.exp(-(((v - 0.25) / 0.2) ** 2)) * np.sqrt(rate / 200)) for rate in rates],
            ]
            for v in potentials
        ],
        source="Synthetic normalized Gaussian response at five scan rates; illustrative only.",
    )
    heat = panel("map", "potential", [str(v) for v in rates], 1, 1)
    heat.update(
        name="Response heatmap",
        kind="Heatmap",
        xlabel="Scan rate / mV s$^{-1}$",
        ylabel="Potential / V",
        heatmap_label="Normalized response",
        legend="Hide",
    )
    nyquist.update(ymax="210")
    doc["panels"] = [cv, nyquist, bars, heat]
    for p in doc["panels"]:
        p.update(title="", box_aspect="1", annotations=[])

    return doc
