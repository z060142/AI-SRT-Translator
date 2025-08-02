@echo off
echo Starting SRT Translator...

REM Check if virtual environment exists
if not exist "srt_translator_env\Scripts\activate.bat" (
    echo Virtual environment not found. Running setup first...
    call setup.bat
    if errorlevel 1 (
        echo Setup failed!
        pause
        exit /b 1
    )
)

REM Activate virtual environment and run the application
echo Activating virtual environment...
call srt_translator_env\Scripts\activate.bat

echo Starting SRT Translator application...
python srt_translator.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application exited with error!
    pause
)