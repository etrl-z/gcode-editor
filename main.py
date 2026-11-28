import sys
import os
from gui import GcodeEditor
from PyQt6.QtWidgets import QApplication, QFileDialog

if __name__ == '__main__':
    app = QApplication(sys.argv)
    filename = sys.argv[1] if len(sys.argv) > 1 else None

    if filename and not os.path.exists(filename):
        filename = None

    if not filename:
        filename, _ = QFileDialog.getOpenFileName(
            None,
            "Open G-code File",
            "",
            "G-code Files (*.gcode *.nc *.txt);;All Files (*)",
        )
        if not filename:
            sys.exit(0)

    editor = GcodeEditor(filename)
    editor.show()
    sys.exit(app.exec())
