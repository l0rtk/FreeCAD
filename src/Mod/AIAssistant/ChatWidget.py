# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Chat Widget - Main chat interface combining message list and input.
"""

import FreeCAD
FreeCAD.Console.PrintMessage("AIAssistant: ChatWidget.py loaded (v2 with system filter)\n")

from typing import Union, List, Dict
from PySide6 import QtWidgets, QtCore, QtGui
from .MessageModel import ChatMessageModel, ChatMessage, MessageRole
from .MessageDelegate import MessageBubbleWidget, TypingIndicatorWidget
from .ChangeDetector import ChangeSet
from .ChangeWidget import ChangeWidget
from .PreviewWidget import PreviewWidget


class ChatListWidget(QtWidgets.QScrollArea):
    """Scrollable list of chat messages using widgets."""

    runCodeRequested = QtCore.Signal(str)
    previewApproved = QtCore.Signal(str)  # code to execute
    previewCancelled = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._message_widgets = []
        self._typing_indicator = None
        self._model = ChatMessageModel()
        self._setup_ui()

    def _setup_ui(self):
        """Build the chat list UI."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.setStyleSheet("""
            QScrollArea {
                background-color: #0d1117;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #0d1117;
                width: 10px;
                border-radius: 5px;
                margin: 4px 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #30363d;
                border-radius: 5px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #484f58;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Container widget
        self._container = QtWidgets.QWidget()
        self._container.setStyleSheet("background-color: #0d1117;")
        self._layout = QtWidgets.QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self._layout.addStretch()

        self.setWidget(self._container)

    def add_message(self, text: str, role: str, debug_info: dict = None) -> int:
        """Add a new message to the chat."""
        import FreeCAD
        FreeCAD.Console.PrintMessage(f"AIAssistant: ChatListWidget.add_message role={role}, debug_info={debug_info is not None}\n")

        # Add to model
        row = self._model.add_message(text, role)

        # Create widget
        message = self._model.get_message(row)
        widget = MessageBubbleWidget(message, debug_info=debug_info)
        widget.runCodeRequested.connect(self.runCodeRequested.emit)

        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._message_widgets.append(widget)

        # Scroll to bottom
        QtCore.QTimer.singleShot(50, self._scroll_to_bottom)

        return row

    def add_streaming_message(self, role: str) -> int:
        """Add a message that will be streamed."""
        row = self._model.add_message("", role, is_streaming=True)

        message = self._model.get_message(row)
        widget = MessageBubbleWidget(message)
        widget.runCodeRequested.connect(self.runCodeRequested.emit)

        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._message_widgets.append(widget)

        QtCore.QTimer.singleShot(50, self._scroll_to_bottom)
        return row

    def update_streaming_message(self, row: int, text: str, is_complete: bool = False):
        """Update a streaming message with new text."""
        if 0 <= row < len(self._message_widgets):
            self._model.update_message(row, text=text, displayed_text=text,
                                       is_streaming=not is_complete)
            widget = self._message_widgets[row]
            widget.update_displayed_text(text)
            QtCore.QTimer.singleShot(50, self._scroll_to_bottom)

    def show_typing_indicator(self):
        """Show the typing indicator."""
        if self._typing_indicator is None:
            self._typing_indicator = TypingIndicatorWidget()
            self._layout.insertWidget(self._layout.count() - 1, self._typing_indicator)

        self._typing_indicator.show()
        self._typing_indicator.start()
        QtCore.QTimer.singleShot(50, self._scroll_to_bottom)

    def hide_typing_indicator(self):
        """Hide the typing indicator."""
        if self._typing_indicator:
            self._typing_indicator.stop()
            self._typing_indicator.hide()
            self._layout.removeWidget(self._typing_indicator)
            self._typing_indicator.deleteLater()
            self._typing_indicator = None

    def clear(self):
        """Clear all messages."""
        # Remove widgets
        for widget in self._message_widgets:
            self._layout.removeWidget(widget)
            widget.deleteLater()

        self._message_widgets = []
        self._model.clear()

        if self._typing_indicator:
            self.hide_typing_indicator()

    def get_conversation_history(self):
        """Get conversation history for LLM."""
        return self._model.get_conversation_history()

    def add_change_message(self, change_set: Union[ChangeSet, dict]):
        """Add a change visualization message."""
        import FreeCAD
        FreeCAD.Console.PrintMessage(f"AIAssistant: ChatListWidget.add_change_message\n")

        # Convert to dict if needed for storage
        changes_dict = change_set.to_dict() if isinstance(change_set, ChangeSet) else change_set

        # Add to model with changes data
        row = self._model.add_message(
            text="Changes applied",
            role=MessageRole.SYSTEM,
            changes=changes_dict
        )

        # Create ChangeWidget directly instead of MessageBubbleWidget
        widget = ChangeWidget(change_set)
        widget.runCodeRequested.connect(self.runCodeRequested.emit)

        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._message_widgets.append(widget)

        # Scroll to bottom
        QtCore.QTimer.singleShot(50, self._scroll_to_bottom)

        return row

    def add_preview_message(self, description: str, preview_items: List[Dict], code: str):
        """Add a preview message with approve/cancel buttons.

        Args:
            description: Human-readable description of what will be created
            preview_items: List of dicts with name, label, type, dimensions
            code: The Python code to execute on approval
        """
        import FreeCAD
        FreeCAD.Console.PrintMessage(f"AIAssistant: ChatListWidget.add_preview_message - {len(preview_items)} items\n")

        # Add to model
        row = self._model.add_message(
            text=description,
            role=MessageRole.SYSTEM
        )

        # Create PreviewWidget
        widget = PreviewWidget(description, preview_items, code)
        widget.approved.connect(lambda: self._on_preview_approved(code, widget))
        widget.cancelled.connect(lambda: self._on_preview_cancelled(widget))

        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._message_widgets.append(widget)

        # Scroll to bottom
        QtCore.QTimer.singleShot(50, self._scroll_to_bottom)

        return row

    def _on_preview_approved(self, code: str, widget: PreviewWidget):
        """Handle preview approval."""
        widget.set_disabled(True)
        self.previewApproved.emit(code)

    def _on_preview_cancelled(self, widget: PreviewWidget):
        """Handle preview cancellation."""
        widget.set_disabled(True)
        self.previewCancelled.emit()

    def _scroll_to_bottom(self):
        """Scroll to the bottom of the chat."""
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class StreamingController(QtCore.QObject):
    """Controls the typewriter streaming effect."""

    characterRevealed = QtCore.Signal(str)  # Current displayed text
    streamingComplete = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self._displayed_text = ""
        self._index = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._reveal_next)

        # Streaming speed (characters per tick)
        self._chars_per_tick = 3
        self._tick_interval = 20  # ms

    def start_streaming(self, text: str):
        """Start streaming the text."""
        self._full_text = text
        self._displayed_text = ""
        self._index = 0

        # Adjust speed based on text length
        length = len(text)
        if length > 2000:
            self._chars_per_tick = 10
            self._tick_interval = 10
        elif length > 500:
            self._chars_per_tick = 5
            self._tick_interval = 15
        else:
            self._chars_per_tick = 2
            self._tick_interval = 20

        self._timer.start(self._tick_interval)

    def stop(self):
        """Stop streaming and show all text."""
        self._timer.stop()
        self._displayed_text = self._full_text
        self.characterRevealed.emit(self._displayed_text)
        self.streamingComplete.emit()

    def skip_to_end(self):
        """Skip animation and show full text."""
        self.stop()

    def _reveal_next(self):
        """Reveal next characters."""
        if self._index >= len(self._full_text):
            self._timer.stop()
            self.streamingComplete.emit()
            return

        # Reveal next chunk
        end = min(self._index + self._chars_per_tick, len(self._full_text))
        self._displayed_text = self._full_text[:end]
        self._index = end

        self.characterRevealed.emit(self._displayed_text)


class ChatWidget(QtWidgets.QWidget):
    """Main chat widget combining list, input, and controls."""

    messageSubmitted = QtCore.Signal(str)  # User sends a message
    runCodeRequested = QtCore.Signal(str)  # User wants to run code
    previewApproved = QtCore.Signal(str)   # User approved preview - code to execute
    previewCancelled = QtCore.Signal()     # User cancelled preview

    def __init__(self, parent=None):
        super().__init__(parent)
        self._streaming_controller = StreamingController(self)
        self._streaming_row = -1
        self._pending_debug_info = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Build the chat widget UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chat list
        self._chat_list = ChatListWidget()
        self._chat_list.runCodeRequested.connect(self.runCodeRequested.emit)
        self._chat_list.previewApproved.connect(self.previewApproved.emit)
        self._chat_list.previewCancelled.connect(self.previewCancelled.emit)
        layout.addWidget(self._chat_list, stretch=1)

        # Input area container
        input_container = QtWidgets.QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #161b22;
                border-top: 1px solid #30363d;
            }
        """)
        input_layout = QtWidgets.QVBoxLayout(input_container)
        input_layout.setContentsMargins(16, 12, 16, 16)
        input_layout.setSpacing(10)

        # Input frame with border
        input_frame = QtWidgets.QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 12px;
            }
            QFrame:focus-within {
                border-color: #58a6ff;
            }
        """)
        input_frame_layout = QtWidgets.QHBoxLayout(input_frame)
        input_frame_layout.setContentsMargins(12, 8, 8, 8)
        input_frame_layout.setSpacing(8)

        # Text input
        self._input = QtWidgets.QTextEdit()
        self._input.setPlaceholderText("Describe what you want to build...")
        self._input.setMinimumHeight(44)
        self._input.setMaximumHeight(120)
        self._input.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #c9d1d9;
                border: none;
                font-size: 14px;
                padding: 4px 0;
            }
        """)
        self._input.installEventFilter(self)
        input_frame_layout.addWidget(self._input, stretch=1)

        # Send button
        self._send_btn = QtWidgets.QPushButton("Send")
        self._send_btn.setFixedSize(72, 36)
        self._send_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:pressed {
                background-color: #238636;
            }
            QPushButton:disabled {
                background-color: #21262d;
                color: #484f58;
            }
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_frame_layout.addWidget(self._send_btn, alignment=QtCore.Qt.AlignBottom)

        input_layout.addWidget(input_frame)

        # Hint text
        hint = QtWidgets.QLabel("Enter to send  ·  Shift+Enter for new line")
        hint.setStyleSheet("color: #484f58; font-size: 11px; background: transparent;")
        hint.setAlignment(QtCore.Qt.AlignCenter)
        input_layout.addWidget(hint)

        layout.addWidget(input_container)

    def _connect_signals(self):
        """Connect internal signals."""
        self._streaming_controller.characterRevealed.connect(self._on_character_revealed)
        self._streaming_controller.streamingComplete.connect(self._on_streaming_complete)

    def eventFilter(self, obj, event):
        """Handle Enter key in input."""
        if obj == self._input and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Return:
                if event.modifiers() & QtCore.Qt.ShiftModifier:
                    # Shift+Enter: new line
                    return False
                else:
                    # Enter: send message
                    self._on_send()
                    return True
        return super().eventFilter(obj, event)

    def _on_send(self):
        """Handle send button click."""
        text = self._input.toPlainText().strip()
        if not text:
            return

        self._input.clear()
        self._chat_list.add_message(text, MessageRole.USER)
        self.messageSubmitted.emit(text)

    def add_user_message(self, text: str):
        """Add a user message programmatically."""
        self._chat_list.add_message(text, MessageRole.USER)

    def add_assistant_message(self, text: str, stream: bool = True, debug_info: dict = None):
        """Add an assistant message, optionally with streaming."""
        import FreeCAD
        FreeCAD.Console.PrintMessage(f"AIAssistant: add_assistant_message stream={stream}, debug_info={debug_info is not None}\n")
        if stream:
            # For streaming, store debug_info to add after streaming completes
            self._pending_debug_info = debug_info
            self._streaming_row = self._chat_list.add_streaming_message(MessageRole.ASSISTANT)
            self._streaming_controller.start_streaming(text)
        else:
            FreeCAD.Console.PrintMessage(f"AIAssistant: Calling add_message with debug_info={debug_info is not None}\n")
            self._chat_list.add_message(text, MessageRole.ASSISTANT, debug_info=debug_info)

    def add_system_message(self, text: str):
        """Add a system message."""
        self._chat_list.add_message(text, MessageRole.SYSTEM)

    def add_error_message(self, text: str):
        """Add an error message."""
        self._chat_list.add_message(text, MessageRole.ERROR)

    def add_change_message(self, change_set: Union[ChangeSet, dict]):
        """Add a change visualization message."""
        self._chat_list.add_change_message(change_set)

    def add_preview_message(self, description: str, preview_items: List[Dict], code: str):
        """Add a preview message with approve/cancel buttons."""
        self._chat_list.add_preview_message(description, preview_items, code)

    def add_message_from_dict(self, msg_dict: dict, show_debug: bool = False):
        """Load a message from session JSON."""
        import FreeCAD
        role = msg_dict.get("role", "system")
        text = msg_dict.get("text", "")
        changes = msg_dict.get("changes")

        FreeCAD.Console.PrintMessage(f"AIAssistant: add_message_from_dict ENTER - role={role!r}, text={text[:30]!r}, has_changes={changes is not None}\n")

        # Handle change messages (stored as system role with changes data)
        if changes:
            FreeCAD.Console.PrintMessage(f"AIAssistant: Loading change message\n")
            self.add_change_message(changes)
            return

        # Skip system messages - they're UI feedback and shouldn't be reloaded
        # Check both the constant and the literal string for robustness
        if role == MessageRole.SYSTEM or role == "system":
            FreeCAD.Console.PrintMessage(f"AIAssistant: SKIPPING system message: {text[:30]!r}\n")
            return

        debug_info = msg_dict.get("debug_info") if show_debug else None
        FreeCAD.Console.PrintMessage(f"AIAssistant: add_message_from_dict LOADING - role={role}, show_debug={show_debug}, has_debug_info={debug_info is not None}\n")

        if role == MessageRole.USER:
            self.add_user_message(text)
        elif role == MessageRole.ASSISTANT:
            self.add_assistant_message(text, stream=False, debug_info=debug_info)
        elif role == MessageRole.ERROR:
            self.add_error_message(text)

    def show_typing(self):
        """Show typing indicator."""
        self._chat_list.show_typing_indicator()

    def hide_typing(self):
        """Hide typing indicator."""
        self._chat_list.hide_typing_indicator()

    def set_input_enabled(self, enabled: bool):
        """Enable/disable input."""
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)

    def clear_chat(self):
        """Clear all messages."""
        self._chat_list.clear()

    def get_conversation_history(self):
        """Get conversation history for LLM."""
        return self._chat_list.get_conversation_history()

    def _on_character_revealed(self, text: str):
        """Handle character reveal during streaming."""
        if self._streaming_row >= 0:
            self._chat_list.update_streaming_message(self._streaming_row, text)

    def _on_streaming_complete(self):
        """Handle streaming completion."""
        import FreeCAD
        FreeCAD.Console.PrintMessage(f"AIAssistant: Streaming complete, row={self._streaming_row}, pending_debug={self._pending_debug_info is not None}\n")

        if self._streaming_row >= 0:
            message = self._chat_list._model.get_message(self._streaming_row)
            if message:
                self._chat_list.update_streaming_message(
                    self._streaming_row,
                    message.text,
                    is_complete=True
                )

            # Add debug info widget if pending
            widget_count = len(self._chat_list._message_widgets)
            FreeCAD.Console.PrintMessage(f"AIAssistant: Checking debug - row={self._streaming_row}, widgets={widget_count}, has_debug={self._pending_debug_info is not None}\n")

            if self._pending_debug_info and self._streaming_row < widget_count:
                widget = self._chat_list._message_widgets[self._streaming_row]
                FreeCAD.Console.PrintMessage("AIAssistant: Adding debug info widget\n")
                widget.add_debug_info(self._pending_debug_info)
                self._pending_debug_info = None
            elif self._pending_debug_info:
                FreeCAD.Console.PrintWarning(f"AIAssistant: Could not add debug info - row {self._streaming_row} >= widget count {widget_count}\n")

        self._streaming_row = -1

    def skip_streaming(self):
        """Skip current streaming animation."""
        self._streaming_controller.skip_to_end()
