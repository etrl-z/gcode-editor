import sys
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPlainTextEdit, QListWidget, QListWidgetItem, QLabel, QMessageBox, QToolBar, QAbstractItemView, QFileDialog, QLineEdit)
from PyQt6.QtGui import QAction, QPalette, QColor, QSyntaxHighlighter, QTextCharFormat, QFont, QPainter, QTextCursor
from PyQt6.QtCore import Qt, QSize, QRect, QSettings
from pathlib import Path
from gcode_parser import GcodeParser

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = len(str(self.blockCount()))
        return 10 + self.fontMetrics().horizontalAdvance('9') * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy: self.line_number_area.scroll(0, dy)
        else: self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()): self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(50, 50, 50))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.GlobalColor.gray)
                painter.drawText(0, int(top), self.line_number_area.width(), self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

class GcodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.comment_format = QTextCharFormat()
        self.x_format = QTextCharFormat()
        self.y_format = QTextCharFormat()
        self.z_format = QTextCharFormat()
        self.default_format = QTextCharFormat()
        self.set_theme('dark')

    def set_theme(self, theme):
        colors = {
            'dark': {
                'text': '#ffffff', 'comment': '#81c784',
                'x': '#ff6b6b', 'y': '#ffd54f', 'z': '#64b5f6',
            },
            'light': {
                'text': '#202124', 'comment': '#26733a',
                'x': '#b3261e', 'y': '#806000', 'z': '#1456a0',
            },
        }[theme]
        self.default_format.setForeground(QColor(colors['text']))
        self.comment_format.setForeground(QColor(colors['comment']))
        self.x_format.setForeground(QColor(colors['x']))
        self.y_format.setForeground(QColor(colors['y']))
        self.z_format.setForeground(QColor(colors['z']))
        self.rehighlight()

    def highlightBlock(self, text):
        comment_match = re.search(r';.*', text)
        if comment_match:
            start = comment_match.start()
            self.setFormat(0, start, self.default_format)
            self.setFormat(start, len(text) - start, self.comment_format)
        else:
            self.setFormat(0, len(text), self.default_format)
            for match in re.finditer(r'([XYZ])([\d\.]+)', text):
                char = match.group(1)
                fmt = self.x_format if char == 'X' else (self.y_format if char == 'Y' else self.z_format)
                self.setFormat(match.start(), match.end() - match.start(), fmt)

class GcodeEditor(QMainWindow):
    MAX_RECENT_FILES = 10

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.settings = QSettings("GCodeEditor", "GCodeLayerEditor")
        self.recent_files = self.settings.value("recent_files", [], type=list)
        self.parser = GcodeParser(file_path)
        self.layers = self.parser.parse()

        with open(self.file_path, 'r') as f:
            self.original_content = f.read()

        self.initUI()
        self.highlighter = GcodeHighlighter(self.editor.document())
        self.add_recent_file(file_path)

    def initUI(self):
        from PyQt6.QtGui import QIcon

        self.setWindowTitle(f'G-code Layer Editor - {self.file_path}')
        self.setWindowIcon(QIcon(str(Path(__file__).with_name('mouse_icon.svg'))))
        self.resize(1000, 700)

        # Create editor first
        self.editor = CodeEditor()
        self.editor.setFont(QFont("Courier New", 10))
        editor_palette = QPalette()
        editor_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        editor_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        self.editor.setPalette(editor_palette)

        # Create layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        left_layout = QVBoxLayout()
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for layer_index, line_number, z_height in self.layers:
            item = QListWidgetItem(f'Layer {layer_index} (Z={z_height}mm) - Line {line_number}')
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.layer_list.addItem(item)

        self.layer_list.itemClicked.connect(self.jump_to_layer)
        left_layout.addWidget(QLabel("Layer Navigation (Shift for multi-sel):"))
        left_layout.addWidget(self.layer_list)

        layout.addLayout(left_layout, 1)

        layout.addWidget(self.editor, 3)

        # Menu Bar
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('&File')
        file_menu.addAction("New Project", self.new_project)
        file_menu.addAction("Open File(s)", self.open_file)
        self.recent_menu = file_menu.addMenu("Open Recent")
        self.recent_menu.aboutToShow.connect(self.open_recent)
        self.refresh_recent_menu()
        
        save_action = QAction("&Save Project", self)
        save_action.triggered.connect(self.save_gcode)
        file_menu.addAction(save_action)
        
        reload_action = QAction("&Reload Original Settings", self)
        reload_action.triggered.connect(self.reset_data)
        file_menu.addAction(reload_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("&Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit Menu
        edit_menu = menubar.addMenu('&Edit')
        
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self.undo_editor)
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self.redo_editor)
        edit_menu.addAction(self.redo_action)
        
        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.editor.selectAll)
        edit_menu.addAction(select_all_action)

        delete_action = QAction("&Delete", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_selected_layers)
        edit_menu.addAction(delete_action)
        edit_menu.addSeparator()
        
        comment_action = QAction("&Comment", self)
        comment_action.triggered.connect(self.comment_selection)
        edit_menu.addAction(comment_action)
        
        uncomment_action = QAction("&Uncomment", self)
        uncomment_action.triggered.connect(self.uncomment_selection)
        edit_menu.addAction(uncomment_action)

        # Settings Menu
        settings_menu = menubar.addMenu('&Settings')
        theme_menu = settings_menu.addMenu('Theme')
        theme_menu.addAction('Light', lambda: self.set_theme('light'))
        theme_menu.addAction('Dark', lambda: self.set_theme('dark'))

        # About Menu
        about_menu = menubar.addMenu('&About')
        about_action = QAction("&About", self)
        about_action.triggered.connect(lambda: QMessageBox.about(self, "About", "G-code Layer Editor v1.0"))
        about_menu.addAction(about_action)

        # Toolbar
        toolbar = QToolBar("Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        toolbar.addSeparator()
        toolbar.addAction(delete_action)
        toolbar.addSeparator()
        toolbar.addAction(comment_action)
        toolbar.addAction(uncomment_action)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.search_text)
        toolbar.addWidget(self.search_bar)

        self.editor.setPlainText(self.original_content)
        self.editor.document().undoAvailable.connect(self.undo_action.setEnabled)
        self.editor.document().redoAvailable.connect(self.redo_action.setEnabled)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)

    def delete_selected_layers(self):
        """Deletes each selected or checked layer through the next layer marker."""
        ranges = self.get_target_layer_ranges()
        if not ranges:
            QMessageBox.warning(self, "Warning", "Please select at least one layer.")
            return

        document = self.editor.document()
        positions = []
        for start_line, end_line in ranges:
            start_block = document.findBlockByNumber(start_line)
            if end_line < document.blockCount():
                end_position = document.findBlockByNumber(end_line).position()
            else:
                end_position = document.characterCount() - 1
            positions.append((start_block.position(), end_position))

        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        for start_position, end_position in reversed(positions):
            cursor.setPosition(start_position)
            cursor.setPosition(end_position, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        cursor.endEditBlock()

        self.refresh_layers_from_editor()
        self.clear_layer_checks()

    def refresh_layers_from_editor(self):
        """Rebuilds layer navigation from the current editor contents."""
        lines = self.editor.toPlainText().splitlines()
        self.layers = self.parser.parse_lines(lines)
        self.layer_list.clear()
        for layer_index, line_number, z_height in self.layers:
            item = QListWidgetItem(f'Layer {layer_index} (Z={z_height}mm) - Line {line_number}')
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.layer_list.addItem(item)
        self.refresh_layer_colors()

    def undo_editor(self):
        self.editor.undo()
        self.refresh_layers_from_editor()

    def redo_editor(self):
        self.editor.redo()
        self.refresh_layers_from_editor()

    def jump_to_layer(self, item):
        match = re.search(r'Layer (\d+)', item.text())
        if match:
            layer_index = int(match.group(1))
            search_str = f';LAYER:{layer_index}'
            
            # Search in the document
            cursor = self.editor.document().find(search_str)
            if not cursor.isNull():
                self.editor.setTextCursor(cursor)
                self.editor.centerCursor()

    def search_text(self, text):
        """Select the next occurrence of the search text in the editor."""
        if not text:
            cursor = self.editor.textCursor()
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)
            return

        cursor = self.editor.textCursor()
        match = self.editor.document().find(text, cursor)
        if match.isNull():
            match = self.editor.document().find(text, QTextCursor(self.editor.document()))
        if not match.isNull():
            self.editor.setTextCursor(match)
            self.editor.centerCursor()

    def get_line_number(self, item_text):
        match = re.search(r'Line (\d+)', item_text)
        return int(match.group(1)) if match else None

    def get_target_layer_ranges(self):
        """Return line ranges for selected or checked layers."""
        target_rows = {
            self.layer_list.row(item)
            for item in self.layer_list.selectedItems()
        }
        target_rows.update(
            row for row in range(self.layer_list.count())
            if self.layer_list.item(row).checkState() == Qt.CheckState.Checked
        )

        ranges = []
        for row in sorted(target_rows):
            start_line = self.get_line_number(self.layer_list.item(row).text())
            if start_line is None:
                continue
            end_line = (
                self.layers[row + 1][1] - 1
                if row + 1 < len(self.layers)
                else self.editor.document().lineCount()
            )
            ranges.append((start_line - 1, end_line))
        return ranges

    def clear_layer_checks(self):
        for row in range(self.layer_list.count()):
            self.layer_list.item(row).setCheckState(Qt.CheckState.Unchecked)

    def refresh_layer_colors(self):
        """Gray out layers whose non-empty lines are all comments."""
        lines = self.editor.toPlainText().splitlines()
        normal_color = self.layer_list.palette().color(QPalette.ColorRole.Text)
        commented_color = QColor("#808080")
        for row, layer in enumerate(self.layers):
            start = layer[1] - 1
            end = self.layers[row + 1][1] - 1 if row + 1 < len(self.layers) else len(lines)
            layer_lines = [line.strip() for line in lines[start:end] if line.strip()]
            is_commented = bool(layer_lines) and all(line.startswith(';') for line in layer_lines)
            self.layer_list.item(row).setForeground(commented_color if is_commented else normal_color)

    def comment_selection(self):
        ranges = self.get_target_layer_ranges()
        if not ranges:
            QMessageBox.warning(self, "Warning", "Please select at least one layer.")
            return

        old_cursor = self.editor.textCursor()
        scroll_value = self.editor.verticalScrollBar().value()
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        text = self.editor.toPlainText()
        lines = text.splitlines()

        for start_line, end_line in ranges:
            for i in range(start_line, min(end_line, len(lines))):
                if not lines[i].startswith(';'):
                    lines[i] = ';' + lines[i]

        self.editor.setPlainText('\n'.join(lines))
        cursor.endEditBlock()

        self.editor.setTextCursor(old_cursor)
        self.editor.verticalScrollBar().setValue(scroll_value)
        self.clear_layer_checks()
        self.refresh_layer_colors()

    def set_theme(self, theme):
        editor_palette = QPalette()
        if theme == 'dark':
            editor_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
            editor_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        else:
            editor_palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
            editor_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        self.editor.setPalette(editor_palette)
        if hasattr(self, 'highlighter'):
            self.highlighter.set_theme(theme)

    def uncomment_selection(self):
        ranges = self.get_target_layer_ranges()
        if not ranges:
            QMessageBox.warning(self, "Warning", "Please select at least one layer.")
            return

        old_cursor = self.editor.textCursor()
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        text = self.editor.toPlainText()
        lines = text.splitlines()

        for start_line, end_line in ranges:
            for i in range(start_line, min(end_line, len(lines))):
                if lines[i].startswith(';'):
                    lines[i] = lines[i][1:]

        self.editor.setPlainText('\n'.join(lines))
        cursor.endEditBlock()
        self.editor.setTextCursor(old_cursor)
        self.clear_layer_checks()
        self.refresh_layer_colors()

    def save_gcode(self):
        """Saves the current G-code content to the file."""
        if not self.file_path or self.file_path == "untitled.gcode":
            path, _ = QFileDialog.getSaveFileName(self, "Save G-code File", "", "G-code Files (*.gcode *.nc *.txt);;All Files (*)")
            if not path:
                return
            self.file_path = path
            self.setWindowTitle(f'G-code Layer Editor - {self.file_path}')

        try:
            with open(self.file_path, 'w') as f:
                f.write(self.editor.toPlainText())
            self.original_content = self.editor.toPlainText()
            self.add_recent_file(self.file_path)
            QMessageBox.information(self, "Success", "File saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def reset_data(self):
        """Resets the editor content to the original state."""
        if QMessageBox.question(self, 'Reset Data', 'Are you sure you want to reload the original file content? Unsaved changes will be lost.') == QMessageBox.StandardButton.Yes:
            self.editor.setPlainText(self.original_content)
            self.refresh_layers_from_editor()

    def new_project(self):
        """Creates a new empty G-code project."""
        if QMessageBox.question(self, 'New Project', 'Create new project? Unsaved changes will be lost.') == QMessageBox.StandardButton.Yes:
            self.file_path = "untitled.gcode"
            self.original_content = ""
            self.editor.setPlainText("")
            self.setWindowTitle(f'G-code Layer Editor - {self.file_path}')
            self.layer_list.clear()
            self.layers = []
            self.parser = GcodeParser(self.file_path)

    def open_file(self):
        """Opens a file dialog to select a G-code file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open G-code File", "", "G-code Files (*.gcode *.nc *.txt);;All Files (*)")
        if file_path:
            self.load_file(file_path)

    def open_recent(self):
        """Refreshes the recent files submenu."""
        self.refresh_recent_menu()

    def add_recent_file(self, file_path):
        """Adds an existing file to the persistent recent files list."""
        if not file_path or file_path == "untitled.gcode":
            return
        path = str(Path(file_path).expanduser().resolve())
        if not Path(path).is_file():
            return
        self.recent_files = [path] + [item for item in self.recent_files if item != path]
        self.recent_files = self.recent_files[:self.MAX_RECENT_FILES]
        self.settings.setValue("recent_files", self.recent_files)
        self.refresh_recent_menu()

    def refresh_recent_menu(self):
        """Rebuilds the menu and drops paths that no longer exist."""
        self.recent_menu.clear()
        self.recent_files = [path for path in self.recent_files if Path(path).is_file()]
        self.settings.setValue("recent_files", self.recent_files)
        if not self.recent_files:
            empty_action = self.recent_menu.addAction("(No recent files)")
            empty_action.setEnabled(False)
        else:
            for path in self.recent_files:
                action = self.recent_menu.addAction(path)
                action.setToolTip(path)
                action.triggered.connect(lambda checked=False, recent_path=path: self.load_file(recent_path))
            self.recent_menu.addSeparator()
            self.recent_menu.addAction("Clear Recent Files", self.clear_recent_files)

    def clear_recent_files(self):
        self.recent_files = []
        self.settings.remove("recent_files")
        self.refresh_recent_menu()

    def load_file(self, file_path):
        """Loads a G-code file and refreshes the UI."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
            self.refresh_recent_menu()
            return

        self.file_path = str(Path(file_path).resolve())
        self.original_content = content
        self.editor.setPlainText(self.original_content)
        self.setWindowTitle(f'G-code Layer Editor - {self.file_path}')
        
        # Re-parse layers
        self.parser = GcodeParser(self.file_path)
        self.layers = self.parser.parse()
        self.layer_list.clear()
        for layer_index, line_number, z_height in self.layers:
            item = QListWidgetItem(f'Layer {layer_index} (Z={z_height}mm) - Line {line_number}')
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.layer_list.addItem(item)

        self.add_recent_file(self.file_path)
        self.refresh_layer_colors()
        
        # Reset undo/redo
        self.editor.document().undoAvailable.connect(self.undo_action.setEnabled)
        self.editor.document().redoAvailable.connect(self.redo_action.setEnabled)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    filename = 'test.gcode'
    if len(sys.argv) > 1: filename = sys.argv[1]
    editor = GcodeEditor(filename)
    editor.show()
    sys.exit(app.exec())
