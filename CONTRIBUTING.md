# Contributing

Read AGENTS.md and docs/ARCHITECTURE.md. Install development dependencies with `python -m pip install -e '.[dev]'`.

Run `ruff check .`, `ruff format --check .`, `python -m unittest discover -s tests -p 'test_*.py'`, and the offscreen UI checks listed in AGENTS.md. Explain behavior changes and validation in pull requests. Include screenshots for UI changes and geometry checks for export changes. Keep example data synthetic, documented, and portable. Do not submit user data or proprietary fonts.
