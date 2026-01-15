# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Preview Widget - Modern preview card showing objects to be created or deleted.
Cursor-inspired design with blue accent for creation, red for deletion.
"""

from PySide6 import QtCore, QtWidgets, QtGui
from typing import List, Dict
from . import Theme

# Deletion mode colors
DELETION_ACCENT = "#ef4444"  # Red-500
DELETION_ACCENT_HOVER = "#dc2626"  # Red-600
DELETION_BG = "rgba(239, 68, 68, 0.08)"  # Light red bg


class PreviewWidget(QtWidgets.QFrame):
    """Widget showing preview of objects to be created or deleted.

    Signals:
        approved: User clicked Approve - execute the code for real
        cancelled: User clicked Cancel - clear preview
        showCodeRequested: User wants to see the code
    """

    approved = QtCore.Signal()
    cancelled = QtCore.Signal()
    showCodeRequested = QtCore.Signal()

    def __init__(self, description: str, preview_items: List[Dict], code: str = "",
                 is_deletion: bool = False, parent=None):
        super().__init__(parent)
        self._code = code
        self._code_visible = False
        self._is_deletion = is_deletion
        self._setup_ui(description, preview_items)
        self._setup_entry_animation()

    def _setup_ui(self, description: str, items: List[Dict]):
        """Set up the widget UI."""
        self.setObjectName("PreviewWidget")

        # Different border color for deletion mode
        border_color = DELETION_ACCENT if self._is_deletion else Theme.COLORS['preview_border']

        self.setStyleSheet(f"""
            #PreviewWidget {{
                background-color: {Theme.COLORS['preview_bg']};
                border: 1px solid {border_color};
                border-radius: {Theme.RADIUS['lg']};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(10)

        # Different title for deletion mode
        title_text = "Deletion Preview" if self._is_deletion else "Preview"
        title_color = DELETION_ACCENT if self._is_deletion else Theme.COLORS['preview_text']

        title_label = QtWidgets.QLabel(title_text)
        title_label.setStyleSheet(f"""
            font-size: {Theme.FONTS['size_sm']};
            font-weight: {Theme.FONTS['weight_semibold']};
            color: {title_color};
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Show code toggle button - ghost style
        self._code_btn = QtWidgets.QPushButton("Show Code")
        self._code_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._code_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.COLORS['text_secondary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['xs']};
                padding: 4px 10px;
                font-size: {Theme.FONTS['size_xs']};
            }}
            QPushButton:hover {{
                background-color: {Theme.COLORS['bg_hover']};
                color: {Theme.COLORS['text_primary']};
            }}
        """)
        self._code_btn.clicked.connect(self._toggle_code)
        header_layout.addWidget(self._code_btn)

        layout.addLayout(header_layout)

        # Description
        if description:
            desc_label = QtWidgets.QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                color: {Theme.COLORS['text_secondary']};
                font-size: {Theme.FONTS['size_base']};
                background: transparent;
            """)
            layout.addWidget(desc_label)

        # Preview items list
        if items:
            items_frame = QtWidgets.QFrame()
            items_frame.setStyleSheet(f"""
                background-color: rgba(0, 0, 0, 0.15);
                border-radius: {Theme.RADIUS['sm']};
            """)
            items_layout = QtWidgets.QVBoxLayout(items_frame)
            items_layout.setContentsMargins(12, 10, 12, 10)
            items_layout.setSpacing(6)

            # Different text for deletion mode
            action = "delete" if self._is_deletion else "create"
            count_label = QtWidgets.QLabel(f"{len(items)} object{'s' if len(items) > 1 else ''} to {action}")
            count_color = DELETION_ACCENT if self._is_deletion else Theme.COLORS['text_muted']
            count_label.setStyleSheet(f"""
                color: {count_color};
                font-size: {Theme.FONTS['size_xs']};
                background: transparent;
            """)
            items_layout.addWidget(count_label)

            for item in items:
                item_widget = self._create_item_row(item)
                items_layout.addWidget(item_widget)

            layout.addWidget(items_frame)

        # Code display (hidden by default)
        self._code_frame = QtWidgets.QFrame()
        self._code_frame.setStyleSheet(f"""
            background-color: {Theme.COLORS['code_bg']};
            border-radius: {Theme.RADIUS['sm']};
            border: 1px solid {Theme.COLORS['code_border']};
        """)
        self._code_frame.setVisible(False)

        code_layout = QtWidgets.QVBoxLayout(self._code_frame)
        code_layout.setContentsMargins(10, 10, 10, 10)

        self._code_text = QtWidgets.QTextEdit()
        self._code_text.setPlainText(self._code)
        self._code_text.setReadOnly(True)
        self._code_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {Theme.COLORS['code_text']};
                border: none;
                font-family: {Theme.FONTS['family_mono']};
                font-size: {Theme.FONTS['size_xs']};
            }}
        """)
        self._code_text.setMaximumHeight(150)
        code_layout.addWidget(self._code_text)

        layout.addWidget(self._code_frame)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)

        # Cancel button - ghost style
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.setCursor(QtCore.Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.COLORS['text_secondary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['sm']};
                padding: 10px 20px;
                font-size: {Theme.FONTS['size_base']};
                font-weight: {Theme.FONTS['weight_medium']};
            }}
            QPushButton:hover {{
                background-color: {Theme.COLORS['bg_hover']};
                color: {Theme.COLORS['text_primary']};
            }}
        """)
        cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()

        # Approve button - blue for create, red for delete
        btn_text = "Approve & Delete" if self._is_deletion else "Approve & Create"
        btn_color = DELETION_ACCENT if self._is_deletion else Theme.COLORS['accent_primary']
        btn_hover = DELETION_ACCENT_HOVER if self._is_deletion else Theme.COLORS['accent_primary_hover']

        approve_btn = QtWidgets.QPushButton(btn_text)
        approve_btn.setCursor(QtCore.Qt.PointingHandCursor)
        approve_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_color};
                color: white;
                border: none;
                border-radius: {Theme.RADIUS['sm']};
                padding: 10px 24px;
                font-size: {Theme.FONTS['size_base']};
                font-weight: {Theme.FONTS['weight_medium']};
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        approve_btn.clicked.connect(self._on_approve)
        btn_layout.addWidget(approve_btn)

        layout.addLayout(btn_layout)

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

    def _create_item_row(self, item: Dict) -> QtWidgets.QWidget:
        """Create a row widget for a preview item."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        # Dot icon - red for deletion, blue for creation
        icon_color = DELETION_ACCENT if self._is_deletion else Theme.COLORS['accent_primary']
        icon = QtWidgets.QLabel("●")
        icon.setStyleSheet(f"color: {icon_color}; font-size: 8px;")
        icon.setFixedWidth(12)
        layout.addWidget(icon)

        # Label name
        label = item.get("label", item.get("name", "Unknown"))
        name_label = QtWidgets.QLabel(label)
        name_label.setStyleSheet(f"""
            color: {Theme.COLORS['text_primary']};
            font-size: {Theme.FONTS['size_sm']};
            background: transparent;
        """)
        layout.addWidget(name_label)

        # Type badge - red tint for deletion, blue for creation
        type_name = item.get("type", "")
        if type_name:
            badge_bg = DELETION_BG if self._is_deletion else "rgba(59, 130, 246, 0.1)"
            type_label = QtWidgets.QLabel(type_name)
            type_label.setStyleSheet(f"""
                color: {Theme.COLORS['text_muted']};
                background-color: {badge_bg};
                border-radius: 3px;
                padding: 1px 6px;
                font-size: {Theme.FONTS['size_xs']};
            """)
            layout.addWidget(type_label)

        # Dimensions if available
        dims = item.get("dimensions", {})
        if dims:
            dim_str = f"{dims.get('width', 0)}×{dims.get('depth', 0)}×{dims.get('height', 0)}"
            dim_label = QtWidgets.QLabel(dim_str)
            dim_label.setStyleSheet(f"""
                color: {Theme.COLORS['text_muted']};
                font-size: {Theme.FONTS['size_xs']};
                font-family: {Theme.FONTS['family_mono']};
                background: transparent;
            """)
            layout.addWidget(dim_label)

        layout.addStretch()
        return widget

    def _toggle_code(self):
        """Toggle code visibility."""
        self._code_visible = not self._code_visible
        self._code_frame.setVisible(self._code_visible)
        self._code_btn.setText("Hide Code" if self._code_visible else "Show Code")
        self.showCodeRequested.emit()

    def _on_approve(self):
        """Handle approve button click."""
        self.approved.emit()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.cancelled.emit()

    def set_disabled(self, disabled: bool):
        """Disable/enable the widget after approval/cancellation."""
        self.setEnabled(not disabled)
        if disabled:
            self.setStyleSheet(f"""
                #PreviewWidget {{
                    background-color: {Theme.COLORS['bg_tertiary']};
                    border: 1px solid {Theme.COLORS['border_subtle']};
                    border-radius: {Theme.RADIUS['lg']};
                    opacity: 0.5;
                }}
            """)
