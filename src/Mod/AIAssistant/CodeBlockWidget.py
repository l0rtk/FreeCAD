# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Code Block Widget - Modern code display with syntax highlighting.
Cursor-inspired dark theme with blue accent.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from .SyntaxHighlighter import PythonHighlighter
from . import Theme


class CodeBlockWidget(QtWidgets.QFrame):
    """Widget for displaying code blocks with syntax highlighting."""

    runRequested = QtCore.Signal(str)
    copyRequested = QtCore.Signal(str)

    def __init__(self, code: str = "", language: str = "python", parent=None):
        super().__init__(parent)
        self._code = code
        self._language = language
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        self.setStyleSheet(f"""
            CodeBlockWidget {{
                background-color: {Theme.COLORS['code_bg']};
                border: 1px solid {Theme.COLORS['code_border']};
                border-radius: {Theme.RADIUS['lg']};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QtWidgets.QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.COLORS['code_header_bg']};
                border-top-left-radius: {Theme.RADIUS['lg']};
                border-top-right-radius: {Theme.RADIUS['lg']};
                border-bottom: 1px solid {Theme.COLORS['code_border']};
            }}
        """)
        header.setFixedHeight(38)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(14, 0, 10, 0)
        header_layout.setSpacing(8)

        # Language badge
        self._lang_label = QtWidgets.QLabel(self._language)
        self._lang_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['text_secondary']};
                font-size: {Theme.FONTS['size_sm']};
                font-weight: {Theme.FONTS['weight_medium']};
                background: transparent;
                padding: 2px 8px;
            }}
        """)
        header_layout.addWidget(self._lang_label)

        header_layout.addStretch()

        # Copy button - ghost style
        self._copy_btn = QtWidgets.QPushButton("Copy")
        self._copy_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._copy_btn.setFixedHeight(28)
        self._copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.COLORS['text_secondary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['sm']};
                padding: 0 12px;
                font-size: {Theme.FONTS['size_sm']};
                font-weight: {Theme.FONTS['weight_medium']};
            }}
            QPushButton:hover {{
                background-color: {Theme.COLORS['bg_hover']};
                border-color: {Theme.COLORS['border_hover']};
                color: {Theme.COLORS['text_primary']};
            }}
            QPushButton:pressed {{
                background-color: {Theme.COLORS['bg_tertiary']};
            }}
        """)
        self._copy_btn.clicked.connect(self._on_copy)
        header_layout.addWidget(self._copy_btn)

        # Run button (only for Python) - blue accent
        if self._language.lower() == "python":
            self._run_btn = QtWidgets.QPushButton("Run")
            self._run_btn.setCursor(QtCore.Qt.PointingHandCursor)
            self._run_btn.setFixedHeight(28)
            self._run_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.COLORS['accent_primary']};
                    color: #ffffff;
                    border: none;
                    border-radius: {Theme.RADIUS['sm']};
                    padding: 0 14px;
                    font-size: {Theme.FONTS['size_sm']};
                    font-weight: {Theme.FONTS['weight_medium']};
                }}
                QPushButton:hover {{
                    background-color: {Theme.COLORS['accent_primary_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.COLORS['accent_primary']};
                }}
            """)
            self._run_btn.clicked.connect(self._on_run)
            header_layout.addWidget(self._run_btn)

        layout.addWidget(header)

        # Code editor
        self._code_edit = QtWidgets.QPlainTextEdit()
        self._code_edit.setReadOnly(True)
        self._code_edit.setPlainText(self._code)
        self._code_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self._code_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {Theme.COLORS['code_bg']};
                color: {Theme.COLORS['code_text']};
                border: none;
                border-bottom-left-radius: {Theme.RADIUS['lg']};
                border-bottom-right-radius: {Theme.RADIUS['lg']};
                font-family: {Theme.FONTS['family_mono']};
                font-size: 13px;
                padding: 14px;
                selection-background-color: {Theme.COLORS['accent_primary']};
            }}
            QScrollBar:horizontal {{
                height: 8px;
                background: transparent;
                margin: 0 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {Theme.COLORS['scrollbar_handle']};
                border-radius: 4px;
                min-width: 40px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {Theme.COLORS['scrollbar_handle_hover']};
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: transparent;
                margin: 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.COLORS['scrollbar_handle']};
                border-radius: 4px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Theme.COLORS['scrollbar_handle_hover']};
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                width: 0px;
                height: 0px;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: none;
            }}
        """)

        # Calculate height based on content
        line_count = max(1, self._code.count('\n') + 1)
        line_height = 20
        content_height = min(line_count * line_height + 28, 350)
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
        self._copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.COLORS['accent_success']};
                color: #ffffff;
                border: none;
                border-radius: {Theme.RADIUS['sm']};
                padding: 0 12px;
                font-size: {Theme.FONTS['size_sm']};
                font-weight: {Theme.FONTS['weight_medium']};
            }}
        """)
        QtCore.QTimer.singleShot(2000, self._reset_copy_btn)
        self.copyRequested.emit(self._code)

    def _reset_copy_btn(self):
        """Reset copy button to default state."""
        self._copy_btn.setText("Copy")
        self._copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.COLORS['text_secondary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['sm']};
                padding: 0 12px;
                font-size: {Theme.FONTS['size_sm']};
                font-weight: {Theme.FONTS['weight_medium']};
            }}
            QPushButton:hover {{
                background-color: {Theme.COLORS['bg_hover']};
                border-color: {Theme.COLORS['border_hover']};
                color: {Theme.COLORS['text_primary']};
            }}
            QPushButton:pressed {{
                background-color: {Theme.COLORS['bg_tertiary']};
            }}
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
        content_height = min(line_count * line_height + 28, 350)
        self._code_edit.setMinimumHeight(content_height)
        self._code_edit.setMaximumHeight(content_height)

    def get_code(self) -> str:
        """Get the current code."""
        return self._code

    def set_run_disabled(self, disabled: bool):
        """Disable or enable the run button."""
        if hasattr(self, '_run_btn'):
            self._run_btn.setEnabled(not disabled)
            if disabled:
                self._run_btn.setText("Executed")
                self._run_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Theme.COLORS['bg_tertiary']};
                        color: {Theme.COLORS['text_muted']};
                        border: none;
                        border-radius: {Theme.RADIUS['sm']};
                        padding: 0 14px;
                        font-size: {Theme.FONTS['size_sm']};
                        font-weight: {Theme.FONTS['weight_medium']};
                    }}
                """)


class InlineCodeLabel(QtWidgets.QLabel):
    """Label styled for inline code."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {Theme.COLORS['bg_tertiary']};
                color: {Theme.COLORS['accent_error']};
                padding: 2px 6px;
                border-radius: 4px;
                font-family: {Theme.FONTS['family_mono']};
                font-size: {Theme.FONTS['size_sm']};
            }}
        """)
