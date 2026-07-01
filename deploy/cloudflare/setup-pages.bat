@echo off
cd /d "%~dp0\..\.."
echo Monster AI — Cloudflare Pages Setup
echo Developed by Suckbob
echo.

python scripts\setup_cloudflare_pages.py --config
echo.
echo Next: python scripts\setup_cloudflare_pages.py --login --deploy
echo Or set CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID then --deploy
pause