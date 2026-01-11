# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Chat Widget - Main chat interface combining message list and input.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from .MessageModel import ChatMessageModel, ChatMessage, MessageRole
from .MessageDelegate import MessageBubbleWidget, TypingIndicatorWidget


class ChatListWidget(QtWidgets.QScrollArea):
    """Scrollable list of chat messages using widgets."""

    runCodeRequested = QtCore.Signal(str)

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
                background-color: #1a1a1a;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1a1a1a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Container widget
        self._container = QtWidgets.QWidget()
        self._container.setStyleSheet("background-color: #1a1a1a;")
        self._layout = QtWidgets.QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self._layout.addStretch()

        self.setWidget(self._container)

    def add_message(self, text: str, role: str) -> int:
        """Add a new message to the chat."""
        # Add to model
        row = self._model.add_message(text, role)

        # Create widget
        message = self._model.get_message(row)
        widget = MessageBubbleWidget(message)
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._streaming_controller = StreamingController(self)
        self._streaming_row = -1
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
        layout.addWidget(self._chat_list, stretch=1)

        # Input area container
        input_container = QtWidgets.QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-top: 1px solid #333;
            }
        """)
        input_layout = QtWidgets.QVBoxLayout(input_container)
        input_layout.setContentsMargins(12, 8, 12, 12)
        input_layout.setSpacing(8)

        # Input row
        input_row = QtWidgets.QHBoxLayout()
        input_row.setSpacing(8)

        # Text input
        self._input = QtWidgets.QTextEdit()
        self._input.setPlaceholderText("Describe what you want to build...")
        self._input.setFixedHeight(60)
        self._input.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QTextEdit:focus {
                border-color: #4a9eff;
            }
        """)
        self._input.installEventFilter(self)
        input_row.addWidget(self._input, stretch=1)

        # Send button
        self._send_btn = QtWidgets.QPushButton("Send")
        self._send_btn.setFixedSize(70, 36)
        self._send_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3a8eef;
            }
            QPushButton:pressed {
                background-color: #2a7edf;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #666;
            }
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self._send_btn, alignment=QtCore.Qt.AlignBottom)

        input_layout.addLayout(input_row)

        # Hint text
        hint = QtWidgets.QLabel("Press Enter to send, Shift+Enter for new line")
        hint.setStyleSheet("color: #666; font-size: 11px;")
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

    def add_assistant_message(self, text: str, stream: bool = True):
        """Add an assistant message, optionally with streaming."""
        if stream:
            self._streaming_row = self._chat_list.add_streaming_message(MessageRole.ASSISTANT)
            self._streaming_controller.start_streaming(text)
        else:
            self._chat_list.add_message(text, MessageRole.ASSISTANT)

    def add_system_message(self, text: str):
        """Add a system message."""
        self._chat_list.add_message(text, MessageRole.SYSTEM)

    def add_error_message(self, text: str):
        """Add an error message."""
        self._chat_list.add_message(text, MessageRole.ERROR)

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
        if self._streaming_row >= 0:
            message = self._chat_list._model.get_message(self._streaming_row)
            if message:
                self._chat_list.update_streaming_message(
                    self._streaming_row,
                    message.text,
                    is_complete=True
                )
        self._streaming_row = -1

    def skip_streaming(self):
        """Skip current streaming animation."""
        self._streaming_controller.skip_to_end()
