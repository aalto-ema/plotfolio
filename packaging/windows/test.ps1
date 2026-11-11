$ErrorActionPreference = 'Stop'
$installer = Get-ChildItem dist/installer/*-Setup.exe
$target = Join-Path $env:RUNNER_TEMP 'PlotFolio install test'
$result = Join-Path $env:RUNNER_TEMP 'plotfolio-smoke.txt'
$install = Start-Process $installer.FullName -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$target`""
) -Wait -PassThru
if ($install.ExitCode -ne 0) { throw "Setup failed: $($install.ExitCode)" }
$exe = Join-Path $target PlotFolio.exe
# An external Python or Qt installation must not mask missing bundle files.
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
foreach ($variable in 'PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM') {
    Remove-Item "Env:$variable" -ErrorAction SilentlyContinue
}
$app = Start-Process $exe -WorkingDirectory $target -ArgumentList @(
    '--installer-smoke-test', "`"$result`""
) -PassThru
if (!$app.WaitForExit(90000)) {
    $app.Kill()
    throw 'Installed application did not finish the smoke test'
}
$output = if (Test-Path $result) { Get-Content $result -Raw }
if ($app.ExitCode -ne 0 -or $output -ne 'PASS') {
    throw "Installed application failed ($($app.ExitCode)): $output"
}
$uninstall = Start-Process (Join-Path $target unins000.exe) -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'
) -Wait -PassThru
if ($uninstall.ExitCode -ne 0 -or (Test-Path $exe)) { throw 'Uninstall failed' }
Write-Output 'PASS: setup, native Qt startup, resources, PDF/SVG/PNG/TIFF exports, manuscript preview and uninstall'
