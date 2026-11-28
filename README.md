# G-code Layer Editor

A desktop G-code editor built with PyQt6. It helps you navigate, inspect, and edit individual print layers.

## Features

- Browse layers with their Z heights and jump to a layer in the editor.
- Select or check layers to comment, uncomment, or delete their G-code.
- See fully commented layers in gray.
- Use undo and redo, search, line numbers, and syntax highlighting for comments and X/Y/Z coordinates.
- Open recently used files.

## Run from source

Install PyQt6 in a virtual environment, then run the editor with a G-code file:

```powershell
python -m pip install PyQt6
python main.py "path\to\file.gcode"
```

If you run `main.py` without a file path, the app opens a file picker.

## Build the Windows executable

From the project directory, install PyInstaller and build a single-file Windows application:

```powershell
python -m pip install PyQt6 PyInstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name GCodeLayerEditor --icon mouse_icon.ico --add-data "mouse_icon.svg;." main.py
```

The executable will be created at `dist\GCodeLayerEditor.exe`.

## Install and add to "Open with"

After building, run the installer script from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

This installs the app for the current Windows user and registers it in **Open with** for `.gcode` files. Then right-click a G-code file and choose **Open with → G-code Layer Editor**.
