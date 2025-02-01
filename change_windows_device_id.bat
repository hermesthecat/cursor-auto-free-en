@echo off
title Change Windows Device ID
color 0a
mode con: cols=120 lines=30
setlocal EnableDelayedExpansion

:: Administrator rights check
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo You must run this script as administrator!
    echo Please right-click the script and select "Run as administrator".
    pause
    exit /b 1
)

:: Security warning
echo WARNING: This process will change your system Device ID.
echo Before continuing:
echo - Close all applications
echo - Save your open work
echo - Temporarily disable antivirus software
echo.
choice /C YN /M "Do you want to continue"
if %errorlevel% neq 1 exit /b

:: Array for random hex characters
set "hex=0123456789ABCDEF"

:: Create new value for MachineGUID
set "newGUID="
for /L %%i in (1,1,32) do (
    set /a "rand=!random! %% 16"
    for %%j in (!rand!) do set "newGUID=!newGUID!!hex:~%%j,1!"
)

:: Split into 8-4-4-4-12 format
set "formattedGUID=%newGUID:~0,8%-%newGUID:~8,4%-%newGUID:~12,4%-%newGUID:~16,4%-%newGUID:~20,12%"

:: Create backup folder in current directory
set "BACKUP_DIR=%~dp0DeviceID_Backup_%date:~-4,4%%date:~-7,2%%date:~-10,2%"
mkdir "%BACKUP_DIR%" 2>nul

echo Backing up current settings...
reg export HKLM\SOFTWARE\Microsoft\Cryptography "%BACKUP_DIR%\Cryptography.reg" /y
reg export "HKLM\SYSTEM\CurrentControlSet\Control\IDConfigDB\Hardware Profiles\0001" "%BACKUP_DIR%\HWProfile.reg" /y

echo.
echo Creating new Device ID: %formattedGUID%
echo.

:: Stop critical services
echo Stopping services...
set "SERVICES=winmgmt Audiosrv AudioEndpointBuilder spooler TokenBroker WpnService"
for %%s in (%SERVICES%) do (
    net stop %%s /y >nul 2>&1
    if !errorlevel! neq 0 echo Could not stop %%s service
)

:: Registry changes
echo Making registry changes...
reg add "HKLM\SOFTWARE\Microsoft\Cryptography" /v MachineGuid /t REG_SZ /d "%formattedGUID%" /f
if %errorlevel% neq 0 goto :error

reg add "HKLM\SYSTEM\CurrentControlSet\Control\IDConfigDB\Hardware Profiles\0001" /v HwProfileGuid /t REG_SZ /d "{%formattedGUID%}" /f
if %errorlevel% neq 0 goto :error

:: Clear system cache
echo Clearing system cache...
echo y | rmdir /s "%SYSTEMDRIVE%\Windows\System32\DriverStore\FileRepository" 2>nul
echo y | rmdir /s "C:\ProgramData\Microsoft\Windows\DeviceMetadataCache" 2>nul
del /f /q "%SYSTEMDRIVE%\Windows\INF\*.PNF" 2>nul

:: Rebuild WMI repository
echo Rebuilding WMI repository...
cd /d %windir%\system32\wbem
for %%i in (*.dll) do (
    regsvr32 /s %%i
    if !errorlevel! neq 0 echo Could not register %%i
)
winmgmt /resetrepository
if %errorlevel% neq 0 echo Could not reset WMI repository

:: Restart services
echo Restarting services...
for %%s in (%SERVICES%) do (
    net start %%s >nul 2>&1
    if !errorlevel! neq 0 echo Could not start %%s service
)

:: Clear system cache
echo Performing final cleanup...
ipconfig /flushdns >nul 2>&1
wsreset >nul 2>&1
netsh winsock reset >nul 2>&1

echo.
echo Process completed successfully!
echo New Device ID: %formattedGUID%
echo.
echo Backups saved to: %BACKUP_DIR%
echo.
goto :end

:error
echo.
echo ERROR: A problem occurred during the process!
echo System will be restored using backups...
reg import "%BACKUP_DIR%\Cryptography.reg"
reg import "%BACKUP_DIR%\HWProfile.reg"

:: Try to restart services
for %%s in (%SERVICES%) do net start %%s >nul 2>&1

:end
echo.
echo If you experience any issues, you can restore using the backup files at:
echo %BACKUP_DIR%
pause 