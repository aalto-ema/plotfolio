"""Collect redistribution notices and record versions used in the bundle."""

import shutil
import sys
from importlib.metadata import distributions, version
from pathlib import Path

from PySide6.QtCore import qVersion


def main(destination):
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(__file__).with_name("licenses"), destination, dirs_exist_ok=True)
    shutil.copyfile("LICENSE", destination / "PlotFolio-LICENSE.txt")
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", destination / "Python-LICENSE.txt")
    packages = []
    for dist in sorted(distributions(), key=lambda item: item.name.lower()):
        packages.append(f"{dist.name}=={dist.version}")
        for item in dist.files or ():
            if ".." in item.parts or item.is_absolute():
                continue
            if not item.name.lower().startswith(
                ("license", "licence", "copying", "notice", "copyright")
            ):
                continue
            source = dist.locate_file(item)
            if source.is_file():
                target = destination / f"{dist.name}-{dist.version}" / item
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    (destination / "build-packages.txt").write_text("\n".join(packages) + "\n", encoding="utf-8")
    qt, pyside = qVersion(), version("PySide6")
    minor = qt.rsplit(".", 1)[0]
    (destination / "README.txt").write_text(
        f"""PlotFolio uses the MIT license. Bundled libraries retain their own licenses.

Qt {qt} and Qt for Python {pyside} are provided under LGPLv3. You may replace
the bundled Qt libraries and bindings with compatible modified versions in the
installed _internal directory and debug those modifications.

Qt corresponding source: https://download.qt.io/archive/qt/{minor}/{qt}/single/
Qt for Python corresponding source: https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v{pyside}
Qt third-party notices: https://doc.qt.io/qt-{minor}/licenses-used-in-qt.html
Qt PDF notices: https://doc.qt.io/qt-{minor}/qtpdf-licensing.html
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
