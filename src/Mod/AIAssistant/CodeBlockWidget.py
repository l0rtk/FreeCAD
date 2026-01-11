# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Code Block Widget - Displays code with syntax highlighting and action buttons.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from .SyntaxHighlighter import PythonHighlighter


class CodeBlockWidget(QtWidgets.QFrame):
    """Widget for displaying code blocks with syntax highlighting."""

    runRequested = QtCore.Signal(str)  # Emits code to run
    copyRequested = QtCore.Signal(str)  # Emits code to copy

    STYLESHEET = """
        CodeBlockWidget {
            background-color: #1e1e1e;
            border: 1px solid #333;
            border-radius: 6px;
        }
        QPlainTextEdit {
            background-color: transparent;
            color: #abb2bf;
            border: none;
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 12px;
            selection-background-color: #3e4451;
        }
        QLabel#languageLabel {
            color: #636d83;
            font-size: 11px;
            padding: 4px 8px;
        }
        QPushButton {
            background-color: transparent;
            color: #636d83;
            border: none;
            padding: 4px 8px;
            font-size: 11px;
        }
        QPushButton:hover {
            color: #abb2bf;
            background-color: #2c313a;
            border-radius: 4px;
        }
        QPushButton:pressed {
            background-color: #3e4451;
        }
    """

    def __init__(self, code: str = "", language: str = "python", parent=None):
        super().__init__(parent)
        self._code = code
        self._language = language
        self._setup_ui()
        self.setStyleSheet(self.STYLESHEET)

    def _setup_ui(self):
        """Build the widget UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QtWidgets.QWidget()
        header.setFixedHeight(32)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 8, 0)
        header_layout.setSpacing(4)

        # Language label
        self._lang_label = QtWidgets.QLabel(self._language)
        self._lang_label.setObjectName("languageLabel")
        header_layout.addWidget(self._lang_label)

        header_layout.addStretch()

        # Copy button
        self._copy_btn = QtWidgets.QPushButton("Copy")
        self._copy_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._copy_btn.clicked.connect(self._on_copy)
        header_layout.addWidget(self._copy_btn)

        # Run button (only for Python)
        if self._language.lower() == "python":
            self._run_btn = QtWidgets.QPushButton("Run")
            self._run_btn.setCursor(QtCore.Qt.PointingHandCursor)
            self._run_btn.setStyleSheet("""
                QPushButton {
                    color: #98c379;
                }
                QPushButton:hover {
                    color: #98c379;
                    background-color: #2c313a;
                }
            """)
            self._run_btn.clicked.connect(self._on_run)
            header_layout.addWidget(self._run_btn)

        layout.addWidget(header)

        # Separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setStyleSheet("background-color: #333; max-height: 1px;")
        layout.addWidget(separator)

        # Code editor
        self._code_edit = QtWidgets.QPlainTextEdit()
        self._code_edit.setReadOnly(True)
        self._code_edit.setPlainText(self._code)
        self._code_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

        # Calculate height based on content
        line_count = max(1, self._code.count('\n') + 1)
        line_height = self._code_edit.fontMetrics().lineSpacing()
        content_height = min(line_count * line_height + 16, 300)  # Max 300px
        self._code_edit.setFixedHeight(content_height)

        # Syntax highlighting
        if self._language.lower() == "python":
            self._highlighter = PythonHighlighter(self._code_edit.document())

        layout.addWidget(self._code_edit)

    def _on_copy(self):
        """Copy code to clipboard."""
        QtWidgets.QApplication.clipboard().setText(self._code)
        self._copy_btn.setText("Copied!")
        QtCore.QTimer.singleShot(2000, lambda: self._copy_btn.setText("Copy"))
        self.copyRequested.emit(self._code)

    def _on_run(self):
        """Request code execution."""
        self.runRequested.emit(self._code)

    def set_code(self, code: str, language: str = None):
        """Update the code content."""
        self._code = code
        self._code_edit.setPlainText(code)

        if language:
            self._language = language
            self._lang_label.setText(language)

        # Recalculate height
        line_count = max(1, code.count('\n') + 1)
        line_height = self._code_edit.fontMetrics().lineSpacing()
        content_height = min(line_count * line_height + 16, 300)
        self._code_edit.setFixedHeight(content_height)

    def get_code(self) -> str:
        """Get the current code."""
        return self._code


class InlineCodeLabel(QtWidgets.QLabel):
    """Label styled for inline code."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                background-color: #2c313a;
                color: #e06c75;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
                font-size: 12px;
            }
        """)
