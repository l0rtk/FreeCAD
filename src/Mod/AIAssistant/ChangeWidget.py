# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Change Widget - Displays document changes with color-coded visualization.

Shows created (green), modified (blue), and deleted (red) objects
with human-readable descriptions and collapsible code section.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from typing import Dict, List, Optional, Union
from .ChangeDetector import ChangeSet, ObjectChange


# Color palette matching the existing UI
CHANGE_COLORS = {
    "created": {
        "icon": "\u2713",  # Checkmark
        "bg": "rgba(16, 185, 129, 0.1)",
        "border": "#10b981",
        "text": "#10b981",
    },
    "modified": {
        "icon": "\u21bb",  # Clockwise arrow
        "bg": "rgba(88, 166, 255, 0.1)",
        "border": "#58a6ff",
        "text": "#58a6ff",
    },
    "deleted": {
        "icon": "\u2717",  # Cross mark
        "bg": "rgba(248, 113, 113, 0.1)",
        "border": "#f87171",
        "text": "#f87171",
    },
}


class ChangeItemWidget(QtWidgets.QFrame):
    """Single change item with icon, colored text, and optional details."""

    def __init__(self, change: Union[ObjectChange, Dict], parent=None):
        super().__init__(parent)
        self._change = change
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        # Get change type and colors
        if isinstance(self._change, ObjectChange):
            change_type = self._change.change_type
            display_text = self._change.to_string()
        else:
            change_type = self._change.get("change_type", "modified")
            display_text = self._change.get("display_text", "Unknown change")

        colors = CHANGE_COLORS.get(change_type, CHANGE_COLORS["modified"])

        self.setStyleSheet(f"""
            ChangeItemWidget {{
                background-color: {colors['bg']};
                border-left: 3px solid {colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
                margin: 2px 0;
            }}
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Icon
        icon_label = QtWidgets.QLabel(colors["icon"])
        icon_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text']};
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }}
        """)
        icon_label.setFixedWidth(20)
        layout.addWidget(icon_label)

        # Text
        text_label = QtWidgets.QLabel(display_text)
        text_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text']};
                font-size: 13px;
                background: transparent;
            }}
        """)
        text_label.setWordWrap(True)
        layout.addWidget(text_label, 1)


class ChangeWidget(QtWidgets.QFrame):
    """Widget displaying a set of changes from code execution."""

    showCodeRequested = QtCore.Signal()
    runCodeRequested = QtCore.Signal(str)

    def __init__(self, change_set: Union[ChangeSet, Dict], parent=None):
        super().__init__(parent)
        self._change_set = change_set
        self._code_visible = False
        self._code_widget = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        self.setStyleSheet("""
            ChangeWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QtWidgets.QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1c2128;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid #30363d;
            }
        """)
        header.setFixedHeight(36)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 8, 0)
        header_layout.setSpacing(8)

        # Title with change count
        total = self._get_total_changes()
        title_text = f"Changes Applied ({total})" if total > 0 else "No Changes"
        title_label = QtWidgets.QLabel(title_text)
        title_label.setStyleSheet("""
            QLabel {
                color: #c9d1d9;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Show/Hide code button
        self._toggle_btn = QtWidgets.QPushButton("\u25b6 Show Code")
        self._toggle_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._toggle_btn.setFixedHeight(26)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #c9d1d9;
                border-color: #8b949e;
            }
            QPushButton:pressed {
                background-color: #484f58;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_code)
        header_layout.addWidget(self._toggle_btn)

        # Run button
        code = self._get_code()
        if code:
            self._run_btn = QtWidgets.QPushButton("Run")
            self._run_btn.setCursor(QtCore.Qt.PointingHandCursor)
            self._run_btn.setFixedHeight(26)
            self._run_btn.setStyleSheet("""
                QPushButton {
                    background-color: #238636;
                    color: #ffffff;
                    border: 1px solid #2ea043;
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2ea043;
                }
                QPushButton:pressed {
                    background-color: #238636;
                }
            """)
            self._run_btn.clicked.connect(self._on_run)
            header_layout.addWidget(self._run_btn)

        layout.addWidget(header)

        # Changes content
        content = QtWidgets.QWidget()
        content.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
            }
        """)
        self._content_layout = QtWidgets.QVBoxLayout(content)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(4)

        # Add change items
        self._add_change_items()

        layout.addWidget(content)

        # Code section (initially hidden)
        self._code_container = QtWidgets.QWidget()
        self._code_container.setVisible(False)
        self._code_container.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
                border-top: 1px solid #30363d;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        code_layout = QtWidgets.QVBoxLayout(self._code_container)
        code_layout.setContentsMargins(0, 0, 0, 0)

        # Create code display
        code = self._get_code()
        if code:
            from .CodeBlockWidget import CodeBlockWidget
            self._code_widget = CodeBlockWidget(code, "python")
            self._code_widget.setStyleSheet("""
                CodeBlockWidget {
                    border: none;
                    border-radius: 0;
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }
            """)
            self._code_widget.runRequested.connect(self._on_run)
            code_layout.addWidget(self._code_widget)

        layout.addWidget(self._code_container)

    def _get_total_changes(self) -> int:
        """Get total number of changes."""
        if isinstance(self._change_set, ChangeSet):
            return self._change_set.total_changes()
        elif isinstance(self._change_set, dict):
            return (
                len(self._change_set.get("created", []))
                + len(self._change_set.get("modified", []))
                + len(self._change_set.get("deleted", []))
            )
        return 0

    def _get_code(self) -> str:
        """Get the code from change set."""
        if isinstance(self._change_set, ChangeSet):
            return self._change_set.code
        elif isinstance(self._change_set, dict):
            return self._change_set.get("code", "")
        return ""

    def _add_change_items(self):
        """Add change item widgets to the content layout."""
        if isinstance(self._change_set, ChangeSet):
            # Add created items
            for change in self._change_set.created:
                item = ChangeItemWidget(change)
                self._content_layout.addWidget(item)

            # Add modified items
            for change in self._change_set.modified:
                item = ChangeItemWidget(change)
                self._content_layout.addWidget(item)

            # Add deleted items
            for change in self._change_set.deleted:
                item = ChangeItemWidget(change)
                self._content_layout.addWidget(item)

        elif isinstance(self._change_set, dict):
            # Handle dict format (from persistence)
            for change_data in self._change_set.get("created", []):
                change_data["change_type"] = "created"
                item = ChangeItemWidget(change_data)
                self._content_layout.addWidget(item)

            for change_data in self._change_set.get("modified", []):
                change_data["change_type"] = "modified"
                item = ChangeItemWidget(change_data)
                self._content_layout.addWidget(item)

            for change_data in self._change_set.get("deleted", []):
                change_data["change_type"] = "deleted"
                item = ChangeItemWidget(change_data)
                self._content_layout.addWidget(item)

        # Show "no changes" message if empty
        if self._get_total_changes() == 0:
            no_changes = QtWidgets.QLabel("No changes detected")
            no_changes.setStyleSheet("""
                QLabel {
                    color: #8b949e;
                    font-size: 13px;
                    font-style: italic;
                    background: transparent;
                    padding: 8px;
                }
            """)
            no_changes.setAlignment(QtCore.Qt.AlignCenter)
            self._content_layout.addWidget(no_changes)

    def _toggle_code(self):
        """Toggle code visibility."""
        self._code_visible = not self._code_visible
        self._code_container.setVisible(self._code_visible)

        if self._code_visible:
            self._toggle_btn.setText("\u25bc Hide Code")
        else:
            self._toggle_btn.setText("\u25b6 Show Code")

        self.showCodeRequested.emit()

    def _on_run(self, code: str = None):
        """Handle run button click."""
        if code is None:
            code = self._get_code()
        if code:
            # Disable the Run button to prevent multiple executions
            if hasattr(self, '_run_btn'):
                self._run_btn.setEnabled(False)
                self._run_btn.setText("Executed")
                self._run_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #21262d;
                        color: #8b949e;
                        border: 1px solid #30363d;
                        border-radius: 6px;
                        padding: 0 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                """)

            # Also disable the run button in the code widget if visible
            if self._code_widget:
                self._code_widget.set_run_disabled(True)

            self.runCodeRequested.emit(code)


class ChangesSummaryWidget(QtWidgets.QFrame):
    """Compact summary widget showing change counts."""

    def __init__(self, change_set: Union[ChangeSet, Dict], parent=None):
        super().__init__(parent)
        self._change_set = change_set
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        self.setStyleSheet("""
            ChangesSummaryWidget {
                background-color: transparent;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        # Get counts
        if isinstance(self._change_set, ChangeSet):
            created = len(self._change_set.created)
            modified = len(self._change_set.modified)
            deleted = len(self._change_set.deleted)
        elif isinstance(self._change_set, dict):
            created = len(self._change_set.get("created", []))
            modified = len(self._change_set.get("modified", []))
            deleted = len(self._change_set.get("deleted", []))
        else:
            created = modified = deleted = 0

        # Add count badges
        if created > 0:
            badge = self._create_badge(f"+{created}", CHANGE_COLORS["created"])
            layout.addWidget(badge)

        if modified > 0:
            badge = self._create_badge(f"~{modified}", CHANGE_COLORS["modified"])
            layout.addWidget(badge)

        if deleted > 0:
            badge = self._create_badge(f"-{deleted}", CHANGE_COLORS["deleted"])
            layout.addWidget(badge)

        layout.addStretch()

    def _create_badge(self, text: str, colors: Dict) -> QtWidgets.QLabel:
        """Create a colored badge label."""
        badge = QtWidgets.QLabel(text)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {colors['bg']};
                color: {colors['text']};
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        return badge
