# Contributing

Read AGENTS.md and docs/ARCHITECTURE.md. Install development dependencies with `python -m pip install -e '.[dev]'`.

Run `ruff check .`, `ruff format --check .`, `python -m unittest discover -s tests -p 'test_*.py'`, and the offscreen UI checks listed in AGENTS.md. Explain behavior changes and validation in pull requests. Include screenshots for UI changes and geometry checks for export changes. Keep example data synthetic, documented, and portable. Do not submit user data or proprietary fonts.

To build a Windows installer, run the **Windows installer** workflow from GitHub Actions, selecting the branch or tag to build. Download the tested `PlotFolio-Windows-x64` artifact and attach its setup executable and SHA-256 checksum to a GitHub Release targeting the same commit. On Windows with x64 Python 3.12, PowerShell 7 and Inno Setup 6.3 or later, install the project and PyInstaller 6 and run `./packaging/windows/build.ps1`. The output is in `dist/installer`; do not commit it. Third-party notices are collected into the installed `licenses` directory.
