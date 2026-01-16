# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Change Widget - Modern change visualization with color-coded items.
Shows created (green), modified (blue), and deleted (red) objects.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from typing import Dict, List, Optional, Union
from ..core.changes import ChangeSet, ObjectChange
from .. import Theme


# Color palette for change types
CHANGE_COLORS = {
    "created": {
        "icon": "+",
        "bg": Theme.COLORS['change_created_bg'],
        "border": Theme.COLORS['change_created'],
        "text": Theme.COLORS['change_created'],
    },
    "modified": {
        "icon": "~",
        "bg": Theme.COLORS['change_modified_bg'],
        "border": Theme.COLORS['change_modified'],
        "text": Theme.COLORS['change_modified'],
    },
    "deleted": {
        "icon": "-",
        "bg": Theme.COLORS['change_deleted_bg'],
        "border": Theme.COLORS['change_deleted'],
        "text": Theme.COLORS['change_deleted'],
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
                border-left: 2px solid {colors['border']};
                border-radius: {Theme.RADIUS['xs']};
            }}
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # Icon
        icon_label = QtWidgets.QLabel(colors["icon"])
        icon_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text']};
                font-size: {Theme.FONTS['size_base']};
                font-weight: {Theme.FONTS['weight_bold']};
                font-family: {Theme.FONTS['family_mono']};
                background: transparent;
            }}
        """)
        icon_label.setFixedWidth(16)
        layout.addWidget(icon_label)

        # Text
        text_label = QtWidgets.QLabel(display_text)
        text_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text']};
                font-size: {Theme.FONTS['size_sm']};
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
        self._items_visible = False  # Start collapsed
        self._code_widget = None
        self._setup_ui()
        self._setup_entry_animation()

    def _setup_ui(self):
        """Build the widget UI."""
        self.setStyleSheet(f"""
            ChangeWidget {{
                background-color: {Theme.COLORS['bg_secondary']};
                border: 1px solid {Theme.COLORS['border_subtle']};
                border-radius: {Theme.RADIUS['lg']};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header - clickable to expand/collapse
        self._header = QtWidgets.QWidget()
        self._header.setCursor(QtCore.Qt.PointingHandCursor)
        self._header.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.COLORS['bg_tertiary']};
                border-top-left-radius: {Theme.RADIUS['lg']};
                border-top-right-radius: {Theme.RADIUS['lg']};
                border-bottom: 1px solid {Theme.COLORS['border_subtle']};
            }}
        """)
        self._header.setFixedHeight(40)
        self._header.mousePressEvent = self._on_header_click
        header_layout = QtWidgets.QHBoxLayout(self._header)
        header_layout.setContentsMargins(14, 0, 10, 0)
        header_layout.setSpacing(10)

        # Chevron icon for expand/collapse indicator
        self._chevron = QtWidgets.QLabel("▶")
        self._chevron.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['text_muted']};
                font-size: 10px;
                background: transparent;
            }}
        """)
        self._chevron.setFixedWidth(14)
        header_layout.addWidget(self._chevron)

        # Title with inline count badges
        title_label = QtWidgets.QLabel("Changes")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.COLORS['text_primary']};
                font-size: {Theme.FONTS['size_sm']};
                font-weight: {Theme.FONTS['weight_semibold']};
                background: transparent;
            }}
        """)
        header_layout.addWidget(title_label)

        # Add inline count badges
        self._add_count_badges(header_layout)

        header_layout.addStretch()

        # Show/Hide code button - chevron style
        self._toggle_btn = QtWidgets.QPushButton("Code")
        self._toggle_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._toggle_btn.setFixedHeight(26)
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.COLORS['text_secondary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['xs']};
                padding: 0 10px;
                font-size: {Theme.FONTS['size_xs']};
            }}
            QPushButton:hover {{
                background-color: {Theme.COLORS['bg_hover']};
                color: {Theme.COLORS['text_primary']};
            }}
        """)
        self._toggle_btn.clicked.connect(self._toggle_code)
        header_layout.addWidget(self._toggle_btn)

        # Run button - blue
        code = self._get_code()
        if code:
            self._run_btn = QtWidgets.QPushButton("Run")
            self._run_btn.setCursor(QtCore.Qt.PointingHandCursor)
            self._run_btn.setFixedHeight(26)
            self._run_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.COLORS['accent_primary']};
                    color: #ffffff;
                    border: none;
                    border-radius: {Theme.RADIUS['xs']};
                    padding: 0 12px;
                    font-size: {Theme.FONTS['size_xs']};
                    font-weight: {Theme.FONTS['weight_medium']};
                }}
                QPushButton:hover {{
                    background-color: {Theme.COLORS['accent_primary_hover']};
                }}
            """)
            self._run_btn.clicked.connect(self._on_run)
            header_layout.addWidget(self._run_btn)

        layout.addWidget(self._header)

        # Changes content - collapsible, hidden by default
        self._content = QtWidgets.QWidget()
        self._content.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.COLORS['bg_primary']};
            }}
        """)
        self._content.setVisible(self._items_visible)  # Start collapsed
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(14, 12, 14, 12)
        self._content_layout.setSpacing(6)

        # Add change items
        self._add_change_items()

        layout.addWidget(self._content)

        # Code section (initially hidden)
        self._code_container = QtWidgets.QWidget()
        self._code_container.setVisible(False)
        self._code_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.COLORS['bg_primary']};
                border-top: 1px solid {Theme.COLORS['border_subtle']};
                border-bottom-left-radius: {Theme.RADIUS['lg']};
                border-bottom-right-radius: {Theme.RADIUS['lg']};
            }}
        """)
        code_layout = QtWidgets.QVBoxLayout(self._code_container)
        code_layout.setContentsMargins(0, 0, 0, 0)

        if code:
            from .CodeBlockWidget import CodeBlockWidget
            self._code_widget = CodeBlockWidget(code, "python")
            self._code_widget.setStyleSheet(f"""
                CodeBlockWidget {{
                    border: none;
                    border-radius: 0;
                    border-bottom-left-radius: {Theme.RADIUS['lg']};
                    border-bottom-right-radius: {Theme.RADIUS['lg']};
                }}
            """)
            self._code_widget.runRequested.connect(self._on_run)
            code_layout.addWidget(self._code_widget)

        layout.addWidget(self._code_container)

    def _setup_entry_animation(self):
        """Setup fade-in animation."""
        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)

        self._fade_anim = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(Theme.ANIMATION['duration_normal'])
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._fade_anim.start()

    def _add_count_badges(self, layout):
        """Add inline count badges to header."""
        if isinstance(self._change_set, ChangeSet):
            created = len(self._change_set.created)
            modified = len(self._change_set.modified)
            deleted = len(self._change_set.deleted)
        elif isinstance(self._change_set, dict):
            created = len(self._change_set.get("created", []))
            modified = len(self._change_set.get("modified", []))
            deleted = len(self._change_set.get("deleted", []))
        else:
            return

        for count, colors_key in [(created, "created"), (modified, "modified"), (deleted, "deleted")]:
            if count > 0:
                colors = CHANGE_COLORS[colors_key]
                badge = QtWidgets.QLabel(f"{colors['icon']}{count}")
                badge.setStyleSheet(f"""
                    QLabel {{
                        background-color: {colors['bg']};
                        color: {colors['text']};
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-size: {Theme.FONTS['size_xs']};
                        font-weight: {Theme.FONTS['weight_semibold']};
                        font-family: {Theme.FONTS['family_mono']};
                    }}
                """)
                layout.addWidget(badge)

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
            for change in self._change_set.created:
                item = ChangeItemWidget(change)
                self._content_layout.addWidget(item)
            for change in self._change_set.modified:
                item = ChangeItemWidget(change)
                self._content_layout.addWidget(item)
            for change in self._change_set.deleted:
                item = ChangeItemWidget(change)
                self._content_layout.addWidget(item)

        elif isinstance(self._change_set, dict):
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

        if self._get_total_changes() == 0:
            no_changes = QtWidgets.QLabel("No changes detected")
            no_changes.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.COLORS['text_muted']};
                    font-size: {Theme.FONTS['size_sm']};
                    font-style: italic;
                    background: transparent;
                    padding: 8px;
                }}
            """)
            no_changes.setAlignment(QtCore.Qt.AlignCenter)
            self._content_layout.addWidget(no_changes)

    def _on_header_click(self, event):
        """Toggle items visibility when header is clicked."""
        self._items_visible = not self._items_visible
        self._content.setVisible(self._items_visible)
        self._chevron.setText("▼" if self._items_visible else "▶")

    def _toggle_code(self):
        """Toggle code visibility."""
        self._code_visible = not self._code_visible
        self._code_container.setVisible(self._code_visible)
        self._toggle_btn.setText("Hide" if self._code_visible else "Code")
        self.showCodeRequested.emit()

    def _on_run(self, code: str = None):
        """Handle run button click."""
        if code is None:
            code = self._get_code()
        if code:
            if hasattr(self, '_run_btn'):
                self._run_btn.setEnabled(False)
                self._run_btn.setText("Done")
                self._run_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Theme.COLORS['bg_tertiary']};
                        color: {Theme.COLORS['text_muted']};
                        border: none;
                        border-radius: {Theme.RADIUS['xs']};
                        padding: 0 12px;
                        font-size: {Theme.FONTS['size_xs']};
                    }}
                """)

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
        self.setStyleSheet("background-color: transparent;")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

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

        for count, colors_key, prefix in [
            (created, "created", "+"),
            (modified, "modified", "~"),
            (deleted, "deleted", "-")
        ]:
            if count > 0:
                colors = CHANGE_COLORS[colors_key]
                badge = QtWidgets.QLabel(f"{prefix}{count}")
                badge.setStyleSheet(f"""
                    QLabel {{
                        background-color: {colors['bg']};
                        color: {colors['text']};
                        padding: 2px 8px;
                        border-radius: 10px;
                        font-size: {Theme.FONTS['size_xs']};
                        font-weight: {Theme.FONTS['weight_semibold']};
                    }}
                """)
                layout.addWidget(badge)

        layout.addStretch()
