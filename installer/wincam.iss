; Inno Setup script for WinCam.  Compile with:  iscc /DAppVersion=1.0.0 installer\wincam.iss
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6C1C6A7E-3E0B-4C6E-9B8B-2E4F0B9A1C11}
AppName=WinCam
AppVersion={#AppVersion}
AppVerName=WinCam {#AppVersion}
AppPublisher=WinCam
DefaultDirName={autopf}\WinCam
DefaultGroupName=WinCam
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=WinCam-{#AppVersion}-Setup
SetupIconFile=..\wincam\resources\wincam.ico
UninstallDisplayIcon={app}\WinCam.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequiredOverridesAllowed=dialog
ShowLanguageDialog=auto

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\WinCam\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\WinCam"; Filename: "{app}\WinCam.exe"
Name: "{group}\{cm:UninstallProgram,WinCam}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\WinCam"; Filename: "{app}\WinCam.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\WinCam.exe"; Description: "{cm:LaunchProgram,WinCam}"; Flags: nowait postinstall skipifsilent
