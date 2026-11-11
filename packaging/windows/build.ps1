$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

Push-Location (Join-Path $PSScriptRoot '../..')
try {
    $version = python -c 'from importlib.metadata import version; print(version("plotfolio"))'
    if ($version -notmatch '^\d+\.\d+\.\d+$') {
        throw "Expected an installed PlotFolio release version, got '$version'"
    }
    python -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name PlotFolio `
        --collect-data plotfolio --hidden-import matplotlib.backends.backend_qtagg `
        packaging/windows/launcher.py
    python packaging/windows/notices.py dist/PlotFolio/licenses

    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $iscc = if ($compiler) { $compiler.Source } else {
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    }
    & $iscc "/DPlotFolioVersion=$version" packaging/windows/PlotFolio.iss
    $installer = Get-Item "dist/installer/PlotFolio-$version-Windows-x64-Setup.exe"
    $hash = (Get-FileHash $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $($installer.Name)" | Set-Content -Encoding ascii "$($installer.FullName).sha256"
} finally {
    Pop-Location
}
