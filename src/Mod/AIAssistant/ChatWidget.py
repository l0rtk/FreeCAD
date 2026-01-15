# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Chat Widget - Modern chat interface with clean design.
Cursor-inspired styling with blue accents.
"""

import FreeCAD
FreeCAD.Console.PrintMessage("AIAssistant: ChatWidget.py loaded (v3 modern design)\n")

from typing import Union, List, Dict
from PySide6 import QtWidgets, QtCore, QtGui
from .MessageModel import ChatMessageModel, ChatMessage, MessageRole
from .MessageDelegate import MessageCard, ThinkingIndicator
from .ChangeDetector import ChangeSet
from .ChangeWidget import ChangeWidget
from .PreviewWidget import PreviewWidget
from . import Theme


class ChatListWidget(QtWidgets.QScrollArea):
    """Scrollable list of chat messages using widgets."""

    runCodeRequested = QtCore.Signal(str)
    previewApproved = QtCore.Signal(str)
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

        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Theme.COLORS['bg_primary']};
                border: none;
            }}
            {Theme.get_scrollbar_style()}
        """)

        # Container widget
        self._container = QtWidgets.QWidget()
        self._container.setStyleSheet(f"background-color: {Theme.COLORS['bg_primary']};")
        self._layout = QtWidgets.QVBoxLayout(self._container)
        self._layout.setContentsMargins(12, 16, 12, 16)
        self._layout.setSpacing(12)
        self._layout.addStretch()

        self.setWidget(self._container)

    def add_message(self, text: str, role: str, debug_info: dict = None) -> int:
        """Add a new message to the chat."""
        row = self._model.add_message(text, role)
        message = self._model.get_message(row)
        widget = MessageCard(message, debug_info=debug_info)
        widget.runCodeRequested.connect(self.runCodeRequested.emit)

        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._message_widgets.append(widget)

        QtCore.QTimer.singleShot(50, self._scroll_to_bottom)
        return row

    def add_streaming_message(self, role: str) -> int:
        """Add a message that will be streamed."""
        row = self._model.add_message("", role, is_streaming=True)
        message = self._model.get_message(row)
        widget = MessageCard(message)
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
            self._typing_indicator = ThinkingIndicator()
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
        changes_dict = change_set.to_dict() if isinstance(change_set, ChangeSet) else change_set

        row = self._model.add_message(
            text="Changes applied",
            role=MessageRole.SYSTEM,
            changes=changes_dict
        )

        widget = ChangeWidget(change_set)
        widget.runCodeRequested.connect(self.runCodeRequested.emit)

        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._message_widgets.append(widget)

        QtCore.QTimer.singleShot(50, self._scroll_to_bottom)
        return row

    def add_preview_message(self, description: str, preview_items: List[Dict], code: str,
                            is_deletion: bool = False):
        """Add a preview message with approve/cancel buttons."""
        row = self._model.add_message(
            text=description,
            role=MessageRole.SYSTEM
        )

        widget = PreviewWidget(description, preview_items, code, is_deletion=is_deletion)
        widget.approved.connect(lambda: self._on_preview_approved(code, widget))
        widget.cancelled.connect(lambda: self._on_preview_cancelled(widget))

        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._message_widgets.append(widget)

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
        """Scroll to the bottom of the chat with smooth animation."""
        scrollbar = self.verticalScrollBar()
        # Use smooth scrolling
        self._smooth_scroll_to(scrollbar.maximum())

    def _smooth_scroll_to(self, target: int):
        """Animate scroll to target position."""
        scrollbar = self.verticalScrollBar()
        current = scrollbar.value()

        if not hasattr(self, '_scroll_anim'):
            self._scroll_anim = QtCore.QPropertyAnimation(scrollbar, b"value")
            self._scroll_anim.setDuration(150)
            self._scroll_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self._scroll_anim.stop()
        self._scroll_anim.setStartValue(current)
        self._scroll_anim.setEndValue(target)
        self._scroll_anim.start()


class StreamingController(QtCore.QObject):
    """Controls the typewriter streaming effect with word-based chunks."""

    characterRevealed = QtCore.Signal(str)
    streamingComplete = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self._displayed_text = ""
        self._index = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._reveal_next)

        # Streaming speed
        self._chars_per_tick = 4
        self._tick_interval = 15

    def start_streaming(self, text: str):
        """Start streaming the text."""
        self._full_text = text
        self._displayed_text = ""
        self._index = 0

        # Adjust speed based on text length
        length = len(text)
        if length > 2000:
            self._chars_per_tick = 15
            self._tick_interval = 8
        elif length > 500:
            self._chars_per_tick = 8
            self._tick_interval = 12
        else:
            self._chars_per_tick = 4
            self._tick_interval = 15

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
        """Reveal next characters - prefer word boundaries."""
        if self._index >= len(self._full_text):
            self._timer.stop()
            self.streamingComplete.emit()
            return

        # Calculate end position
        target_end = min(self._index + self._chars_per_tick, len(self._full_text))

        # Try to end at a word boundary (space, newline)
        if target_end < len(self._full_text):
            for i in range(target_end, min(target_end + 10, len(self._full_text))):
                if self._full_text[i] in ' \n\t':
                    target_end = i + 1
                    break

        self._displayed_text = self._full_text[:target_end]
        self._index = target_end

        self.characterRevealed.emit(self._displayed_text)


class ChatWidget(QtWidgets.QWidget):
    """Main chat widget with modern styling."""

    messageSubmitted = QtCore.Signal(str)
    runCodeRequested = QtCore.Signal(str)
    previewApproved = QtCore.Signal(str)
    previewCancelled = QtCore.Signal()

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
        input_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.COLORS['bg_secondary']};
                border-top: 1px solid {Theme.COLORS['border_subtle']};
            }}
        """)
        input_layout = QtWidgets.QVBoxLayout(input_container)
        input_layout.setContentsMargins(16, 14, 16, 16)
        input_layout.setSpacing(10)

        # Input frame with border
        input_frame = QtWidgets.QFrame()
        input_frame.setObjectName("input_frame")
        input_frame.setStyleSheet(f"""
            QFrame#input_frame {{
                background-color: {Theme.COLORS['bg_input']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['lg']};
            }}
            QFrame#input_frame:focus-within {{
                border-color: {Theme.COLORS['border_focus']};
            }}
        """)
        input_frame_layout = QtWidgets.QHBoxLayout(input_frame)
        input_frame_layout.setContentsMargins(14, 10, 10, 10)
        input_frame_layout.setSpacing(10)

        # Text input
        self._input = QtWidgets.QTextEdit()
        self._input.setPlaceholderText("What would you like to build?")
        self._input.setMinimumHeight(44)
        self._input.setMaximumHeight(120)
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {Theme.COLORS['text_primary']};
                border: none;
                font-size: {Theme.FONTS['size_base']};
                padding: 4px 0;
                selection-background-color: {Theme.COLORS['accent_primary']};
            }}
        """)
        self._input.installEventFilter(self)
        input_frame_layout.addWidget(self._input, stretch=1)

        # Send button
        self._send_btn = QtWidgets.QPushButton("Send")
        self._send_btn.setFixedSize(72, 38)
        self._send_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.COLORS['accent_primary']};
                color: #ffffff;
                border: none;
                border-radius: {Theme.RADIUS['md']};
                font-weight: {Theme.FONTS['weight_medium']};
                font-size: {Theme.FONTS['size_base']};
            }}
            QPushButton:hover {{
                background-color: {Theme.COLORS['accent_primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: {Theme.COLORS['accent_primary']};
            }}
            QPushButton:disabled {{
                background-color: {Theme.COLORS['bg_tertiary']};
                color: {Theme.COLORS['text_muted']};
            }}
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_frame_layout.addWidget(self._send_btn, alignment=QtCore.Qt.AlignBottom)

        input_layout.addWidget(input_frame)

        # Hint text
        hint = QtWidgets.QLabel("Enter to send  ·  Shift+Enter for new line")
        hint.setStyleSheet(f"""
            color: {Theme.COLORS['text_muted']};
            font-size: {Theme.FONTS['size_xs']};
            background: transparent;
        """)
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
                    return False
                else:
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
        if stream:
            self._pending_debug_info = debug_info
            self._streaming_row = self._chat_list.add_streaming_message(MessageRole.ASSISTANT)
            self._streaming_controller.start_streaming(text)
        else:
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

    def add_preview_message(self, description: str, preview_items: List[Dict], code: str,
                            is_deletion: bool = False):
        """Add a preview message with approve/cancel buttons."""
        self._chat_list.add_preview_message(description, preview_items, code, is_deletion)

    def add_message_from_dict(self, msg_dict: dict, show_debug: bool = False):
        """Load a message from session JSON."""
        role = msg_dict.get("role", "system")
        text = msg_dict.get("text", "")
        changes = msg_dict.get("changes")

        if changes:
            self.add_change_message(changes)
            return

        if role == MessageRole.SYSTEM or role == "system":
            return

        debug_info = msg_dict.get("debug_info") if show_debug else None

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
        if self._streaming_row >= 0:
            message = self._chat_list._model.get_message(self._streaming_row)
            if message:
                self._chat_list.update_streaming_message(
                    self._streaming_row,
                    message.text,
                    is_complete=True
                )

            widget_count = len(self._chat_list._message_widgets)
            if self._pending_debug_info and self._streaming_row < widget_count:
                widget = self._chat_list._message_widgets[self._streaming_row]
                widget.add_debug_info(self._pending_debug_info)
                self._pending_debug_info = None

        self._streaming_row = -1

    def skip_streaming(self):
        """Skip current streaming animation."""
        self._streaming_controller.skip_to_end()
