@echo off
REM Fix MediaTek/DOOGEE ADB driver (run as Administrator)
REM Developed by Suckbob | Monster AI Call Guard
cd /d "%~dp0..\.."
set INF=%CD%\data\callguard\usb_driver\usb_driver\android_winusb.inf
if not exist "%INF%" (
  echo [ERROR] Driver INF missing. Run fix-adb-driver.ps1 first.
  pause
  exit /b 1
)
echo Installing Google Android USB driver...
pnputil /add-driver "%INF%" /install
echo.
echo Now open Device Manager and update the DOOGEE device:
echo   USB Composite Device ^(VID_0E8D^) -^> Update driver -^> Android ADB Interface
echo.
pause