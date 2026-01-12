# SPDX-License-Identifier: LGPL-2.1-or-later
"""
AI Assistant Panel - Main dock widget for natural language CAD modeling.
Features a modern Cursor-like chat interface.
"""

import FreeCAD
import FreeCADGui
from PySide6 import QtWidgets, QtCore, QtGui

from . import LLMBackend
from . import ContextBuilder
from . import CodeExecutor
from .ChatWidget import ChatWidget
from .SessionManager import SessionManager


class LLMWorker(QtCore.QThread):
    """Background worker for LLM API calls."""
    finished = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, llm, user_input, context, conversation):
        super().__init__()
        self.llm = llm
        self.user_input = user_input
        self.context = context
        self.conversation = conversation

    def run(self):
        try:
            response = self.llm.chat(self.user_input, self.context, self.conversation)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))


class AIAssistantDockWidget(QtWidgets.QDockWidget):
    """Main AI Assistant dock widget with modern chat interface."""

    def __init__(self, parent=None):
        super().__init__("AI Assistant", parent)
        self.setObjectName("AIAssistantPanel")
        self.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea
        )

        self.llm = LLMBackend.LLMBackend()
        self.worker = None
        self.pending_input = None
        self._last_code = ""

        # Session manager for persisting conversations
        self.session_manager = SessionManager()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Build the UI."""
        main = QtWidgets.QWidget()
        main.setStyleSheet("background-color: #1a1a1a;")
        layout = QtWidgets.QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QtWidgets.QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-bottom: 1px solid #333;
            }
        """)
        header.setFixedHeight(40)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        title = QtWidgets.QLabel("AI Assistant")
        title.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Settings button
        self.settings_btn = QtWidgets.QToolButton()
        self.settings_btn.setText("...")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.settings_btn.setStyleSheet("""
            QToolButton {
                color: #888;
                background: transparent;
                border: none;
                font-size: 16px;
                padding: 4px 8px;
            }
            QToolButton:hover {
                color: #e0e0e0;
                background-color: #333;
                border-radius: 4px;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        self._setup_settings_menu()
        header_layout.addWidget(self.settings_btn)

        # Clear button
        clear_btn = QtWidgets.QToolButton()
        clear_btn.setText("Clear")
        clear_btn.setToolTip("Clear chat")
        clear_btn.setStyleSheet("""
            QToolButton {
                color: #888;
                background: transparent;
                border: none;
                font-size: 12px;
                padding: 4px 8px;
            }
            QToolButton:hover {
                color: #e0e0e0;
                background-color: #333;
                border-radius: 4px;
            }
        """)
        clear_btn.clicked.connect(self._on_clear)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # Chat widget
        self._chat = ChatWidget()
        layout.addWidget(self._chat, stretch=1)

        self.setWidget(main)
        self.setMinimumWidth(380)
        self.setMinimumHeight(500)

    def _setup_settings_menu(self):
        """Setup the settings dropdown menu."""
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
            QMenu::separator {
                height: 1px;
                background-color: #444;
                margin: 4px 8px;
            }
        """)

        self.context_action = menu.addAction("Include document context")
        self.context_action.setCheckable(True)
        self.context_action.setChecked(True)

        self.autorun_action = menu.addAction("Auto-run code")
        self.autorun_action.setCheckable(True)
        self.autorun_action.setChecked(False)

        self.streaming_action = menu.addAction("Streaming animation")
        self.streaming_action.setCheckable(True)
        self.streaming_action.setChecked(True)

        menu.addSeparator()

        clear_history = menu.addAction("Clear conversation history")
        clear_history.triggered.connect(self._clear_conversation)

        self.settings_btn.setMenu(menu)

    def _connect_signals(self):
        """Connect UI signals."""
        self._chat.messageSubmitted.connect(self._on_send)
        self._chat.runCodeRequested.connect(self._on_run_code)

        # Connect to session manager for auto-save
        self._chat._chat_list._model.message_added.connect(
            self.session_manager.save_message
        )

    def _on_send(self, user_input: str):
        """Handle message submission."""
        if not user_input:
            return

        # Prevent double-send
        if self.worker and self.worker.isRunning():
            return

        self.pending_input = user_input

        # Show typing indicator
        self._chat.show_typing()
        self._chat.set_input_enabled(False)

        # Build context if enabled
        context = ""
        if self.context_action.isChecked():
            context = ContextBuilder.build_context()

        # Get conversation history
        conversation = self._chat.get_conversation_history()

        # Start background worker
        self.worker = LLMWorker(self.llm, user_input, context, conversation)
        self.worker.finished.connect(self._on_response)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_response(self, response: str):
        """Handle successful LLM response."""
        # Hide typing indicator
        self._chat.hide_typing()
        self._chat.set_input_enabled(True)

        # Store the code for later execution
        self._last_code = response

        # Display response with or without streaming
        use_streaming = self.streaming_action.isChecked()
        self._chat.add_assistant_message(response, stream=use_streaming)

        self.pending_input = None

        # Auto-run if enabled
        if self.autorun_action.isChecked():
            # Delay to let streaming complete
            QtCore.QTimer.singleShot(500, lambda: self._on_run_code(response))

    def _on_error(self, error_msg: str):
        """Handle LLM error."""
        self._chat.hide_typing()
        self._chat.set_input_enabled(True)
        self._chat.add_error_message(error_msg)
        self.pending_input = None

    def _on_run_code(self, code: str):
        """Execute the provided code."""
        if not code.strip():
            return

        success, message = CodeExecutor.execute(code)

        if success:
            self._chat.add_system_message("Code executed successfully")
        else:
            self._chat.add_error_message(f"Execution error: {message}")

    def _on_clear(self):
        """Clear the chat UI."""
        self._chat.clear_chat()
        self._last_code = ""

    def _clear_conversation(self):
        """Clear conversation history and start new session."""
        self._on_clear()
        self.session_manager.clear_current_session()
        self._chat.add_system_message("Conversation cleared - new session started")
