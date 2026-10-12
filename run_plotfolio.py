"""Launch the local PlotFolio source from VS Code or a terminal.

Select the project's .venv interpreter before running this file.
An optional project filename can be passed as a command-line argument.
"""

import sys
from pathlib import Path


def main():
    # Resolve source relative to this file, regardless of the working directory.
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    try:
        from plotfolio.app import main as run_app
    except ModuleNotFoundError as error:
        print(
            f"Missing dependency: {error.name}.\n"
            "Select the project's .venv Python interpreter in VS Code, or install "
            "dependencies with:\n"
            f'  "{sys.executable}" -m pip install -e "{root}"',
            file=sys.stderr,
        )
        return 1
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
