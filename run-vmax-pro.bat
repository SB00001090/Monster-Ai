@echo off
REM Monster AI — 本機 V Max Pro（RTX 4060 Ti 8GB 最佳化）
REM Developed by Suckbob | Monster AI
cd /d "%~dp0"
set MONSTER_GPU_PROFILE=vmax_pro
set MONSTER_HOST=127.0.0.1
set MONSTER_PORT=7860
echo.
echo  V MAX PRO — Local Monster AI
echo  GPU: RTX 4060 Ti ^| Profile: vmax_pro
echo  UI:  http://127.0.0.1:7860
echo  Mini: http://127.0.0.1:7860/mini-studio
echo.
call run.bat