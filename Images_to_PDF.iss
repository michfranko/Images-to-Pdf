[Setup]
AppName=Images to PDF
AppVersion=1.0.0
AppPublisher=Images to PDF
DefaultDirName={autopf}\Images to PDF
DefaultGroupName=Images to PDF
UninstallDisplayIcon={app}\Images_to_PDF.exe
OutputDir=installer
OutputBaseFilename=Images_to_PDF_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\Images_to_PDF.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Images to PDF"; Filename: "{app}\Images_to_PDF.exe"
Name: "{autodesktop}\Images to PDF"; Filename: "{app}\Images_to_PDF.exe"
