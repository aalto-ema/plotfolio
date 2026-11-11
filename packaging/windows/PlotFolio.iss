[Setup]
AppId=PlotFolio
AppName=PlotFolio
AppVersion={#PlotFolioVersion}
AppPublisher=PlotFolio contributors
AppPublisherURL=https://github.com/aalto-ema/plotfolio
AppSupportURL=https://github.com/aalto-ema/plotfolio/issues
DefaultDirName={localappdata}\Programs\PlotFolio
DefaultGroupName=PlotFolio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\..\dist\installer
OutputBaseFilename=PlotFolio-{#PlotFolioVersion}-Windows-x64-Setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\PlotFolio.exe
WizardStyle=modern

[Files]
Source: "..\..\dist\PlotFolio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{group}\PlotFolio"; Filename: "{app}\PlotFolio.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\PlotFolio"; Filename: "{app}\PlotFolio.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\PlotFolio.exe"; Description: "Launch PlotFolio"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
