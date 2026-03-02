@echo off
REM Ralph Wiggum Stop-Hook Launcher for Windows
REM Runs the stop-hook and monitors until all tasks are complete

setlocal

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Detect Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
) else (
    where python3 >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python3"
    ) else (
        echo Error: Python not found in PATH
        exit /b 1
    )
)

echo.
echo 🍩 Ralph Wiggum Stop-Hook Launcher
echo ===================================
echo.
echo Base Directory: %SCRIPT_DIR%
echo.

REM Run the hook
"%PYTHON_CMD%" "%SCRIPT_DIR%ralph_stop_hook.py" --base-path "%SCRIPT_DIR%" --log-file "%SCRIPT_DIR%logs\ralph_hook.log"

if %errorlevel% equ 0 (
    echo.
    echo ✅ All tasks complete!
) else (
    echo.
    echo ⚠️ Hook interrupted
)

endlocal
