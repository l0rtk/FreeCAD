# SPDX-License-Identifier: LGPL-2.1-or-later
"""
AI Assistant Panel - Main dock widget for natural language CAD modeling.
Features a modern Cursor-like chat interface.
"""

import subprocess
from datetime import datetime

import FreeCAD
import FreeCADGui
from PySide6 import QtWidgets, QtCore, QtGui

FreeCAD.Console.PrintMessage("AIAssistant: AIPanel.py loaded (v2 with session title)\n")

from . import LLMBackend
from . import ContextBuilder
from . import CodeExecutor
from . import SnapshotManager
from . import ChangeDetector
from .ChatWidget import ChatWidget
from .SessionManager import SessionManager
from .PreviewManager import PreviewManager


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

        # Preview manager for 3D previews before execution
        self._preview_manager = PreviewManager()

        # Start console observer to capture errors for AI context
        ContextBuilder.start_console_observer()

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
        header.setFixedHeight(50)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        # Title area with main title and session subtitle
        title_area = QtWidgets.QWidget()
        title_area.setStyleSheet("background: transparent;")
        title_area_layout = QtWidgets.QVBoxLayout(title_area)
        title_area_layout.setContentsMargins(0, 4, 0, 4)
        title_area_layout.setSpacing(0)

        title = QtWidgets.QLabel("AI Assistant")
        title.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 14px;
                background: transparent;
            }
        """)
        title_area_layout.addWidget(title)

        # Session title label
        self._session_label = QtWidgets.QLabel("")
        self._session_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                background: transparent;
            }
        """)
        self._session_label.hide()  # Hidden until a session is loaded
        title_area_layout.addWidget(self._session_label)

        header_layout.addWidget(title_area)
        header_layout.addStretch()

        # Sessions button
        self.sessions_btn = QtWidgets.QToolButton()
        self.sessions_btn.setText("Sessions")
        self.sessions_btn.setToolTip("View and switch sessions")
        self.sessions_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.sessions_btn.setStyleSheet("""
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
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        header_layout.addWidget(self.sessions_btn)

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

        self.debug_action = menu.addAction("Debug mode")
        self.debug_action.setCheckable(True)
        self.debug_action.setChecked(False)
        self.debug_action.toggled.connect(self._on_debug_toggled)

        menu.addSeparator()

        clear_history = menu.addAction("Clear conversation history")
        clear_history.triggered.connect(self._clear_conversation)

        self.settings_btn.setMenu(menu)

    def _connect_signals(self):
        """Connect UI signals."""
        self._chat.messageSubmitted.connect(self._on_send)
        self._chat.runCodeRequested.connect(self._on_run_code)
        self._chat.previewApproved.connect(self._on_preview_approved)
        self._chat.previewCancelled.connect(self._on_preview_cancelled)

        # Connect to session manager for auto-save
        self._chat._chat_list._model.message_added.connect(
            self.session_manager.save_message
        )

        # Setup sessions menu - use aboutToShow to refresh before displaying
        self._sessions_menu = QtWidgets.QMenu(self)
        self._sessions_menu.aboutToShow.connect(self._refresh_sessions_menu)
        self.sessions_btn.setMenu(self._sessions_menu)

    def _refresh_sessions_menu(self):
        """Refresh the sessions dropdown menu."""
        menu = self._sessions_menu
        menu.clear()
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

        new_session = menu.addAction("+ New Session")
        new_session.triggered.connect(self._on_new_session)
        menu.addSeparator()

        # List recent sessions
        sessions = self.session_manager.list_sessions()[:10]
        current_id = self.session_manager.get_current_session_id()

        if sessions:
            for session in sessions:
                label = self._format_session_item(session)
                if session["session_id"] == current_id:
                    label = "● " + label
                action = menu.addAction(label)
                action.setData(session["session_id"])
                # Use default argument to capture session value
                action.triggered.connect(
                    lambda checked, sid=session["session_id"]: self._on_load_session(sid)
                )
        else:
            no_sessions = menu.addAction("No sessions yet")
            no_sessions.setEnabled(False)

        menu.addSeparator()
        open_folder = menu.addAction("Open sessions folder...")
        open_folder.triggered.connect(self._open_sessions_folder)

    def _format_session_item(self, session):
        """Format session for display in menu."""
        try:
            created = datetime.fromisoformat(session["created"])
            now = datetime.now()

            if created.date() == now.date():
                date_str = created.strftime("Today %H:%M")
            elif created.date() == (now.date().replace(day=now.day - 1)):
                date_str = created.strftime("Yesterday %H:%M")
            else:
                date_str = created.strftime("%b %d %H:%M")

            preview = session.get("preview", "")[:30]
            if preview:
                return f"{date_str} - {preview}"
            return date_str
        except Exception:
            return session["session_id"]

    def _on_new_session(self):
        """Start a new session."""
        self._on_clear()
        self.session_manager.clear_current_session()
        self._session_label.hide()
        self._chat.add_system_message("New session started")

    def _on_load_session(self, session_id):
        """Load a previous session."""
        messages = self.session_manager.load_session(session_id)
        self._chat.clear_chat()

        # Update session title in header
        self._update_session_title(session_id, messages)

        # Temporarily disconnect to avoid re-saving loaded messages
        try:
            self._chat._chat_list._model.message_added.disconnect(
                self.session_manager.save_message
            )
        except RuntimeError:
            pass  # Already disconnected

        show_debug = self.debug_action.isChecked()
        FreeCAD.Console.PrintMessage(f"AIAssistant: Loading session {session_id}, {len(messages)} messages, show_debug={show_debug}\n")

        for i, msg in enumerate(messages):
            has_debug = "debug_info" in msg and msg["debug_info"] is not None
            FreeCAD.Console.PrintMessage(f"AIAssistant: Loading msg {i}, role={msg.get('role')}, has_debug_info={has_debug}\n")
            self._chat.add_message_from_dict(msg, show_debug=show_debug)
            # Process events every 5 messages to keep UI responsive
            if i % 5 == 0:
                QtCore.QCoreApplication.processEvents()

        # Reconnect the signal
        self._chat._chat_list._model.message_added.connect(
            self.session_manager.save_message
        )

    def _update_session_title(self, session_id: str, messages: list):
        """Update the session title in the header."""
        FreeCAD.Console.PrintMessage(f"AIAssistant: _update_session_title called with session_id={session_id}\n")

        # Get session date from ID
        try:
            session_date = datetime.strptime(session_id, "%Y-%m-%d_%H-%M-%S")
            now = datetime.now()

            if session_date.date() == now.date():
                date_str = session_date.strftime("Today %H:%M")
            else:
                date_str = session_date.strftime("%b %d, %H:%M")
        except ValueError:
            date_str = session_id

        # Get preview from first user message
        preview = ""
        for msg in messages:
            if msg.get("role") == "user":
                text = msg.get("text", "")
                preview = text[:40] + "..." if len(text) > 40 else text
                break

        # Set label
        title_text = f"{date_str} - {preview}" if preview else date_str
        FreeCAD.Console.PrintMessage(f"AIAssistant: Setting session title to: {title_text}\n")
        self._session_label.setText(title_text)
        self._session_label.show()
        FreeCAD.Console.PrintMessage(f"AIAssistant: Session label visible={self._session_label.isVisible()}\n")

    def _open_sessions_folder(self):
        """Open the sessions folder in file manager."""
        try:
            subprocess.run(["xdg-open", str(self.session_manager._sessions_dir)])
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to open sessions folder: {e}\n")

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

        # Capture object snapshot for future context enrichment (unique timestamp per request)
        from datetime import datetime
        snapshot_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_path = SnapshotManager.save_snapshot(timestamp=snapshot_timestamp)

        # Link snapshot to session
        if snapshot_path:
            self.session_manager.add_snapshot_reference(snapshot_timestamp)

        # Get conversation history
        conversation = self._chat.get_conversation_history()

        # Start background worker
        self.worker = LLMWorker(self.llm, user_input, context, conversation)
        self.worker.finished.connect(self._on_response)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_response(self, response: str):
        """Handle successful LLM response - create preview."""
        # Hide typing indicator
        self._chat.hide_typing()
        self._chat.set_input_enabled(True)

        # Store the code for later execution
        self._last_code = response

        # Log full request/response for debugging
        self.session_manager.log_llm_request(
            user_message=self.pending_input or "",
            system_prompt=self.llm.last_system_prompt,
            context=self.llm.last_context,
            conversation_history=self.llm.last_conversation,
            response=response,
            model=self.llm.model,
            api_url=self.llm.api_url,
            duration_ms=self.llm.last_duration_ms,
            success=True
        )

        # Parse description and code from response
        description, code = self._parse_response(response)

        # If auto-run is enabled, skip preview and execute directly
        if self.autorun_action.isChecked():
            # Show traditional code block for auto-run mode
            self._show_traditional_response(response)
            QtCore.QTimer.singleShot(500, lambda: self._on_run_code(code))
            return

        # If no code found, show as regular message
        if not code.strip():
            self._show_traditional_response(response)
            self.pending_input = None
            return

        # Create preview in temp document
        FreeCAD.Console.PrintMessage(f"AIAssistant: Creating preview...\n")
        preview_success = self._preview_manager.create_preview(code)

        if preview_success:
            # Get preview summary
            preview_items = self._preview_manager.get_preview_summary()
            FreeCAD.Console.PrintMessage(f"AIAssistant: Preview created with {len(preview_items)} objects\n")

            # Show preview widget
            self._chat.add_preview_message(
                description=description or "I'll create the following objects:",
                preview_items=preview_items,
                code=code
            )
        else:
            # Preview failed - fall back to traditional code block
            FreeCAD.Console.PrintWarning("AIAssistant: Preview failed, showing code block\n")
            self._preview_manager.clear_preview()
            self._show_traditional_response(response)

        self.pending_input = None

    def _parse_response(self, response: str) -> tuple:
        """Parse LLM response to extract description and code.

        Returns:
            Tuple of (description, code)
        """
        import re

        # Try to find Python code block
        code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            # Description is everything before the code block
            description = response[:code_match.start()].strip()
            # Clean up description - remove markdown artifacts
            description = re.sub(r'\n+', ' ', description)
            description = description.strip()
            return (description, code)

        # Try to find any code block
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            description = response[:code_match.start()].strip()
            description = re.sub(r'\n+', ' ', description)
            return (description, code)

        # No code block found - might be pure code or pure text
        # Check if it looks like Python code
        if 'import FreeCAD' in response or 'Part.' in response or 'doc.addObject' in response:
            return ("", response.strip())

        # Pure text response
        return (response.strip(), "")

    def _show_traditional_response(self, response: str):
        """Show response as traditional code block (for backward compatibility)."""
        # Build debug info if debug mode enabled
        debug_info = None
        if self.debug_action.isChecked():
            debug_info = {
                "duration_ms": self.llm.last_duration_ms,
                "model": self.llm.model,
                "context_length": len(self.llm.last_context),
                "system_prompt": self.llm.last_system_prompt,
                "context": self.llm.last_context,
                "conversation_history": self.llm.last_conversation,
                "user_message": self.pending_input or "",
            }

        # Display response with or without streaming
        use_streaming = self.streaming_action.isChecked()
        self._chat.add_assistant_message(response, stream=use_streaming, debug_info=debug_info)

    def _on_error(self, error_msg: str):
        """Handle LLM error."""
        self._chat.hide_typing()
        self._chat.set_input_enabled(True)

        # Log failed request for debugging
        self.session_manager.log_llm_request(
            user_message=self.pending_input or "",
            system_prompt=self.llm.last_system_prompt,
            context=self.llm.last_context,
            conversation_history=self.llm.last_conversation,
            response="",
            model=self.llm.model,
            api_url=self.llm.api_url,
            duration_ms=self.llm.last_duration_ms,
            success=False,
            error=error_msg
        )

        self._chat.add_error_message(error_msg)
        self.pending_input = None

    def _on_preview_approved(self, code: str):
        """Handle user approval of preview - execute code for real."""
        FreeCAD.Console.PrintMessage("AIAssistant: Preview approved - executing code\n")

        # Clear the preview objects
        self._preview_manager.clear_preview()

        # Now execute the code for real and show changes
        self._on_run_code(code)

    def _on_preview_cancelled(self):
        """Handle user cancellation of preview."""
        FreeCAD.Console.PrintMessage("AIAssistant: Preview cancelled\n")

        # Clear the preview objects
        self._preview_manager.cancel()

        # Add a system message
        self._chat.add_system_message("Preview cancelled")

    def _on_run_code(self, code: str):
        """Execute the provided code and display changes."""
        if not code.strip():
            return

        # Capture document state BEFORE execution
        before_snapshot = SnapshotManager.capture_current_state()

        # Execute the code
        success, message = CodeExecutor.execute(code)

        # Capture document state AFTER execution
        after_snapshot = SnapshotManager.capture_current_state()

        # Detect changes
        change_set = ChangeDetector.detect_changes(before_snapshot, after_snapshot, code)
        change_set.execution_success = success
        change_set.execution_message = message

        if success:
            if change_set.is_empty():
                self._chat.add_system_message("Code executed successfully (no object changes)")
            else:
                # Display changes with ChangeWidget
                self._chat.add_change_message(change_set)
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

    def _on_debug_toggled(self, checked: bool):
        """Handle debug mode toggle - reload current session to show/hide debug info."""
        current_id = self.session_manager.get_current_session_id()
        FreeCAD.Console.PrintMessage(f"AIAssistant: Debug toggled to {checked}, current_session={current_id}\n")
        if current_id:
            # Reload current session with new debug mode setting
            self._on_load_session(current_id)

    def closeEvent(self, event):
        """Clean up when panel is closed."""
        # Stop the console observer
        ContextBuilder.stop_console_observer()
        super().closeEvent(event)
