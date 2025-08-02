@echo off
echo Setting up SRT translator environment...

where uv >nul 2>&1
if %errorlevel% == 0 (
    echo Using uv to create virtual environment...
    uv venv srt_translator_env
    call srt_translator_env\Scripts\activate.bat
    uv pip install requests tkinterdnd2
    echo.
    echo Setup complete! To start:
    echo srt_translator_env\Scripts\activate.bat ^&^& python srt_translator.py
) else (
    echo Using venv to create virtual environment...
    python -m venv srt_translator_env
    call srt_translator_env\Scripts\activate.bat
    pip install requests tkinterdnd2
    echo.
    echo Setup complete! To start:
    echo srt_translator_env\Scripts\activate.bat ^&^& python srt_translator.py
)

pause