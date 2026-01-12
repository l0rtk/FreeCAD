# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Message Model - Data structures and Qt model for chat messages.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import re

from PySide6 import QtCore


@dataclass
class CodeBlock:
    """Represents a code block extracted from a message."""
    code: str
    language: str = "python"
    start_pos: int = 0
    end_pos: int = 0


@dataclass
class ChatMessage:
    """Represents a single chat message."""
    text: str
    role: str  # 'user', 'assistant', 'system', 'error'
    timestamp: datetime = field(default_factory=datetime.now)
    code_blocks: List[CodeBlock] = field(default_factory=list)
    is_streaming: bool = False
    displayed_text: str = ""  # For streaming animation

    def __post_init__(self):
        if not self.displayed_text:
            self.displayed_text = self.text
        self._extract_code_blocks()

    def _extract_code_blocks(self):
        """Extract code blocks from the message text."""
        self.code_blocks = []
        pattern = r'```(\w+)?\n?(.*?)```'
        for match in re.finditer(pattern, self.text, re.DOTALL):
            language = match.group(1) or "python"
            code = match.group(2).strip()
            self.code_blocks.append(CodeBlock(
                code=code,
                language=language,
                start_pos=match.start(),
                end_pos=match.end()
            ))

    def get_plain_text(self) -> str:
        """Get text without code block markers."""
        text = self.displayed_text
        # Remove code blocks for plain text display
        text = re.sub(r'```\w*\n?', '', text)
        text = re.sub(r'```', '', text)
        return text.strip()

    def has_code(self) -> bool:
        """Check if message contains code blocks."""
        return len(self.code_blocks) > 0 or self._looks_like_code()

    def _looks_like_code(self) -> bool:
        """Heuristic check if text looks like code."""
        code_indicators = ['import ', 'def ', 'class ', 'FreeCAD.', 'Arch.', '=', '()', 'doc.']
        return any(ind in self.text for ind in code_indicators)


class MessageRole:
    """Constants for message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


class ChatMessageModel(QtCore.QAbstractListModel):
    """Qt model for chat messages."""

    # Custom roles
    TextRole = QtCore.Qt.UserRole + 1
    RoleRole = QtCore.Qt.UserRole + 2
    TimestampRole = QtCore.Qt.UserRole + 3
    CodeBlocksRole = QtCore.Qt.UserRole + 4
    IsStreamingRole = QtCore.Qt.UserRole + 5
    DisplayedTextRole = QtCore.Qt.UserRole + 6
    HasCodeRole = QtCore.Qt.UserRole + 7

    # Signal emitted when a message is added (for session persistence)
    message_added = QtCore.Signal(object)  # Emits ChatMessage

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages: List[ChatMessage] = []

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._messages)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._messages):
            return None

        message = self._messages[index.row()]

        if role == QtCore.Qt.DisplayRole or role == self.TextRole:
            return message.text
        elif role == self.RoleRole:
            return message.role
        elif role == self.TimestampRole:
            return message.timestamp
        elif role == self.CodeBlocksRole:
            return message.code_blocks
        elif role == self.IsStreamingRole:
            return message.is_streaming
        elif role == self.DisplayedTextRole:
            return message.displayed_text
        elif role == self.HasCodeRole:
            return message.has_code()

        return None

    def roleNames(self):
        return {
            QtCore.Qt.DisplayRole: b"display",
            self.TextRole: b"text",
            self.RoleRole: b"role",
            self.TimestampRole: b"timestamp",
            self.CodeBlocksRole: b"codeBlocks",
            self.IsStreamingRole: b"isStreaming",
            self.DisplayedTextRole: b"displayedText",
            self.HasCodeRole: b"hasCode",
        }

    def add_message(self, text: str, role: str, is_streaming: bool = False) -> int:
        """Add a new message and return its index."""
        row = len(self._messages)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)

        message = ChatMessage(
            text=text,
            role=role,
            is_streaming=is_streaming,
            displayed_text="" if is_streaming else text
        )
        self._messages.append(message)

        self.endInsertRows()

        # Emit signal for session persistence (only for non-streaming messages)
        if not is_streaming:
            self.message_added.emit(message)

        return row

    def update_message(self, row: int, text: str = None, displayed_text: str = None,
                       is_streaming: bool = None):
        """Update an existing message."""
        if row < 0 or row >= len(self._messages):
            return

        message = self._messages[row]
        was_streaming = message.is_streaming

        if text is not None:
            message.text = text
            message._extract_code_blocks()
        if displayed_text is not None:
            message.displayed_text = displayed_text
        if is_streaming is not None:
            message.is_streaming = is_streaming

        index = self.index(row)
        self.dataChanged.emit(index, index)

        # Emit signal when streaming completes (for session persistence)
        if was_streaming and is_streaming is False:
            self.message_added.emit(message)

    def get_message(self, row: int) -> Optional[ChatMessage]:
        """Get message at row."""
        if 0 <= row < len(self._messages):
            return self._messages[row]
        return None

    def clear(self):
        """Clear all messages."""
        self.beginResetModel()
        self._messages = []
        self.endResetModel()

    def get_conversation_history(self) -> List[dict]:
        """Get conversation history for LLM context."""
        history = []
        for msg in self._messages:
            if msg.role in (MessageRole.USER, MessageRole.ASSISTANT):
                history.append({
                    "role": msg.role,
                    "content": msg.text
                })
        return history[-20:]  # Last 10 exchanges

    def message_count(self) -> int:
        """Return number of messages."""
        return len(self._messages)
