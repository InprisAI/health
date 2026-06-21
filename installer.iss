#define AppVersion "1.0.0"

[Setup]
AppId={{A7C3E9F1-2B4D-4E8A-9F6C-010000000001}}
AppName=Health Reminder
AppVerName=Health Reminder {#AppVersion}
AppVersion={#AppVersion}
AppPublisher=Inpris
DefaultDirName={autopf}\HealthReminder
DefaultGroupName=Health Reminder
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=HealthReminderSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\HealthReminder.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Launch automatically when Windows starts"; GroupDescription: "Additional options:"; Flags: checkedonce

[Files]
Source: "dist\HealthReminder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Health Reminder"; Filename: "{app}\HealthReminder.exe"
Name: "{userstartup}\Health Reminder"; Filename: "{app}\HealthReminder.exe"; Tasks: startup

[Run]
Filename: "{app}\HealthReminder.exe"; Description: "Start Health Reminder now"; Flags: nowait postinstall skipifsilent
