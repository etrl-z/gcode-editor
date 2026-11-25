import sys
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPlainTextEdit, QListWidget, QLabel, QMessageBox, QToolBar, QAbstractItemView, QWidget)
from PyQt6.QtGui import QAction, QPalette, QColor, QSyntaxHighlighter, QTextCharFormat, QFont, QPainter, QTextCursor
from PyQt6.QtCore import Qt, QSize, QRect
from parser import GcodeParser

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
        self.comment_format.setForeground(QColor("#4caf50"))
        self.x_format = QTextCharFormat()
        self.x_format.setForeground(QColor("#ff5252"))
        self.y_format = QTextCharFormat()
        self.y_format.setForeground(QColor("#ffeb3b"))
        self.z_format = QTextCharFormat()
        self.z_format.setForeground(QColor("#2196f3"))
        self.default_format = QTextCharFormat()
        self.default_format.setForeground(QColor("white"))

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
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.parser = GcodeParser(file_path)
        self.layers = self.parser.parse()

        with open(self.file_path, 'r') as f:
            self.original_content = f.read()

        self.initUI()
        self.highlighter = GcodeHighlighter(self.editor.document())

    def initUI(self):
        self.setWindowTitle(f'G-code Layer Editor - {self.file_path}')
        self.resize(1000, 700)

        toolbar = QToolBar("Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self.undo_action = QAction(self.style().standardIcon(self.style().StandardPixmap.SP_ArrowBack), "&Annulla", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(lambda: self.editor.undo())
        toolbar.addAction(self.undo_action)

        self.redo_action = QAction(self.style().standardIcon(self.style().StandardPixmap.SP_ArrowForward), "&Ripeti", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(lambda: self.editor.redo())
        toolbar.addAction(self.redo_action)

        toolbar.addSeparator()

        btn_comment = QAction("Commenta selezione", self)
        btn_comment.triggered.connect(self.comment_selection)
        toolbar.addAction(btn_comment)

        btn_save = QAction("Salva", self)
        btn_save.triggered.connect(self.save_gcode)
        toolbar.addAction(btn_save)

        btn_reset = QAction("Ripristina dati iniziali", self)
        btn_reset.triggered.connect(self.reset_data)
        toolbar.addAction(btn_reset)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        left_layout = QVBoxLayout()
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for layer_index, line_number, z_height in self.layers:
            self.layer_list.addItem(f'Layer {layer_index} (Z={z_height}mm) - Linea {line_number}')

        self.layer_list.itemClicked.connect(self.jump_to_layer)
        left_layout.addWidget(QLabel("Navigazione Layer (Shift per multi-sel):"))
        left_layout.addWidget(self.layer_list)

        layout.addLayout(left_layout, 1)

        self.editor = CodeEditor()
        self.editor.setFont(QFont("Courier New", 10))
        editor_palette = QPalette()
        editor_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        editor_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        self.editor.setPalette(editor_palette)

        self.editor.setPlainText(self.original_content)
        self.editor.document().undoAvailable.connect(self.undo_action.setEnabled)
        self.editor.document().redoAvailable.connect(self.redo_action.setEnabled)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)
        layout.addWidget(self.editor, 3)

    def jump_to_layer(self, item):
        match = re.search(r'Linea (\d+)', item.text())
        if match:
            line_number = int(match.group(1)) - 1
            cursor = QTextCursor(self.editor.document().findBlockByNumber(line_number))
            self.editor.setTextCursor(cursor)
            self.editor.centerCursor()

    def get_line_number(self, item_text):
        match = re.search(r'Linea (\d+)', item_text)
        return int(match.group(1)) if match else None

    def comment_selection(self):
        selected_items = self.layer_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Attenzione", "Seleziona almeno un layer.")
            return

        selected_items.sort(key=lambda item: self.layer_list.row(item))
        start_line = self.get_line_number(selected_items[0].text()) - 1
        last_item_idx = self.layer_list.row(selected_items[-1])
        if last_item_idx + 1 < len(self.layers):
            end_line = self.layers[last_item_idx + 1][1] - 1
        else:
            end_line = self.editor.document().lineCount()

        old_cursor = self.editor.textCursor()
        scroll_value = self.editor.verticalScrollBar().value()

        # Usiamo il cursore per raggruppare l'azione
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()

        text = self.editor.toPlainText()
        lines = text.splitlines()

        for i in range(start_line, min(end_line, len(lines))):
            if i < len(lines) and not lines[i].startswith(';'):
                lines[i] = ';' + lines[i]

        self.editor.setPlainText('\n'.join(lines))
        cursor.endEditBlock()

        self.editor.setTextCursor(old_cursor)
        self.editor.verticalScrollBar().setValue(scroll_value)

    def save_gcode(self):
        try:
            with open(self.file_path, 'w') as f: f.write(self.editor.toPlainText())
            QMessageBox.information(self, "Salvataggio", "G-code salvato!")
        except Exception as e: QMessageBox.critical(self, "Errore", f"{e}")

    def reset_data(self):
        if QMessageBox.question(self, 'Conferma', 'Ripristinare?') == QMessageBox.StandardButton.Yes:
            self.editor.setPlainText(self.original_content)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    filename = 'test.gcode'
    if len(sys.argv) > 1: filename = sys.argv[1]
    editor = GcodeEditor(filename)
    editor.show()
    sys.exit(app.exec())
