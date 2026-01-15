# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Message Delegate - Modern card-based message rendering.
Cursor-inspired design with clean cards, no avatars, and skeleton loading.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from .MessageModel import ChatMessage, MessageRole
from .CodeBlockWidget import CodeBlockWidget
from . import Theme
import re


class DebugInfoWidget(QtWidgets.QWidget):
    """Collapsible debug info panel for LLM requests."""

    def __init__(self, debug_info: dict, parent=None):
        super().__init__(parent)
        self._debug_info = debug_info
        self._expanded = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(4)

        # Toggle button
        self._toggle_btn = QtWidgets.QPushButton("Debug Info")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                color: {Theme.COLORS['debug_accent']};
                font-size: {Theme.FONTS['size_xs']};
                text-align: left;
                padding: 4px 8px;
                background: transparent;
                border: none;
                font-weight: {Theme.FONTS['weight_medium']};
            }}
            QPushButton:hover {{
                color: {Theme.COLORS['accent_primary_hover']};
            }}
        """)
        self._toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self._toggle_btn)

        # Content
        self._content = QtWidgets.QFrame()
        self._content.setVisible(True)
        self._content.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.COLORS['debug_bg']};
                border-radius: {Theme.RADIUS['sm']};
                border: 1px solid {Theme.COLORS['debug_border']};
            }}
        """)
        content_layout = QtWidgets.QVBoxLayout(self._content)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(8)

        # Stats
        duration = self._debug_info.get('duration_ms', 0)
        model = self._debug_info.get('model', 'unknown')
        context_len = self._debug_info.get('context_length', 0)
        history_len = len(self._debug_info.get('conversation_history', []))

        stats_text = f"{duration:.0f}ms  ·  {model}  ·  {context_len} chars  ·  {history_len} msgs"
        stats_label = QtWidgets.QLabel(stats_text)
        stats_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['debug_accent']};
                font-size: {Theme.FONTS['size_xs']};
                font-family: {Theme.FONTS['family_mono']};
                background: transparent;
            }}
        """)
        content_layout.addWidget(stats_label)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)

        for btn_text, btn_handler in [
            ("Full Request", self._show_full_request),
            ("System Prompt", lambda: self._show_text("System Prompt", self._debug_info.get("system_prompt", ""))),
            ("Context", lambda: self._show_text("Document Context", self._debug_info.get("context", ""))),
        ]:
            btn = QtWidgets.QPushButton(btn_text)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet(Theme.get_button_ghost_style())
            btn.clicked.connect(btn_handler)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)
        layout.addWidget(self._content)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)

    def _show_full_request(self):
        """Show the complete request sent to the LLM."""
        lines = []
        lines.append("=" * 60)
        lines.append("FULL LLM REQUEST")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Model: {self._debug_info.get('model', 'unknown')}")
        lines.append(f"Duration: {self._debug_info.get('duration_ms', 0):.0f}ms")
        lines.append(f"Context Length: {self._debug_info.get('context_length', 0)} chars")
        lines.append("")
        lines.append("-" * 60)
        lines.append("USER MESSAGE:")
        lines.append("-" * 60)
        lines.append(self._debug_info.get('user_message', '(none)'))
        lines.append("")

        history = self._debug_info.get('conversation_history', [])
        if history:
            lines.append("-" * 60)
            lines.append(f"CONVERSATION HISTORY ({len(history)} messages):")
            lines.append("-" * 60)
            for i, msg in enumerate(history):
                role = msg.get('role', 'unknown').upper()
                content = msg.get('content', '')
                lines.append(f"\n[{i+1}] {role}:")
                lines.append(content[:500] + "..." if len(content) > 500 else content)
            lines.append("")

        context = self._debug_info.get('context', '')
        lines.append("-" * 60)
        lines.append("DOCUMENT CONTEXT (RAG):")
        lines.append("-" * 60)
        lines.append(context if context else "(no context)")
        lines.append("")
        lines.append("-" * 60)
        lines.append("SYSTEM PROMPT:")
        lines.append("-" * 60)
        lines.append(self._debug_info.get('system_prompt', '(none)'))

        self._show_text("Full LLM Request", "\n".join(lines))

    def _show_text(self, title: str, text: str):
        """Show full text in a dialog."""
        dialog = QtWidgets.QDialog(self.window())
        dialog.setWindowTitle(title)
        dialog.resize(700, 500)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {Theme.COLORS['bg_primary']};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)

        text_edit = QtWidgets.QPlainTextEdit(text)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {Theme.COLORS['bg_secondary']};
                color: {Theme.COLORS['text_primary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['sm']};
                font-family: {Theme.FONTS['family_mono']};
                font-size: {Theme.FONTS['size_sm']};
                padding: 12px;
            }}
        """)
        layout.addWidget(text_edit)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setStyleSheet(Theme.get_button_ghost_style())
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=QtCore.Qt.AlignRight)

        dialog.exec()


class MessageCard(QtWidgets.QFrame):
    """Modern message card - no avatars, clean design."""

    runCodeRequested = QtCore.Signal(str)

    def __init__(self, message: ChatMessage, parent=None, debug_info: dict = None):
        super().__init__(parent)
        self._message = message
        self._debug_info = debug_info
        self._code_widgets = []
        self._content_layout = None
        self._text_label = None
        self._setup_ui()
        self._setup_entry_animation()

    def _setup_ui(self):
        """Build the card UI based on message role."""
        role = self._message.role

        if role == MessageRole.SYSTEM:
            self._setup_system_message()
        elif role == MessageRole.USER:
            self._setup_user_message()
        elif role == MessageRole.ERROR:
            self._setup_error_message()
        else:  # ASSISTANT
            self._setup_assistant_message()

    def _setup_entry_animation(self):
        """Setup fade-in animation for the message."""
        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)

        self._fade_anim = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(Theme.ANIMATION['duration_normal'])
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._fade_anim.start()

    def _setup_user_message(self):
        """User message: right-aligned, no background."""
        self.setStyleSheet("background: transparent;")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(60, 8, 12, 8)  # Left margin to push right
        layout.setSpacing(0)

        # Spacer to push content right
        layout.addStretch()

        # Text label
        self._text_label = QtWidgets.QLabel(self._message.displayed_text or self._message.text)
        self._text_label.setWordWrap(True)
        self._text_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self._text_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['user_msg_text']};
                font-size: {Theme.FONTS['size_base']};
                line-height: {Theme.FONTS['line_height_normal']};
                background: transparent;
                padding: 0;
            }}
        """)
        self._text_label.setAlignment(QtCore.Qt.AlignRight)
        layout.addWidget(self._text_label)

    def _setup_assistant_message(self):
        """Assistant message: card with subtle border."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.COLORS['assistant_card_bg']};
                border: 1px solid {Theme.COLORS['assistant_card_border']};
                border-radius: {Theme.RADIUS['lg']};
            }}
        """)

        self._content_layout = QtWidgets.QVBoxLayout(self)
        self._content_layout.setContentsMargins(16, 14, 16, 14)
        self._content_layout.setSpacing(10)

        # Render content
        self._render_content()

        # Add debug info if provided
        if self._debug_info:
            debug_widget = DebugInfoWidget(self._debug_info)
            self._content_layout.addWidget(debug_widget)

    def _setup_system_message(self):
        """System message: centered, muted text."""
        self.setStyleSheet("background: transparent;")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        label = QtWidgets.QLabel(self._message.text)
        label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['system_text']};
                font-size: {Theme.FONTS['size_sm']};
                font-style: italic;
                background: transparent;
            }}
        """)
        layout.addWidget(label)

    def _setup_error_message(self):
        """Error message: red-tinted card."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.COLORS['error_bg']};
                border: 1px solid {Theme.COLORS['error_border']};
                border-radius: {Theme.RADIUS['lg']};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Error indicator
        header = QtWidgets.QLabel("Error")
        header.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['accent_error']};
                font-size: {Theme.FONTS['size_sm']};
                font-weight: {Theme.FONTS['weight_semibold']};
                background: transparent;
            }}
        """)
        layout.addWidget(header)

        # Error text
        text = QtWidgets.QLabel(self._message.text)
        text.setWordWrap(True)
        text.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        text.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['error_text']};
                font-size: {Theme.FONTS['size_base']};
                line-height: {Theme.FONTS['line_height_normal']};
                background: transparent;
            }}
        """)
        layout.addWidget(text)

    def _render_content(self):
        """Render assistant message content with code blocks."""
        text = self._message.displayed_text or self._message.text

        # Check if entire message is code
        if self._looks_like_pure_code(text):
            code_widget = CodeBlockWidget(text.strip(), "python")
            code_widget.runRequested.connect(self.runCodeRequested.emit)
            self._code_widgets.append(code_widget)
            self._content_layout.addWidget(code_widget)
            return

        # Split text by code blocks
        parts = self._split_by_code_blocks(text)

        for part_type, content in parts:
            if part_type == "text" and content.strip():
                label = QtWidgets.QLabel(content.strip())
                label.setWordWrap(True)
                label.setTextInteractionFlags(
                    QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
                )
                label.setStyleSheet(f"""
                    QLabel {{
                        color: {Theme.COLORS['assistant_text']};
                        font-size: {Theme.FONTS['size_base']};
                        line-height: {Theme.FONTS['line_height_normal']};
                        background: transparent;
                    }}
                """)
                self._content_layout.addWidget(label)
                if self._text_label is None:
                    self._text_label = label

            elif part_type == "code":
                lang, code = content
                code_widget = CodeBlockWidget(code, lang)
                code_widget.runRequested.connect(self.runCodeRequested.emit)
                self._code_widgets.append(code_widget)
                self._content_layout.addWidget(code_widget)

        # Fallback: if no widgets were added and message is not streaming, show placeholder
        # For streaming messages with empty text, we skip this (text will come later)
        if self._content_layout.count() == 0 and not self._message.is_streaming:
            display_text = text.strip() if text.strip() else "(No response)"
            label = QtWidgets.QLabel(display_text)
            label.setWordWrap(True)
            label.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.COLORS['assistant_text']};
                    font-size: {Theme.FONTS['size_base']};
                    background: transparent;
                }}
            """)
            self._content_layout.addWidget(label)
            self._text_label = label

    def _looks_like_pure_code(self, text: str) -> bool:
        """Check if text appears to be pure code."""
        text = text.strip()
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
            if match.start() > last_end:
                parts.append(("text", text[last_end:match.start()]))

            lang = match.group(1) or "python"
            code = match.group(2).strip()
            parts.append(("code", (lang, code)))
            last_end = match.end()

        if last_end < len(text):
            parts.append(("text", text[last_end:]))

        if not parts:
            parts.append(("text", text))

        return parts

    def add_debug_info(self, debug_info: dict):
        """Add debug info widget to the message."""
        if self._content_layout and self._message.role == MessageRole.ASSISTANT:
            debug_widget = DebugInfoWidget(debug_info)
            self._content_layout.addWidget(debug_widget)

    def update_displayed_text(self, text: str):
        """Update the displayed text (for streaming)."""
        self._message.displayed_text = text

        # For assistant messages, rebuild content
        if self._message.role == MessageRole.ASSISTANT:
            # Clear existing content
            while self._content_layout.count():
                item = self._content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._code_widgets = []
            self._text_label = None
            self._render_content()
        elif self._text_label:
            self._text_label.setText(text)


class SkeletonBar(QtWidgets.QWidget):
    """A single skeleton loading bar with shimmer animation."""

    def __init__(self, width_percent: int = 100, parent=None):
        super().__init__(parent)
        self._width_percent = width_percent
        self._shimmer_pos = 0.0
        self.setFixedHeight(14)
        self.setMinimumWidth(50)

        # Animation timer
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._update_shimmer)

    def start(self):
        """Start shimmer animation."""
        self._timer.start(30)  # ~33fps

    def stop(self):
        """Stop shimmer animation."""
        self._timer.stop()

    def _update_shimmer(self):
        """Update shimmer position."""
        self._shimmer_pos += 0.02
        if self._shimmer_pos > 1.5:
            self._shimmer_pos = -0.5
        self.update()

    def paintEvent(self, event):
        """Paint the skeleton bar with shimmer effect."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Calculate bar width based on percent
        bar_width = int(self.width() * (self._width_percent / 100))
        bar_rect = QtCore.QRectF(0, 0, bar_width, self.height())

        # Base color
        base_color = QtGui.QColor(Theme.COLORS['skeleton_base'])
        shimmer_color = QtGui.QColor(Theme.COLORS['skeleton_shimmer'])

        # Create gradient for shimmer effect
        gradient = QtGui.QLinearGradient(0, 0, bar_width, 0)

        # Position the shimmer
        shimmer_start = self._shimmer_pos - 0.3
        shimmer_end = self._shimmer_pos + 0.3

        gradient.setColorAt(0, base_color)
        if 0 < shimmer_start < 1:
            gradient.setColorAt(max(0, shimmer_start), base_color)
        if 0 < self._shimmer_pos < 1:
            gradient.setColorAt(self._shimmer_pos, shimmer_color)
        if 0 < shimmer_end < 1:
            gradient.setColorAt(min(1, shimmer_end), base_color)
        gradient.setColorAt(1, base_color)

        painter.setBrush(QtGui.QBrush(gradient))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(bar_rect, 4, 4)


class ThinkingIndicator(QtWidgets.QFrame):
    """Modern thinking indicator with skeleton shimmer bars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_index = 0
        self._status_messages = [
            "Thinking...",
            "Analyzing...",
            "Generating...",
        ]
        self._setup_ui()

    def _setup_ui(self):
        """Build the indicator UI."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.COLORS['assistant_card_bg']};
                border: 1px solid {Theme.COLORS['assistant_card_border']};
                border-radius: {Theme.RADIUS['lg']};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Skeleton bars container
        bars_container = QtWidgets.QWidget()
        bars_layout = QtWidgets.QVBoxLayout(bars_container)
        bars_layout.setContentsMargins(0, 0, 0, 0)
        bars_layout.setSpacing(8)

        # Three bars with different widths
        self._bars = []
        for width in [65, 85, 45]:
            bar = SkeletonBar(width)
            self._bars.append(bar)
            bars_layout.addWidget(bar)

        layout.addWidget(bars_container)

        # Status text
        self._status_label = QtWidgets.QLabel(self._status_messages[0])
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['text_muted']};
                font-size: {Theme.FONTS['size_sm']};
                background: transparent;
            }}
        """)
        layout.addWidget(self._status_label)

        # Status rotation timer
        self._status_timer = QtCore.QTimer(self)
        self._status_timer.timeout.connect(self._rotate_status)

    def start(self):
        """Start the animation."""
        for bar in self._bars:
            bar.start()
        self._status_timer.start(2000)  # Rotate status every 2s

    def stop(self):
        """Stop the animation."""
        for bar in self._bars:
            bar.stop()
        self._status_timer.stop()

    def _rotate_status(self):
        """Rotate through status messages."""
        self._status_index = (self._status_index + 1) % len(self._status_messages)
        self._status_label.setText(self._status_messages[self._status_index])

    def set_status(self, status: str):
        """Set a custom status message."""
        self._status_label.setText(status)


# Backwards compatibility alias
MessageBubbleWidget = MessageCard
TypingIndicatorWidget = ThinkingIndicator
