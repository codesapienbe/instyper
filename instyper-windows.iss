
[Setup]
AppName=instyper
AppVersion=0.1.0
DefaultDirName={pf}\instyper
DefaultGroupName=instyper
OutputDir=dist
OutputBaseFilename=instyper-windows-setup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\instyper-windows.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\instyper"; Filename: "{app}\instyper-windows.exe"
Name: "{commondesktop}\instyper"; Filename: "{app}\instyper-windows.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons"; Flags: unchecked
