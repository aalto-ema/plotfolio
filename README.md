# PlotFolio

A local Python desktop studio for publication-quality scientific figures, built with PySide6 and Matplotlib. Licensed under MIT. PlotFolio is an early-stage desktop application (0.3.0).

## Run

Python 3.10 or newer is required.

```sh
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install .
plotfolio
```

You can also run `python -m plotfolio` or `plotfolio project.plotfolio.json`.

### Run the local source

With the project's virtual environment activated, run `python run_plotfolio.py`.
The launcher uses the source in this folder, including your latest edits.
You can supply an optional
project filename: `python run_plotfolio.py examples/example.plotfolio.json`.

## Features

- CSV import and read-only data previews; projects embed data and images.
- Live figure, panel, series and annotation editing with undo/redo.
- Line, scatter, categorical, histogram, heatmap and image panels; image insets.
- Physical figure dimensions, grid ratios and spans, shared axes, explicit limits and ticks.
- Per-series colors, markers, legend labels, line styles, scaling and uncertainty columns.
- Inside/outside or shared legends, independent typography, columns and draggable exportable positions.
- Math labels, text, lines, arrows and translucent shapes.
- Uppercase/lowercase panel labels, optional parentheses and global or per-panel positions.
- Arial defaults and balanced, title-free synthetic CV, Nyquist, bar and heatmap examples.
- PDF, SVG, PNG and TIFF exports. Exact-size vector PDF manuscript previews, including placement into a copy of an existing manuscript PDF.
- ACS, RSC and Wiley starting templates. Check the individual journal requirements.

Arial must be installed on your computer; it is not distributed with PlotFolio. Matplotlib falls back to an installed font if unavailable. PDF dimensions are exact; on-screen zoom depends on display scaling.

See [the user guide](docs/USER_GUIDE.md), [architecture](docs/ARCHITECTURE.md) and [contributing](CONTRIBUTING.md). All supplied examples are synthetic and carry provenance. PlotFolio does not infer statistics or automatically average replicated values.

## Development and reporting issues

Clone [aalto-ema/plotfolio](https://github.com/aalto-ema/plotfolio) and install development dependencies with `python -m pip install -e '.[dev]'`. Report reproducible problems through GitHub Issues using synthetic data. This repository contains source code; standalone installers are not yet provided. The automated checks run on Linux; local UI checks have also run on macOS. Windows UI behavior has not yet been validated.
