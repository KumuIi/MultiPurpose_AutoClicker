[Setup]
AppName=AutoClicker
AppVersion=1.0.0
AppPublisher=KumuIi
AppPublisherURL=https://github.com/KumuIi/MultiPurpose_AutoClicker
AppSupportURL=https://github.com/KumuIi/MultiPurpose_AutoClicker/issues
DefaultDirName={autopf}\AutoClicker
DefaultGroupName=AutoClicker
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=AutoClicker_Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\AutoClicker.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\AutoClicker.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AutoClicker";           Filename: "{app}\AutoClicker.exe"; IconFilename: "{app}\AutoClicker.exe"
Name: "{group}\Uninstall AutoClicker"; Filename: "{uninstallexe}"
Name: "{commondesktop}\AutoClicker";   Filename: "{app}\AutoClicker.exe"; IconFilename: "{app}\AutoClicker.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AutoClicker.exe"; \
    Description: "Launch AutoClicker"; \
    Flags: nowait postinstall skipifsilent
