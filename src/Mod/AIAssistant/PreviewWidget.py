# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Preview Widget - UI component showing preview of objects to be created.

Displays description, list of objects, and Approve/Cancel buttons.
Styled to match the dark theme of the AI Assistant.
"""

from PySide6 import QtCore, QtWidgets, QtGui
from typing import List, Dict


# Styling constants
PREVIEW_BG = "#1a2e1a"  # Dark green background
PREVIEW_BORDER = "#2d5a2d"  # Green border
PREVIEW_TEXT = "#a8d8a8"  # Light green text
APPROVE_BTN_BG = "#10b981"  # Green button
APPROVE_BTN_HOVER = "#059669"
CANCEL_BTN_BG = "#374151"  # Gray button
CANCEL_BTN_HOVER = "#4b5563"


class PreviewWidget(QtWidgets.QFrame):
    """Widget showing preview of objects to be created with approve/cancel.

    Signals:
        approved: User clicked Approve - execute the code for real
        cancelled: User clicked Cancel - clear preview
        showCodeRequested: User wants to see the code
    """

    approved = QtCore.Signal()
    cancelled = QtCore.Signal()
    showCodeRequested = QtCore.Signal()

    def __init__(self, description: str, preview_items: List[Dict], code: str = "", parent=None):
        """Initialize preview widget.

        Args:
            description: Human-readable description of what will be created
            preview_items: List of dicts with name, label, type, dimensions
            code: The Python code (for showing on request)
            parent: Parent widget
        """
        super().__init__(parent)
        self._code = code
        self._code_visible = False
        self._setup_ui(description, preview_items)

    def _setup_ui(self, description: str, items: List[Dict]):
        """Set up the widget UI."""
        self.setObjectName("PreviewWidget")
        self.setStyleSheet(f"""
            #PreviewWidget {{
                background-color: {PREVIEW_BG};
                border: 1px solid {PREVIEW_BORDER};
                border-radius: 8px;
                padding: 12px;
                margin: 4px 0px;
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header with icon
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(8)

        icon_label = QtWidgets.QLabel("👁️")
        icon_label.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(icon_label)

        title_label = QtWidgets.QLabel("Preview")
        title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {PREVIEW_TEXT};
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Show code toggle button
        self._code_btn = QtWidgets.QPushButton("Show Code")
        self._code_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {PREVIEW_TEXT};
                border: 1px solid {PREVIEW_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {PREVIEW_BORDER};
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
                color: #d1d5db;
                font-size: 13px;
                padding: 4px 0px;
            """)
            layout.addWidget(desc_label)

        # Preview items list
        if items:
            items_frame = QtWidgets.QFrame()
            items_frame.setStyleSheet(f"""
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
                padding: 8px;
            """)
            items_layout = QtWidgets.QVBoxLayout(items_frame)
            items_layout.setContentsMargins(8, 8, 8, 8)
            items_layout.setSpacing(4)

            count_label = QtWidgets.QLabel(f"Objects to create ({len(items)}):")
            count_label.setStyleSheet(f"""
                color: {PREVIEW_TEXT};
                font-size: 12px;
                font-weight: bold;
            """)
            items_layout.addWidget(count_label)

            for item in items:
                item_widget = self._create_item_row(item)
                items_layout.addWidget(item_widget)

            layout.addWidget(items_frame)

        # Code display (hidden by default)
        self._code_frame = QtWidgets.QFrame()
        self._code_frame.setStyleSheet("""
            background-color: #0d1117;
            border-radius: 6px;
            padding: 8px;
        """)
        self._code_frame.setVisible(False)

        code_layout = QtWidgets.QVBoxLayout(self._code_frame)
        code_layout.setContentsMargins(8, 8, 8, 8)

        self._code_text = QtWidgets.QTextEdit()
        self._code_text.setPlainText(self._code)
        self._code_text.setReadOnly(True)
        self._code_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: none;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        self._code_text.setMaximumHeight(150)
        code_layout.addWidget(self._code_text)

        layout.addWidget(self._code_frame)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)

        # Cancel button
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CANCEL_BTN_BG};
                color: #d1d5db;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {CANCEL_BTN_HOVER};
            }}
        """)
        cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()

        # Approve button
        approve_btn = QtWidgets.QPushButton("✓ Approve & Create")
        approve_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {APPROVE_BTN_BG};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {APPROVE_BTN_HOVER};
            }}
        """)
        approve_btn.clicked.connect(self._on_approve)
        btn_layout.addWidget(approve_btn)

        layout.addLayout(btn_layout)

    def _create_item_row(self, item: Dict) -> QtWidgets.QWidget:
        """Create a row widget for a preview item."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        # Green dot icon
        icon = QtWidgets.QLabel("●")
        icon.setStyleSheet(f"color: {APPROVE_BTN_BG}; font-size: 10px;")
        icon.setFixedWidth(16)
        layout.addWidget(icon)

        # Label name
        label = item.get("label", item.get("name", "Unknown"))
        name_label = QtWidgets.QLabel(label)
        name_label.setStyleSheet("color: #e5e7eb; font-size: 12px;")
        layout.addWidget(name_label)

        # Type badge
        type_name = item.get("type", "")
        if type_name:
            type_label = QtWidgets.QLabel(type_name)
            type_label.setStyleSheet(f"""
                color: {PREVIEW_TEXT};
                background-color: rgba(45, 90, 45, 0.5);
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 10px;
            """)
            layout.addWidget(type_label)

        # Dimensions if available
        dims = item.get("dimensions", {})
        if dims:
            dim_str = f"{dims.get('width', 0)} × {dims.get('depth', 0)} × {dims.get('height', 0)}"
            dim_label = QtWidgets.QLabel(dim_str)
            dim_label.setStyleSheet("color: #9ca3af; font-size: 10px;")
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
                    background-color: #1e1e1e;
                    border: 1px solid #333;
                    border-radius: 8px;
                    padding: 12px;
                    margin: 4px 0px;
                    opacity: 0.6;
                }}
            """)
