# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Message Delegate - Custom rendering for chat message bubbles.
Uses widget-based approach for rich content (code blocks, buttons).
"""

from PySide6 import QtWidgets, QtCore, QtGui
from .MessageModel import ChatMessage, MessageRole
from .CodeBlockWidget import CodeBlockWidget
import re


class MessageBubbleWidget(QtWidgets.QFrame):
    """Widget representing a single message bubble."""

    runCodeRequested = QtCore.Signal(str)

    # Colors
    COLORS = {
        MessageRole.USER: {
            "bg": "#2a4a7a",
            "text": "#ffffff",
            "name": "#7eb3ff",
            "name_text": "You"
        },
        MessageRole.ASSISTANT: {
            "bg": "#2d2d2d",
            "text": "#e0e0e0",
            "name": "#98c379",
            "name_text": "AI"
        },
        MessageRole.SYSTEM: {
            "bg": "#1a1a2e",
            "text": "#888888",
            "name": "#636d83",
            "name_text": "System"
        },
        MessageRole.ERROR: {
            "bg": "#3d1f1f",
            "text": "#ff6b6b",
            "name": "#e06c75",
            "name_text": "Error"
        }
    }

    def __init__(self, message: ChatMessage, parent=None):
        super().__init__(parent)
        self._message = message
        self._code_widgets = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the bubble UI."""
        role = self._message.role
        colors = self.COLORS.get(role, self.COLORS[MessageRole.ASSISTANT])

        # Container styling
        self.setStyleSheet(f"""
            MessageBubbleWidget {{
                background-color: {colors['bg']};
                border-radius: 12px;
                margin: 4px 8px;
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(6)

        # Role label (name)
        name_label = QtWidgets.QLabel(colors['name_text'])
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['name']};
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        layout.addWidget(name_label)

        # Parse and display content
        self._render_content(layout, colors)

    def _render_content(self, layout: QtWidgets.QVBoxLayout, colors: dict):
        """Render message content with code blocks."""
        text = self._message.displayed_text or self._message.text

        # Check if entire message is code (from AI generating code)
        if self._message.role == MessageRole.ASSISTANT and self._looks_like_pure_code(text):
            # Render as single code block
            code_widget = CodeBlockWidget(text.strip(), "python")
            code_widget.runRequested.connect(self.runCodeRequested.emit)
            self._code_widgets.append(code_widget)
            layout.addWidget(code_widget)
            return

        # Split text by code blocks
        parts = self._split_by_code_blocks(text)

        for part_type, content in parts:
            if part_type == "text" and content.strip():
                # Regular text
                label = QtWidgets.QLabel(content.strip())
                label.setWordWrap(True)
                label.setTextInteractionFlags(
                    QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
                )
                label.setStyleSheet(f"""
                    QLabel {{
                        color: {colors['text']};
                        font-size: 13px;
                        line-height: 1.4;
                    }}
                """)
                layout.addWidget(label)

            elif part_type == "code":
                # Code block
                lang, code = content
                code_widget = CodeBlockWidget(code, lang)
                code_widget.runRequested.connect(self.runCodeRequested.emit)
                self._code_widgets.append(code_widget)
                layout.addWidget(code_widget)

    def _looks_like_pure_code(self, text: str) -> bool:
        """Check if text appears to be pure code (no markdown)."""
        text = text.strip()
        # If it starts with common code patterns and has no markdown
        code_starters = ['import ', 'from ', 'def ', 'class ', '#', 'doc =', 'FreeCAD.']
        has_markdown = text.startswith('```') or '```' in text
        starts_with_code = any(text.startswith(s) for s in code_starters)
        return starts_with_code and not has_markdown

    def _split_by_code_blocks(self, text: str):
        """Split text into text parts and code blocks."""
        parts = []
        pattern = r'```(\w+)?\n?(.*?)```'

        last_end = 0
        for match in re.finditer(pattern, text, re.DOTALL):
            # Text before code block
            if match.start() > last_end:
                parts.append(("text", text[last_end:match.start()]))

            # Code block
            lang = match.group(1) or "python"
            code = match.group(2).strip()
            parts.append(("code", (lang, code)))

            last_end = match.end()

        # Remaining text
        if last_end < len(text):
            parts.append(("text", text[last_end:]))

        # If no parts, treat entire text as text
        if not parts:
            parts.append(("text", text))

        return parts

    def update_displayed_text(self, text: str):
        """Update the displayed text (for streaming)."""
        self._message.displayed_text = text
        # Rebuild UI
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        colors = self.COLORS.get(self._message.role, self.COLORS[MessageRole.ASSISTANT])

        # Re-add name label
        name_label = QtWidgets.QLabel(colors['name_text'])
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['name']};
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        layout.addWidget(name_label)

        self._code_widgets = []
        self._render_content(layout, colors)


class TypingIndicatorWidget(QtWidgets.QFrame):
    """Animated typing indicator (three bouncing dots)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dot_index = 0
        self._setup_ui()

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._animate)

    def _setup_ui(self):
        """Build the indicator UI."""
        self.setStyleSheet("""
            TypingIndicatorWidget {
                background-color: #2d2d2d;
                border-radius: 12px;
                margin: 4px 8px;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # AI label
        ai_label = QtWidgets.QLabel("AI")
        ai_label.setStyleSheet("""
            QLabel {
                color: #98c379;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        layout.addWidget(ai_label)

        layout.addSpacing(8)

        # Three dots
        self._dots = []
        for i in range(3):
            dot = QtWidgets.QLabel("●")
            dot.setStyleSheet("color: #636d83; font-size: 10px;")
            self._dots.append(dot)
            layout.addWidget(dot)

        layout.addStretch()

    def start(self):
        """Start the animation."""
        self._timer.start(300)

    def stop(self):
        """Stop the animation."""
        self._timer.stop()

    def _animate(self):
        """Animate the dots."""
        for i, dot in enumerate(self._dots):
            if i == self._dot_index:
                dot.setStyleSheet("color: #98c379; font-size: 10px;")
            else:
                dot.setStyleSheet("color: #636d83; font-size: 10px;")

        self._dot_index = (self._dot_index + 1) % 3
