import sys
from gui import GcodeEditor
from PyQt6.QtWidgets import QApplication

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Get filename from arguments, otherwise prompt user or show error
    filename = sys.argv[1] if len(sys.argv) > 1 else None

    # Simple check if file exists
    import os
    if filename and not os.path.exists(filename):
        print(f"File not found: {filename}")
        sys.exit(1)

    editor = GcodeEditor(filename or 'test.gcode') # fallback
    editor.show()
    sys.exit(app.exec())
