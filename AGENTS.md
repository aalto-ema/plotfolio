# Working on PlotFolio

PlotFolio is a local Python/Qt editor for publication-quality scientific figures.
Read `docs/ARCHITECTURE.md` and the relevant module before editing. The user's
instructions take precedence over this file.

## Working conventions

- Keep source code in `src/plotfolio`, regression tests in `tests`, and synthetic
  example data in `examples`. Do not commit virtual environments, caches,
  generated exports, user datasets, or absolute machine-specific paths.
- Preserve project compatibility. Add schema defaults and migrations whenever
  fields change; never silently reinterpret old data or overwrite source files.
- Keep numerical/data behavior in Qt-independent modules. UI forms should bind
  model properties rather than duplicate plotting calculations.
- Use the shared theme and widget components. Do not create a second color,
  spacing, or control-style system for a new dialog.
- All example data must be explicitly synthetic with documented provenance.
  Never invent experimental measurements, infer uncertainty definitions, or
  average replicates without a user-visible choice.
- Preserve acquisition order for CV and other trajectories. Keep equal axis
  units for Nyquist plots. Screen preview resizing must never change export size.
- Save projects with embedded data/images. Never execute project contents.
- Prefer targeted changes and meaningful tests. Do not delegate to other agents
  unless requested by the user or required by another applicable instruction.

## Validation

Install with `python -m pip install -e '.[dev]'`, then run:

```
ruff check .
ruff format --check .
python -m unittest discover -s tests -p 'test_*.py'
QT_QPA_PLATFORM=offscreen python tests/ui_smoke.py
QT_QPA_PLATFORM=offscreen python tests/ui_interactions.py
```

Use platform-appropriate environment-variable syntax on Windows. For UI/layout
changes, render a screenshot and inspect it. For PDF-preview changes, inspect
both the PDF geometry and a rasterized page. Run the relevant suites again only
when changes or unresolved failures justify it.

## Scope and releases

The user has authorized pushing completed, validated changes to the existing
`aalto-ema/plotfolio` GitHub repository by default. Commit and push project changes
after relevant checks pass, and report any push failure. Never commit user data,
credentials, virtual environments, or generated exports. This authorization does
not extend to publishing packages or creating repositories elsewhere.
Use `CHANGELOG.md` for user-visible changes. Read `CONTRIBUTING.md` for the public
contribution workflow. Keep guidance in this file specific to this project.
