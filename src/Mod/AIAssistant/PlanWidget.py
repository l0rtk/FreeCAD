# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Plan Widget - Shows AI's execution plan for user approval before code generation.
Part of the two-phase LLM flow: plan → approve → code → preview → execute.
"""

import re
from PySide6 import QtCore, QtWidgets, QtGui
from typing import List, Dict, Optional
from . import Theme


class PlanStep:
    """A single step in the execution plan."""

    def __init__(self, number: int, action: str, description: str,
                 objects: List[str] = None, outcome: str = ""):
        self.number = number
        self.action = action
        self.description = description
        self.objects = objects or []
        self.outcome = outcome

    @staticmethod
    def parse_plan(plan_text: str) -> List["PlanStep"]:
        """Parse plan text into PlanStep objects.

        Expected format:
        ## Plan
        1. **Action**: Description
           - Objects: obj1, obj2
           - Outcome: expected result

        Args:
            plan_text: Raw plan text from LLM

        Returns:
            List of PlanStep objects
        """
        steps = []
        # Match numbered steps: "1. **Action**: Description" or "1. Action: Description"
        pattern = r'(\d+)\.\s+\*?\*?([^*:]+)\*?\*?:\s*([^\n]+)'
        matches = re.findall(pattern, plan_text)

        for match in matches:
            number = int(match[0])
            action = match[1].strip()
            description = match[2].strip()

            # Try to extract objects and outcome from following lines
            objects = []
            outcome = ""

            steps.append(PlanStep(
                number=number,
                action=action,
                description=description,
                objects=objects,
                outcome=outcome
            ))

        return steps


class PlanStepWidget(QtWidgets.QWidget):
    """Widget for a single plan step."""

    def __init__(self, step: PlanStep, parent=None):
        super().__init__(parent)
        self._step = step
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        # Step number badge
        number_label = QtWidgets.QLabel(str(self._step.number))
        number_label.setFixedSize(24, 24)
        number_label.setAlignment(QtCore.Qt.AlignCenter)
        number_label.setStyleSheet(f"""
            background-color: {Theme.COLORS['accent_primary']};
            color: white;
            border-radius: 12px;
            font-size: {Theme.FONTS['size_xs']};
            font-weight: {Theme.FONTS['weight_semibold']};
        """)
        layout.addWidget(number_label)

        # Step content
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        # Action (bold) + Description
        action_label = QtWidgets.QLabel(f"<b>{self._step.action}</b>: {self._step.description}")
        action_label.setWordWrap(True)
        action_label.setStyleSheet(f"""
            color: {Theme.COLORS['text_primary']};
            font-size: {Theme.FONTS['size_sm']};
            background: transparent;
        """)
        content_layout.addWidget(action_label)

        # Objects involved (if any)
        if self._step.objects:
            objects_text = ", ".join(self._step.objects)
            objects_label = QtWidgets.QLabel(f"Objects: {objects_text}")
            objects_label.setStyleSheet(f"""
                color: {Theme.COLORS['text_muted']};
                font-size: {Theme.FONTS['size_xs']};
                background: transparent;
            """)
            content_layout.addWidget(objects_label)

        layout.addWidget(content, stretch=1)


class PlanWidget(QtWidgets.QFrame):
    """Widget showing execution plan for user approval.

    Signals:
        planApproved: User approved the plan as-is
        planEdited(str): User edited the plan, new text provided
        planCancelled: User cancelled the plan
    """

    planApproved = QtCore.Signal()
    planEdited = QtCore.Signal(str)
    planCancelled = QtCore.Signal()

    def __init__(self, plan_text: str, user_request: str = "", parent=None):
        super().__init__(parent)
        self._plan_text = plan_text
        self._user_request = user_request
        self._steps = PlanStep.parse_plan(plan_text)
        self._edit_mode = False
        self._setup_ui()
        self._setup_entry_animation()

    def _setup_ui(self):
        """Set up the widget UI."""
        self.setObjectName("PlanWidget")
        self.setStyleSheet(f"""
            #PlanWidget {{
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
        header_layout.setSpacing(10)

        title_label = QtWidgets.QLabel("Execution Plan")
        title_label.setStyleSheet(f"""
            font-size: {Theme.FONTS['size_sm']};
            font-weight: {Theme.FONTS['weight_semibold']};
            color: {Theme.COLORS['accent_primary']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)

        # Step count badge
        count_label = QtWidgets.QLabel(f"{len(self._steps)} steps")
        count_label.setStyleSheet(f"""
            color: {Theme.COLORS['text_muted']};
            font-size: {Theme.FONTS['size_xs']};
            background: transparent;
        """)
        header_layout.addWidget(count_label)

        header_layout.addStretch()

        # Edit toggle button
        self._edit_btn = QtWidgets.QPushButton("Edit Plan")
        self._edit_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._edit_btn.setStyleSheet(f"""
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
        self._edit_btn.clicked.connect(self._toggle_edit_mode)
        header_layout.addWidget(self._edit_btn)

        layout.addLayout(header_layout)

        # Description
        desc_label = QtWidgets.QLabel("Review this plan before I generate the code:")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {Theme.COLORS['text_secondary']};
            font-size: {Theme.FONTS['size_base']};
            background: transparent;
        """)
        layout.addWidget(desc_label)

        # Steps container (shown in view mode)
        self._steps_frame = QtWidgets.QFrame()
        self._steps_frame.setStyleSheet(f"""
            background-color: rgba(0, 0, 0, 0.15);
            border-radius: {Theme.RADIUS['sm']};
        """)
        steps_layout = QtWidgets.QVBoxLayout(self._steps_frame)
        steps_layout.setContentsMargins(12, 10, 12, 10)
        steps_layout.setSpacing(8)

        for step in self._steps:
            step_widget = PlanStepWidget(step)
            steps_layout.addWidget(step_widget)

        # If no steps parsed, show raw plan
        if not self._steps:
            raw_label = QtWidgets.QLabel(self._plan_text)
            raw_label.setWordWrap(True)
            raw_label.setStyleSheet(f"""
                color: {Theme.COLORS['text_primary']};
                font-size: {Theme.FONTS['size_sm']};
                background: transparent;
            """)
            steps_layout.addWidget(raw_label)

        layout.addWidget(self._steps_frame)

        # Edit text area (hidden by default)
        self._edit_frame = QtWidgets.QFrame()
        self._edit_frame.setStyleSheet(f"""
            background-color: {Theme.COLORS['code_bg']};
            border-radius: {Theme.RADIUS['sm']};
            border: 1px solid {Theme.COLORS['code_border']};
        """)
        self._edit_frame.setVisible(False)

        edit_layout = QtWidgets.QVBoxLayout(self._edit_frame)
        edit_layout.setContentsMargins(10, 10, 10, 10)

        self._edit_text = QtWidgets.QTextEdit()
        self._edit_text.setPlainText(self._plan_text)
        self._edit_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {Theme.COLORS['text_primary']};
                border: none;
                font-family: {Theme.FONTS['family_mono']};
                font-size: {Theme.FONTS['size_sm']};
            }}
        """)
        self._edit_text.setMinimumHeight(120)
        edit_layout.addWidget(self._edit_text)

        layout.addWidget(self._edit_frame)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)

        # Cancel button
        self._cancel_btn = QtWidgets.QPushButton("Cancel")
        self._cancel_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet(f"""
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
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        btn_layout.addStretch()

        # Approve button
        self._approve_btn = QtWidgets.QPushButton("Approve Plan")
        self._approve_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._approve_btn.setStyleSheet(f"""
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
        """)
        self._approve_btn.clicked.connect(self._on_approve)
        btn_layout.addWidget(self._approve_btn)

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

    def _toggle_edit_mode(self):
        """Toggle between view and edit mode."""
        self._edit_mode = not self._edit_mode
        self._steps_frame.setVisible(not self._edit_mode)
        self._edit_frame.setVisible(self._edit_mode)
        self._edit_btn.setText("View Plan" if self._edit_mode else "Edit Plan")

        if self._edit_mode:
            # Update approve button text
            self._approve_btn.setText("Approve Edited Plan")
        else:
            self._approve_btn.setText("Approve Plan")

    def _on_approve(self):
        """Handle approve button click."""
        if self._edit_mode:
            # User edited the plan
            edited_text = self._edit_text.toPlainText()
            self.planEdited.emit(edited_text)
        else:
            # User approved as-is
            self.planApproved.emit()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.planCancelled.emit()

    def set_disabled(self, disabled: bool):
        """Disable/enable the widget after approval/cancellation."""
        self.setEnabled(not disabled)
        if disabled:
            self.setStyleSheet(f"""
                #PlanWidget {{
                    background-color: {Theme.COLORS['bg_tertiary']};
                    border: 1px solid {Theme.COLORS['border_subtle']};
                    border-radius: {Theme.RADIUS['lg']};
                    opacity: 0.5;
                }}
            """)

    def get_plan_text(self) -> str:
        """Get current plan text (edited or original)."""
        if self._edit_mode:
            return self._edit_text.toPlainText()
        return self._plan_text
