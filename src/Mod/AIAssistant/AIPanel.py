# SPDX-License-Identifier: LGPL-2.1-or-later
"""
AI Assistant Panel - Main dock widget for natural language CAD modeling.
"""

import FreeCAD
import FreeCADGui
from PySide6 import QtWidgets, QtCore, QtGui

from . import LLMBackend
from . import ContextBuilder
from . import CodeExecutor


class AIAssistantDockWidget(QtWidgets.QDockWidget):
    """Main AI Assistant dock widget."""

    def __init__(self, parent=None):
        super().__init__("AI Assistant", parent)
        self.setObjectName("AIAssistantPanel")
        self.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea
        )

        self.llm = LLMBackend.LLMBackend()
        self.conversation = []

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Build the UI."""
        main = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(main)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("AI Assistant")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()

        self.settings_btn = QtWidgets.QToolButton()
        self.settings_btn.setText("...")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self._setup_settings_menu()
        header.addWidget(self.settings_btn)
        layout.addLayout(header)

        # Chat display
        self.chat_display = QtWidgets.QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(150)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                font-family: sans-serif;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.chat_display, stretch=2)

        # Code preview
        code_header = QtWidgets.QHBoxLayout()
        code_header.addWidget(QtWidgets.QLabel("Generated Code:"))
        self.copy_btn = QtWidgets.QPushButton("Copy")
        self.copy_btn.setMaximumWidth(60)
        self.copy_btn.clicked.connect(self._copy_code)
        code_header.addWidget(self.copy_btn)
        layout.addLayout(code_header)

        self.code_display = QtWidgets.QPlainTextEdit()
        self.code_display.setMinimumHeight(80)
        self.code_display.setStyleSheet("""
            QPlainTextEdit {
                font-family: monospace;
                font-size: 11px;
                background-color: #2d2d2d;
                color: #9cdcfe;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.code_display, stretch=1)

        # Input area
        input_label = QtWidgets.QLabel("What do you want to build?")
        layout.addWidget(input_label)

        self.input_field = QtWidgets.QLineEdit()
        self.input_field.setPlaceholderText("e.g., Create a box with a hole in the center...")
        self.input_field.setStyleSheet("padding: 6px;")
        layout.addWidget(self.input_field)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()

        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.setStyleSheet("padding: 6px 16px;")
        btn_layout.addWidget(self.send_btn)

        self.run_btn = QtWidgets.QPushButton("Run Code")
        self.run_btn.setEnabled(False)
        self.run_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton:hover:!disabled {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self.run_btn)

        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.setStyleSheet("padding: 6px 12px;")
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

        # Status bar
        self.status = QtWidgets.QLabel("Ready")
        self.status.setStyleSheet("color: palette(mid); font-size: 11px;")
        layout.addWidget(self.status)

        self.setWidget(main)
        self.setMinimumWidth(320)

    def _setup_settings_menu(self):
        """Setup the settings dropdown menu."""
        menu = QtWidgets.QMenu(self)

        self.context_action = menu.addAction("Include document context")
        self.context_action.setCheckable(True)
        self.context_action.setChecked(True)

        self.autorun_action = menu.addAction("Auto-run code")
        self.autorun_action.setCheckable(True)
        self.autorun_action.setChecked(False)

        menu.addSeparator()

        clear_history = menu.addAction("Clear conversation history")
        clear_history.triggered.connect(self._clear_conversation)

        self.settings_btn.setMenu(menu)

    def _connect_signals(self):
        """Connect UI signals."""
        self.input_field.returnPressed.connect(self._on_send)
        self.send_btn.clicked.connect(self._on_send)
        self.run_btn.clicked.connect(self._on_run)
        self.clear_btn.clicked.connect(self._on_clear)

    def _append_message(self, role: str, content: str, is_code: bool = False):
        """Append a message to the chat display."""
        if role == "You":
            color = "#61afef"  # Blue
        elif role == "AI":
            color = "#98c379"  # Green
        elif role == "Error":
            color = "#e06c75"  # Red
        else:
            color = "#abb2bf"  # Gray for System

        self.chat_display.append(
            f'<span style="color: {color}; font-weight: bold;">{role}:</span>'
        )
        if is_code:
            preview = content[:100] + "..." if len(content) > 100 else content
            escaped = preview.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            self.chat_display.append(
                f'<pre style="margin: 2px 0 8px 0; color: #abb2bf;">{escaped}</pre>'
            )
        else:
            self.chat_display.append(
                f'<p style="margin: 2px 0 8px 0; color: #d4d4d4;">{content}</p>'
            )

        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_send(self):
        """Handle send button click."""
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        self.input_field.clear()
        self._append_message("You", user_input)

        # Update UI state
        self.status.setText("Thinking...")
        self.send_btn.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        # Build context if enabled
        context = ""
        if self.context_action.isChecked():
            context = ContextBuilder.build_context()

        # Call LLM
        response = self.llm.chat(user_input, context, self.conversation)

        # Update conversation history
        self.conversation.append({"role": "user", "content": user_input})
        self.conversation.append({"role": "assistant", "content": response})

        # Keep only last 10 exchanges
        if len(self.conversation) > 20:
            self.conversation = self.conversation[-20:]

        # Display response
        self._append_message("AI", response, is_code=True)
        self.code_display.setPlainText(response)
        self.run_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status.setText("Code ready - review and click Run")

        # Auto-run if enabled
        if self.autorun_action.isChecked():
            self._on_run()

    def _on_run(self):
        """Execute the generated code."""
        code = self.code_display.toPlainText()
        if not code.strip():
            return

        self.status.setText("Executing...")
        QtWidgets.QApplication.processEvents()

        success, message = CodeExecutor.execute(code)

        if success:
            self.status.setText("Executed successfully")
            self.status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self._append_message("System", "Code executed successfully")
        else:
            self.status.setText(f"Error: {message[:50]}")
            self.status.setStyleSheet("color: #f44336; font-size: 11px;")
            self._append_message("Error", message)

        # Reset status color after delay
        QtCore.QTimer.singleShot(3000, self._reset_status_style)

    def _reset_status_style(self):
        self.status.setStyleSheet("color: palette(mid); font-size: 11px;")

    def _on_clear(self):
        """Clear the UI."""
        self.chat_display.clear()
        self.code_display.clear()
        self.run_btn.setEnabled(False)
        self.status.setText("Ready")
        self._reset_status_style()

    def _clear_conversation(self):
        """Clear conversation history."""
        self.conversation = []
        self._on_clear()
        self.status.setText("Conversation cleared")

    def _copy_code(self):
        """Copy code to clipboard."""
        code = self.code_display.toPlainText()
        if code:
            QtWidgets.QApplication.clipboard().setText(code)
            self.status.setText("Code copied to clipboard")
