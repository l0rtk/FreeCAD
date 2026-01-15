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

FreeCAD.Console.PrintMessage("AIAssistant: AIPanel.py loaded (v3 modern design)\n")

from pathlib import Path

from . import ClaudeCodeBackend
from . import ContextBuilder
from . import CodeExecutor
from . import SnapshotManager
from . import ChangeDetector
from . import SourceManager
from . import Theme
from .ChatWidget import ChatWidget
from .SessionManager import SessionManager
from .PreviewManager import PreviewManager
from .ContextSelectionWidget import ContextSelectionWidget


# Maximum attempts to auto-fix code that fails preview
MAX_FIX_ATTEMPTS = 3


class LLMWorker(QtCore.QThread):
    """Background worker for LLM API calls."""
    finished = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, llm, user_input, context, conversation, screenshot=None):
        super().__init__()
        self.llm = llm
        self.user_input = user_input
        self.context = context
        self.conversation = conversation
        self.screenshot = screenshot

    def run(self):
        try:
            response = self.llm.chat(
                self.user_input, self.context, self.conversation, self.screenshot
            )
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

        # Initialize Claude Code backend
        self._project_dir = self._get_project_dir()
        self.llm = ClaudeCodeBackend.ClaudeCodeBackend(self._project_dir)
        FreeCAD.Console.PrintMessage(
            f"AIAssistant: Using Claude Code backend (project: {self._project_dir})\n"
        )

        self.worker = None
        self._fix_worker = None  # Worker for auto-fix requests
        self._plan_worker = None  # Worker for plan mode phase 2
        self.pending_input = None
        self._last_code = ""
        self._last_screenshot = None  # Base64 PNG of last viewport capture

        # Plan mode state
        self._pending_plan = None  # Approved plan text for code generation
        self._plan_user_request = None  # Original user request for plan
        self._plan_mode_request = False  # True if current request is for plan (phase 1)

        # Session manager for persisting conversations
        self.session_manager = SessionManager()

        # Preview manager for 3D previews before execution
        self._preview_manager = PreviewManager()

        # Start console observer to capture errors for AI context
        ContextBuilder.start_console_observer()

        self._setup_ui()
        self._connect_signals()

        # Ensure source file exists for saved documents
        self._ensure_source_file()

        # Ensure CLAUDE.md exists for Claude Code backend
        self._ensure_claude_md()

    def _setup_ui(self):
        """Build the UI."""
        main = QtWidgets.QWidget()
        main.setStyleSheet(f"background-color: {Theme.COLORS['bg_primary']};")
        layout = QtWidgets.QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QtWidgets.QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.COLORS['bg_secondary']};
                border-bottom: 1px solid {Theme.COLORS['border_subtle']};
            }}
        """)
        header.setFixedHeight(48)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(14, 0, 10, 0)
        header_layout.setSpacing(6)

        # Title area with main title and session subtitle
        title_area = QtWidgets.QWidget()
        title_area.setStyleSheet("background: transparent;")
        title_area_layout = QtWidgets.QVBoxLayout(title_area)
        title_area_layout.setContentsMargins(0, 6, 0, 6)
        title_area_layout.setSpacing(0)

        title = QtWidgets.QLabel("AI Assistant")
        title.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['text_primary']};
                font-weight: {Theme.FONTS['weight_semibold']};
                font-size: {Theme.FONTS['size_base']};
                background: transparent;
            }}
        """)
        title_area_layout.addWidget(title)

        # Session title label
        self._session_label = QtWidgets.QLabel("")
        self._session_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['text_muted']};
                font-size: {Theme.FONTS['size_xs']};
                background: transparent;
            }}
        """)
        self._session_label.hide()
        title_area_layout.addWidget(self._session_label)

        header_layout.addWidget(title_area)
        header_layout.addStretch()

        # Header button style
        header_btn_style = f"""
            QToolButton {{
                color: {Theme.COLORS['text_secondary']};
                background: transparent;
                border: none;
                font-size: {Theme.FONTS['size_sm']};
                padding: 6px 10px;
                border-radius: {Theme.RADIUS['xs']};
            }}
            QToolButton:hover {{
                color: {Theme.COLORS['text_primary']};
                background-color: {Theme.COLORS['bg_hover']};
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
        """

        # Sessions button
        self.sessions_btn = QtWidgets.QToolButton()
        self.sessions_btn.setText("Sessions")
        self.sessions_btn.setToolTip("View and switch sessions")
        self.sessions_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.sessions_btn.setStyleSheet(header_btn_style)
        header_layout.addWidget(self.sessions_btn)

        # Settings button
        self.settings_btn = QtWidgets.QToolButton()
        self.settings_btn.setText("...")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.settings_btn.setStyleSheet(header_btn_style.replace(
            f"font-size: {Theme.FONTS['size_sm']};",
            f"font-size: {Theme.FONTS['size_lg']};"
        ))
        self._setup_settings_menu()
        header_layout.addWidget(self.settings_btn)

        # Clear button
        clear_btn = QtWidgets.QToolButton()
        clear_btn.setText("Clear")
        clear_btn.setToolTip("Clear chat")
        clear_btn.setStyleSheet(header_btn_style)
        clear_btn.clicked.connect(self._on_clear)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # Context selection widget (above chat)
        self._context_widget = ContextSelectionWidget()
        layout.addWidget(self._context_widget)

        # Chat widget
        self._chat = ChatWidget()
        layout.addWidget(self._chat, stretch=1)

        self.setWidget(main)
        self.setMinimumWidth(380)
        self.setMinimumHeight(500)

    def _setup_settings_menu(self):
        """Setup the settings dropdown menu."""
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Theme.COLORS['bg_secondary']};
                color: {Theme.COLORS['text_primary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['sm']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: {Theme.RADIUS['xs']};
            }}
            QMenu::item:selected {{
                background-color: {Theme.COLORS['bg_hover']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {Theme.COLORS['border_subtle']};
                margin: 4px 8px;
            }}
        """)

        self.context_action = menu.addAction("Include document context")
        self.context_action.setCheckable(True)
        self.context_action.setChecked(True)

        self.autorun_action = menu.addAction("Auto-run code")
        self.autorun_action.setCheckable(True)
        self.autorun_action.setChecked(False)

        self.auto_accept_action = menu.addAction("Auto-accept previews")
        self.auto_accept_action.setCheckable(True)
        self.auto_accept_action.setChecked(False)

        self.plan_mode_action = menu.addAction("Plan mode (2-phase)")
        self.plan_mode_action.setCheckable(True)
        self.plan_mode_action.setChecked(False)

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

        # Plan mode signals
        self._chat.planApproved.connect(self._on_plan_approved)
        self._chat.planEdited.connect(self._on_plan_edited)
        self._chat.planCancelled.connect(self._on_plan_cancelled)

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
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Theme.COLORS['bg_secondary']};
                color: {Theme.COLORS['text_primary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['sm']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: {Theme.RADIUS['xs']};
            }}
            QMenu::item:selected {{
                background-color: {Theme.COLORS['bg_hover']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {Theme.COLORS['border_subtle']};
                margin: 4px 8px;
            }}
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

        # Update project directory (handles document changes)
        self._update_project_dir()

        # Ensure source file exists for saved documents
        self._ensure_source_file()

        # Backup source.py before Claude potentially edits it (for restore on cancel)
        SourceManager.backup_source()

        # Build context if enabled (using context widget selection)
        context = ""
        if self.context_action.isChecked():
            objects_filter = self._context_widget.get_context_objects()
            context = ContextBuilder.build_context(objects_filter=objects_filter)

        # Capture object snapshot for future context enrichment (unique timestamp per request)
        from datetime import datetime
        snapshot_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_path = SnapshotManager.save_snapshot(timestamp=snapshot_timestamp)

        # Link snapshot to session
        if snapshot_path:
            self.session_manager.add_snapshot_reference(snapshot_timestamp)

        # Get conversation history
        conversation = self._chat.get_conversation_history()

        # Check if plan mode is enabled
        self._plan_mode_request = self.plan_mode_action.isChecked()

        if self._plan_mode_request:
            # Phase 1: Request plan only
            self._plan_user_request = user_input
            plan_prompt = f"""PLAN MODE: Analyze this request and create an execution plan.

User request: {user_input}

Output ONLY a plan in this format:
## Plan
1. **[Action]**: [Description of what will be created/modified]
2. **[Action]**: [Description]
...

Do NOT write any code. Only output the numbered plan steps."""

            self.worker = LLMWorker(
                self.llm, plan_prompt, context, conversation, self._last_screenshot
            )
        else:
            # Normal mode: request code directly
            self.worker = LLMWorker(
                self.llm, user_input, context, conversation, self._last_screenshot
            )

        self.worker.finished.connect(self._on_response)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_response(self, response: str):
        """Handle successful LLM response - create preview or show plan."""
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

        # Handle plan mode response (Phase 1)
        if self._plan_mode_request:
            self._plan_mode_request = False  # Reset flag
            FreeCAD.Console.PrintMessage("AIAssistant: Plan mode - showing plan for approval\n")
            self._chat.add_plan_message(response, self._plan_user_request or "")
            self.pending_input = None
            return

        # Check if Claude edited source.py directly (new direct editing flow)
        if getattr(self.llm, 'source_was_edited', False):
            FreeCAD.Console.PrintMessage("AIAssistant: Detected direct source.py edit - using diff preview\n")
            self._handle_source_edit_response(response)
            self.pending_input = None
            return

        # Claude didn't edit source.py - clear backup so patch flow is used on approve
        SourceManager.clear_backup()

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

        # Try to create preview with auto-fix if needed
        self._attempt_preview_with_autofix(description, code, response)

        self.pending_input = None

    def _handle_source_edit_response(self, response: str):
        """Handle response where Claude edited source.py directly.

        This is the new direct source editing flow:
        1. Get OLD source.py from backup
        2. Get NEW source.py from disk (Claude already edited it)
        3. Create diff preview showing what changed
        4. On approve: execute new source.py
        5. On cancel: restore from backup

        Args:
            response: Claude's text response (explanation of changes)
        """
        old_source = SourceManager.get_backup_content()
        new_source = SourceManager.read_source()

        # Debug: log what changed
        FreeCAD.Console.PrintMessage(
            f"AIAssistant: Old source length: {len(old_source) if old_source else 0}, "
            f"New source length: {len(new_source) if new_source else 0}\n"
        )

        # If no backup or no change, just show the text response
        if not old_source or old_source == new_source:
            FreeCAD.Console.PrintMessage("AIAssistant: No source changes detected\n")
            SourceManager.clear_backup()
            tool_calls = getattr(self.llm, 'last_tool_calls', None)
            self._chat.add_assistant_message(response, tool_calls=tool_calls)
            return

        # Create diff preview - execute OLD vs NEW, show differences
        FreeCAD.Console.PrintMessage("AIAssistant: Creating diff preview...\n")
        success, error_msg = self._preview_manager.create_diff_preview(old_source, new_source)

        if success:
            # Get preview summary
            preview_items = self._preview_manager.get_preview_summary()
            is_deletion = self._preview_manager.is_deletion_preview()

            FreeCAD.Console.PrintMessage(
                f"AIAssistant: Diff preview created with {len(preview_items)} changes "
                f"(deletion={is_deletion})\n"
            )

            # Check if auto-accept is enabled
            auto_approve = self.auto_accept_action.isChecked()

            # Get tool calls from backend
            tool_calls = getattr(self.llm, 'last_tool_calls', None)

            # Show preview widget
            # Note: For source edits, the "code" is the new source.py content
            # This is used by approve handler to know it's a source edit
            self._chat.add_preview_message(
                description=response or "Source.py modified",
                preview_items=preview_items,
                code=new_source,  # Full new source.py
                is_deletion=is_deletion,
                auto_approve=auto_approve,
                tool_calls=tool_calls
            )
        else:
            # Diff preview failed - restore backup and show error
            FreeCAD.Console.PrintWarning(f"AIAssistant: Diff preview failed: {error_msg}\n")
            SourceManager.restore_source()
            self._chat.add_error_message(f"Preview failed: {error_msg}")

    def _attempt_preview_with_autofix(self, description: str, code: str, original_response: str, attempt: int = 1):
        """Try to create preview, auto-fix errors if needed.

        Args:
            description: Text description from LLM response
            code: Python code to execute
            original_response: Original full LLM response (for fallback display)
            attempt: Current attempt number (1-based)
        """
        # Keep typing indicator visible during retries
        if attempt > 1:
            self._chat.show_typing()
            FreeCAD.Console.PrintMessage(f"AIAssistant: Auto-fix attempt {attempt}...\n")

        # Try to create preview
        FreeCAD.Console.PrintMessage(f"AIAssistant: Creating preview (attempt {attempt})...\n")
        success, error_msg = self._preview_manager.create_preview(code)

        if success:
            # Get preview summary
            preview_items = self._preview_manager.get_preview_summary()
            is_deletion = self._preview_manager.is_deletion_preview()
            FreeCAD.Console.PrintMessage(
                f"AIAssistant: Preview created with {len(preview_items)} objects "
                f"(deletion={is_deletion})\n"
            )

            # Hide typing if shown during retry
            if attempt > 1:
                self._chat.hide_typing()

            # Show preview widget with appropriate description
            if is_deletion:
                default_desc = "I'll delete the following objects:"
            else:
                default_desc = "I'll create the following objects:"

            # Check if auto-accept is enabled
            auto_approve = self.auto_accept_action.isChecked()

            # Get tool calls from backend (if any)
            tool_calls = getattr(self.llm, 'last_tool_calls', None)

            self._chat.add_preview_message(
                description=description or default_desc,
                preview_items=preview_items,
                code=code,
                is_deletion=is_deletion,
                auto_approve=auto_approve,
                tool_calls=tool_calls
            )
            return

        # Preview failed - check if this is a deletion operation
        # Deletion failures should NOT trigger auto-fix (can't "fix" a non-existent object)
        is_deletion_attempt = self._preview_manager.is_deletion_preview() or \
                              bool(self._preview_manager._detect_deletion_targets(code))

        if is_deletion_attempt:
            # Deletion failed - show error to user, don't try to auto-fix
            FreeCAD.Console.PrintWarning(f"AIAssistant: Deletion preview failed: {error_msg}\n")
            self._chat.hide_typing()
            self._preview_manager.clear_preview()
            self._chat.add_error_message(f"Cannot delete: {error_msg}")
            return

        # Preview failed (creation) - try auto-fix
        if attempt >= MAX_FIX_ATTEMPTS:
            # Give up - show traditional code block
            FreeCAD.Console.PrintWarning(f"AIAssistant: Max auto-fix attempts reached, showing code block\n")
            self._chat.hide_typing()
            self._preview_manager.clear_preview()
            self._show_traditional_response(original_response)
            return

        # Ask LLM to fix the code
        FreeCAD.Console.PrintMessage(f"AIAssistant: Preview failed, requesting fix from LLM...\n")
        # Show typing indicator during auto-fix
        self._chat.show_typing()
        self._request_code_fix(description, code, error_msg, original_response, attempt)

    def _request_code_fix(self, description: str, code: str, error: str, original_response: str, attempt: int):
        """Send error to LLM and request fixed code.

        Args:
            description: Original description from response
            code: Code that failed
            error: Error message from execution
            original_response: Original full response (for fallback)
            attempt: Current attempt number
        """
        fix_prompt = f"""The following FreeCAD Python code failed with an error:

```python
{code}
```

Error:
{error}

Please fix the code. The code runs in a SANDBOX where existing document objects are NOT available.
If you need to reference existing objects, recreate them or use hardcoded values.

Return ONLY the fixed Python code in a ```python code block, no explanation needed."""

        # Start background worker for fix request
        self._fix_worker = LLMWorker(self.llm, fix_prompt, "", [])
        self._fix_worker.finished.connect(
            lambda fixed_response: self._on_fix_response(description, fixed_response, original_response, attempt)
        )
        self._fix_worker.error.connect(self._on_fix_error)
        self._fix_worker.start()

    def _on_fix_response(self, description: str, response: str, original_response: str, attempt: int):
        """Handle fixed code from LLM.

        Args:
            description: Original description
            response: LLM response with fixed code
            original_response: Original full response (for fallback)
            attempt: Previous attempt number
        """
        _, fixed_code = self._parse_response(response)

        if fixed_code.strip():
            # Retry preview with fixed code
            self._attempt_preview_with_autofix(description, fixed_code, original_response, attempt + 1)
        else:
            # Couldn't parse fixed code - fall back
            FreeCAD.Console.PrintWarning("AIAssistant: Couldn't parse fixed code, showing original\n")
            self._chat.hide_typing()
            self._preview_manager.clear_preview()
            self._show_traditional_response(original_response)

    def _on_fix_error(self, error_msg: str):
        """Handle error from fix request."""
        FreeCAD.Console.PrintError(f"AIAssistant: Auto-fix request failed: {error_msg}\n")
        self._chat.hide_typing()
        self._preview_manager.clear_preview()
        # Fall back to showing original response
        if self._last_code:
            self._show_traditional_response(self._last_code)

    def _parse_response(self, response: str) -> tuple:
        """Parse LLM response to extract description and code.

        Returns:
            Tuple of (description, code)
        """
        import re

        # Try to find Python code block with closing fence
        code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            # Description is everything before the code block
            description = response[:code_match.start()].strip()
            # Clean up description - remove markdown artifacts
            description = re.sub(r'\n+', ' ', description)
            description = description.strip()
            return (description, code)

        # Try to find any code block with closing fence
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            description = response[:code_match.start()].strip()
            description = re.sub(r'\n+', ' ', description)
            return (description, code)

        # Handle UNCLOSED code blocks (LLM truncated response without closing ```)
        # This is a common issue where the response has ```python but no closing ```
        unclosed_match = re.search(r'```python\s*\n(.*)', response, re.DOTALL)
        if unclosed_match:
            code = unclosed_match.group(1).strip()
            description = response[:unclosed_match.start()].strip()
            description = re.sub(r'\n+', ' ', description)
            FreeCAD.Console.PrintWarning(
                "AIAssistant: Detected unclosed code block - LLM response may be truncated\n"
            )
            return (description, code)

        # No code block found - might be pure code or pure text
        # Check if it looks like Python code
        code_indicators = [
            'import FreeCAD',
            'FreeCAD.',
            'Part.',
            'doc.addObject',
            'doc.removeObject',  # Deletion operations
            '.removeObject(',    # Alternative pattern
            'doc.recompute()',   # Common ending
        ]
        if any(indicator in response for indicator in code_indicators):
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
        tool_calls = getattr(self.llm, 'last_tool_calls', None)
        self._chat.add_assistant_message(response, stream=use_streaming, debug_info=debug_info, tool_calls=tool_calls)

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

        # Check if this is a source edit (backup exists) vs old-style patch
        if SourceManager.has_backup():
            # Source edit flow: source.py already has the changes, execute it
            FreeCAD.Console.PrintMessage("AIAssistant: Executing edited source.py\n")
            source_content = SourceManager.read_source()

            # Capture state BEFORE clearing (to detect what was deleted)
            before_snapshot = SnapshotManager.capture_current_state()

            # CRITICAL: Clear all document objects before re-executing source.py
            # This prevents duplicates (Floor001, etc.) when objects already exist
            doc = FreeCAD.ActiveDocument
            if doc:
                # Build list of objects to remove (excluding system objects)
                objects_to_remove = [
                    obj.Name for obj in doc.Objects
                    if obj.TypeId not in ("App::Origin", "App::Plane", "App::Line")
                ]
                FreeCAD.Console.PrintMessage(
                    f"AIAssistant: Clearing {len(objects_to_remove)} objects before re-execution\n"
                )
                for obj_name in objects_to_remove:
                    try:
                        doc.removeObject(obj_name)
                    except Exception:
                        pass

            # Execute the new source.py (on clean document)
            success, message = CodeExecutor.execute(source_content)

            # Capture state after
            after_snapshot = SnapshotManager.capture_current_state()

            if success:
                # Clear backup - source.py is now canonical
                SourceManager.clear_backup()

                # Capture screenshot for LLM feedback
                self._last_screenshot = self._capture_screenshot()

                # Detect and show changes
                change_set = ChangeDetector.detect_changes(
                    before_snapshot, after_snapshot, code=""
                )
                change_set.execution_success = success
                change_set.execution_message = message

                if change_set.is_empty():
                    self._chat.add_system_message("Source.py executed successfully (no object changes)")
                else:
                    self._chat.add_change_message(change_set)
            else:
                # Execution failed - restore backup
                FreeCAD.Console.PrintError(f"AIAssistant: Source execution failed: {message}\n")
                SourceManager.restore_source()
                self._chat.add_error_message(f"Execution error: {message}")
        else:
            # Old-style patch flow: execute the code and show changes
            self._on_run_code(code, already_executed=True)

    def _on_preview_cancelled(self):
        """Handle user cancellation of preview."""
        FreeCAD.Console.PrintMessage("AIAssistant: Preview cancelled\n")

        # Clear the preview objects
        self._preview_manager.cancel()

        # Restore source.py from backup if this was a source edit
        if SourceManager.has_backup():
            FreeCAD.Console.PrintMessage("AIAssistant: Restoring source.py from backup\n")
            SourceManager.restore_source()

        # Add a system message
        self._chat.add_system_message("Preview cancelled")

    def _on_plan_approved(self, plan_text: str):
        """Handle plan approval - request code generation (Phase 2)."""
        FreeCAD.Console.PrintMessage("AIAssistant: Plan approved - requesting code generation\n")
        self._pending_plan = plan_text
        self._generate_code_from_plan(plan_text)

    def _on_plan_edited(self, edited_plan: str):
        """Handle plan edit and approval - request code with edited plan."""
        FreeCAD.Console.PrintMessage("AIAssistant: Plan edited and approved - requesting code generation\n")
        self._pending_plan = edited_plan
        self._generate_code_from_plan(edited_plan)

    def _on_plan_cancelled(self):
        """Handle plan cancellation."""
        FreeCAD.Console.PrintMessage("AIAssistant: Plan cancelled\n")
        self._pending_plan = None
        self._plan_user_request = None
        self._chat.add_system_message("Plan cancelled")

    def _generate_code_from_plan(self, plan_text: str):
        """Request code generation based on approved plan (Phase 2).

        Args:
            plan_text: The approved (or edited) plan text
        """
        # Prevent double-send
        if self._plan_worker and self._plan_worker.isRunning():
            return

        # Show typing indicator
        self._chat.show_typing()
        self._chat.set_input_enabled(False)

        # Build context (using context widget selection)
        context = ""
        if self.context_action.isChecked():
            objects_filter = self._context_widget.get_context_objects()
            context = ContextBuilder.build_context(objects_filter=objects_filter)

        # Get conversation history
        conversation = self._chat.get_conversation_history()

        # Build prompt for code generation
        code_prompt = f"""The user approved this execution plan:

{plan_text}

Original request: {self._plan_user_request or ""}

Now write the FreeCAD Python code to implement this plan exactly as specified.
Return ONLY the Python code in a ```python code block."""

        # Start background worker for code generation
        self._plan_worker = LLMWorker(
            self.llm, code_prompt, context, conversation, self._last_screenshot
        )
        self._plan_worker.finished.connect(self._on_plan_code_response)
        self._plan_worker.error.connect(self._on_error)
        self._plan_worker.start()

    def _on_plan_code_response(self, response: str):
        """Handle code response from plan (Phase 2)."""
        # Hide typing indicator
        self._chat.hide_typing()
        self._chat.set_input_enabled(True)

        # Clear plan state
        self._pending_plan = None
        self._plan_user_request = None

        # Store code for later execution
        self._last_code = response

        # Log the request
        self.session_manager.log_llm_request(
            user_message="[Plan Phase 2: Code Generation]",
            system_prompt=self.llm.last_system_prompt,
            context=self.llm.last_context,
            conversation_history=self.llm.last_conversation,
            response=response,
            model=self.llm.model,
            api_url=self.llm.api_url,
            duration_ms=self.llm.last_duration_ms,
            success=True
        )

        # Parse and show preview as normal
        description, code = self._parse_response(response)

        if not code.strip():
            self._show_traditional_response(response)
            return

        # Create preview
        self._attempt_preview_with_autofix(description, code, response)

    def _on_run_code(self, code: str, already_executed: bool = False):
        """Execute the provided code and display changes.

        Args:
            code: Python code to execute
            already_executed: If True, don't show Run button (code came from preview approval)
        """
        if not code.strip():
            return

        # Capture document state BEFORE execution
        before_snapshot = SnapshotManager.capture_current_state()

        # Execute the code
        success, message = CodeExecutor.execute(code)

        # Capture document state AFTER execution
        after_snapshot = SnapshotManager.capture_current_state()

        # Detect changes
        # Don't include code if already executed (from preview approval) - prevents showing Run button
        change_set = ChangeDetector.detect_changes(
            before_snapshot, after_snapshot,
            code="" if already_executed else code
        )
        change_set.execution_success = success
        change_set.execution_message = message

        if success:
            # Capture screenshot for LLM feedback
            self._last_screenshot = self._capture_screenshot()

            # Save code to source file (for regeneration and context)
            SourceManager.append_code(code)

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

    def _get_project_dir(self) -> str:
        """Get project directory for Claude Code working directory.

        Returns:
            Path to project folder (parent/doc_stem/) or None if doc not saved
        """
        doc = FreeCAD.ActiveDocument
        if doc and doc.FileName:
            doc_path = Path(doc.FileName)
            # Project folder: parent/doc_stem/
            project_dir = doc_path.parent / doc_path.stem
            # Create folder if needed (matches SourceManager/SessionManager pattern)
            project_dir.mkdir(parents=True, exist_ok=True)
            return str(project_dir)
        return None

    def _update_project_dir(self):
        """Update project directory when document changes.

        Called before each LLM request to handle:
        - Document opened after panel created
        - Document saved to new location
        - Switching between documents
        """
        new_dir = self._get_project_dir()
        if new_dir and new_dir != self._project_dir:
            self._project_dir = new_dir
            # Update backend's project_dir if it supports it
            if hasattr(self.llm, 'project_dir'):
                self.llm.project_dir = new_dir
                FreeCAD.Console.PrintMessage(
                    f"AIAssistant: Project directory updated to {new_dir}\n"
                )
            # Ensure CLAUDE.md exists in new project
            self._ensure_claude_md()

    def _ensure_claude_md(self):
        """Ensure CLAUDE.md exists in project directory for Claude Code backend.

        If using Claude Code and project dir exists but has no CLAUDE.md,
        copy the template file.
        """
        if not self._project_dir:
            return

        claude_md_path = Path(self._project_dir) / "CLAUDE.md"
        if claude_md_path.exists():
            return

        # Copy template
        try:
            template_path = Path(__file__).parent / "project_claude_template.md"
            if template_path.exists():
                import shutil
                shutil.copy(template_path, claude_md_path)
                FreeCAD.Console.PrintMessage(
                    f"AIAssistant: Created CLAUDE.md in {self._project_dir}\n"
                )
        except Exception as e:
            FreeCAD.Console.PrintWarning(
                f"AIAssistant: Failed to create CLAUDE.md: {e}\n"
            )

    def _ensure_source_file(self):
        """
        Ensure source file exists for current document.

        Creates an empty source file with headers if the document is saved
        but doesn't have a source file yet. This enables proactive source
        tracking even before any AI code is executed.
        """
        doc = FreeCAD.ActiveDocument
        if doc and doc.FileName:
            if not SourceManager.exists():
                SourceManager.init_source_file()

    def _capture_screenshot(self) -> str:
        """Capture current viewport as base64 PNG.

        Returns:
            Base64 encoded PNG string, or None if capture failed
        """
        import tempfile
        import base64
        import os

        try:
            if not FreeCADGui.ActiveDocument:
                return None

            view = FreeCADGui.ActiveDocument.ActiveView
            if not hasattr(view, "saveImage"):
                return None  # Not a 3D view

            # Set isometric view and fit all objects
            view.viewIsometric()
            view.fitAll()

            # Save to temp file
            tmp_path = tempfile.mktemp(suffix=".png")
            try:
                view.saveImage(tmp_path, 800, 600)

                with open(tmp_path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"AIAssistant: Screenshot capture failed: {e}\n")
            return None

    def closeEvent(self, event):
        """Clean up when panel is closed."""
        # Stop the console observer
        ContextBuilder.stop_console_observer()
        super().closeEvent(event)
