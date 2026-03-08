@echo off
chcp 65001 >nul 2>&1
title BLACKJACK 21
cd /d "%~dp0"

echo.
echo   ==========================================
echo       BLACKJACK 21
echo   ==========================================
echo.
echo   1  Terminal (консоль)
echo   2  GUI (Pygame)
echo.
set /p choice="  Выбор: "

if "%choice%"=="1" (
    python main.py terminal
) else if "%choice%"=="2" (
    python main.py gui
) else (
    echo   Неверный выбор
)
pause
