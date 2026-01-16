# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Context Selection Widget - UI for selecting which objects to include in LLM context.
Provides All/Selected/Custom modes with collapsible object list.
"""

import FreeCAD
import FreeCADGui
from PySide6 import QtCore, QtWidgets, QtGui
from typing import List, Optional, Set
from .. import Theme


class ContextMode:
    """Context selection modes."""
    ALL = "all"
    SELECTED = "selected"
    CUSTOM = "custom"


class ContextSelectionWidget(QtWidgets.QFrame):
    """Widget for selecting objects to include in LLM context.

    Provides three modes:
    - All objects: Include entire document context
    - Selected: Include only FreeCAD selection
    - Custom: Manual selection via checkboxes

    Signals:
        selectionChanged: Emitted when context selection changes
    """

    selectionChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = ContextMode.ALL
        self._custom_objects: Set[str] = set()  # Object names for custom mode
        self._expanded = False
        self._setup_ui()

        # Connect to FreeCAD selection observer
        self._setup_selection_observer()

    def _setup_ui(self):
        """Set up the widget UI."""
        self.setObjectName("ContextSelectionWidget")
        self.setStyleSheet(f"""
            #ContextSelectionWidget {{
                background-color: {Theme.COLORS['bg_tertiary']};
                border: 1px solid {Theme.COLORS['border_subtle']};
                border-radius: {Theme.RADIUS['sm']};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # Header row (always visible)
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # "Context:" label
        label = QtWidgets.QLabel("Context:")
        label.setStyleSheet(f"""
            color: {Theme.COLORS['text_muted']};
            font-size: {Theme.FONTS['size_xs']};
            background: transparent;
        """)
        header_layout.addWidget(label)

        # Mode dropdown
        self._mode_combo = QtWidgets.QComboBox()
        self._mode_combo.addItem("All objects", ContextMode.ALL)
        self._mode_combo.addItem("Selected only", ContextMode.SELECTED)
        self._mode_combo.addItem("Custom...", ContextMode.CUSTOM)
        self._mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Theme.COLORS['bg_secondary']};
                color: {Theme.COLORS['text_primary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['xs']};
                padding: 2px 8px;
                font-size: {Theme.FONTS['size_xs']};
                min-width: 100px;
            }}
            QComboBox:hover {{
                border-color: {Theme.COLORS['border_focus']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 16px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {Theme.COLORS['text_muted']};
                margin-right: 4px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Theme.COLORS['bg_secondary']};
                color: {Theme.COLORS['text_primary']};
                border: 1px solid {Theme.COLORS['border_default']};
                selection-background-color: {Theme.COLORS['bg_hover']};
            }}
        """)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        header_layout.addWidget(self._mode_combo)

        # Object count badge
        self._count_badge = QtWidgets.QLabel("0 objects")
        self._count_badge.setStyleSheet(f"""
            color: {Theme.COLORS['text_muted']};
            font-size: {Theme.FONTS['size_xs']};
            background: transparent;
        """)
        header_layout.addWidget(self._count_badge)

        header_layout.addStretch()

        # Expand/collapse button (for custom mode)
        self._expand_btn = QtWidgets.QPushButton("▾")
        self._expand_btn.setFixedSize(20, 20)
        self._expand_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._expand_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Theme.COLORS['text_muted']};
                border: none;
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {Theme.COLORS['text_primary']};
            }}
        """)
        self._expand_btn.clicked.connect(self._toggle_expand)
        self._expand_btn.setVisible(False)  # Only show in custom mode
        header_layout.addWidget(self._expand_btn)

        layout.addWidget(header)

        # Expandable content (for custom mode)
        self._content = QtWidgets.QWidget()
        self._content.setVisible(False)
        content_layout = QtWidgets.QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        # Select all / none buttons
        btn_row = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        select_all_btn = QtWidgets.QPushButton("Select All")
        select_all_btn.setFixedHeight(22)
        select_all_btn.setCursor(QtCore.Qt.PointingHandCursor)
        select_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Theme.COLORS['accent_primary']};
                border: none;
                font-size: {Theme.FONTS['size_xs']};
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        select_all_btn.clicked.connect(self._select_all)
        btn_layout.addWidget(select_all_btn)

        select_none_btn = QtWidgets.QPushButton("Select None")
        select_none_btn.setFixedHeight(22)
        select_none_btn.setCursor(QtCore.Qt.PointingHandCursor)
        select_none_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Theme.COLORS['accent_primary']};
                border: none;
                font-size: {Theme.FONTS['size_xs']};
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        select_none_btn.clicked.connect(self._select_none)
        btn_layout.addWidget(select_none_btn)

        btn_layout.addStretch()
        content_layout.addWidget(btn_row)

        # Scrollable object list
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
        """)

        self._objects_container = QtWidgets.QWidget()
        self._objects_layout = QtWidgets.QVBoxLayout(self._objects_container)
        self._objects_layout.setContentsMargins(0, 0, 0, 0)
        self._objects_layout.setSpacing(2)
        scroll.setWidget(self._objects_container)
        content_layout.addWidget(scroll)

        layout.addWidget(self._content)

        # Initial update
        self._update_count()

    def _setup_selection_observer(self):
        """Set up FreeCAD selection observer for 'Selected' mode."""
        # Note: In a full implementation, we'd use FreeCADGui.Selection.addObserver()
        # For now, we'll refresh on demand
        pass

    def _on_mode_changed(self, index: int):
        """Handle mode selection change."""
        self._mode = self._mode_combo.currentData()

        # Show/hide expand button and content
        is_custom = self._mode == ContextMode.CUSTOM
        self._expand_btn.setVisible(is_custom)

        if is_custom and self._expanded:
            self._refresh_object_list()
            self._content.setVisible(True)
        else:
            self._content.setVisible(False)

        self._update_count()
        self.selectionChanged.emit()

    def _toggle_expand(self):
        """Toggle expanded state."""
        self._expanded = not self._expanded
        self._expand_btn.setText("▴" if self._expanded else "▾")
        self._content.setVisible(self._expanded)

        if self._expanded:
            self._refresh_object_list()

    def _refresh_object_list(self):
        """Refresh the list of document objects."""
        # Clear existing
        while self._objects_layout.count():
            child = self._objects_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        doc = FreeCAD.ActiveDocument
        if not doc:
            return

        # Add checkbox for each object
        for obj in doc.Objects:
            # Skip hidden/internal objects
            if obj.TypeId in ("App::Origin", "App::Plane", "App::Line"):
                continue

            checkbox = QtWidgets.QCheckBox(obj.Label)
            checkbox.setObjectName(obj.Name)  # Store Name, show Label
            checkbox.setChecked(obj.Name in self._custom_objects)
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {Theme.COLORS['text_primary']};
                    font-size: {Theme.FONTS['size_xs']};
                    background: transparent;
                    spacing: 6px;
                }}
                QCheckBox::indicator {{
                    width: 14px;
                    height: 14px;
                    border-radius: 3px;
                    border: 1px solid {Theme.COLORS['border_default']};
                    background: {Theme.COLORS['bg_secondary']};
                }}
                QCheckBox::indicator:checked {{
                    background: {Theme.COLORS['accent_primary']};
                    border-color: {Theme.COLORS['accent_primary']};
                }}
            """)
            checkbox.toggled.connect(self._on_checkbox_toggled)
            self._objects_layout.addWidget(checkbox)

    def _on_checkbox_toggled(self, checked: bool):
        """Handle object checkbox toggle."""
        checkbox = self.sender()
        obj_name = checkbox.objectName()

        if checked:
            self._custom_objects.add(obj_name)
        else:
            self._custom_objects.discard(obj_name)

        self._update_count()
        self.selectionChanged.emit()

    def _select_all(self):
        """Select all objects in custom mode."""
        doc = FreeCAD.ActiveDocument
        if not doc:
            return

        for obj in doc.Objects:
            if obj.TypeId not in ("App::Origin", "App::Plane", "App::Line"):
                self._custom_objects.add(obj.Name)

        self._refresh_object_list()
        self._update_count()
        self.selectionChanged.emit()

    def _select_none(self):
        """Deselect all objects in custom mode."""
        self._custom_objects.clear()
        self._refresh_object_list()
        self._update_count()
        self.selectionChanged.emit()

    def _update_count(self):
        """Update the object count badge."""
        count = self._get_context_object_count()
        self._count_badge.setText(f"{count} objects" if count != 1 else "1 object")

    def _get_context_object_count(self) -> int:
        """Get number of objects in current context selection."""
        doc = FreeCAD.ActiveDocument
        if not doc:
            return 0

        if self._mode == ContextMode.ALL:
            # Count non-internal objects
            return sum(1 for obj in doc.Objects
                       if obj.TypeId not in ("App::Origin", "App::Plane", "App::Line"))
        elif self._mode == ContextMode.SELECTED:
            # Count selected objects
            return len(FreeCADGui.Selection.getSelection())
        else:  # CUSTOM
            return len(self._custom_objects)

    def get_context_objects(self) -> Optional[List[str]]:
        """Get list of object names to include in context.

        Returns:
            None for 'All' mode (include everything)
            List of object names for 'Selected' or 'Custom' modes
        """
        if self._mode == ContextMode.ALL:
            return None  # Signal to include all

        elif self._mode == ContextMode.SELECTED:
            # Get current FreeCAD selection
            selection = FreeCADGui.Selection.getSelection()
            return [obj.Name for obj in selection]

        else:  # CUSTOM
            return list(self._custom_objects)

    def get_mode(self) -> str:
        """Get current context mode."""
        return self._mode

    def set_mode(self, mode: str):
        """Set context mode programmatically."""
        index = self._mode_combo.findData(mode)
        if index >= 0:
            self._mode_combo.setCurrentIndex(index)

    def refresh(self):
        """Refresh the widget (call when document changes)."""
        if self._mode == ContextMode.CUSTOM and self._expanded:
            self._refresh_object_list()
        self._update_count()
