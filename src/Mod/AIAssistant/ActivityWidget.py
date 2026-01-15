# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Activity Widget - Collapsible widget showing Claude Code tool activity.
Displays what tools (Glob, Read, Grep) Claude used during a request.
"""

from PySide6 import QtCore, QtWidgets
from typing import List, Dict
from . import Theme


# Tool icons for display (emoji)
TOOL_ICONS = {
    "Glob": "\U0001F50D",      # 🔍
    "Read": "\U0001F4C4",      # 📄
    "Grep": "\U0001F50E",      # 🔎
    "Edit": "\U0000270F",      # ✏️
    "Bash": "\U0001F4BB",      # 💻
    "Task": "\U0001F4CB",      # 📋
    "WebFetch": "\U0001F310",  # 🌐
    "WebSearch": "\U0001F310", # 🌐
}


def format_tool_call(tool: str, input_data: dict) -> str:
    """Format a tool call for display.

    Args:
        tool: Tool name (Glob, Read, Grep, Bash, Task, etc.)
        input_data: Tool input parameters

    Returns:
        Formatted string for display
    """
    icon = TOOL_ICONS.get(tool, "\U0001F527")  # 🔧 default

    if tool == "Glob":
        pattern = input_data.get("pattern", "")
        return f"{icon} Glob: {pattern}"
    elif tool == "Read":
        path = input_data.get("file_path", "")
        # Truncate long paths - show last 50 chars
        if len(path) > 50:
            path = "..." + path[-47:]
        return f"{icon} Read: {path}"
    elif tool == "Grep":
        pattern = input_data.get("pattern", "")
        path = input_data.get("path", ".")
        if len(path) > 30:
            path = "..." + path[-27:]
        return f"{icon} Grep: '{pattern}' in {path}"
    elif tool == "Edit":
        path = input_data.get("file_path", "")
        # Show just filename for source.py edits
        if "/" in path:
            path = path.split("/")[-1]
        return f"{icon} Edit: {path}"
    elif tool == "Bash":
        cmd = input_data.get("command", "")
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        return f"{icon} Bash: {cmd}"
    elif tool == "Task":
        desc = input_data.get("description", "")
        prompt = input_data.get("prompt", "")[:40]
        if desc:
            return f"{icon} Task: {desc}"
        return f"{icon} Task: {prompt}..."
    elif tool == "WebFetch":
        url = input_data.get("url", "")
        if len(url) > 50:
            url = url[:47] + "..."
        return f"{icon} Fetch: {url}"
    elif tool == "WebSearch":
        query = input_data.get("query", "")
        return f"{icon} Search: {query}"
    else:
        # Generic fallback - show first meaningful value
        for key in ["pattern", "path", "file_path", "command", "query", "prompt"]:
            if key in input_data:
                val = str(input_data[key])[:50]
                return f"{icon} {tool}: {val}"
        return f"{icon} {tool}"


class ActivityWidget(QtWidgets.QFrame):
    """Collapsible widget showing Claude Code tool activity.

    Displays what tools Claude used (Glob, Read, Grep) during a request,
    giving users visibility into Claude's exploration of the codebase.
    """

    def __init__(self, tool_calls: List[Dict], parent=None):
        """Initialize the activity widget.

        Args:
            tool_calls: List of dicts with 'tool' and 'input' keys
            parent: Parent widget
        """
        super().__init__(parent)
        self._tool_calls = tool_calls
        self._expanded = True  # Start expanded to show details
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        self.setObjectName("ActivityWidget")
        self._update_style()
        # Ensure widget has minimum size for visibility
        self.setMinimumHeight(40)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        # Header row (always visible)
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        # Expand/collapse button
        self._expand_btn = QtWidgets.QPushButton("+" if not self._expanded else "-")
        self._expand_btn.setFixedSize(18, 18)
        self._expand_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._expand_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.COLORS['bg_tertiary']};
                color: {Theme.COLORS['text_muted']};
                border: none;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {Theme.COLORS['bg_hover']};
                color: {Theme.COLORS['text_primary']};
            }}
        """)
        self._expand_btn.clicked.connect(self._toggle_expand)
        header_layout.addWidget(self._expand_btn)

        # Activity label
        count = len(self._tool_calls)
        activity_text = f"Activity ({count} step{'s' if count != 1 else ''})"
        self._header_label = QtWidgets.QLabel(activity_text)
        self._header_label.setStyleSheet(f"""
            color: {Theme.COLORS['text_muted']};
            font-size: {Theme.FONTS['size_xs']};
            background: transparent;
        """)
        header_layout.addWidget(self._header_label)

        header_layout.addStretch()
        layout.addWidget(header)

        # Expandable content
        self._content = QtWidgets.QWidget()
        self._content.setVisible(self._expanded)
        content_layout = QtWidgets.QVBoxLayout(self._content)
        content_layout.setContentsMargins(24, 4, 0, 0)  # Indent under header
        content_layout.setSpacing(2)

        # Add tool call items
        for tool_call in self._tool_calls:
            item_label = QtWidgets.QLabel(
                format_tool_call(tool_call.get("tool", ""), tool_call.get("input", {}))
            )
            item_label.setStyleSheet(f"""
                color: {Theme.COLORS['text_secondary']};
                font-size: {Theme.FONTS['size_xs']};
                font-family: monospace;
                background: transparent;
            """)
            item_label.setWordWrap(True)
            content_layout.addWidget(item_label)

        layout.addWidget(self._content)

    def _update_style(self):
        """Update widget style."""
        self.setStyleSheet(f"""
            #ActivityWidget {{
                background-color: {Theme.COLORS['bg_tertiary']};
                border: 1px solid {Theme.COLORS['border_subtle']};
                border-radius: {Theme.RADIUS['sm']};
            }}
        """)

    def _toggle_expand(self):
        """Toggle expanded state."""
        self._expanded = not self._expanded
        self._expand_btn.setText("-" if self._expanded else "+")
        self._content.setVisible(self._expanded)

    def is_expanded(self) -> bool:
        """Check if widget is expanded."""
        return self._expanded

    def set_expanded(self, expanded: bool):
        """Set expanded state."""
        if self._expanded != expanded:
            self._toggle_expand()

    def get_tool_calls(self) -> List[Dict]:
        """Get the tool calls."""
        return self._tool_calls
