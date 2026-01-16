# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Step Preview Widget - Mini preview widget for individual plan steps.
Shows step description, objects affected, and preview button.
"""

from PySide6 import QtCore, QtWidgets, QtGui
from typing import List, Dict, Optional
from .. import Theme


class StepState:
    """State of a plan step."""
    PENDING = "pending"
    PREVIEWING = "previewing"
    APPROVED = "approved"
    FAILED = "failed"


class StepPreviewWidget(QtWidgets.QFrame):
    """Widget for previewing individual plan steps.

    Signals:
        previewRequested: User clicked Preview for this step
        stepApproved: User approved this step
        stepRejected: User rejected this step
    """

    previewRequested = QtCore.Signal(int)  # Emits step number
    stepApproved = QtCore.Signal(int)
    stepRejected = QtCore.Signal(int)

    def __init__(self, step_number: int, action: str, description: str,
                 objects: List[str] = None, parent=None):
        super().__init__(parent)
        self._step_number = step_number
        self._action = action
        self._description = description
        self._objects = objects or []
        self._state = StepState.PENDING
        self._preview_items: List[Dict] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        self.setObjectName("StepPreviewWidget")
        self._update_style()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Step number badge
        self._number_label = QtWidgets.QLabel(str(self._step_number))
        self._number_label.setFixedSize(28, 28)
        self._number_label.setAlignment(QtCore.Qt.AlignCenter)
        self._update_number_badge()
        layout.addWidget(self._number_label)

        # Content area
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        # Action + Description
        action_label = QtWidgets.QLabel(f"<b>{self._action}</b>: {self._description}")
        action_label.setWordWrap(True)
        action_label.setStyleSheet(f"""
            color: {Theme.COLORS['text_primary']};
            font-size: {Theme.FONTS['size_sm']};
            background: transparent;
        """)
        content_layout.addWidget(action_label)

        # Objects (if any)
        if self._objects:
            objects_label = QtWidgets.QLabel(f"Objects: {', '.join(self._objects)}")
            objects_label.setStyleSheet(f"""
                color: {Theme.COLORS['text_muted']};
                font-size: {Theme.FONTS['size_xs']};
                background: transparent;
            """)
            content_layout.addWidget(objects_label)

        # Status label (hidden by default)
        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet(f"""
            color: {Theme.COLORS['text_muted']};
            font-size: {Theme.FONTS['size_xs']};
            background: transparent;
        """)
        self._status_label.setVisible(False)
        content_layout.addWidget(self._status_label)

        layout.addWidget(content, stretch=1)

        # Preview button
        self._preview_btn = QtWidgets.QPushButton("Preview")
        self._preview_btn.setFixedSize(72, 28)
        self._preview_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._preview_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.COLORS['text_secondary']};
                border: 1px solid {Theme.COLORS['border_default']};
                border-radius: {Theme.RADIUS['xs']};
                font-size: {Theme.FONTS['size_xs']};
            }}
            QPushButton:hover {{
                background-color: {Theme.COLORS['bg_hover']};
                color: {Theme.COLORS['text_primary']};
            }}
        """)
        self._preview_btn.clicked.connect(self._on_preview_clicked)
        layout.addWidget(self._preview_btn)

        # Status icon (checkmark or X)
        self._status_icon = QtWidgets.QLabel("")
        self._status_icon.setFixedSize(24, 24)
        self._status_icon.setAlignment(QtCore.Qt.AlignCenter)
        self._status_icon.setVisible(False)
        layout.addWidget(self._status_icon)

    def _update_style(self):
        """Update widget style based on state."""
        if self._state == StepState.APPROVED:
            border_color = Theme.COLORS['accent_success']
            bg_color = "rgba(34, 197, 94, 0.05)"
        elif self._state == StepState.FAILED:
            border_color = Theme.COLORS['accent_error']
            bg_color = "rgba(239, 68, 68, 0.05)"
        elif self._state == StepState.PREVIEWING:
            border_color = Theme.COLORS['accent_primary']
            bg_color = "rgba(59, 130, 246, 0.05)"
        else:  # PENDING
            border_color = Theme.COLORS['border_subtle']
            bg_color = "transparent"

        self.setStyleSheet(f"""
            #StepPreviewWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {Theme.RADIUS['sm']};
            }}
        """)

    def _update_number_badge(self):
        """Update number badge style based on state."""
        if self._state == StepState.APPROVED:
            bg_color = Theme.COLORS['accent_success']
        elif self._state == StepState.FAILED:
            bg_color = Theme.COLORS['accent_error']
        elif self._state == StepState.PREVIEWING:
            bg_color = Theme.COLORS['accent_primary']
        else:  # PENDING
            bg_color = Theme.COLORS['bg_tertiary']

        self._number_label.setStyleSheet(f"""
            background-color: {bg_color};
            color: white;
            border-radius: 14px;
            font-size: {Theme.FONTS['size_xs']};
            font-weight: {Theme.FONTS['weight_semibold']};
        """)

    def _on_preview_clicked(self):
        """Handle preview button click."""
        self.previewRequested.emit(self._step_number)

    def set_state(self, state: str):
        """Set the step state and update UI.

        Args:
            state: One of StepState values
        """
        self._state = state
        self._update_style()
        self._update_number_badge()

        # Update button and icon visibility
        if state == StepState.APPROVED:
            self._preview_btn.setVisible(False)
            self._status_icon.setText("✓")
            self._status_icon.setStyleSheet(f"""
                color: {Theme.COLORS['accent_success']};
                font-size: 16px;
                font-weight: bold;
            """)
            self._status_icon.setVisible(True)
        elif state == StepState.FAILED:
            self._preview_btn.setVisible(False)
            self._status_icon.setText("✗")
            self._status_icon.setStyleSheet(f"""
                color: {Theme.COLORS['accent_error']};
                font-size: 16px;
                font-weight: bold;
            """)
            self._status_icon.setVisible(True)
        elif state == StepState.PREVIEWING:
            self._preview_btn.setText("...")
            self._preview_btn.setEnabled(False)
        else:  # PENDING
            self._preview_btn.setText("Preview")
            self._preview_btn.setEnabled(True)
            self._preview_btn.setVisible(True)
            self._status_icon.setVisible(False)

    def set_status_message(self, message: str):
        """Set a status message below the step description."""
        if message:
            self._status_label.setText(message)
            self._status_label.setVisible(True)
        else:
            self._status_label.setVisible(False)

    def set_preview_items(self, items: List[Dict]):
        """Set the preview items for this step."""
        self._preview_items = items

    def get_step_number(self) -> int:
        """Get the step number."""
        return self._step_number

    def get_state(self) -> str:
        """Get current state."""
        return self._state

    def is_approved(self) -> bool:
        """Check if step is approved."""
        return self._state == StepState.APPROVED


class MultiStepPreviewWidget(QtWidgets.QFrame):
    """Container widget for multiple step previews.

    Shows all steps with their individual preview status and
    provides Execute All / Cancel buttons.

    Signals:
        executeAllRequested: User clicked Execute All
        cancelled: User cancelled the multi-step preview
        stepPreviewRequested(int): User requested preview for specific step
    """

    executeAllRequested = QtCore.Signal()
    cancelled = QtCore.Signal()
    stepPreviewRequested = QtCore.Signal(int)

    def __init__(self, steps: List[Dict], parent=None):
        """Initialize with list of step dictionaries.

        Args:
            steps: List of dicts with keys: number, action, description, objects
        """
        super().__init__(parent)
        self._steps = steps
        self._step_widgets: List[StepPreviewWidget] = []
        self._setup_ui()
        self._setup_entry_animation()

    def _setup_ui(self):
        """Set up the widget UI."""
        self.setObjectName("MultiStepPreviewWidget")
        self.setStyleSheet(f"""
            #MultiStepPreviewWidget {{
                background-color: {Theme.COLORS['preview_bg']};
                border: 1px solid {Theme.COLORS['accent_primary']};
                border-radius: {Theme.RADIUS['lg']};
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header
        header_layout = QtWidgets.QHBoxLayout()
        title_label = QtWidgets.QLabel("Multi-Step Preview")
        title_label.setStyleSheet(f"""
            font-size: {Theme.FONTS['size_sm']};
            font-weight: {Theme.FONTS['weight_semibold']};
            color: {Theme.COLORS['accent_primary']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)

        # Progress badge
        self._progress_label = QtWidgets.QLabel(f"0/{len(self._steps)} approved")
        self._progress_label.setStyleSheet(f"""
            color: {Theme.COLORS['text_muted']};
            font-size: {Theme.FONTS['size_xs']};
            background: transparent;
        """)
        header_layout.addWidget(self._progress_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Steps container
        steps_frame = QtWidgets.QFrame()
        steps_frame.setStyleSheet(f"""
            background-color: rgba(0, 0, 0, 0.1);
            border-radius: {Theme.RADIUS['sm']};
        """)
        steps_layout = QtWidgets.QVBoxLayout(steps_frame)
        steps_layout.setContentsMargins(8, 8, 8, 8)
        steps_layout.setSpacing(6)

        for step in self._steps:
            step_widget = StepPreviewWidget(
                step_number=step.get("number", 0),
                action=step.get("action", ""),
                description=step.get("description", ""),
                objects=step.get("objects", [])
            )
            step_widget.previewRequested.connect(self._on_step_preview_requested)
            steps_layout.addWidget(step_widget)
            self._step_widgets.append(step_widget)

        layout.addWidget(steps_frame)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)

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

        self._execute_btn = QtWidgets.QPushButton("Execute All")
        self._execute_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._execute_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.COLORS['accent_primary']};
                color: white;
                border: none;
                border-radius: {Theme.RADIUS['sm']};
                padding: 10px 24px;
                font-size: {Theme.FONTS['size_base']};
                font-weight: {Theme.FONTS['weight_medium']};
            }}
            QPushButton:hover {{
                background-color: {Theme.COLORS['accent_primary_hover']};
            }}
            QPushButton:disabled {{
                background-color: {Theme.COLORS['bg_tertiary']};
                color: {Theme.COLORS['text_muted']};
            }}
        """)
        self._execute_btn.clicked.connect(self._on_execute_all)
        btn_layout.addWidget(self._execute_btn)

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

    def _on_step_preview_requested(self, step_number: int):
        """Handle step preview request."""
        self.stepPreviewRequested.emit(step_number)

    def _on_execute_all(self):
        """Handle Execute All button click."""
        self.executeAllRequested.emit()

    def _on_cancel(self):
        """Handle Cancel button click."""
        self.cancelled.emit()

    def set_step_state(self, step_number: int, state: str, message: str = ""):
        """Set state for a specific step.

        Args:
            step_number: The step number (1-based)
            state: One of StepState values
            message: Optional status message
        """
        for widget in self._step_widgets:
            if widget.get_step_number() == step_number:
                widget.set_state(state)
                if message:
                    widget.set_status_message(message)
                break
        self._update_progress()

    def _update_progress(self):
        """Update the progress label."""
        approved = sum(1 for w in self._step_widgets if w.is_approved())
        self._progress_label.setText(f"{approved}/{len(self._step_widgets)} approved")

        # Enable Execute All only when all steps are approved
        all_approved = approved == len(self._step_widgets)
        self._execute_btn.setEnabled(all_approved)

    def get_all_approved(self) -> bool:
        """Check if all steps are approved."""
        return all(w.is_approved() for w in self._step_widgets)

    def set_disabled(self, disabled: bool):
        """Disable/enable the widget."""
        self.setEnabled(not disabled)
        if disabled:
            self.setStyleSheet(f"""
                #MultiStepPreviewWidget {{
                    background-color: {Theme.COLORS['bg_tertiary']};
                    border: 1px solid {Theme.COLORS['border_subtle']};
                    border-radius: {Theme.RADIUS['lg']};
                    opacity: 0.5;
                }}
            """)
