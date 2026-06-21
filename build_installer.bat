@echo off
setlocal
cd /d "%~dp0"

echo === Installing build tools ===
python -m pip uninstall -y pathlib 2>nul
python -m pip install --upgrade pip pyinstaller pillow -q
if errorlevel 1 exit /b 1

echo === Building HealthReminder.exe ===
python -m PyInstaller --noconfirm --clean HealthReminder.spec
if errorlevel 1 exit /b 1

set "ISCC="
for %%P in (
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
  "C:\Program Files\Inno Setup 6\ISCC.exe"
  "%~dp0tools\InnoSetup6\ISCC.exe"
) do if exist %%P set "ISCC=%%~P"

if not defined ISCC (
  echo === Downloading Inno Setup 6 ===
  if not exist "tools" mkdir tools
  if not exist "tools\InnoSetup6" mkdir "tools\InnoSetup6"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='https://jrsoftware.org/download.php/is.exe'; $o=Join-Path (Get-Location) 'tools\innosetup-installer.exe'; $dir=Join-Path (Get-Location) 'tools\InnoSetup6'; if (-not (Test-Path $o)) { Invoke-WebRequest -Uri $u -OutFile $o -UseBasicParsing }; Start-Process -FilePath $o -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES',(\"/DIR=$dir\") -Wait"
  set "ISCC=%~dp0tools\InnoSetup6\ISCC.exe"
)

if not exist "%ISCC%" (
  echo ERROR: Inno Setup compiler not found.
  exit /b 1
)

echo === Building installer ===
"%ISCC%" "%~dp0installer.iss"
if errorlevel 1 exit /b 1

echo.
echo Done: %~dp0HealthReminderSetup.exe
endlocal
