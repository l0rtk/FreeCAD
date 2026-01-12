# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Message Delegate - Custom rendering for chat message bubbles.
Uses widget-based approach for rich content (code blocks, buttons).
"""

from PySide6 import QtWidgets, QtCore, QtGui
from .MessageModel import ChatMessage, MessageRole
from .CodeBlockWidget import CodeBlockWidget
import re


class AvatarWidget(QtWidgets.QLabel):
    """Circular avatar with initials."""

    def __init__(self, text: str, bg_color: str, text_color: str, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(28, 28)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 14px;
                font-weight: bold;
                font-size: 11px;
            }}
        """)


class DebugInfoWidget(QtWidgets.QWidget):
    """Collapsible debug info panel for LLM requests."""

    def __init__(self, debug_info: dict, parent=None):
        super().__init__(parent)
        self._debug_info = debug_info
        self._expanded = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(4)

        # Toggle button
        self._toggle_btn = QtWidgets.QPushButton("▶ Debug Info")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                color: #6b7280;
                font-size: 11px;
                text-align: left;
                padding: 4px 8px;
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #9ca3af;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self._toggle_btn)

        # Content (hidden by default)
        self._content = QtWidgets.QFrame()
        self._content.setVisible(False)
        self._content.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                border: 1px solid #30363d;
            }
        """)
        content_layout = QtWidgets.QVBoxLayout(self._content)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(6)

        # Stats
        duration = self._debug_info.get('duration_ms', 0)
        model = self._debug_info.get('model', 'unknown')
        context_len = self._debug_info.get('context_length', 0)

        stats_text = f"Duration: {duration:.0f}ms  |  Model: {model}  |  Context: {context_len} chars"
        stats_label = QtWidgets.QLabel(stats_text)
        stats_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 11px;
                font-family: monospace;
                background: transparent;
            }
        """)
        content_layout.addWidget(stats_label)

        # Buttons to show full data
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)

        prompt_btn = QtWidgets.QPushButton("System Prompt")
        prompt_btn.setCursor(QtCore.Qt.PointingHandCursor)
        prompt_btn.setStyleSheet(self._button_style())
        prompt_btn.clicked.connect(
            lambda: self._show_text("System Prompt", self._debug_info.get("system_prompt", ""))
        )
        btn_layout.addWidget(prompt_btn)

        context_btn = QtWidgets.QPushButton("Context")
        context_btn.setCursor(QtCore.Qt.PointingHandCursor)
        context_btn.setStyleSheet(self._button_style())
        context_btn.clicked.connect(
            lambda: self._show_text("Document Context", self._debug_info.get("context", ""))
        )
        btn_layout.addWidget(context_btn)

        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)

        layout.addWidget(self._content)

    def _button_style(self):
        return """
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #484f58;
            }
        """

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._toggle_btn.setText("▼ Debug Info" if self._expanded else "▶ Debug Info")

    def _show_text(self, title: str, text: str):
        """Show full text in a dialog."""
        dialog = QtWidgets.QDialog(self.window())
        dialog.setWindowTitle(title)
        dialog.resize(700, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
        """)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)

        text_edit = QtWidgets.QPlainTextEdit(text)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 8px;
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
                font-size: 12px;
                padding: 12px;
            }
        """)
        layout.addWidget(text_edit)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #30363d;
            }
        """)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=QtCore.Qt.AlignRight)

        dialog.exec()


class MessageBubbleWidget(QtWidgets.QFrame):
    """Widget representing a single message bubble."""

    runCodeRequested = QtCore.Signal(str)

    # Colors - more vibrant and Cursor-like
    COLORS = {
        MessageRole.USER: {
            "bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2d3748, stop:1 #1a202c)",
            "bg_solid": "#2d3748",
            "text": "#e2e8f0",
            "name": "#a0aec0",
            "name_text": "You",
            "avatar_bg": "#4a5568",
            "avatar_text": "#fff",
            "avatar_icon": "U"
        },
        MessageRole.ASSISTANT: {
            "bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #374151, stop:1 #1f2937)",
            "bg_solid": "#374151",
            "text": "#f3f4f6",
            "name": "#10b981",
            "name_text": "AI",
            "avatar_bg": "#10b981",
            "avatar_text": "#fff",
            "avatar_icon": "AI"
        },
        MessageRole.SYSTEM: {
            "bg": "transparent",
            "bg_solid": "transparent",
            "text": "#9ca3af",
            "name": "#6b7280",
            "name_text": "",
            "avatar_bg": "#4b5563",
            "avatar_text": "#fff",
            "avatar_icon": "S"
        },
        MessageRole.ERROR: {
            "bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7f1d1d, stop:1 #450a0a)",
            "bg_solid": "#7f1d1d",
            "text": "#fca5a5",
            "name": "#f87171",
            "name_text": "Error",
            "avatar_bg": "#dc2626",
            "avatar_text": "#fff",
            "avatar_icon": "!"
        }
    }

    def __init__(self, message: ChatMessage, parent=None, debug_info: dict = None):
        super().__init__(parent)
        self._message = message
        self._code_widgets = []
        self._content_frame = None
        self._content_layout = None
        self._setup_ui()

        # Add debug info if provided
        if debug_info:
            self.add_debug_info(debug_info)

    def _setup_ui(self):
        """Build the bubble UI."""
        role = self._message.role
        colors = self.COLORS.get(role, self.COLORS[MessageRole.ASSISTANT])

        # Main horizontal layout: avatar + content
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(10)

        # For system messages, center and simplify
        if role == MessageRole.SYSTEM:
            main_layout.setAlignment(QtCore.Qt.AlignCenter)
            label = QtWidgets.QLabel(self._message.text)
            label.setStyleSheet(f"""
                QLabel {{
                    color: {colors['text']};
                    font-size: 12px;
                    font-style: italic;
                    padding: 8px 16px;
                    background-color: rgba(75, 85, 99, 0.3);
                    border-radius: 12px;
                }}
            """)
            main_layout.addWidget(label)
            return

        # Avatar
        avatar = AvatarWidget(
            colors['avatar_icon'],
            colors['avatar_bg'],
            colors['avatar_text']
        )
        main_layout.addWidget(avatar, alignment=QtCore.Qt.AlignTop)

        # Content container
        self._content_frame = QtWidgets.QFrame()
        self._content_frame.setStyleSheet(f"""
            QFrame {{
                background: {colors['bg']};
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)

        self._content_layout = QtWidgets.QVBoxLayout(self._content_frame)
        self._content_layout.setContentsMargins(14, 10, 14, 12)
        self._content_layout.setSpacing(8)

        # Role label (name) - only if not empty
        if colors['name_text']:
            name_label = QtWidgets.QLabel(colors['name_text'])
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: {colors['name']};
                    font-weight: 600;
                    font-size: 12px;
                    background: transparent;
                    border: none;
                }}
            """)
            self._content_layout.addWidget(name_label)

        # Parse and display content
        self._render_content(self._content_layout, colors)

        main_layout.addWidget(self._content_frame, stretch=1)

        # Add spacer on the right for user messages to push content left
        # (or we could right-align user messages, but keeping consistent for now)

    def add_debug_info(self, debug_info: dict):
        """Add debug info widget to the message."""
        if self._content_layout and self._message.role == MessageRole.ASSISTANT:
            debug_widget = DebugInfoWidget(debug_info)
            self._content_layout.addWidget(debug_widget)

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
                        line-height: 1.5;
                        background: transparent;
                        border: none;
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

        # Re-setup UI
        self._code_widgets = []
        self._setup_ui_content()

    def _setup_ui_content(self):
        """Rebuild just the content part."""
        role = self._message.role
        colors = self.COLORS.get(role, self.COLORS[MessageRole.ASSISTANT])

        main_layout = self.layout()

        if role == MessageRole.SYSTEM:
            main_layout.setAlignment(QtCore.Qt.AlignCenter)
            label = QtWidgets.QLabel(self._message.displayed_text or self._message.text)
            label.setStyleSheet(f"""
                QLabel {{
                    color: {colors['text']};
                    font-size: 12px;
                    font-style: italic;
                    padding: 8px 16px;
                    background-color: rgba(75, 85, 99, 0.3);
                    border-radius: 12px;
                }}
            """)
            main_layout.addWidget(label)
            return

        # Avatar
        avatar = AvatarWidget(
            colors['avatar_icon'],
            colors['avatar_bg'],
            colors['avatar_text']
        )
        main_layout.addWidget(avatar, alignment=QtCore.Qt.AlignTop)

        # Content container
        content_frame = QtWidgets.QFrame()
        content_frame.setStyleSheet(f"""
            QFrame {{
                background: {colors['bg']};
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)

        content_layout = QtWidgets.QVBoxLayout(content_frame)
        content_layout.setContentsMargins(14, 10, 14, 12)
        content_layout.setSpacing(8)

        if colors['name_text']:
            name_label = QtWidgets.QLabel(colors['name_text'])
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: {colors['name']};
                    font-weight: 600;
                    font-size: 12px;
                    background: transparent;
                    border: none;
                }}
            """)
            content_layout.addWidget(name_label)

        self._render_content(content_layout, colors)
        main_layout.addWidget(content_frame, stretch=1)


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
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(10)

        # Avatar
        avatar = AvatarWidget("AI", "#10b981", "#fff")
        main_layout.addWidget(avatar, alignment=QtCore.Qt.AlignTop)

        # Bubble
        bubble = QtWidgets.QFrame()
        bubble.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #374151, stop:1 #1f2937);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        bubble_layout = QtWidgets.QHBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 14, 16, 14)
        bubble_layout.setSpacing(4)

        # Three dots
        self._dots = []
        for i in range(3):
            dot = QtWidgets.QLabel("●")
            dot.setStyleSheet("color: #6b7280; font-size: 14px; background: transparent;")
            self._dots.append(dot)
            bubble_layout.addWidget(dot)

        main_layout.addWidget(bubble)
        main_layout.addStretch()

    def start(self):
        """Start the animation."""
        self._timer.start(400)

    def stop(self):
        """Stop the animation."""
        self._timer.stop()

    def _animate(self):
        """Animate the dots with bounce effect."""
        for i, dot in enumerate(self._dots):
            if i == self._dot_index:
                dot.setStyleSheet("color: #10b981; font-size: 14px; background: transparent;")
            else:
                dot.setStyleSheet("color: #6b7280; font-size: 14px; background: transparent;")

        self._dot_index = (self._dot_index + 1) % 3
