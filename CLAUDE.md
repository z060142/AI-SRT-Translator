# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based SRT subtitle translation tool with a GUI interface that supports batch processing. The application translates English subtitles to Traditional Chinese using various AI translation APIs (OpenAI, Anthropic Claude, or custom APIs via OpenRouter).

## Main Commands

### Running the Application
```bash
python srt_translator.py
```

### Setting up Environment (Windows)
```bash
setup.bat
```
This creates a virtual environment using either `uv` (preferred) or `venv` and installs dependencies.

### Manual Environment Setup
```bash
# Create virtual environment
python -m venv srt_translator_env

# Activate environment (Windows)
srt_translator_env\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### Building Executable
```bash
cd build_tools
python build_safe_exe.py  # Recommended - includes security optimizations
# OR
python build_exe.py      # Basic build
```

## Architecture

### Core Components

1. **SRTEntry** (`srt_translator.py:17-26`) - Data structure representing a single subtitle entry with index, timestamps, original text, and translated text.

2. **SRTParser** (`srt_translator.py:28-61`) - Handles parsing SRT files into SRTEntry objects and converting back to SRT format.

3. **APITranslator** (`srt_translator.py:63-194`) - Manages translation API calls with support for:
   - OpenAI API format
   - Anthropic Claude API format  
   - Generic API endpoints
   - Automatic API type detection based on URL/model

4. **BatchTranslator** (`srt_translator.py:196-307`) - Optimizes translation by batching entries and maintaining context between translations.

5. **SRTTranslatorGUI** (`srt_translator.py:309-655`) - Main GUI application built with tkinter, featuring:
   - Drag-and-drop file support
   - Batch file processing
   - Progress tracking
   - Configuration persistence

### Key Features

- **Batch Processing**: Can process multiple SRT files in sequence
- **Context-Aware Translation**: Maintains context from previous subtitles for better translation consistency
- **Multiple API Support**: Compatible with OpenAI, Claude, and custom API endpoints
- **Configuration Persistence**: Saves API settings in `srt_translator_config.json`
- **Progress Tracking**: Real-time progress updates with detailed statistics
- **Error Handling**: Robust error handling with fallback to individual translation for failed batches

### Translation Process

1. Files are parsed into SRTEntry objects
2. Entries are grouped into batches (max 100 words per batch)
3. Each batch is translated with context from previous translations
4. Translated files are saved with `.zh.srt` suffix

### Configuration

API configuration is stored in `srt_translator_config.json` with:
- `api_url`: Translation API endpoint
- `model`: Model name/identifier  
- `api_key`: API authentication key

### Dependencies

- `requests>=2.25.1` - HTTP client for API calls
- `tkinterdnd2>=0.3.0` - Drag-and-drop support for GUI

### Build Tools

The `build_tools/` directory contains PyInstaller scripts for creating standalone executables:
- `build_safe_exe.py`: Recommended build script with security optimizations to reduce antivirus false positives
- `build_exe.py`: Basic build script
- `version_info.txt`: Windows version information for the executable