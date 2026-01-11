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

    def __init__(self, code: str = "", language: str = "python", parent=None):
        super().__init__(parent)
        self._code = code
        self._language = language
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        self.setStyleSheet("""
            CodeBlockWidget {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QtWidgets.QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #161b22;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid #30363d;
            }
        """)
        header.setFixedHeight(36)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 8, 0)
        header_layout.setSpacing(8)

        # Language label
        self._lang_label = QtWidgets.QLabel(self._language)
        self._lang_label.setStyleSheet("""
            QLabel {
                color: #8b949e;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
        """)
        header_layout.addWidget(self._lang_label)

        header_layout.addStretch()

        # Copy button
        self._copy_btn = QtWidgets.QPushButton("Copy")
        self._copy_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._copy_btn.setFixedHeight(26)
        self._copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
            }
            QPushButton:pressed {
                background-color: #484f58;
            }
        """)
        self._copy_btn.clicked.connect(self._on_copy)
        header_layout.addWidget(self._copy_btn)

        # Run button (only for Python)
        if self._language.lower() == "python":
            self._run_btn = QtWidgets.QPushButton("Run")
            self._run_btn.setCursor(QtCore.Qt.PointingHandCursor)
            self._run_btn.setFixedHeight(26)
            self._run_btn.setStyleSheet("""
                QPushButton {
                    background-color: #238636;
                    color: #ffffff;
                    border: 1px solid #2ea043;
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2ea043;
                }
                QPushButton:pressed {
                    background-color: #238636;
                }
            """)
            self._run_btn.clicked.connect(self._on_run)
            header_layout.addWidget(self._run_btn)

        layout.addWidget(header)

        # Code editor
        self._code_edit = QtWidgets.QPlainTextEdit()
        self._code_edit.setReadOnly(True)
        self._code_edit.setPlainText(self._code)
        self._code_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self._code_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', monospace;
                font-size: 13px;
                padding: 12px;
                selection-background-color: #264f78;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: #0d1117;
            }
            QScrollBar::handle:horizontal {
                background: #30363d;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #0d1117;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 4px;
            }
        """)

        # Calculate height based on content
        line_count = max(1, self._code.count('\n') + 1)
        line_height = 20  # Approximate line height
        content_height = min(line_count * line_height + 24, 350)  # Max 350px
        self._code_edit.setMinimumHeight(content_height)
        self._code_edit.setMaximumHeight(content_height)

        # Syntax highlighting
        if self._language.lower() == "python":
            self._highlighter = PythonHighlighter(self._code_edit.document())

        layout.addWidget(self._code_edit)

    def _on_copy(self):
        """Copy code to clipboard."""
        QtWidgets.QApplication.clipboard().setText(self._code)
        self._copy_btn.setText("Copied!")
        self._copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: 1px solid #2ea043;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        QtCore.QTimer.singleShot(2000, self._reset_copy_btn)
        self.copyRequested.emit(self._code)

    def _reset_copy_btn(self):
        """Reset copy button to default state."""
        self._copy_btn.setText("Copy")
        self._copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
            }
            QPushButton:pressed {
                background-color: #484f58;
            }
        """)

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
        line_height = 20
        content_height = min(line_count * line_height + 24, 350)
        self._code_edit.setMinimumHeight(content_height)
        self._code_edit.setMaximumHeight(content_height)

    def get_code(self) -> str:
        """Get the current code."""
        return self._code


class InlineCodeLabel(QtWidgets.QLabel):
    """Label styled for inline code."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                background-color: #343942;
                color: #e06c75;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
                font-size: 12px;
            }
        """)
